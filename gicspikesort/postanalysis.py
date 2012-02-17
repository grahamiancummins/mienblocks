#!/usr/bin/env python
# encoding: utf-8
#Created by Graham Cummins on 2007-09-25.

# Copyright (C) 2007 Graham I Cummins
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


import sorter
reload(sorter)
from sorter import *
from mien.datafiles.viewer import * 
from mien.dsp.widgets import SubDataBrowse
from mien.wx.graphs.graph import Graph, colorscale

import time
import wavestats
WAVESTATS=wavestats.FUNCTIONS.copy()
for k in WAVESTATS.keys():
	if k.startswith("DM:"):
		del(WAVESTATS[k])


class SpikeSorterPostAnalysis(BaseGui):
	def __init__(self, dv):
		self.dv=dv
		BaseGui.__init__(self, dv, title="Spike Sorter Analysis", menus=["Data", "Displays"], pycommand=False,height=4, showframe=False)	

		commands=[
		    ['Data', 'Precondition Data', self.precon]
		    ['Data', 'Convert Events to Templates', self.buildtemp]
			['Displays', 'Stored Template', self.showTemplate], 
			['Displays', 'Calculated Template', self.showCalcTemplate], 
			['Displays', 'Calculated - Stored Template', self.showTemplateDiff], 	
			['Displays', 'Current Spike Residual', self.showCSResid], 	
			['Displays', 'Plot Wave Stats (hist)', self.showStats],
			['Displays', 'Plot Wave Stats (scatter)', self.showStats2]
			]

		self.fillMenus(commands)
		outer = wx.BoxSizer(wx.VERTICAL)
		
		cbox = wx.BoxSizer(wx.HORIZONTAL)
		btn = wx.Button(self.main, -1, " Prev ")
		cbox.Add(btn, 0, wx.ALIGN_BOTTOM|wx.ALL, 5)
		wx.EVT_BUTTON(self.main, btn.GetId(), self.lastSpike)
		btn = wx.Button(self.main, -1, " Next ")
		cbox.Add(btn, 0, wx.ALIGN_BOTTOM|wx.ALL, 5)
		wx.EVT_BUTTON(self.main, btn.GetId(), self.nextSpike)
		
		outer.Add(cbox, 0, wx.GROW|wx.ALIGN_TOP|wx.ALL, 5)
		
		self.tgraph=GraphFSR(self.main, -1)
		outer.Add(self.tgraph, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		self.tgraph.fs=self.dv.graph.fs
		self.tgraph.axis["ticks"] = 0
		self.tgraph.legend = False
		self.selected=-1

		self.main.SetSizerAndFit(outer)
		self.main.SetClientSize(self.main.GetBestSize())
		self.Show(True)

	def update_self(self, **kwargs):
		pass
		
	def precon(self, event):
		pass
		
	def buildtemp(self, event):
		pass

	def showCalcTemplate(self, event):
		td=self.getCalcTemp()
		self.displayTemp(td)
		
	def showTemplateDiff(self, event):
		cd=self.getCalcTemp()
		sd=self.getStoredTemplate()
		self.displayTemp(cd-sd)

	def displayTemp(self, tid):
		self.tgraph.plots={}
		self.tgraph.fs=self.dv.graph.fs
		l=tid.shape[0]/self.dv.data.fs()
		self.tgraph.limit(array([0, l, 0, 1.0]))
		self.tgraph.addPlot(tid, style="image", colorrange='local', offset=0.0, height=tid.shape[1], order=1)
		try: 
			self.tgraph.fullScale()
			self.tgraph.DrawAll()
		except:
			pass

	def getStoredTemplate(self):
		ti=self.dv.data.getSubData('/hidden/template')
		tid=ti.getData()
		nc=tid.shape[1]/2
		sep=zeros((tid.shape[0], 1), tid.dtype)
		cs1=slice(0, tid.shape[1], 2)			
		cs2=slice(1, tid.shape[1], 2)
		me=tid[:,cs1]
		sep+=me.min()
		sd=tid[:,cs2]
		sd=sd*-1
		tid=concatenate([me, sep, sd], 1)
		return tid

	def getCalcTemp(self):
		w=self.getSpikeWaves()
		tm=w.mean(2)
		ts=w.std(2)
		sep=zeros((tm.shape[0], 1), tm.dtype)
		sep+=tm.min()
		tid=concatenate([tm, sep, ts], 1)
		return tid
		
	def showTemplate(self, event=None):
		tid=self.getStoredTemplate()
		self.displayTemp(tid)


	def showCSResid(self, event):
		lims=self.ss.getSelectedSpikeWindow(True)
		if lims==None:
			return
		self.tgraph.plots={}
		self.tgraph.fs=self.dv.graph.fs
		ti=self.ss.getTemp('template')
		if ti[1]:
			tid=ti[1].getData()
			me=tid[:, arange(0, tid.shape[1], 2)]
			dat=self.ss.dv.data.getData()[lims[0]:lims[0]+me.shape[0],:]
			dat=me-dat
			l=tid.shape[0]/self.dv.data.fs()
			self.tgraph.limit(array([0, l, 0, 1.0]))
			self.tgraph.addPlot(dat, style="image", colorrange='local', offset=0.0, height=dat.shape[1], order=1)
		try: 
			self.tgraph.fullScale()
			self.tgraph.DrawAll()
		except:
			pass

	def bounceStats(self, event):
		reload(wavestats)
		for k in WAVESTATS.keys():
			if not wavestats.FUNCTIONS.has_key(k):
				del(WAVESTATS[k])
		WAVESTATS.update(wavestats.FUNCTIONS)
		
	def getSpikeWaves(self):
		'''return an array "waves" or None if there are none defined. The array has three dimensions, (samples, channels, events)'''
		waves=self.dv.data
		wd=waves.getData()
		reps=waves.attrib('Reps')	
		waves=reshape(wd, (wd.shape[0],-1,reps))
		return waves
		
	def getWaveformStats(self, whichstat):
		w=self.getSpikeWaves()
		if w==None:
			return w
		st=WAVESTATS[whichstat](w, None)
		return st
				
	def showStats(self, event=None):
		d=self.askParam([{"Name":"Select Stats", "Type":"Select", "Value":WAVESTATS.keys()}])
		if not d:
			return
		if not d[0]:
			d[0]=WAVESTATS.keys()
		ofs=0	
		self.tgraph.plots={}
		self.tgraph.fs=1
		for n in d[0]:
			st=self.getWaveformStats(n)
			if st==None:
				self.report("Can't get stat %s" % n)
				continue
			sv=st.min()
			si=(st.max()-sv)/100.0
			rhist=hist2(st, si, sv)
			mhv=rhist.max()
			self.report("%s: %.4g to %.4g with binwidth %.4g" % (n, sv, sv+si*rhist.shape[0], si))
			n=self.tgraph.addPlot(rhist, style="hist", name=n, start=0, binwidth=1, offset=ofs)
			ofs=ofs-2.0-mhv
		self.tgraph.fullScale()
		self.tgraph.DrawAll()	
	
	def subPlot(self, s="Plot"):
		bar = {'size':(400,400), 'style':wx.DEFAULT_FRAME_STYLE|wx.NO_FULL_REPAINT_ON_RESIZE, 'title':s}
		f=wx.Frame(self, -1, **bar)
		g=Graph(f, -1)
		f.Show(True)
		g.killframe = f.Destroy
		self.subplot=g
		g.OnAltClick=lambda x:self.subAltClick(x)
		return g
	
	def subAltClick(self, event):
		x=event.GetX()
		y=event.GetY()
		dat=self.subplot.plots['SSStats']['data']
		dat=self.subplot.graphCoords(dat)
		spike=argmin(eucd(dat, array([x,y])))
		c=zeros(dat.shape[0])
		c[spike]=1.0
		self.selected=spike
		self.showSpike(self.selected)
		self.subplot.plots["SSStats"]['colorlist']=colorscale(c, 'hot', (-1,1.2))
		self.subplot.DrawAll()
		
	def showStats2(self, event=None):
		stats=WAVESTATS.keys()
		optstats=["None"]+stats
		d=self.askParam([{"Name":"X Axis", "Type":"List", "Value":stats},
						 {"Name":"Y Axis", "Type":"List", "Value":stats},
						 {"Name":"Color",  "Type":"List", "Value":optstats},
						 {"Name":"Point Size",  "Type":"List", "Value":optstats},
						  ])
		if not d:
			return
		g=self.subPlot("%s vs %s" % (d[1], d[0]))
		x=self.getWaveformStats(d[0])	
		self.report("X axis is %s: %.4g to %.4g" % (d[0], x.min(), x.max()))
		y=self.getWaveformStats(d[1])	
		self.report("Y axis is %s: %.4g to %.4g" % (d[1], y.min(), y.max()))
		x=column_stack([x, y])
		c=None
		w=None
		if d[2]!="None":
			c=self.getWaveformStats(d[2])
			self.report("Color is %s: %.4g to %.4g" % (d[2], c.min(), c.max()))
			g.addCscale(c, 'hot')
			c=colorscale(c, 'hot')
		if d[3]!="None":
			w=self.getWaveformStats(d[3])
			self.report("Point size is %s: %.4g to %.4g" % (d[3], w.min(), w.max()))
			w=w-w.min()
			w=w/w.max()
			w=4+15*w
		g.addPlot(x, style="points", colorlist=c, widthlist=w, width=6, name="SSStats")
		g.fullScale()
		g.DrawAll()

	def showSpike(self, i):
		q=self.dv.preferences['Ensemble display mode']
		if q!='Sequential':
			self.dv.preferences['Ensemble display mode']='Sequential'
			self.dv.onSetPreferences()
		ln=self.dv.data.getData().shape[0]
		self.report('showing spike %i' % i)
		sti=ln*i/self.dv.graph.fs
		spi=(ln*i+ln)/self.dv.graph.fs
		l=self.dv.graph.limits.copy()
		l[0]=sti
		l[1]=spi
		self.dv.graph.limit(l)
		self.dv.graph.DrawAll()
		
	def nextSpike(self, event):
		self.selected+=1
		if self.selected>=self.dv.data.attrib('Reps'):
			self.selected=0
		self.showSpike(self.selected)
		
	def lastSpike(self, event):
		self.selected-=1
		if self.selected<0:
			self.selected=self.dv.data.attrib('Reps')-1
		self.showSpike(self.selected)