import os
import time

class INI:
    def __init__(self,app):
        # access to:
        self.d = app.d  # collected data
        global SIG
        SIG = app._p    # private data (signals names)
        global _PD
        _PD = app._p    # private data
        self.a = app    # The parent, pncconf

    def write_inifile(self, base):
        filename = os.path.join(base, self.d.machinename + ".ini")
        file = open(filename, "w")
        print >>file, _("# Generated by PNCconf at %s") % time.asctime()
        print >>file, _("# If you make changes to this file, they will be")
        print >>file, _("# overwritten when you run PNCconf again")
        
        print >>file
        print >>file, "[EMC]"
        print >>file, "MACHINE = %s" % self.d.machinename
        print >>file, "DEBUG = 0"

        # the joints_axes conversion script named 'update_ini'
        # will try to update for joints_axes if no VERSION is set
        print >>file, "VERSION = 1.0"

        print >>file
        print >>file, "[DISPLAY]"
        if self.d.frontend == _PD._AXIS:
            print >>file, "DISPLAY = axis"
        elif self.d.frontend == _PD._TKLINUXCNC:
            print >>file, "DISPLAY = tklinuxcnc"
        elif self.d.frontend == _PD._GMOCCAPY:
            print >>file, "DISPLAY = gmoccapy"
        elif self.d.frontend == _PD._TOUCHY:
            print >>file, "DISPLAY = touchy"
        if self.d.gladevcp:
            theme = self.d.gladevcptheme
            if theme == "Follow System Theme":theme = ""
            else: theme = " -t "+theme
            if self.d.frontend in(_PD._AXIS, _PD._TOUCHY):
                if self.d.centerembededgvcp:
                    print >>file, "EMBED_TAB_NAME = GladeVCP"
                    print >>file, "EMBED_TAB_COMMAND = halcmd loadusr -Wn gladevcp gladevcp -c gladevcp%s -H gvcp_call_list.hal -x {XID} gvcp-panel.ui"%(theme)
                elif self.d.sideembededgvcp:
                    print >>file, "GLADEVCP =%s -H gvcp_call_list.hal gvcp-panel.ui"%(theme)
            elif self.d.frontend == _PD._GMOCCAPY:
                if self.d.centerembededgvcp:
                    print >>file, "EMBED_TAB_NAME = Center_panel"
                    print >>file, "EMBED_TAB_LOCATION = ntb_preview"
                elif self.d.sideembededgvcp:
                    print >>file, "EMBED_TAB_NAME = Right Panel"
                    print >>file, "EMBED_TAB_LOCATION = box_right"
                else:
                    print >>file, "EMBED_TAB_NAME = User Panel"
                    print >>file, "EMBED_TAB_LOCATION = ntb_user_tabs"
                print >>file, "EMBED_TAB_COMMAND = gladevcp -c gladevcp %s -H gvcp_call_list.hal -x {XID} gvcp-panel.ui"%(theme)

        if self.d.position_offset == 1: temp ="RELATIVE"
        else: temp = "MACHINE"
        print >>file, "POSITION_OFFSET = %s"% temp
        if self.d.position_feedback == 1: temp ="ACTUAL"
        else: temp = "COMMANDED"
        print >>file, "POSITION_FEEDBACK = %s"% temp
        print >>file, "MAX_FEED_OVERRIDE = %f"% self.d.max_feed_override
        print >>file, "MAX_SPINDLE_OVERRIDE = %f"% self.d.max_spindle_override
        print >>file, "MIN_SPINDLE_OVERRIDE = %f"% self.d.min_spindle_override
        print >>file, "INTRO_GRAPHIC = linuxcnc.gif"
        print >>file, "INTRO_TIME = 5"
        print >>file, "PROGRAM_PREFIX = %s" % \
                                    os.path.expanduser("~/linuxcnc/nc_files")
        if self.d.pyvcp:
            print >>file, "PYVCP = pyvcp-panel.xml"
        # these are for AXIS GUI only
        if self.d.units == _PD._METRIC:
            print >>file, "INCREMENTS = %s"% self.d.increments_metric
        else:
            print >>file, "INCREMENTS = %s"% self.d.increments_imperial
        if self.d.axes == 2:
            print >>file, "LATHE = 1"
        print >>file, "POSITION_FEEDBACK = %s"% temp
        print >>file, "DEFAULT_LINEAR_VELOCITY = %f"% self.d.default_linear_velocity
        print >>file, "MAX_LINEAR_VELOCITY = %f"% self.d.max_linear_velocity
        print >>file, "MIN_LINEAR_VELOCITY = %f"% self.d.min_linear_velocity
        print >>file, "DEFAULT_ANGULAR_VELOCITY = %f"% self.d.default_angular_velocity
        print >>file, "MAX_ANGULAR_VELOCITY = %f"% self.d.max_angular_velocity
        print >>file, "MIN_ANGULAR_VELOCITY = %f"% self.d.min_angular_velocity
        print >>file, "EDITOR = %s"% self.d.editor
        print >>file, "GEOMETRY = %s"% self.d.geometry 

        print >>file
        print >>file, "[FILTER]"
        print >>file, "PROGRAM_EXTENSION = .png,.gif,.jpg Greyscale Depth Image"
        print >>file, "PROGRAM_EXTENSION = .py Python Script"
        print >>file, "png = image-to-gcode"
        print >>file, "gif = image-to-gcode"
        print >>file, "jpg = image-to-gcode"
        print >>file, "py = python"        

        print >>file
        print >>file, "[TASK]"
        print >>file, "TASK = milltask"
        print >>file, "CYCLE_TIME = 0.010"

        print >>file
        print >>file, "[RS274NGC]"
        print >>file, "PARAMETER_FILE = linuxcnc.var"

        #base_period = self.d.ideal_period()

        print >>file
        print >>file, "[EMCMOT]"
        print >>file, "EMCMOT = motmod"
        print >>file, "COMM_TIMEOUT = 1.0"
        #print >>file, "BASE_PERIOD = %d" % self.d.baseperiod
        print >>file, "SERVO_PERIOD = %d" % self.d.servoperiod
        print >>file
        print >>file, "[HOSTMOT2]"
        print >>file, "# **** This is for info only ****"
        print >>file, "# DRIVER0=%s"% self.d.mesa0_currentfirmwaredata[_PD._HALDRIVER]
        print >>file, "# BOARD0=%s"% self.d.mesa0_currentfirmwaredata[_PD._BOARDNAME]
        if self.d.number_mesa == 2:
            print >>file, "# DRIVER1=%s" % self.d.mesa1_currentfirmwaredata[_PD._HALDRIVER]
            print >>file, "# BOARD1=%s"% self.d.mesa1_currentfirmwaredata[_PD._BOARDNAME]
        if self.d._substitution_list:
            print >>file, "# These are to ease setting custom component's parameters in a custom HAL file"
            print >>file
            for i,temp in enumerate(self.d._substitution_list):
                a,b = self.d._substitution_list[i]
                if a =="":
                    print >>file
                else:
                    print >>file,"%s=%s"%(a,b)
        print >>file
        print >>file, "[HAL]"
        print >>file, "HALUI = halui"          
        print >>file, "HALFILE = %s.hal" % self.d.machinename
        print >>file, "HALFILE = custom.hal"
        if self.d.frontend in( _PD._AXIS, _PD._GMOCCAPY):
            print >>file, "POSTGUI_HALFILE = postgui_call_list.hal"
        print >>file, "SHUTDOWN = shutdown.hal"
        print >>file
        print >>file, "[HALUI]"          
        if self.d.halui == True:
            for i in range(0,15):
                cmd =self.d["halui_cmd" + str(i)]
                if cmd =="": break
                print >>file,"MDI_COMMAND = %s"% cmd           

        # Build axis/joints info

        # add X axis
        num_joints = 1; coords = "X"; tandemflag = False
        tandemjoint = self.d.make_pinname(self.a.stepgen_sig("x2"))
        if tandemjoint:
            #add tandem to X
            tandemflag = True
            num_joints += 1
            coords += 'X'

        if self.d.axes in (0,1): # xyz or xyyza
            # add Y axis
            num_joints += 1
            coords += 'Y'
            tandemjoint = self.d.make_pinname(self.a.stepgen_sig("y2"))
            if tandemjoint:
                #add tandem to Y
                tandemflag = True
                num_joints += 1
                coords += 'Y'

        # add Z axis
        num_joints += 1
        coords += 'Z'
        tandemjoint = self.d.make_pinname(self.a.stepgen_sig("z2"))
        if tandemjoint:
            tandemflag = True
            num_joints += 1
            coords += 'Z'

        if self.d.axes == 1: # for xyza
            # add A axis 
            num_joints += 1
            coords += 'A'
            tandemjoint = self.d.make_pinname(self.a.stepgen_sig("a2"))
            if tandemjoint:
                # add tandem to A
                tandemflag = True
                num_joints += 1
                coords += 'A'
        if not self.d.axes in (0,1,2):
            print "___________________unknown self.d.axes",self.d.axes
            return
        print >>file
        print >>file,  "[KINS]"
        # trivial kinematics: no. of joints == no.of axes)
        # with trivkins, axes do not have to be consecutive
        print >>file, "JOINTS = %d"%num_joints
        if tandemflag:
            print >>file, "KINEMATICS = trivkins coordinates=%s kinstype=BOTH"%coords.replace(" ","")
        else:
            print >>file, "KINEMATICS = trivkins coordinates=%s"%coords.replace(" ","")
        print >>file
        print >>file, "[TRAJ]"
        print >>file, "COORDINATES = ",coords
        if self.d.axes == 1:
            print >>file, "MAX_ANGULAR_VELOCITY = %.2f" % self.d.amaxvel
            defvel = min(60, self.d.amaxvel/10.)
            print >>file, "DEFAULT_ANGULAR_VELOCITY = %.2f" % defvel
        if self.d.units == _PD._METRIC:
            print >>file, "LINEAR_UNITS = mm"
        else:
            print >>file, "LINEAR_UNITS = inch"
        print >>file, "ANGULAR_UNITS = degree"
        if self.d.axes == 2:
            maxvel = max(self.d.xmaxvel, self.d.zmaxvel)
        else:
            maxvel = max(self.d.xmaxvel, self.d.ymaxvel, self.d.zmaxvel)
        hypotvel = (self.d.xmaxvel**2 + self.d.ymaxvel**2 + self.d.zmaxvel**2) **.5
        defvel = min(maxvel, max(.1, maxvel/10.))
        print >>file, "DEFAULT_LINEAR_VELOCITY = %.2f" % defvel
        print >>file, "MAX_LINEAR_VELOCITY = %.2f" % maxvel
        if self.d.restore_joint_position:
            print >>file, "POSITION_FILE = position.txt"
        if not self.d.require_homing:
            print >>file, "NO_FORCE_HOMING = 1"
        print >>file
        print >>file, "[EMCIO]"
        print >>file, "EMCIO = io"
        print >>file, "CYCLE_TIME = 0.100"
        print >>file, "TOOL_TABLE = tool.tbl"
        if self.d.allow_spindle_on_toolchange:
            print >>file, "TOOL_CHANGE_WITH_SPINDLE_ON = 1"
        if self.d.raise_z_on_toolchange:
            print >>file, "TOOL_CHANGE_QUILL_UP = 1"
        if self.d.random_toolchanger:
            print >>file, "RANDOM_TOOLCHANGER = 1"
        
        all_homes = self.a.home_sig("x") and self.a.home_sig("z")
        if self.d.axes in (0,1): all_homes = all_homes and self.a.home_sig("y")
        if self.d.axes == 1: all_homes = all_homes and self.a.home_sig("a")

        ##############################################################
        # build axis/joint info
        ##############################################################
        # self.d.axes:
        # 0 = xyz
        # 1 = xz
        # 2 = xyza
        # todo: simplify hardcoding for trivkins sequential joint no.s

        jnum = 0
        # Always X AXIS
        self.write_one_axis(file, 'x')
        tandemjoint = self.a.tandem_check('x')
        self.write_one_joint(file, 0, "x", "LINEAR", all_homes, bool(not tandemjoint is None))
        if tandemjoint:
            jnum += 1
            self.write_one_joint(file, jnum, "x", "LINEAR", all_homes, True)
        jnum += 1
        print >>file, "#******************************************"

        # Maybe add Y AXIS
        if self.d.axes in(0,1): # xyz or xyza
            self.write_one_axis(file, 'y')
            tandemjoint = self.a.tandem_check('y')
            self.write_one_joint(file, jnum, "y", "LINEAR", all_homes, bool(not tandemjoint is None))
            if tandemjoint:
                jnum += 1
                self.write_one_joint(file, jnum, "y", "LINEAR", all_homes, True)
            jnum += 1
            print >>file, "#******************************************"

        # Always add Z AXIS
        self.write_one_axis(file, 'z')
        tandemjoint = self.a.tandem_check('z')
        self.write_one_joint(file, jnum, "z", "LINEAR", all_homes, bool(not tandemjoint is None))
        if tandemjoint:
            jnum += 1
            self.write_one_joint(file, jnum, "z", "LINEAR", all_homes, True)
        jnum += 1
        print >>file, "#******************************************"

        # Maybe add A AXIS
        if self.d.axes == 1: # xyza
            self.write_one_axis(file, 'a')
            tandemjoint = self.a.tandem_check('a')
            self.write_one_joint(file, jnum, "a", "LINEAR", all_homes, bool(not tandemjoint is None))
            if tandemjoint:
                jnum += 1
                self.write_one_joint(file, jnum, "a", "LINEAR", all_homes, True)
            jnum += 1
            print >>file, "#******************************************"

        # always add SPINDLE
        self.write_one_joint(file, 9, "s", "null", all_homes, False)
        file.close()
        self.d.add_md5sum(filename)

    def write_one_joint(self, file, num, letter, type, all_homes, tandemflag):
        def get(s): return self.d[letter + s]
        pwmgen = self.a.pwmgen_sig(letter)
        tppwmgen = self.a.tppwmgen_sig(letter)
        stepgen = self.a.stepgen_sig(letter)
        encoder = self.a.encoder_sig(letter)
        resolver = self.a.resolver_sig(letter)
        potoutput = self.a.potoutput_sig(letter)
        
        closedloop = False
        if stepgen and (encoder or resolver): closedloop = True
        if (encoder or resolver) and (pwmgen or tppwmgen) : closedloop = True
        if closedloop and letter == "s": closedloop = False
        #print "INI ",letter + " is closedloop? "+ str(closedloop),encoder,pwmgen,tppwmgen,stepgen

        print >>file
        if letter == 's':
            print >>file, "[SPINDLE_%d]" % num
        else:
            print >>file, "[JOINT_%d]" % num
            print >>file, "TYPE = %s" % type
            print >>file, "HOME = %s" % get("homepos")
            print >>file, "FERROR = %s"% get("maxferror")
            print >>file, "MIN_FERROR = %s" % get("minferror")
        if not letter == "s" or (letter == "s" and stepgen):
            print >>file, "MAX_VELOCITY = %s" % get("maxvel")
            print >>file, "MAX_ACCELERATION = %s" % get("maxacc")
            if stepgen:
                print >>file, "# The values below should be 25% larger than MAX_VELOCITY and MAX_ACCELERATION"
                print >>file, "# If using BACKLASH compensation STEPGEN_MAXACCEL should be 100% larger."
                if get("usecomp") or get("usebacklash"):
                    factor = 2.0
                else:
                    factor = 1.25
                print >>file, "STEPGEN_MAXVEL = %.2f" % (float(get("maxvel")) * factor)
                print >>file, "STEPGEN_MAXACCEL = %.2f" % (float(get("maxacc")) * factor)

        print >>file, "P = %s" % get("P")
        print >>file, "I = %s" % get("I") 
        print >>file, "D = %s" % get("D")
        print >>file, "FF0 = %s" % get("FF0")
        print >>file, "FF1 = %s" % get("FF1")
        print >>file, "FF2 = %s" % get("FF2")
        print >>file, "BIAS = %s"% get("bias") 
        print >>file, "DEADBAND = %s"% get("deadband")
        print >>file, "MAX_OUTPUT = %s" % get("maxoutput")
        if encoder or resolver:
            if get("invertencoder"):
                temp = -1
            else: temp = 1
            if encoder:
                print >>file, "ENCODER_SCALE = %s" % (get("encoderscale") * temp)
            else:
                print >>file, "RESOLVER_SCALE = %s" % (get("encoderscale") * temp)
        if pwmgen or potoutput:
            if get("invertmotor"):
                temp = -1
            else: temp = 1

            if letter == 's':
                if self.d.susenegativevoltage:
                    min_voltage_factor = -1
                else:
                    min_voltage_factor = 0 # dont output negative voltages
                max_voltage_factor = 10.0/self.d.soutputmaxvoltage # voltagelimit
                if self.d.suseoutputrange2:
                    scale = 1 # we scale the multiple ranges in the HAL file
                else:
                    scale = self.d.soutputscale # we scale to the max RPM
                print >>file, "OUTPUT_SCALE = %s"% ( int(max_voltage_factor * scale * temp) )
                print >>file, "OUTPUT_MIN_LIMIT = %s"% ( int(min_voltage_factor * scale) )
                print >>file, "OUTPUT_MAX_LIMIT = %s"% ( int(scale) )
                print >>file
            else:
                print >>file, "OUTPUT_SCALE = %s" % (get("outputscale") * temp)
                pwmpinname = self.d.make_pinname(pwmgen)
                if (pwmgen and "analog" in pwmpinname) or potoutput:
                    print >>file, "OUTPUT_MIN_LIMIT = %s"% (get("outputminlimit"))
                    print >>file, "OUTPUT_MAX_LIMIT = %s"% (get("outputmaxlimit"))

        if stepgen:
            print >>file, "# these are in nanoseconds"
            print >>file, "DIRSETUP   = %d"% int(get("dirsetup"))
            print >>file, "DIRHOLD    = %d"% int(get("dirhold"))
            print >>file, "STEPLEN    = %d"% int(get("steptime"))          
            print >>file, "STEPSPACE  = %d"% int(get("stepspace"))
            if get("invertmotor"):
                temp = -1
            else: temp = 1
            print >>file, "STEP_SCALE = %s"% (get("stepscale") * temp)
        if letter == 's':return
        if get("usecomp"):
            print >>file, "COMP_FILE = %s" % get("compfilename")
            print >>file, "COMP_FILE_TYPE = %s" % get("comptype")
        if get("usebacklash"):
            print >>file, "BACKLASH = %s" % get("backlash")
        minlim, maxlim = self.find_limits(letter)
        print >>file, "MIN_LIMIT = %s" % minlim
        print >>file, "MAX_LIMIT = %s" % maxlim
        thisaxishome = set(("all-home", "home-" + letter, "min-home-" + letter, "max-home-" + letter, "both-home-" + letter))
        ignore = set(("min-home-" + letter, "max-home-" + letter, "both-home-" + letter))
        homes = False
        for i in thisaxishome:
            if self.d.findsignal(i): homes = True
        # set homing speeds and directions
        # search direction : True = positive direction
        # latch direction :  True = opposite direction
        if homes:
            searchvel = abs(get("homesearchvel"))
            latchvel = abs(get("homelatchvel"))
            #print get("searchdir")
            if get("searchdir") == 0:
                 searchvel = -searchvel
                 if get("latchdir") == 0: 
                    latchvel = -latchvel 
            else:
                if get("latchdir") == 1: 
                    latchvel = -latchvel
            print >>file, "HOME_OFFSET = %f" % get("homesw")
            print >>file, "HOME_SEARCH_VEL = %f" % searchvel                      
            print >>file, "HOME_LATCH_VEL = %f" % latchvel
            print >>file, "HOME_FINAL_VEL = %f" % get("homefinalvel")
            if get("usehomeindex"):useindex = "YES"
            else: useindex = "NO"   
            print >>file, "HOME_USE_INDEX = %s" % useindex
            for i in ignore:
                if self.d.findsignal(i):
                    print >>file, "HOME_IGNORE_LIMITS = YES"
                    break
            # if all axis have homing switches and user doesn't request
            # manual individual homing:
            if all_homes and not self.d.individual_homing:
                seqnum = int(get("homesequence"))
                # if a tandem joint we wish to finish the home sequence together
                if tandemflag: wait ='-'
                else: wait = ''
                print >>file, "HOME_SEQUENCE = %s%d" % (wait,seqnum)
        else:
            print >>file, "HOME_OFFSET = %s" % get("homepos")

    def write_one_axis(self, file, letter):
        # For KINEMATICS_IDENTITY:
        #     use axis MIN,MAX values identical corresponding joint values
        def get(s): return self.d[letter + s]
        minlim, maxlim = self.find_limits(letter)
        if not letter == "s":
            axis_letter = letter.upper()
            print >>file
            print >>file, "#******************************************"
            print >>file, "[AXIS_%s]" % axis_letter
            print >>file, "MAX_VELOCITY = %s" % get("maxvel")
            print >>file, "MAX_ACCELERATION = %s" % get("maxacc")
            print >>file, "MIN_LIMIT = %s" % minlim
            print >>file, "MAX_LIMIT = %s" % maxlim

    # linuxcnc doesn't like having home right on an end of travel,
    # so extend the travel limit by up to .01in or .1mm
    def find_limits(self, letter):
        def get(s): return self.d[letter + s]
        minlim = -abs(get("minlim"))
        maxlim = get("maxlim")
        home = get("homepos")
        if self.d.units == _PD._METRIC: extend = .01
        else: extend = .001
        minlim = min(minlim, home - extend)
        maxlim = max(maxlim, home + extend)
        return (minlim, maxlim)

# BOILER CODE
    def __getitem__(self, item):
        return getattr(self, item)
    def __setitem__(self, item, value):
        return setattr(self, item, value)
