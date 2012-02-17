#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2008-02-01.

# Copyright (C) 2008 Graham I Cummins
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
from mien.wx.graphs.graph import *
from mien.image.arrayops import pcolorImage
from mien.wx.graphs.graphGL import GraphGL
from threading import Thread
from time import sleep


wxEVT_RETURN_PT=wx.NewEventType()

def EVT_RETURN_PT(win, func):
	win.Connect(-1, -1, wxEVT_RETURN_PT, func)

class PtEvent(wx.PyEvent):
	def __init__(self, pt, mode):
		wx.PyEvent.__init__(self)
		self.SetEventType(wxEVT_RETURN_PT)
		self.pt=pt
		self.mode=mode

class SpaceGraph(Graph):
	
	def __init__(self,parent,id=-1, **wxOpt):
		Graph.__init__(self,parent,id=-1, **wxOpt)
		self.drawingFunctions["space"]=self.drawSpace
		self.drawingFunctions["polyline"]=self.drawPolyLine
		
	def addSpacePlot(self, space, crange=None, name='plot'):
		if space.data[0]=='full' and crange==None:
			dat=space.full()
			nz = dat>0
			if not any(nz):
				return
			#mnz = dat[nz].min()
			#huge = mnz*5000
			#dat = minimum(dat, huge)
			crange = (0, dat.max())
			self.addArrayPlot(dat, crange, name)
			return
		if not any(space.data[1]):
			return
		if crange == None:
			crange = (0, space.max())
		options ={'style':'space',
		  'nodraw':False}
		options['order']=len(self.plots.keys())
		options["color"], options["dashStyle"]=self.nextcolor()
		ind, c = space.sparse()
		options['colorlist']=colorscale(c, 'rgb', crange)
		index=1
		basename=name
		while  self.plots.has_key(name):
			index+=1
			name = "%s_%i" % (basename, index)
		options["data"]=ind
		self.plots[name] = options
		return name
	
	def addRawSpacePlot(self, ind, color, name='plot'):
		options ={'style':'space',
		  'nodraw':False}
		options['order']=len(self.plots.keys())
		options["color"], options["dashStyle"]=self.nextcolor()
		options['colorlist']=color
		index=1
		basename=name
		while  self.plots.has_key(name):
			index+=1
			name = "%s_%i" % (basename, index)
		options["data"]=ind
		self.plots[name] = options
		return name
		
		
	def doMeasure(self, event):
		x=event.GetX()
		y=event.GetY()
		rx, ry = self.numericalCoordinates((float(x),float(y)))[0,:]
		pt=(int(round(rx)), int(round(ry)))
		wx.EVT_LEFT_UP(self, self.OnLeftRelease)
		wx.EVT_LEFT_DOWN(self, self.OnLeftClick)
		evt = PtEvent(pt, self._returnEventInfo[1])
		wx.PostEvent(self._returnEventInfo[0], evt)
		self._returnEventInfo=None
		self._yh=None
		
	def markup(self, pts, symbol='circle', size=5, color=None):
		options ={'style':'points',
			"symbolStyle":symbol,
			'order':0,
			'nodraw':False}
		if color:
			options['color']=wx.Color(color)
		else:
			options["color"], options["dashStyle"]=self.nextcolor()
		name='markup'
		index=1
		while  self.plots.has_key(name):
			index+=1
			name = "markup_%i" % (index,)
		options["data"]=pts
		options['width']=size
		self.plots[name] = options
		return name	
		
	def getAPoint(self, gui, mode):
		self._returnEventInfo=(gui, mode)
		wx.EVT_LEFT_UP(self, lambda x:0)
		wx.EVT_LEFT_DOWN(self, self.doMeasure)
		
	def addArrayPlot(self, a,  crange=None, name='plot'):
		options ={'style':'ScalingImage',
		  'nodraw':False,
			'pcolor':'rgb'}
		options['order']=1000
		options["color"], options["dashStyle"]=self.nextcolor()
		while len(a.shape)>2:
			a=a[:,:,0]
		a=a[:, arange(a.shape[1]-1, -1, -1)]
		a=reshape(a, (a.shape[0], a.shape[1], 1))
		if not crange or 'local' in crange:
			options["colorrange"]=None
		else:	
			options["colorrange"]=crange
		index=1
		basename=name
		while  self.plots.has_key(name):
			index+=1
			name = "%s_%i" % (basename, index)
		options["data"]=a
		self.plots[name] = options
		return name
	

	def hexGridPlot(self, a, w, e, b, name):
		if a.shape[1]==1:
			pts=[]
			from gicmapseek.hexgrid import hexItoXY
			for i in range(a.shape[0]):
				pts.append(hexItoXY(i, w, e, False))
			self.addPlot(array(pts), style='points', width=int(round(e)), name=name, colorlist=colorscale(a[:,0]))
		elif a.shape[1]==6:
			from gicmapseek.hexgrid import halfLinesFromHex
			pts=halfLinesFromHex(a, w, e, b)
			self.addPlot(pts[:,:4], style='polyline', width=1, name=name, colorlist=colorscale(pts[:,4]))
		else:
			from gicmapseek.hexgrid import lineCoordsFromHex
			pts=lineCoordsFromHex(a, w, e, b)
			self.addPlot(pts[:,:4], style='polyline', width=1, name=name, colorlist=colorscale(pts[:,4]))

	def plotNavData(self, d):
		s=d.getData()
		if d.attrib('SampleType')=='hexgrid':
			w=d.attrib('width')
			e=d.attrib('edge')
			b=d.attrib('blanks')
			od=d.getSubData('/base')
			if od:
				od=od.getData()
				self.addArrayPlot(od, crange=(od.min(), od.max()), name='bias_base')
			self.hexGridPlot(s, w, e, b, name='bias')
			self.limits=array([-1,w*e+2, -1.0, .866*e*(s.shape[0]/w)+2])	
		else:	
			self.addArrayPlot(s, crange=(s.min(), s.max()), name='bias')
			self.limits=array([-1,s.shape[0]+2, -1.0, s.shape[1]+2])	
		
		sd=d.getSubData('/source')
		if sd:
			sd=sd.getData()
			self.markup(sd[:,:2], 'circle', int(max(15, min(s.shape)/50.)))
		td=d.getSubData('/target')
		if td:
			td=td.getData()
			self.markup(td[:,:2], 'circle', int(max(15, min(s.shape)/50.)))	

	def drawPolyLine(self, name, data, dc):
		if not len(data)>1:
			return	
		# mask = self.inWindow(data[:,:2], True)
		# if not len(mask)>1:
		# 	return
		# data=take(data, mask, 0)
		spts = self.graphCoords(data[:,:2])
		epts = self.graphCoords(data[:,2:])
		ds=self.plots[name].get("dashStyle", wx.SOLID)
		w=self.plots[name].get('width', 1)
		if self.plots[name].get("colorlist"):
			colors = self.plots[name]["colorlist"]	
			pen = map(lambda x:wx.Pen(x, w, ds), colors)
		else:
			pen=wx.Pen(self.plots[name]['color'], w, ds)
		dc.DrawLineList(column_stack([spts, epts]), pen)		

	def drawSpace(self, name, data, dc):
		colors = self.plots[name]["colorlist"]
		mask = self.inWindow(data, True)
		if not len(mask):
			return
		data = take(data, mask, 0)
		colors = take(colors, mask, 0)
		data = self.graphCoords(data)
		w, h = self.GetSizeTuple()
		xs=float(w)/(self.limits[1]-self.limits[0])
		ys=float(h)/(self.limits[2]-self.limits[3])
		v=ones_like(data)
		v[:,0]=xs
		v[:,1]=ys
		data=column_stack([data, v])
		if min(xs,abs(ys))>4:
			pen =wx.Pen(wx.Color(60,60,60), 1)
		else:
			pen =map(lambda x:wx.Pen(x, 1), colors)
		brush = map(lambda x:wx.Brush(x, wx.SOLID), colors)
		dc.DrawRectangleList(data, pen, brush)

