#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-05-08.

# Copyright (C) 2009 Graham I Cummins
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 59 Temple
# Place, Suite 330, Boston, MA 02111-1307 USA
#

import wx
import wx.lib.agw.floatspin as FS
from mien.spatial.alignment import alignObject

class AlignmentControls(wx.Dialog):
	def __init__(self, master):
		wx.Dialog.__init__(self, master)
		self.cv=master
		self.imcenter=None
		self.dontAlign = "std_"
		scale_precision = 0.01
		rot_precision = 1.0
		trans_prec = 10.0
		
		self.last = {'Rot_x':0.0, "Rot_y":0.0, "Rot_z":0.0, "Scale_x":1.0, "Scale_y":1.0, "Scale_z":1.0,
			"Trans_x":0.0, "Trans_y":0.0, "Trans_z":0.0}
		self.SetTitle("CV Alignment Control")
		sizer = wx.BoxSizer(wx.VERTICAL)
		tw = self.GetTextExtent("W")[0]*30
		#choose alignment set
		btn = wx.Button(self, -1, " Choose Elements to Exclude ")
		wx.EVT_BUTTON(self, btn.GetId(), self.set_alignment_exclusion)
		sizer.Add(btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)		
		#choose stretch precision
		bs = wx.BoxSizer(wx.HORIZONTAL)
		bs.Add(wx.StaticText(self, -1, "Scale increment:"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		self.scale_prec = wx.TextCtrl(self, -1, str(scale_precision), style=wx.TE_PROCESS_ENTER, size=(12,-1))
		wx.EVT_TEXT_ENTER(self, self.scale_prec.GetId(), self.set_scale_prec)
		bs.Add(self.scale_prec, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		sizer.Add(bs, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		#choose rot precision
		bs = wx.BoxSizer(wx.HORIZONTAL)
		bs.Add(wx.StaticText(self, -1, "Rotation increment:"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		self.rot_prec = wx.TextCtrl(self, -1, str(rot_precision), style=wx.TE_PROCESS_ENTER, size=(12,-1))
		wx.EVT_TEXT_ENTER(self, self.rot_prec.GetId(), self.set_rot_prec)
		bs.Add(self.rot_prec, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		sizer.Add(bs, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)	
		#choose trans precision
		bs = wx.BoxSizer(wx.HORIZONTAL)
		bs.Add(wx.StaticText(self, -1, "Translation increment:"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		self.trans_prec = wx.TextCtrl(self, -1, str(trans_prec), style=wx.TE_PROCESS_ENTER, size=(12,-1))
		wx.EVT_TEXT_ENTER(self, self.trans_prec.GetId(), self.set_trans_prec)
		bs.Add(self.trans_prec, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		sizer.Add(bs, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)		
		#pitch
		bs = wx.BoxSizer(wx.HORIZONTAL)
		bs.Add(wx.StaticText(self, -1, "Pitch:"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		self.fspitch = FS.FloatSpin(self, -1,
                                       increment=rot_precision, value=0.0, extrastyle=FS.FS_LEFT)
		bs.Add(self.fspitch, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		sizer.Add(bs, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)		
		#yaw 		
		bs = wx.BoxSizer(wx.HORIZONTAL)
		bs.Add(wx.StaticText(self, -1, "Yaw:"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		self.fsyaw = FS.FloatSpin(self, -1, 
                                       increment=rot_precision, value=0.0, extrastyle=FS.FS_LEFT)
		bs.Add(self.fsyaw, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		sizer.Add(bs, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)		
		#roll
		bs = wx.BoxSizer(wx.HORIZONTAL)
		bs.Add(wx.StaticText(self, -1, "Roll:"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		self.fsroll = FS.FloatSpin(self, -1, 
                                       increment=rot_precision, value=0.0, extrastyle=FS.FS_LEFT)
		bs.Add(self.fsroll, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		sizer.Add(bs, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)	
		#xtrans
		bs = wx.BoxSizer(wx.HORIZONTAL)
		bs.Add(wx.StaticText(self, -1, "X Trans:"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		self.xtrans = FS.FloatSpin(self, -1, 
                                       increment=trans_prec, value=0.0, extrastyle=FS.FS_LEFT)
		bs.Add(self.xtrans, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		sizer.Add(bs, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)		
		#ytrans		
		bs = wx.BoxSizer(wx.HORIZONTAL)
		bs.Add(wx.StaticText(self, -1, "Y Trans:"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		self.ytrans = FS.FloatSpin(self, -1, 
                                       increment=trans_prec, value=0.0, extrastyle=FS.FS_LEFT)
		bs.Add(self.ytrans, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		sizer.Add(bs, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)		
		#ztrans
		bs = wx.BoxSizer(wx.HORIZONTAL)
		bs.Add(wx.StaticText(self, -1, "Z Trans:"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		self.ztrans = FS.FloatSpin(self, -1, 
                                       increment=trans_prec, value=0.0, extrastyle=FS.FS_LEFT)
		bs.Add(self.ztrans, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		sizer.Add(bs, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)			
		#y-stretch
		bs = wx.BoxSizer(wx.HORIZONTAL)
		bs.Add(wx.StaticText(self, -1, "Y Scale:"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		self.fsyscale = FS.FloatSpin(self, -1,
                                       increment=scale_precision, value=1.0, extrastyle=FS.FS_LEFT)
		bs.Add(self.fsyscale, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		sizer.Add(bs, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)		
		#z-stretch
		bs = wx.BoxSizer(wx.HORIZONTAL)
		bs.Add(wx.StaticText(self, -1, "Z Scale:"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		self.fszscale = FS.FloatSpin(self, -1, 
                                       increment=scale_precision, value=1.0, extrastyle=FS.FS_LEFT)
		bs.Add(self.fszscale, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		sizer.Add(bs, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)		
		#x-stretch
		bs = wx.BoxSizer(wx.HORIZONTAL)
		bs.Add(wx.StaticText(self, -1, "X Scale:"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		self.fsxscale = FS.FloatSpin(self, -1, 
                                       increment=scale_precision, value=1.0, extrastyle=FS.FS_LEFT)
		bs.Add(self.fsxscale, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		sizer.Add(bs, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)		
		#bindings
		for widg in [self.fsxscale, self.fsyscale, self.fszscale, self.fspitch, self.fsyaw, self.fsroll,
			self.xtrans, self.ytrans, self.ztrans]:
			widg.SetFormat("%f")
			widg.SetDigits(4)
			widg.Bind(FS.EVT_FLOATSPIN, self.apply_align)

		self.ctrl_vals = {'Rot_x':self.fspitch, "Rot_y":self.fsroll, 
							"Rot_z":self.fsyaw, "Scale_x":self.fsxscale, 
							"Scale_y":self.fsyscale, "Scale_z":self.fszscale,
							'Trans_x':self.xtrans, 'Trans_y':self.ytrans, "Trans_z":self.ztrans}															
		#quit
		btn = wx.Button(self, -1, " Close ")
		wx.EVT_BUTTON(self, btn.GetId(), lambda x:self.Destroy())
		sizer.Add(btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		self.SetSizer(sizer)
		self.SetAutoLayout(True)
		sizer.Fit(self)
		self.Show(True)

	def set_scale_prec(self, event):
		value = float(self.scale_prec.GetValue().strip())
		for ctrl in [self.fsxscale, self.fsyscale, self.fszscale]:
			ctrl.SetIncrement(value)

	def set_alignment_exclusion(self, event):
		els = self.cv.getElements()
		if els:
			self.dontAlign = els
		else:
			self.dontAlign = "std_"
		
	def set_rot_prec(self, event):
		value = float(self.rot_prec.GetValue().strip())
		for ctrl in [self.fspitch, self.fsyaw, self.fsroll]:
			ctrl.SetIncrement(value)
			
	def set_trans_prec(self, event):
		value = float(self.trans_prec.GetValue().strip())
		for ctrl in [self.xtrans, self.ytrans, self.ztrans]:
			ctrl.SetIncrement(value)
		
	def get_alignment_set(self):
		els = self.cv.document.getElements(["Cell", "Fiducial", "SpatialField"])
		if type(self.dontAlign)==str:
			els = [e for e in els if not e.name().startswith(self.dontAlign)]
		else:
			els = [e for e in els if not e in self.dontAlign]
		return els	

	def calc_diff(self, trans):
		nt = {}
		for k in ['Rot_x',"Rot_y","Rot_z", "Trans_x", "Trans_y", "Trans_z"]:
			nt[k] = trans[k]-self.last[k]
		for k in ['Scale_x',"Scale_y","Scale_z"]:
			nt[k] = trans[k]/self.last[k]	
		return nt	

	def is_noop(self, nt):
		for k in ['Rot_x',"Rot_y","Rot_z", "Trans_x", "Trans_y", "Trans_z"]:
			if nt[k] !=0:
				return False
		for k in ['Scale_x',"Scale_y","Scale_z"]:
			if nt[k] != 1.0:
				return False
		return True
		
		
	def apply_align(self, event):
		trans = {}
		for name in self.ctrl_vals:
			trans[name]=self.ctrl_vals[name].GetValue()
		ntrans = self.calc_diff(trans)
		if self.is_noop(ntrans):
			return 
		print ntrans
		for obj in self.get_alignment_set():
			alignObject(obj, ntrans)	
		self.last=trans
		self.cv.graph.clearAll()
		for o in self.cv.getPlotTargets():
			self.cv.graph.plotXML(o)
		self.cv.graph.OnDraw()


