#!/usr/bin/env python
#
#    This is stepconf, a graphical configuration editor for LinuxCNC
#    Copyright 2007 Jeff Epler <jepler@unpythonic.net>
#    stepconf 1.1 revamped by Chris Morley 2014
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#*************
# FINISH PAGE
#*************
import shutil
import os
import errno
import xml.dom.minidom
import commands
from gi.repository import Gtk
from stepconf.definitions import *

def finished_prepare(self):
	pass
def finished_finish(self):
	self.build_config()

def build_config(self):
	base = self.build_base()
	self.save(base)
	self.d.save_preferences()
	self.a.INI.write_inifile(base)
	self.a.HAL.write_halfile(base)
	self.copy(base, "tool.tbl")
	if self.a.warning_dialog(MESS_QUIT,False):
		Gtk.main_quit()

def build_base(self):
	base = os.path.expanduser("~/linuxcnc/configs/%s" % self.d.machinename)
	ncfiles = os.path.expanduser("~/linuxcnc/nc_files")
	if not os.path.exists(ncfiles):
		try:
			os.makedirs(ncfiles)
		except os.error, detail:
			if detail.errno != errno.EEXIST: raise
	
		examples = os.path.join(self.a.program_path, "share", "linuxcnc", "ncfiles")
		if not os.path.exists(examples):
			examples = os.path.join(self.a.program_path, "nc_files")
		if os.path.exists(examples):
			os.symlink(examples, os.path.join(ncfiles, "examples"))
	try:
		os.makedirs(base)
	except os.error, detail:
		if detail.errno != errno.EEXIST: raise
	return base


def copy(self, base, filename):
	dest = os.path.join(base, filename)
	if not os.path.exists(dest):
		shutil.copy(os.path.join(self.a.distdir, filename), dest)

def save(self,basedir):
	base = basedir

	if self.d.classicladder: 
		if not self.d.laddername == "custom.clp":
			filename = os.path.join(self.a.distdir, "configurable_options/ladder/%s" % self.d.laddername)
			original = os.path.expanduser("~/linuxcnc/configs/%s/custom.clp" % self.d.machinename)
			if os.path.exists(filename):     
				if os.path.exists(original):
					print "custom file already exists"
					shutil.copy( original,os.path.expanduser("~/linuxcnc/configs/%s/custom_backup.clp" % self.d.machinename) ) 
					print "made backup of existing custom"
				shutil.copy( filename,original)
				print "copied ladder program to usr directory"
				print"%s" % filename
			else:
				print "Master or temp ladder files missing from configurable_options dir"

	# Extra subroutine
	if (self.d.pyvcp == True or self.d.gladevcp == True ):
		if(self.d.pyvcptype == PYVCP_DEFAULT or self.d.gladevcptype == GLADEVCP_DEFAULT): # default panel
			# Subroutine
			subroutine = os.path.expanduser("~/linuxcnc/configs/%s/%s" % (self.d.machinename, "probe_tool_lenght.ngc"))
			fngc = open(subroutine, "w")
			print >>fngc, ("""o<probe_tool_lenght> sub
(Set Z Zero for G54 coordinate)""")
			print >>fngc, ("	G53 G0 X%d Y%d Z%d" % (self.d.probe_x_pos, self.d.probe_y_pos, self.d.probe_z_pos))
			print >>fngc, ("""	G49 (Delete any reference)
	G38.2 Z0 F200
	G91 G0 Z1 (Off the switch)
	(try again at lower speed)
	G90
	G38.2 Z0 F15
	G91 G0 Z1 (Off the switch)
	#1000=#5063 (save reference tool length)
	(print,reference length is #1000)
	(G54 G10 L20 P1 Z[#1000])""")
			print >>fngc, ("	G54 G10 L20 P1 Z[%s] (switch height)" % (self.d.probe_sensor_height))
			print >>fngc, ("""	G90 (done)
o<probe_tool_lenght> endsub""")
			fngc.close()

	if self.d.pyvcp:
		originalname = os.path.expanduser("~/linuxcnc/configs/%s/%s" % (self.d.machinename, self.d.pyvcpname))
		if(self.d.pyvcptype == PYVCP_DEFAULT): # default panel
			# Create default panel
			self.create_pyvcp_panel(originalname)
		elif(self.d.pyvcptype == PYVCP_CUSTOM): # custom panel
			if os.path.exists(originalname):
				 print "custom PYVCP file already exists"
			else:
				self.create_pyvcp_custom(originalname)
				print "created PYVCP panel %s" % self.d.pyvcpname
		elif(self.d.pyvcptype == PYVCP_NONE): # no panel
			None
		else:
			print "Master PYVCP files missing from configurable_options dir"

	if self.d.gladevcp:
		originalname = os.path.expanduser("~/linuxcnc/configs/%s/%s" % (self.d.machinename, self.d.gladevcpname))
		if(self.d.gladevcptype == GLADEVCP_DEFAULT): # default panel
			# Create default panel
			self.create_gladevcp_panel(originalname)
		elif(self.d.gladevcptype == GLADEVCP_CUSTOM): # custom panel
			if os.path.exists(originalname):
				 print "custom GLADEVCP file already exists"
			else:
				self.create_gladevcp_custom(originalname)
				print "created GLADEVCP panel %s" % self.d.gladevcpname
		elif(self.d.gladevcptype == GLADEVCP_NONE): # no panel
			None
		else:
			print "Master GladeVCP files missing from configurable_options dir"
		# Create gladevcp.py file
		originalname = os.path.expanduser("~/linuxcnc/configs/%s/%s" % (self.d.machinename, FILE_GLADEVCP_HANDLER))
		self.create_gladevcp_py(originalname)

	filename = "%s.stepconf" % base
	d = xml.dom.minidom.getDOMImplementation().createDocument(None, "stepconf", None)
	e = d.documentElement

	for k, v in sorted(self.d.__dict__.iteritems()):
		if k.startswith("_"): continue
		n = d.createElement('property')
		e.appendChild(n)

		if isinstance(v, float): n.setAttribute('type', 'float')
		elif isinstance(v, bool): n.setAttribute('type', 'bool')
		elif isinstance(v, int): n.setAttribute('type', 'int')
		elif isinstance(v, list): n.setAttribute('type', 'eval')
		else: n.setAttribute('type', 'string')

		n.setAttribute('name', k)
		n.setAttribute('value', str(v))
	
	d.writexml(open(filename, "wb"), addindent="  ", newl="\n")
	print("%s" % base)

	# see http://freedesktop.org/wiki/Software/xdg-user-dirs
	desktop = commands.getoutput("""
		test -f ${XDG_CONFIG_HOME:-~/.config}/user-dirs.dirs && . ${XDG_CONFIG_HOME:-~/.config}/user-dirs.dirs
		echo ${XDG_DESKTOP_DIR:-$HOME/Desktop}""")
	if self.d.createsymlink:
		shortcut = os.path.join(desktop, self.d.machinename)
		if os.path.exists(desktop) and not os.path.exists(shortcut):
			os.symlink(base,shortcut)

	if self.d.createshortcut and os.path.exists(desktop):
		if os.path.exists(self.a.program_path + "/scripts/linuxcnc"):
			scriptspath = (self.a.program_path + "/scripts/linuxcnc")
		else:
			scriptspath ="linuxcnc"

		filename = os.path.join(desktop, "%s.desktop" % self.d.machinename)
		file = open(filename, "w")
		print >>file,"[Desktop Entry]"
		print >>file,"Version=1.0"
		print >>file,"Terminal=false"
		print >>file,"Name=" + _("launch %s") % self.d.machinename
		print >>file,"Exec=%s %s/%s.ini" \
					 % ( scriptspath, base, self.d.machinename )
		print >>file,"Type=Application"
		print >>file,"Comment=" + _("Desktop Launcher for LinuxCNC config made by Stepconf")
		print >>file,"Icon=%s"% self.a.linuxcncicon
		file.close()
		# Ubuntu 10.04 require launcher to have execute permissions
		os.chmod(filename,0775)
