#!/usr/bin/env python3

from __future__ import print_function

import sys
import math

import warnings

from gettext import gettext as _

# Set up logging
from qtvcp import logger
LOG = logger.getLogger(__name__)

from PyQt5.QtCore import pyqtSignal, QPoint, QSize, Qt, QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (QApplication, QHBoxLayout, QMessageBox, QSlider,
        QWidget)
try:
    from PyQt5.QtOpenGL import QGLWidget
except ImportError:
    LOG.critical("Qtvcp error with qt5_graphics - is package python3-pyqt5.qtopengl installed?")

LIB_GOOD = True
try:
    from OpenGL import GL
    from OpenGL import GLU
except ImportError:
    LOG.error('Qtvcp Error with graphics - is python3-openGL installed?')
    LIB_GOOD = False

if sys.version_info.major > 2:
    import gi
    gi.require_version('Pango', '1.0')
    from gi.repository import Pango
    import _thread
else:
    import pango
    import thread as _thread
    
import glnav
from rs274 import glcanon
from rs274 import interpret
import linuxcnc
import gcode

import time
import re
import tempfile
import shutil
import os

from qtvcp.widgets.fake_status import fakeStatus

###################################
# For stand alone window
###################################
class Window(QWidget):
    def __init__(self, inifile):
        super(Window, self).__init__()
        self.glWidget = Lcnc_3dGraphics()
  
        self.xSlider = self.createSlider()
        self.ySlider = self.createSlider()
        self.zSlider = self.createSlider()
        self.zoomSlider = self.createZoomSlider()

        self.xSlider.valueChanged.connect(self.glWidget.setXRotation)
        self.glWidget.xRotationChanged.connect(self.xSlider.setValue)
        self.ySlider.valueChanged.connect(self.glWidget.setYRotation)
        self.glWidget.yRotationChanged.connect(self.ySlider.setValue)
        self.zSlider.valueChanged.connect(self.glWidget.setZRotation)
        self.glWidget.zRotationChanged.connect(self.zSlider.setValue)
        self.zoomSlider.valueChanged.connect(self.glWidget.setZoom)

        mainLayout = QHBoxLayout()
        mainLayout.addWidget(self.glWidget)
        mainLayout.addWidget(self.xSlider)
        mainLayout.addWidget(self.ySlider)
        mainLayout.addWidget(self.zSlider)
        mainLayout.addWidget(self.zoomSlider)
        self.setLayout(mainLayout)
  
        self.xSlider.setValue(15 * 16)
        self.ySlider.setValue(345 * 16)
        self.zSlider.setValue(0 * 16)
        self.zSlider.setValue(10)

        self.setWindowTitle("Hello GL")
  
    def createSlider(self):
        slider = QSlider(Qt.Vertical)
  
        slider.setRange(0, 360 * 16)
        slider.setSingleStep(16)
        slider.setPageStep(15 * 16)
        slider.setTickInterval(15 * 16)
        slider.setTickPosition(QSlider.TicksRight)
  
        return slider

    def createZoomSlider(self):
        slider = QSlider(Qt.Vertical)
  
        slider.setRange(1, 1000000)
        slider.setSingleStep(1)
        slider.setPageStep(10)
        slider.setTickInterval(10)
        slider.setTickPosition(QSlider.TicksRight)
  
        return slider

#################
# Helper class
#################
class DummyProgress:
    def nextphase(self, unused): pass
    def progress(self): pass

class Progress:
    def __init__(self, phases, total):
        self.num_phases = phases
        self.phase = 0
        self.total = total or 1
        self.lastcount = 0
        self.text = None

    def update(self, count, force=0):
        if force or count - self.lastcount > 400:
            fraction = (self.phase + count * 1. / self.total) / self.num_phases
            self.lastcount = count
            self.emit_percent(int(fraction *100))

    # this is class patched
    def emit_percent(self, percent):
        pass

    def nextphase(self, total):
        self.phase += 1
        self.total = total or 1
        self.lastcount = -100
        self.update(0, True)

    def done(self):
        self.emit_percent(-1)

    # not sure if this is used - copied from AXIS code
    def set_text(self, text):
        if self.text is None:
            self.text = ".info.progress"
        else:
            print(".info.progress", text)

class StatCanon(glcanon.GLCanon, interpret.StatMixin):
    def __init__(self, colors, geometry, lathe_view_option, stat, random, text, linecount, progress, arcdivision):
        glcanon.GLCanon.__init__(self, colors, geometry)
        interpret.StatMixin.__init__(self, stat, random)
        self.lathe_view_option = lathe_view_option
        self.text = text
        self.linecount = linecount
        self.progress = progress
        self.aborted = False
        self.arcdivision = arcdivision

    def is_lathe(self): return self.lathe_view_option

    def change_tool(self, pocket):
        glcanon.GLCanon.change_tool(self,pocket)
        interpret.StatMixin.change_tool(self,pocket)

    # not sure if this is used - copied from AXIS code
    def do_cancel(self, event):
        self.aborted = True

    # not sure if this is used - copied from AXIS code
    def check_abort(self):
        #root_window.update()
        if self.aborted: raise KeyboardInterrupt

    def next_line(self, st):
        glcanon.GLCanon.next_line(self, st)
        self.progress.update(self.lineno)
        # not sure if this is used - copied from AXIS code
        if self.notify:
            print("info",self.notify_message)
            self.notify = 0

###############################
# widget for graphics plotting
###############################
class Lcnc_3dGraphics(QGLWidget,  glcanon.GlCanonDraw, glnav.GlNavBase):
    percentLoaded = pyqtSignal(int)
    xRotationChanged = pyqtSignal(int)
    yRotationChanged = pyqtSignal(int)
    zRotationChanged = pyqtSignal(int)
    rotation_vectors = [(1.,0.,0.), (0., 0., 1.)]

    def __init__(self, parent=None):
        super(Lcnc_3dGraphics,self).__init__(parent)
        glnav.GlNavBase.__init__(self)

        def C(s):
            a = self.colors[s + "_alpha"]
            s = self.colors[s]
            return [int(x * 255) for x in s + (a,)]
        # requires linuxcnc running before laoding this widget
        inifile = os.environ.get('INI_FILE_NAME', '/dev/null')

        # if status is not available then we are probably
        # displaying in designer so fake it
        stat = linuxcnc.stat()
        try:
            stat.poll()
        except:
            LOG.warning('linuxcnc staus failed, Assuming linuxcnc is not running so using fake status for a XYZ machine')
            stat = fakeStatus()

        self.inifile = linuxcnc.ini(inifile)
        self.logger = linuxcnc.positionlogger(linuxcnc.stat(),
            C('backplotjog'),
            C('backplottraverse'),
            C('backplotfeed'),
            C('backplotarc'),
            C('backplottoolchange'),
            C('backplotprobing'),
            self.get_geometry()
        )
        # start tracking linuxcnc position so we can plot it
        _thread.start_new_thread(self.logger.start, (.01,))
        glcanon.GlCanonDraw.__init__(self, stat, self.logger)

        # set defaults
        self.current_view = 'p'
        self.fingerprint = ()
        self.select_primed = None
        self.lat = 0
        self.minlat = -90
        self.maxlat = 90

        self._current_file = None
        self.highlight_line = None
        self.program_alpha = False
        self.use_joints_mode = False
        self.use_commanded = True
        self.show_limits = True
        self.show_extents_option = True
        self.gcode_properties = None
        self.show_live_plot = True
        self.show_velocity = True
        self.metric_units = True
        self.show_program = True
        self.show_rapids = True
        self.use_relative = True
        self.show_tool = True
        self.show_dtg = True
        self.grid_size = 0.0
        temp = self.inifile.find("DISPLAY", "LATHE")
        self.lathe_option = bool(temp == "1" or temp == "True" or temp == "true" )
        self.foam_option = bool(self.inifile.find("DISPLAY", "FOAM"))
        self.show_offsets = False
        self.show_overlay = False
        self.enable_dro = False
        self.use_default_controls = True
        self.mouse_btn_mode = 0
        self.cancel_rotate = False
        self.use_gradient_background = False
        self.gradient_color1 = (0.0, 0.0, 1)
        self.gradient_color2 = (0.0, 0.0, 0.0)
        self.a_axis_wrapped = self.inifile.find("AXIS_A", "WRAPPED_ROTARY")
        self.b_axis_wrapped = self.inifile.find("AXIS_B", "WRAPPED_ROTARY")
        self.c_axis_wrapped = self.inifile.find("AXIS_C", "WRAPPED_ROTARY")

        live_axis_count = 0
        for i,j in enumerate("XYZABCUVW"):
            if self.stat.axis_mask & (1<<i) == 0: continue
            live_axis_count += 1
        self.num_joints = int(self.inifile.find("KINS", "JOINTS") or live_axis_count)

        self.object = 0
        self.xRot = 0
        self.yRot = 0
        self.zRot = 0
  
        # add a 100ms timer to poll linuxcnc stats
        self.timer = QTimer()
        self.timer.timeout.connect(self.poll)
        self.timer.start(100)

        self.Green = QColor.fromCmykF(0.40, 0.0, 1.0, 0.0)
        self.inhibit_selection = True

    def poll(self):
        s = self.stat
        try:
            s.poll()
        except:
            return
        fingerprint = (self.logger.npts, self.soft_limits(),
            s.actual_position, s.joint_actual_position,
            s.homed, s.g5x_offset, s.g92_offset, s.limit, s.tool_in_spindle,
            s.motion_mode, s.current_vel)

        if fingerprint != self.fingerprint:
            self.fingerprint = fingerprint
            self.update()
        return True

    # when shown make sure display is set to the default view
    def showEvent(self, event):
        super(Lcnc_3dGraphics ,self).showEvent(event)
        self.set_current_view()

    def load(self,filename = None):
        s = self.stat
        s.poll()
        if not filename and s.file:
            filename = s.file
        elif not filename and not s.file:
            return


        lines = open(filename).readlines()
        progress = Progress(2, len(lines))
        progress.emit_percent = self.emit_percent

        code = []
        i = 0
        for i, l in enumerate(lines):
            l = l.expandtabs().replace("\r", "")
            code.extend(["%6d: " % (i+1), "lineno", l, ""])
            if i % 1000 == 0:
                del code[:]
                progress.update(i)
        if code:
            pass
        progress.nextphase(len(lines))


        td = tempfile.mkdtemp()
        self._current_file = filename
        try:
            random = int(self.inifile.find("EMCIO", "RANDOM_TOOLCHANGER") or 0)
            arcdivision = int(self.inifile.find("DISPLAY", "ARCDIVISION") or 64)
            text = ''
            canon = StatCanon(self.colors, self.get_geometry(),self.lathe_option, s, text, random, i, progress, arcdivision)
            parameter = self.inifile.find("RS274NGC", "PARAMETER_FILE")
            temp_parameter = os.path.join(td, os.path.basename(parameter or "linuxcnc.var"))
            if parameter:
                shutil.copy(parameter, temp_parameter)
            canon.parameter_file = temp_parameter
            unitcode = "G%d" % (20 + (s.linear_units == 1))
            initcode = self.inifile.find("RS274NGC", "RS274NGC_STARTUP_CODE") or ""
            result, seq = self.load_preview(filename, canon, unitcode, initcode)
            if result > gcode.MIN_ERROR:
                self.report_gcode_error(result, seq, filename)
            self.calculate_gcode_properties(canon)
        except Exception as e:
            print (e)
            self.gcode_properties = None
        finally:
            shutil.rmtree(td)
            if canon:
                canon.progress = DummyProgress()
            try:
                progress.done()
            except UnboundLocalError:
                pass
        self._redraw()

    def emit_percent(self, percent):
        self.percentLoaded.emit(percent)

    def calculate_gcode_properties(self, canon):
        def dist(point1, point2):
            (x, y, z) = point1
            (p, q, r) = point2
            return ((x-p)**2 + (y-q)**2 + (z-r)**2) ** .5

        def from_internal_units(pos, unit=None):
            if unit is None:
                unit = self.stat.linear_units
            lu = (unit or 1) * 25.4

            lus = [lu, lu, lu, 1, 1, 1, lu, lu, lu]
            return [aa*bb for aa, bb in zip(pos, lus)]

        def from_internal_linear_unit(v, unit=None):
            if unit is None:
                unit = self.stat.linear_units
            lu = (unit or 1) * 25.4
            return v*lu

        props = {}
        loaded_file = self._current_file
        max_speed = float(
            self.inifile.find("DISPLAY","MAX_LINEAR_VELOCITY")
            or self.inifile.find("TRAJ","MAX_LINEAR_VELOCITY")
            or self.inifile.find("AXIS_X","MAX_VELOCITY")
            or 1)

        if not loaded_file:
            props['name'] = _("No file loaded")
        else:
            ext = os.path.splitext(loaded_file)[1]
            program_filter = None
            if ext:
                program_filter = self.inifile.find("FILTER", ext[1:])
            name = os.path.basename(loaded_file)
            if program_filter:
                props['name'] = _("generated from %s") % name
            else:
                props['name'] = name

            size = os.stat(loaded_file).st_size
            lines = sum(1 for line in open(loaded_file))
            props['size'] = _("%(size)s bytes\n%(lines)s gcode lines") % {'size': size, 'lines': lines}

            if self.metric_units:
                conv = 1
                units = "mm"
                fmt = "%.3f"
            else:
                conv = 1/25.4
                units = "in"
                fmt = "%.4f"

            mf = max_speed
            #print canon.traverse[0]

            g0 = sum(dist(l[1][:3], l[2][:3]) for l in canon.traverse)
            g1 = (sum(dist(l[1][:3], l[2][:3]) for l in canon.feed) +
                sum(dist(l[1][:3], l[2][:3]) for l in canon.arcfeed))
            gt = (sum(dist(l[1][:3], l[2][:3])/min(mf, l[3]) for l in canon.feed) +
                sum(dist(l[1][:3], l[2][:3])/min(mf, l[3])  for l in canon.arcfeed) +
                sum(dist(l[1][:3], l[2][:3])/mf  for l in canon.traverse) +
                canon.dwell_time
                )
 
            props['G0'] = "%f %s".replace("%f", fmt) % (from_internal_linear_unit(g0, conv), units)
            props['gG1'] = "%f %s".replace("%f", fmt) % (from_internal_linear_unit(g1, conv), units)
            if gt > 120:
                props['Run'] = _("%.1f Minutes") % (gt/60)
            else:
                props['Run'] = _("%d Ceconds") % (int(gt))

            min_extents = from_internal_units(canon.min_extents, conv)
            max_extents = from_internal_units(canon.max_extents, conv)
            for (i, c) in enumerate("XYZ"):
                a = min_extents[i]
                b = max_extents[i]
                if a != b:
                    props[c] = _("%(a)f to %(b)f = %(diff)f %(units)s").replace("%f", fmt) % {'a': a, 'b': b, 'diff': b-a, 'units': units}
            props['Units'] = units
        self.gcode_properties = props

    # setup details when window shows
    def realize(self):
        self.set_current_view()
        s = self.stat
        try:
            s.poll()
        except:
            return
        self._current_file = None

        self.font_base, width, linespace = glnav.use_pango_font('courier bold 16', 0, 128)
        self.font_linespace = linespace
        self.font_charwidth = width
        glcanon.GlCanonDraw.realize(self)
        if s.file: self.load()

    # gettter / setters
    def get_font_info(self):
        return self.font_charwidth, self.font_linespace, self.font_base
    def get_program_alpha(self): return self.program_alpha
    def get_joints_mode(self): return self.use_joints_mode
    def get_show_commanded(self): return self.use_commanded
    def get_show_extents(self): return self.show_extents_option
    def get_gcode_properties(self): return self.gcode_properties
    def get_show_limits(self): return self.show_limits
    def get_show_live_plot(self): return self.show_live_plot
    def get_show_machine_speed(self): return self.show_velocity
    def get_show_metric(self): return self.metric_units
    def get_show_program(self): return self.show_program
    def get_show_rapids(self): return self.show_rapids
    def get_show_relative(self): return self.use_relative
    def get_show_tool(self): return self.show_tool
    def get_show_distance_to_go(self): return self.show_dtg
    def get_grid_size(self): return self.grid_size
    def get_show_offsets(self): return self.show_offsets
    def get_view(self):
        view_dict = {'x':0, 'y':1, 'y2':1, 'z':2, 'z2':2, 'p':3}
        return view_dict.get(self.current_view, 3)
    def get_geometry(self):
        temp = self.inifile.find("DISPLAY", "GEOMETRY")
        if temp:
            _geometry = re.split(" *(-?[XYZABCUVW])", temp.upper())
            self._geometry = "".join(reversed(_geometry))
        else:
            self._geometry = 'XYZ'
        return self._geometry
    def is_lathe(self): return self.lathe_option
    def is_foam(self): return self.foam_option
    def get_current_tool(self):
        for i in self.stat.tool_table:
            if i[0] == self.stat.tool_in_spindle:
                return i
    def get_highlight_line(self): return self.highlight_line
    def get_a_axis_wrapped(self): return self.a_axis_wrapped
    def get_b_axis_wrapped(self): return self.b_axis_wrapped
    def get_c_axis_wrapped(self): return self.c_axis_wrapped
    def set_current_view(self):
        if self.current_view not in ['p', 'x', 'y', 'y2', 'z', 'z2']:
            return
        return getattr(self, 'set_view_%s' % self.current_view)()
    def clear_live_plotter(self):
        self.logger.clear()
        self.update()

    def winfo_width(self):
        return self.geometry().width()

    def winfo_height(self):
        return self.geometry().height()

    # trick - we are not gtk
    def activate(self):
        return
    def deactivate(self):
        return
    def swapbuffers(self):
        return
    # redirect for conversion from pygtk to pyqt
    # gcannon assumes this function name
    def _redraw(self):
        self.updateGL()

    # This overrides glcannon.py method so we can change the DRO 
    def dro_format(self,s,spd,dtg,limit,homed,positions,axisdtg,g5x_offset,g92_offset,tlo_offset):
            if not self.enable_dro:
                return limit, homed, [''], ['']

            if self.metric_units:
                format = "% 6s:% 9.3f"
                if self.show_dtg:
                    droformat = " " + format + "  DTG %1s:% 9.3f"
                else:
                    droformat = " " + format
                offsetformat = "% 5s %1s:% 9.3f  G92 %1s:% 9.3f"
                rotformat = "% 5s %1s:% 9.3f"
            else:
                format = "% 6s:% 9.4f"
                if self.show_dtg:
                    droformat = " " + format + "  DTG %1s:% 9.4f"
                else:
                    droformat = " " + format
                offsetformat = "% 5s %1s:% 9.4f  G92 %1s:% 9.4f"
                rotformat = "% 5s %1s:% 9.4f"
            diaformat = " " + format

            posstrs = []
            droposstrs = []
            for i in range(9):
                a = "XYZABCUVW"[i]
                if s.axis_mask & (1<<i):
                    posstrs.append(format % (a, positions[i]))
                    if self.show_dtg:
                        droposstrs.append(droformat % (a, positions[i], a, axisdtg[i]))
                    else:
                        droposstrs.append(droformat % (a, positions[i]))
            droposstrs.append("")

            for i in range(9):
                index = s.g5x_index
                if index<7:
                    label = "G5%d" % (index+3)
                else:
                    label = "G59.%d" % (index-6)

                a = "XYZABCUVW"[i]
                if s.axis_mask & (1<<i):
                    droposstrs.append(offsetformat % (label, a, g5x_offset[i], a, g92_offset[i]))
            droposstrs.append(rotformat % (label, 'R', s.rotation_xy))

            droposstrs.append("")
            for i in range(9):
                a = "XYZABCUVW"[i]
                if s.axis_mask & (1<<i):
                    droposstrs.append(rotformat % ("TLO", a, tlo_offset[i]))

            # if its a lathe only show radius or diameter as per property
            if self.is_lathe():
                posstrs[0] = ""
                if self.show_lathe_radius:
                    posstrs.insert(1, format % ("Rad", positions[0]))
                else:
                    posstrs.insert(1, format % ("Dia", positions[0]*2.0))
                droposstrs[0] = ""
                if self.show_dtg:
                    if self.show_lathe_radius:
                        droposstrs.insert(1, droformat % ("Rad", positions[0], "R", axisdtg[0]))
                    else:
                        droposstrs.insert(1, droformat % ("Dia", positions[0]*2.0, "D", axisdtg[0]*2.0))
                else:
                    if self.show_lathe_radius:
                        droposstrs.insert(1, droformat % ("Rad", positions[0]))
                    else:
                        droposstrs.insert(1, diaformat % ("Dia", positions[0]*2.0))

            if self.show_velocity:
                posstrs.append(format % ("Vel", spd))
                pos=0
                for i in range(9):
                    if s.axis_mask & (1<<i): pos +=1
                if self.is_lathe:
                    pos +=1
                droposstrs.insert(pos, " " + format % ("Vel", spd))

            if self.show_dtg:
                posstrs.append(format % ("DTG", dtg))
            return limit, homed, posstrs, droposstrs

    def minimumSizeHint(self):
        return QSize(50, 50)

    def sizeHint(self):
        return QSize(400, 400)

    def normalizeAngle(self, angle):
        while angle < 0:
            angle += 360 * 16
        while angle > 360 * 16:
            angle -= 360 * 16
        return angle

    def setXRotation(self, angle):
        angle = self.normalizeAngle(angle)
        if angle != self.xRot:
            self.xRot = angle
            self.xRotationChanged.emit(angle)
            self.updateGL()

    def setYRotation(self, angle):
        angle = self.normalizeAngle(angle)
        if angle != self.yRot:
            self.yRot = angle
            self.yRotationChanged.emit(angle)
            self.updateGL()

    def setZRotation(self, angle):
        angle = self.normalizeAngle(angle)
        if angle != self.zRot:
            self.zRot = angle
            self.zRotationChanged.emit(angle)
            self.updateGL()

    def setZoom(self, zoom):
        self.distance = zoom/100.0
        self.updateGL()

    # called when widget is completely redrawn
    def initializeGL(self):
        self.object = self.makeObject()
        self.realize()
        GL.glEnable(GL.GL_CULL_FACE)
        return

    # redraws the screen aprox every 100ms
    def paintGL(self):
        #GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        #GL.glLoadIdentity() # reset the model-view matrix
        #GL.glTranslated(0.0, 0.0, -10.0)
        #GL.glRotated(self.xRot / 16.0, 1.0, 0.0, 0.0) # rotate on x
        #GL.glRotated(self.yRot / 16.0, 0.0, 1.0, 0.0) # rotate on y
        #GL.glRotated(self.zRot / 16.0, 0.0, 0.0, 1.0) # rotate on z

        
        try:
            if self.perspective:
                self.redraw_perspective()
            else:
                self.redraw_ortho()

        except Exception as e:
            #print'error',e
            return
            #genList = GL.glGenLists(1)
            #self.draw_small_origin(genList)
            #GL.glCallList(genList)
            # display something - probably in QtDesigner
            # GL.glCallList(self.object)

    # replaces glcanoon function
    def redraw_perspective(self):

        w = self.winfo_width()
        h = self.winfo_height()
        GL.glViewport(0, 0, w, h) # left corner in pixels
        if self.use_gradient_background:
                GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
                ###
                GL.glMatrixMode(GL.GL_PROJECTION)
                GL.glLoadIdentity() # switch to identity (origin) matrix

                GL.glMatrixMode(GL.GL_MODELVIEW)
                GL.glPushMatrix()
                GL.glPushMatrix()
                GL.glLoadIdentity()

                GL.glDisable(GL.GL_DEPTH_TEST)
                GL.glBegin(GL.GL_QUADS)
                #//bottom color
                color = self.gradient_color1
                GL.glColor3f(color[0],color[1],color[2])
                GL.glVertex2f(-1.0, -1.0)
                GL.glVertex2f(1.0, -1.0)
                #//top color
                color = self.gradient_color2
                GL.glColor3f(color[0],color[1],color[2])
                GL.glVertex2f(1.0, 1.0)
                GL.glVertex2f(-1.0, 1.0)
                GL.glEnd()
                GL.glEnable(GL.GL_DEPTH_TEST)

                GL.glPopMatrix()
                GL.glPopMatrix()

        else:
            # Clear the background and depth buffer.
            GL.glClearColor(*(self.colors['back'] + (0,)))
            GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)

        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        GLU.gluPerspective(self.fovy,               # The vertical Field of View, in radians: the amount of "zoom".
                                                    # Think "camera lens". Usually between 90 (extra wide) and 30 (quite zoomed in)
                        float(w)/float(h),          # Aspect Ratio. Notice that 4/3 == 800/600 screen resolution
                        self.near,                  # near clipping plane. Keep as big as possible, or you'll get precision issues.
                        self.far + self.distance)   # Far clipping plane. Keep as little as possible.
        GLU.gluLookAt(0, 0, self.distance,  # the position of your camera, in world space
            0, 0, 0,                        # where you want to look at, in world space
            0., 1., 0.)                     # probably glm::vec3(0,1,0), but (0,-1,0) would make you looking upside-down
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glPushMatrix()
        try:
            self.redraw()
        finally:
            GL.glFlush()                               # Tidy up
            GL.glPopMatrix()                   # Restore the matrix

    # replaces glcanoon function
    def redraw_ortho(self):
        if not self.initialised: return
        w = self.winfo_width()
        h = self.winfo_height()
        GL.glViewport(0, 0, w, h)
        if self.use_gradient_background:
            GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
            GL.glMatrixMode(GL.GL_PROJECTION)
            GL.glLoadIdentity()

            GL.glMatrixMode(GL.GL_MODELVIEW)
            GL.glPushMatrix()
            GL.glPushMatrix()
            GL.glLoadIdentity()

            GL.glDisable(GL.GL_DEPTH_TEST)
            GL.glBegin(GL.GL_QUADS)
            #//bottom color
            color = self.gradient_color1
            GL.glColor3f(color[0],color[1],color[2])
            GL.glVertex2f(-1.0, -1.0)
            GL.glVertex2f(1.0, -1.0)
            #//top color
            color = self.gradient_color2
            GL.glColor3f(color[0],color[1],color[2])
            GL.glVertex2f(1.0, 1.0)
            GL.glVertex2f(-1.0, 1.0)
            GL.glEnd()
            GL.glEnable(GL.GL_DEPTH_TEST)

            GL.glPopMatrix()
            GL.glPopMatrix()

        else:
            # Clear the background and depth buffer.
            GL.glClearColor(*(self.colors['back'] + (0,)))
            GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)

        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        ztran = self.distance
        k = (abs(ztran or 1)) ** .55555
        l = k * h / w
        GL.glOrtho(-k, k, -l, l, -1000, 1000.)
        GLU.gluLookAt(0, 0, 1,
            0, 0, 0,
            0., 1., 0.)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glPushMatrix()
        try:
            self.redraw()
        finally:
            GL.glFlush()                               # Tidy up
            GL.glPopMatrix()                   # Restore the matrix

    # resizes the view to fit the window
    def resizeGL(self, width, height):
        side = min(width, height)
        if side < 0:
            return
        GL.glViewport((width - side) // 2, (height - side) // 2, side, side)
        GL.glMatrixMode(GL.GL_PROJECTION) # To operate on projection-view matrix
        GL.glLoadIdentity() # reset the model-view matrix
        GL.glOrtho(-0.5, +0.5, +0.5, -0.5, 4.0, 15.0)
        GL.glMatrixMode(GL.GL_MODELVIEW) # To operate on model-view matrix

    ####################################
    # Property setting functions
    ####################################
    def set_alpha_mode(self, state):
        self.program_alpha = state
        self.updateGL()

    def set_inhibit_selection(self, state):
        self.inhibit_selection = state

    ####################################
    # view controls
    ####################################
    def set_prime(self, x, y):
        if self.select_primed:
            primedx, primedy = self.select_primed
            distance = max(abs(x - primedx), abs(y - primedy))
            if distance > 8: self.select_cancel()

    def select_prime(self, x, y):
        self.select_primed = x, y

    # TODO This return statement breaks segment picking on the screen but
    # Also stop the display from pausing plotting update while searching
    # probably needs a thread - strange that Tkinter and GTK don't suffer...
    def select_fire(self):
        if self.inhibit_selection: return
        if not self.select_primed: return
        x, y = self.select_primed
        self.select_primed = None
        self.select(x, y)

    def select_cancel(self, widget=None, event=None):
        self.select_primed = None

    def wheelEvent(self, _event):
        # Use the mouse wheel to zoom in/out
        a = _event.angleDelta().y()/200
        if a < 0:
            self.zoomout()
        else:
            self.zoomin()
        _event.accept()

    def mousePressEvent(self, event):
        if (event.buttons() & Qt.LeftButton):
            self.select_prime(event.pos().x(), event.pos().y())
            #print self.winfo_width()/2 - event.pos().x(), self.winfo_height()/2 - event.pos().y()
        self.recordMouse(event.pos().x(), event.pos().y())
        self.startZoom(event.pos().y())

    # event.buttons = current button state
    # event_button  = event causing button
    def mouseReleaseEvent(self, event):
        if event.button() & Qt.LeftButton:
            self.select_fire()

    def mouseDoubleClickEvent(self, event):
        if event.button() & Qt.RightButton:
            self.logger.clear()

    def mouseMoveEvent(self, event):
        # move
        if event.buttons() & Qt.LeftButton:
            self.translateOrRotate(event.pos().x(), event.pos().y())
        # rotate
        elif event.buttons() & Qt.RightButton:
            if not self.cancel_rotate:
                self.set_prime(event.pos().x(), event.pos().y())
                self.rotateOrTranslate(event.pos().x(), event.pos().y())
        # zoom
        elif event.buttons() & Qt.MiddleButton:
            self.continueZoom(event.pos().y())

    def user_plot(self):
        pass
        #GL.glCallList(self.object)

    def panView(self,vertical=0,horizontal=0):
        self.translateOrRotate(self.xmouse + vertical, self.ymouse + horizontal)

    def rotateView(self,vertical=0,horizontal=0):
        self.rotateOrTranslate(self.xmouse + vertical, self.ymouse + horizontal)

    ############################################################
    # display for when linuxcnc isn't runnimg - forQTDesigner
    ############################################################
    def makeObject(self):
        genList = GL.glGenLists(1)
        GL.glNewList(genList, GL.GL_COMPILE)
  
        GL.glBegin(GL.GL_QUADS)
        factor = 4
        # Make a tee section
        x1 = +0.06 * factor
        y1 = -0.14 * factor
        x2 = +0.14 * factor
        y2 = -0.06 * factor
        x3 = +0.08 * factor
        y3 = +0.00 * factor
        x4 = +0.30 * factor
        y4 = +0.22 * factor

        # cross
        self.quad(x1, y1, x2, y2, y2, x2, y1, x1, z= .05, color = self.Green)
        # vertical line
        self.quad(x3, y3, x4, y4, y4, x4, y3, x3, z= .05, color = self.Green)

        # cross depth
        self.extrude(x1, y1, x2, y2, z= .05, color = self.Green)
        self.extrude(x2, y2, y2, x2, z= .05, color = self.Green)
        self.extrude(y2, x2, y1, x1, z= .05, color = self.Green)
        self.extrude(y1, x1, x1, y1, z= .05, color = self.Green)

        # vertical depth
        self.extrude(x3, y3, x4, y4, z= .05, color = self.Green)
        self.extrude(x4, y4, y4, x4, z= .05, color = self.Green)
        self.extrude(y4, x4, y3, x3, z= .05, color = self.Green)
  
        NumSectors = 200
  
        # Make a circle
        for i in range(NumSectors):
            angle1 = (i * 2 * math.pi) / NumSectors
            x5 = 0.30 * math.sin(angle1) * factor
            y5 = 0.30 * math.cos(angle1) * factor
            x6 = 0.20 * math.sin(angle1) * factor
            y6 = 0.20 * math.cos(angle1) * factor
  
            angle2 = ((i + 1) * 2 * math.pi) / NumSectors
            x7 = 0.20 * math.sin(angle2) * factor
            y7 = 0.20 * math.cos(angle2) * factor
            x8 = 0.30 * math.sin(angle2) * factor
            y8 = 0.30 * math.cos(angle2) * factor
  
            self.quad(x5, y5, x6, y6, x7, y7, x8, y8, z= .05, color = self.Green)
  
            self.extrude(x6, y6, x7, y7, z= .05, color = self.Green)
            self.extrude(x8, y8, x5, y5, z= .05, color = self.Green)
  
        GL.glEnd()
        GL.glEndList()
  
        return genList
  
    def quad(self, x1, y1, x2, y2, x3, y3, x4, y4, z, color):
        self.qglColor(color)
  
        GL.glVertex3d(x1, y1, -z)
        GL.glVertex3d(x2, y2, -z)
        GL.glVertex3d(x3, y3, -z)
        GL.glVertex3d(x4, y4, -z)
  
        GL.glVertex3d(x4, y4, +z)
        GL.glVertex3d(x3, y3, +z)
        GL.glVertex3d(x2, y2, +z)
        GL.glVertex3d(x1, y1, +z)

    def lathe_quad(self, x1, x2, x3, x4, z1, z2, z3, z4, color):
        self.qglColor(color)
  
        GL.glVertex3d(x1, 0, z1)
        GL.glVertex3d(x2, 0, z2)
        GL.glVertex3d(x3, 0, z3)
        GL.glVertex3d(x4, 0, z4)

        # defeat back face cull
        GL.glVertex3d(x4, 0, z4)
        GL.glVertex3d(x3, 0, z3)
        GL.glVertex3d(x2, 0, z2)
        GL.glVertex3d(x1, 0, z1)

    def extrude(self, x1, y1, x2, y2, z, color):
        self.qglColor(color)
  
        GL.glVertex3d(x1, y1, +z)
        GL.glVertex3d(x2, y2, +z)
        GL.glVertex3d(x2, y2, -z)
        GL.glVertex3d(x1, y1, -z)

###########
# Testing
###########
if __name__ == '__main__':

    app = QApplication(sys.argv)
    if len(sys.argv) == 1:
        inifilename = None
    elif len(sys.argv) == 2:
        inifilename = sys.argv[1]
    else:
        os.open('usage()')
    window = Window(inifilename)
    window.show()
    sys.exit(app.exec_())
  

