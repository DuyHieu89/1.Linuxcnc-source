#!/usr/bin/env python
# -*- encoding: utf-8 -*-
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
# This presents and collects the data from the GUI pages
#
# To add pages:
# add the glade file to directory. the first container name will be the reference name (delete the window)
# create a python file with the name of glade file. So test.glade must be test.py
# add function call here: <reference name>_prepare() and <reference name>_finish() to this file
# add GLADE callbacks for the page here.
# add large or common function calls to stepconf.py
# add the reference name, Text name and active state to private data variable: self.available_page and
# available_page_lib of stepconf.py

import os
from gi.repository import Gtk
from gi.repository import GObject
from importlib import import_module


def add_method(self, method, name=None):
	if name is None:
		name = method.func_name
	setattr(self.__class__, name, method)
		
class Pages:
	def __init__(self, app):
		self.d = app.d      # collected data
		self.w = app.w      # widget names
		self.a = app        # parent, stepconf
		self._p = app._p    # private data
		global debug
		debug = self.a.debug
		global dbg
		dbg = self.a.dbg
		self.dbg = dbg
		
		# Import all methods from py pages
		for lib in (self._p.available_page_lib):
			#print(lib)
			mod = import_module("stepconf." + lib)
			module_dict = mod.__dict__
			try:
				to_import = mod.__all__
			except AttributeError:
				to_import = [name for name in module_dict if not name.startswith('_')]
	
			for current_function_name in to_import:
				current_function = module_dict[current_function_name]
				add_method(self, current_function, current_function_name)


#********************
# Notebook Controls
#********************
	def on_window1_destroy(self, *args):
		if self.a.warning_dialog (self._p.MESS_ABORT,False):
			Gtk.main_quit()
			return True
		else:
			return True
		return

	# seaches (self._p.available_page) from the current page forward,
	# for the next page that is True or till second-to-last page.
	# if state found True: call current page finish function.
	# If that returns False then call the next page prepare function and show page
	def on_button_fwd_clicked(self,widget):
		cur = self.w.notebook1.get_current_page()
		u = cur+1
		cur_name,cur_text,cur_state = self._p.available_page[cur]
		while u < len(self._p.available_page):
			name,text,state = self._p.available_page[u]
			dbg( "FWD search %s,%s,%s,%s,of %d pages"%(u,name,text,state,len(self._p.available_page)-1))
			if state:
				if not self['%s_finish'%cur_name]():
					self.w.notebook1.set_current_page(u)
					dbg( 'prepare %s'% name)
					self['%s_prepare'%name]()
					self.w.title_label.set_text(text)
					dbg("set %d current"%u)
				break
			u +=1
		# second-to-last page? change the fwd button to finish and show icon
		if u == len(self._p.available_page)-1:
			self.w.apply_image.set_visible(True)
			self.w.label_fwd.set_text(self._p.MESS_DONE)
		# last page? nothing to prepare just finish
		elif u == len(self._p.available_page):
			name,text,state = self._p.available_page[cur]
			self['%s_finish'%name]()
		# if comming from page 0 to page 1 sensitize 
		# the back button and change fwd button text
		if cur == 0:
			self.w.button_back.set_sensitive(True)
			self.w.label_fwd.set_text(self._p.MESS_FWD)

	# seaches (self._p.available_page) from the current page backward,
	# for the next page that is True or till first page.
	# if state found True: call current page finish function.
	# If that returns False then call the next page prepare function and show page
	def on_button_back_clicked(self,widget):
		cur = self.w.notebook1.get_current_page()
		u = cur-1
		cur_name,cur_text,cur_state = self._p.available_page[cur]
		while u > -1:
			name,text,state = self._p.available_page[u]
			dbg( "BACK search %s,%s,%s,%s,of %d pages"%(u,name,text,state,len(self._p.available_page)-1))
			if state:
				if not cur == len(self._p.available_page)-1:
					self['%s_finish'%cur_name]()
				self.w.notebook1.set_current_page(u)
				self['%s_prepare'%name]()
				self.w.title_label.set_text(text)
				dbg("set %d current"%u)
				break
			u -=1
		# Not last page? change finish button text and hide icon
		if u <= len(self._p.available_page):
			self.w.apply_image.set_visible(False)
			self.w.label_fwd.set_text(self._p.MESS_FWD)
		# page 0 ? de-sensitize the back button and change fwd button text 
		if u == 0:
			self.w.button_back.set_sensitive(False)
			self.w.label_fwd.set_text(self._p.MESS_START)
	
	def set_buttons_sensitive(self,fstate,bstate):
		self.w.button_fwd.set_sensitive(fstate)
		self.w.button_back.set_sensitive(bstate)
	
	# Sets the visual state of a list of page(s)
	# The page names must be the one used in self._p.available_page
	# If a pages state is false it won't be seen or it's functions called.
	# if you deselect the current page it will show till next time it is cycled
	def page_set_state(self,page_list,state):
		dbg("page_set_state() %s ,%s"%(page_list,state))
		for i,data in enumerate(self._p.available_page):
			name,text,curstate = data
			if name in page_list:
				self._p.available_page[i][2] = state
				dbg("State changed to %s"% state)
				break

#####################################################
# All Page Methods
#####################################################
#***************
# Intialize
#***************
	def initialize(self):
		# one time initialized data
		liststore = self.w.drivertype.get_model()
		for i in self._p.alldrivertypes:
			#self.w.drivertype.append_text(i[1])
			liststore.append([i[1]])
		#self.w.drivertype.append_text(_("Other"))
		liststore.append([_("Other")])
		self.w.title_label.set_text(self._p.available_page[0][1])
		self.w.button_back.set_sensitive(False)
		self.w.label_fwd.set_text(self._p.MESS_START)
		if debug:
			self.w.window1.set_title('Stepconf -debug mode')
		# halui table
		renderer = Gtk.CellRendererText()
		column = Gtk.TreeViewColumn("Index", renderer, text=0)
		column.set_reorderable(False)
		self.w.viewTable1.append_column(column)
		renderer = Gtk.CellRendererText()
		renderer.set_property('editable', True)
		renderer.connect("edited", self.on_halui_row_changed)
		column = Gtk.TreeViewColumn("MDI__COMMAND", renderer, text=1)
		self.w.viewTable1.append_column(column)
		# pport1 combo boxes
		model = self.w.output_list
		model.clear()
		for name in self._p.human_output_names: model.append((name,))
		model = self.w.input_list
		model.clear()
		for name in self._p.human_input_names: model.append((name,))
		# pport2 comboboxes
		model = self.w.pp2_output_list
		model.clear()
		for ind,name in enumerate(self._p.human_output_names):
			if not ind in( 0,1,2,3,4,5,6,7):
				model.append((name,))
		model = self.w.pp2_input_list
		model.clear()
		for name in self._p.human_input_names: model.append((name,))
		self.intro_prepare()

#************
# INTRO PAGE
#************
	def intro_prepare(self):
		pass
	def intro_finish(self):
		pass

#*********************
# General Axis methods and callbacks
#*********************
	def on_jogminus_pressed(self, *args):
		self.a.jogminus = 1
		self.a.update_axis_test()
	
	def on_jogminus_released(self, *args):
		self.a.jogminus = 0
		self.a.update_axis_test()
	
	def on_jogplus_pressed(self, *args):
		self.a.jogplus = 1
		self.a.update_axis_test()
	def on_jogplus_released(self, *args):
		self.a.jogplus = 0
		self.a.update_axis_test()
	
	def update_axis_params(self, *args):
		self.a.update_axis_test()
	
	def axis_prepare(self, axis):
		def set_text(n):
			self.w[axis + n].set_text("%s" % self.d[axis + n])
			# Set a name for this widget. Necessary for css id
			self.w[axis + n].set_name("%s%s" % (axis, n))
		def set_active(n):
			self.w[axis + n].set_active(self.d[axis + n])
		SIG = self._p
		set_text("steprev")
		set_text("microstep")
		set_text("pulleynum")
		set_text("pulleyden")
		set_text("leadscrew")
		set_text("maxvel")
		set_text("maxacc")
		set_text("homepos")
		set_text("minlim")
		set_text("maxlim")
		set_text("homesw")
		set_text("homevel")
		set_active("latchdir")
	
		if axis == "a":
			self.w[axis + "screwunits"].set_text(_("degree / rev"))
			self.w[axis + "velunits"].set_text(_("deg / s"))
			self.w[axis + "accunits"].set_text(_(u"deg / s²"))
			self.w[axis + "accdistunits"].set_text(_("deg"))
			self.w[axis + "scaleunits"].set_text(_("Steps / deg"))
		elif self.d.units:
			self.w[axis + "screwunits"].set_text(_("mm / rev"))
			self.w[axis + "velunits"].set_text(_("mm / s"))
			self.w[axis + "accunits"].set_text(_(u"mm / s²"))
			self.w[axis + "accdistunits"].set_text(_("mm"))
			self.w[axis + "scaleunits"].set_text(_("Steps / mm"))
		else:
			self.w[axis + "screwunits"].set_text(_("rev / in"))
			self.w[axis + "velunits"].set_text(_("in / s"))
			self.w[axis + "accunits"].set_text(_(u"in / s²"))
			self.w[axis + "accdistunits"].set_text(_("in"))
			self.w[axis + "scaleunits"].set_text(_("Steps / in"))
	
		inputs = self.a.build_input_set()
		thisaxishome = set((SIG.ALL_HOME, SIG.ALL_LIMIT_HOME, "home-" + axis, "min-home-" + axis,
							"max-home-" + axis, "both-home-" + axis))
		# Test if exists limit switches
		homes = bool(inputs & thisaxishome)
		self.w[axis + "homesw"].set_sensitive(homes)
		self.w[axis + "homevel"].set_sensitive(homes)
		self.w[axis + "latchdir"].set_sensitive(homes)
	
		self.w[axis + "steprev"].grab_focus()
		GObject.idle_add(lambda: self.a.update_pps(axis))
	
	def axis_done(self, axis):
		def get_text(n): self.d[axis + n] = float(self.w[axis + n].get_text())
		def get_active(n): self.d[axis + n] = self.w[axis + n].get_active()
		get_text("steprev")
		get_text("microstep")
		get_text("pulleynum")
		get_text("pulleyden")
		get_text("leadscrew")
		get_text("maxvel")
		get_text("maxacc")
		get_text("homepos")
		get_text("minlim")
		get_text("maxlim")
		get_text("homesw")
		get_text("homevel")
		get_active("latchdir")


# BOILER CODE
	def __getitem__(self, item):
		return getattr(self, item)
	def __setitem__(self, item, value):
		return setattr(self, item, value)
	
