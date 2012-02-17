#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-05-21.

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


import wx, os
import wx.lib.agw.floatspin as FS
import numpy as N

class ScopeControls(wx.Dialog):
	def __init__(self, master):
		wx.Dialog.__init__(self, master)
		self.cv=master
		self.info = {"DOF":0.0,
					"Z Loc":0.0}
		sizer = wx.BoxSizer(wx.VERTICAL)
		#get info 
		btn = wx.Button(self, -1, " Update info ")
		wx.EVT_BUTTON(self, btn.GetId(), self.get)
		sizer.Add(btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		#get info 
		btn = wx.Button(self, -1, " Zero ")
		wx.EVT_BUTTON(self, btn.GetId(), self.start)
		sizer.Add(btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)			
		#choose Z precision
		bs = wx.BoxSizer(wx.HORIZONTAL)
		bs.Add(wx.StaticText(self, -1, "Focus Step:"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		self.fprec = wx.TextCtrl(self, -1, "10.0", style=wx.TE_PROCESS_ENTER, size=(48,-1))
		wx.EVT_TEXT_ENTER(self, self.fprec.GetId(), self.set_prec)
		bs.Add(self.fprec, 0, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		sizer.Add(bs, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		#choose dof prec
		bs = wx.BoxSizer(wx.HORIZONTAL)
		bs.Add(wx.StaticText(self, -1, "DOF Step:"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		self.dofprec = wx.TextCtrl(self, -1, "10.0", style=wx.TE_PROCESS_ENTER, size=(48,-1))
		wx.EVT_TEXT_ENTER(self, self.dofprec.GetId(), self.set_prec)
		bs.Add(self.dofprec, 0, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		sizer.Add(bs, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		#dof
		bs = wx.BoxSizer(wx.HORIZONTAL)
		bs.Add(wx.StaticText(self, -1, "Dof:"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		self.dof = FS.FloatSpin(self, -1,
                                       increment=1.0, value=20.0, extrastyle=FS.FS_LEFT)
		bs.Add(self.dof, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		sizer.Add(bs, 0, wx.ALIGN_CENTRE|wx.ALL, 5)	
		self.dof.SetFormat("%f")
		self.dof.SetDigits(4)
		self.dof.Bind(FS.EVT_FLOATSPIN, self.setfocus)
		#focus
		bs = wx.BoxSizer(wx.HORIZONTAL)
		bs.Add(wx.StaticText(self, -1, "Focus:"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		self.focus = FS.FloatSpin(self, -1,
                                       increment=1.0, value=20.0, extrastyle=FS.FS_LEFT)
		bs.Add(self.focus, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		sizer.Add(bs, 0, wx.ALIGN_CENTRE|wx.ALL, 5)	
		self.focus.SetFormat("%f")
		self.focus.SetDigits(4)
		self.focus.Bind(FS.EVT_FLOATSPIN, self.setfocus)	

		bs = wx.BoxSizer(wx.HORIZONTAL)
		self.infotext = wx.StaticText(self, -1, " WIDTH=100")
		bs.Add(self.infotext, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 0)
		sizer.Add(bs, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 0)	
		self.get()

		#animate
		btn = wx.Button(self, -1, " Animate ")
		wx.EVT_BUTTON(self, btn.GetId(), self.animate)
		sizer.Add(btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)

		#quit
		btn = wx.Button(self, -1, " Close ")
		wx.EVT_BUTTON(self, btn.GetId(), lambda x:self.Destroy())
		sizer.Add(btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		self.SetSizer(sizer)
		self.SetAutoLayout(True)
		sizer.Fit(self)
		self.Show(True)
		
		
	def setfocus(self, event):
		foc=self.focus.GetValue()
		dof = self.dof.GetValue()
		self.cv.graph.depthoffield = dof
		vp = self.cv.graph.viewpoint + (self.cv.graph.viewpoint*self.cv.graph.forward)
		vp = vp - foc*self.cv.graph.forward
		self.cv.graph.viewpoint=vp
		self.cv.graph.OnDraw()
		self.get()
	
	def start(self, event):
		self.cv.graph.up = N.array([0.0,1,0])
		self.cv.graph.forward = N.array([0.0,0,-1.0])
		self.cv.graph.viewpoint = N.array([0.0,0,10.0])
		self.cv.graph.depthoffield = 10.0
		self.cv.graph.OnDraw()
		self.get()
		
	def get(self, event=None):
		zax = self.cv.graph.forward
		foc = -1*(self.cv.graph.viewpoint*self.cv.graph.forward).sum()
		dof = self.cv.graph.depthoffield
		vp = self.cv.graph.viewpoint
		ext = self.cv.graph.extent
		n = tuple(list(zax)+list(vp)+[ext])
		s = "Z = %.2g %.2g %.2g\nVP=%.2g %.2g %.2g\nWIDTH=%.2g" % n
		self.infotext.SetLabel(s)
		self.focus.SetValue(foc)
		self.dof.SetValue(dof)
		
	def set_prec(self, event):
		value = float(self.fprec.GetValue().strip())
		self.cv.report( "setting focus increment to %.2g" % value)
		self.focus.SetIncrement(value)
		value = float(self.dofprec.GetValue().strip())
		self.dof.SetIncrement(value)
	
	def animate(self, event):
		d = self.cv.askParam([{'Name':'Directory', 'Value':'ScopeAnimation'},
			{'Name':'To Depth?', 'Value':0.0}])
		if not d:
			return
		dir=d[0]
		if os.path.isdir(dir):
			os.system("rm -rf %s" % dir)
		os.mkdir(dir)
		fi = float(self.fprec.GetValue().strip())
		cf =self.focus.GetValue()
		i = 0
		while cf > d[1]:
			self.focus.SetValue(cf)
			self.setfocus(None)
			fname=os.path.join(dir, "frame%05i.bmp" % i)
			self.cv.graph.screenShot(fname=fname)
			print fname
			i+=1
			cf-=fi
		self.cv.report("Saved Images")
