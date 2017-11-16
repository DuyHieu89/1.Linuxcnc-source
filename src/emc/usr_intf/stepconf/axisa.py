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

#********************
# AXIS A PAGE
#********************
def axisa_prepare(self):
	self.axis_prepare('a')
def axisa_finish(self):
	self.axis_done('a')
# AXIS A callbacks
def on_asteprev_changed(self, *args): self.update_pps('a')
def on_amicrostep_changed(self, *args): self.update_pps('a')
def on_apulleyden_changed(self, *args): self.update_pps('a')
def on_apulleynum_changed(self, *args): self.update_pps('a')
def on_aleadscrew_changed(self, *args): self.update_pps('a')
def on_amaxvel_changed(self, *args): self.update_pps('a')
def on_amaxacc_changed(self, *args): self.update_pps('a')
def on_aaxistest_clicked(self, *args): self.test_axis('a')
def on_apreset_button_clicked(self, *args): self.preset_axis('a')
