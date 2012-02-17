#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-05-29.

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
from numpy import *
from mien.math.array import rotate3D, rotateArrayAround
import wx
import time


def convert_ang(thet, roll, pitch, yaw):
	'''converts the XY plane projection of an angle under the indicated Euler angle xforms. Return is a scalar which is also an XY plane projection'''
	pa = array([1.0, 0, 0])
	ya = array([0.0, 0, 1.0])
	vec = array([[sin(thet), cos(thet), 0.0]])
	vec = rotateArrayAround(array([0.0, 1, 0]), roll, vec)
	vec = rotateArrayAround(array([0.0, 0, 1]), yaw, vec)
	#pitch axis correction (this is exactly the same as pitch first, then yaw)
	pa = rotateArrayAround(array([0.0, 0, 1]), yaw, array([[1.0, 0, 0]]))[0]
	#print pa
	vec = rotateArrayAround(pa, pitch, vec)
	thet2 = arctan2(vec[0,0], vec[0,1])
	return thet2
	
def ypr_rotmat(thet, roll, pitch, yaw):
	sr=sin(roll)
	cr=cos(roll)
	sp=sin(pitch)
	cp=cos(pitch)
	sy=sin(yaw)
	cy=cos(yaw)
	rotmat = array([
		[cp*cy,					-cp*sy, 	sp],
		[cr*sy+sr*sp*cy, cr*cy-sr*sp*sy, 	-sr*cp],
		[sr*sy-cr*sp*cy, sr*cy+cr*sp*sy,	cr*cp]])
	vec = array([[sin(thet), cos(thet), 0.0]])
	vec = dot(vec, rotmat.transpose())	
	thet2 = arctan2(vec[0,0], vec[0,1])
	return thet2	
	
	
class CC(wx.Dialog):
	def __init__(self, master):
		wx.Dialog.__init__(self, master)
		self.cv=master
		self.g = self.cv.graph
		self.pitch_angle = 18.0*pi/180
		self.yaw_angle = 30.0*pi/180	
		sizer = wx.BoxSizer(wx.VERTICAL)		
		
		bs = wx.BoxSizer(wx.HORIZONTAL)
		bs.Add(wx.StaticText(self, -1, "hair angle (theta):"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		self.theta = wx.TextCtrl(self, -1, "85.0", size=(48,-1))
		bs.Add(self.theta, 0, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		sizer.Add(bs, 0, wx.ALIGN_CENTRE|wx.ALL, 5)	
		bs = wx.BoxSizer(wx.HORIZONTAL)
		bs.Add(wx.StaticText(self, -1, "circ angle (alpha):"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		self.roll_angle = wx.TextCtrl(self, -1, "193", size=(48,-1))
		bs.Add(self.roll_angle, 0, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		sizer.Add(bs, 0, wx.ALIGN_CENTRE|wx.ALL, 5)	
		btn = wx.Button(self, -1, " Start ")
		wx.EVT_BUTTON(self, btn.GetId(), self.start)
		sizer.Add(btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)

		btn = wx.Button(self, -1, " Roll ")
		wx.EVT_BUTTON(self, btn.GetId(), self.step1)
		sizer.Add(btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		
		btn = wx.Button(self, -1, " Roll+Pitch ")
		wx.EVT_BUTTON(self, btn.GetId(), self.step2)
		sizer.Add(btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		
		btn = wx.Button(self, -1, " Roll+Pitch+Yaw ")
		wx.EVT_BUTTON(self, btn.GetId(), self.step3)
		sizer.Add(btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
				
		btn = wx.Button(self, -1, " Animate ")
		wx.EVT_BUTTON(self, btn.GetId(), self.animate)
		sizer.Add(btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		
		self.plots={'axis':None, 'cercus':None, 'hair':None, 'dvec':None, 'final':None}
		self.start_data = {'axis':array([[0,0,0],[0,2,0],[0,0,0],[1.4,0,0],[0,0,0.0],[0,0,1.0]]), 
			'cercus':array([[0,0,0,.3],[0,-6,0, .001]]),
			 'hair':array([[0, -2, 0.0, .05], [0, -2, 1.0, .001]]), 
			'dvec':None,
			'axiscolors':array([[0,0,.7],[0,.7,0],[.7,0,0]])}
		self.draw_data = {}
		self.SetSizer(sizer)
		self.SetAutoLayout(True)
		sizer.Fit(self)
		self.Show(True)



	def draw(self):
		self.g.clearAll()
		self.plots['axis'] = self.g.addLinesPlot(self.draw_data['axis'], width=2, style='lines', colorlist=list(self.draw_data['axiscolors']))
		self.plots['cercus']=self.g.addFrustaPlot(self.draw_data['cercus'])
		self.plots['hair']=self.g.addFrustaPlot(self.draw_data['hair'])
		self.plots['dvec']=self.g.addLinesPlot(self.draw_data['dvec'], width=3, style='lines')
		dv =  self.draw_data['dvec'][1,:] - self.draw_data['dvec'][0,:]
		self.plots['final']=self.g.addLinesPlot(array([[0,0,.2], [dv[0], dv[1], .2]]), color=(1,1,1), width=3, style='lines')
		thet = arctan2(dv[0], dv[1])*180/pi
		self.cv.report("Projected angle is %.3g (remember this is CLOCKWISE)" % thet)
		
		self.g.OnDraw()		

	def start(self, event=None):
		thet = float(self.theta.GetValue())
		self.cv.report("Initial angle is %.3g (remember this is CLOCKWISE)" % thet)
		thet = thet*pi/180
		self.start_data['dvec']=array([[0, -2, 1.0], [sin(thet), cos(thet)-2, 1.0]])
		for k in self.start_data:
			self.draw_data[k]=self.start_data[k].copy()
		self.draw()

		
	def transform(self, dat, angs):
		dat = dat.copy()
		if len(angs) > 0:
			dat[:,:3] = rotateArrayAround(array([0.0, 1.0, 0]), -1*angs[0], dat[:,:3])
		if len(angs) > 1:
			dat[:,:3] = rotateArrayAround(array([1.0, 0.0, 0]), -1*angs[1], dat[:,:3])
		if len(angs) > 2:
			dat[:,:3] = rotateArrayAround(array([0.0, 0.0, 1.0]), -1*angs[2], dat[:,:3])
		return dat
		
	def show_transform(self, t):
		for k in self.start_data:
			if 'axis' in k:
				self.draw_data[k]=self.start_data[k]
			else:
				self.draw_data[k]=self.transform(self.start_data[k], t)
		self.draw()
	
	def step1(self, event):
		self.start()
		roll = 	float(self.roll_angle.GetValue())
		self.cv.report('Applying roll of %.2g' % roll)
		roll = 	-1*roll*pi/180
		self.show_transform([roll])
	
	def step2(self, event):
		self.start()
		roll = 	float(self.roll_angle.GetValue())
		pitch = self.pitch_angle*180/pi
		self.cv.report('Applying roll of %.2g, pitch of %.2g' % (roll, pitch))
		roll = 	-1*roll*pi/180
		self.show_transform([roll, self.pitch_angle])
		
	def step3(self, event):
		self.start()
		roll = 	float(self.roll_angle.GetValue())
		pitch = self.pitch_angle*180/pi
		yaw = self.yaw_angle*180/pi
		self.cv.report('Applying roll of %.2g, pitch of %.2g, yaw of %.2g' % (roll, pitch, yaw))
		rr = 	-1*roll*pi/180
		self.show_transform([rr, self.pitch_angle, self.yaw_angle])
		thet = float(self.theta.GetValue())*pi/180
		t2= convert_ang(thet, -1*rr, -1*self.pitch_angle, -1*self.yaw_angle)
		self.cv.report('convert_ang: %0.5g' % (t2*180/pi,))
		t3= ypr_rotmat(thet, -1*rr, -1*self.pitch_angle, -1*self.yaw_angle)
		self.cv.report('ypr: %0.5g' % (t3*180/pi,))


		
	def animate(self, event):
		
		import os
		if os.path.exists("angle_rot_anim"):
			os.system("rm -rf angle_rot_anim")
		os.mkdir("angle_rot_anim")
		frame = 0
		fname = "angle_rot_anim/frame%05i.png" % frame
		self.start(None)
		self.g.screenShot(fname=fname)
		roll = 	float(self.roll_angle.GetValue())
		roll = 	-1*roll*pi/180
		for r in linspace(0, roll, 50):
			self.show_transform([r])
			time.sleep(.1)
			frame += 1 
			fname = "angle_rot_anim/frame%05i.png" % frame
			self.g.screenShot(fname=fname)
		for r in linspace(0, self.pitch_angle, 20):
			self.show_transform([roll, r])
			time.sleep(.1)			
			frame += 1 
			fname = "angle_rot_anim/frame%05i.png" % frame
			self.g.screenShot(fname=fname)
		for r in linspace(0, self.yaw_angle, 50):
			self.show_transform([roll, self.pitch_angle, r])
			time.sleep(.1)
			frame += 1 
			fname = "angle_rot_anim/frame%05i.png" % frame
			self.g.screenShot(fname=fname)
		

def fixedFieldString(numbers, maxwidth=10):
	s = ""
	for n in numbers:
		sn = "%0.5g" % n
		pad = maxwidth - len(sn)
		s= s + " "*pad + sn
	return s
			

if __name__ == '__main__':
	import sys
	ldat = open(sys.argv[1]).readlines()
	pitch = -18.0*pi/180
	yaw = -30.0*pi/180	
	print("      Hair     Alpha     Theta      Land       Gic    GicAlt")	
	for i in range(len(ldat)):
		try:
			ld = map(float, ldat[i].split()[:7])
		except:
			continue
		if not ld:
			continue
		hid = int(ld[0])
		adeg = ld[1]
		thetd = ld[2]
		laa = ld[6]
		ar = adeg*pi/180
		thet = thetd*pi/180
		gic= convert_ang(thet, ar, pitch, yaw)*180/pi
		print(fixedFieldString((hid, adeg, thetd, laa, gic)))
		
		
		
		
	




