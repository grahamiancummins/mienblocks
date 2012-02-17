#!/usr/bin/env python
# encoding: utf-8
#Created by gic on 2007-05-03.

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
WAVESTATS=wavestats.FUNCTIONS


class SSAnalysis(BaseGui):
	def __init__(self, ss):
		self.ss=ss
		self.ss.update_analysis=self.local_update
		self.dv=ss.dv
		BaseGui.__init__(self, ss, title="Spike Sorter Analysis", menus=["Displays", "Commands", "Selection"], pycommand=False,height=4, showframe=False)	

		commands=[
			['Displays', 'Show Current Template', self.showTemplate], 	
			['Displays', 'Store Template', self.saveTemplate], 	
			['Displays', 'Show Stored Template', self.showStoredTemplate], 	
			['Displays', 'Show Template Diff', self.showDiffTemplate], 	
			['Displays', 'Current Spike Residual', self.showCSResid], 	
			['Displays', 'Spikes/Threshold', self.showThreshSurvey],
			['Displays', 'Jitter', self.showJitter],
			['Displays', 'Plot Wave Stats (hist)', self.showStats],
			['Displays', 'Plot Wave Stats (scatter)', self.showStats2],
			['Commands', 'Swap Markers', self.swapMarks],
			['Commands', 'Reload Wave Stat Functions', self.bounceStats],
                        ['Commands', 'KlustaKwik Separate', self.kkSep],
			['Selection', 'Select Events', self.selectEvents],
			['Selection', 'Append To Selection', lambda x:self.selectEvents(None, True)],
			['Selection', 'Cache Spikes', self.cacheEvents],
			['Selection', 'Invert Selection', self.flipSelect],
			['Selection', 'Use Selection for Detected Spikes', self.useSelect],
			['Selection', 'Use Cached Spikes for Detected Spikes', self.revertSelect],
			['Selection', 'Clear Selection (and cache)', self.clearSelect],
			['Selection', 'Highlight Selected', self.showSelectedEvents],
			]

		self.fillMenus(commands)
		outer = wx.BoxSizer(wx.HORIZONTAL)
		self.tgraph=GraphFSR(self.main, -1)
		outer.Add(self.tgraph, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		self.tgraph.fs=self.dv.graph.fs
		self.tgraph.axis["ticks"] = 0
		self.tgraph.legend = False
		sw=self.ss.preferences['Screen Width']
		sh=self.ss.preferences["Screen Height"]
		dvw=round(3*sw/4.0)
		dvh=round(.55*sh)
		self.showing=None	

		self.main.SetSizerAndFit(outer)
		self.main.SetClientSize(self.main.GetBestSize())
		self.SetDimensions(dvw, dvh, sw-dvw, sh-dvh)
		self.dataRefs={}
		self.selected_events=[]

	def update_self(self, **kwargs):
		pass
		
	def local_update(self, what):
		if what=='selectspike':
			if self.showing=='resid': 
				self.showCSResid(None)
			try:
				dat=self.subplot.plots['SSStats']['data']
				c=zeros(dat.shape[0])
				c[self.ss.current_spike]=1.0
				self.subplot.plots["SSStats"]['colorlist']=colorscale(c, 'hot', (-1,1.2))
				self.subplot.DrawAll()
			except:
				pass

	def swapMarks(self, event):
		self.tgraph.xmarkers, self.ss.rgraph.ymarkers = self.ss.rgraph.ymarkers, self.tgraph.xmarkers
		self.tgraph.DrawAll()
		self.ss.rgraph.drawMarkers()


	def displayTemp(self, tn):
		if type(tn)==str:
			ti=self.ss.getTemp(tn)
			if not ti[1]:
				self.report("no template found")
				self.tgraph.plots={}
				self.tgraph.DrawAll()
				self.showing='nothing'
				return	
			self.tgraph.plots={}
			self.tgraph.fs=self.dv.graph.fs
			tid=ti[1].getData()	
		else:
			tid=tn	
		nc=tid.shape[1]/2
		sep=zeros((tid.shape[0], 1), tid.dtype)
		cs1=slice(0, tid.shape[1], 2)			
		cs2=slice(1, tid.shape[1], 2)
		me=tid[:,cs1]
		sep+=me.min()
		sd=tid[:,cs2]
		sd=sd*-1
		self.report("Mean range %.3g to %.3g, std range %.3g to %.3g" % (me.min(), me.max(), sd.min(), sd.max()))
		tid=concatenate([me, sep, sd], 1)
		l=tid.shape[0]/self.dv.data.fs()
		self.tgraph.limit(array([0, l, 0, 1.0]))
		self.tgraph.addPlot(tid, style="image", colorrange='local', offset=0.0, height=tid.shape[1], order=1)
		sjt=self.ss.getTemp('shiftjitter')
		if 	sjt[1]:
			lead=ti[1].attrib('Lead')
			out=sjt[1].getData()
			me=round(out.mean(0))
			sd=out.std(0)
			marks=zeros((2*sd.shape[0]+1, 2), sd.dtype)
			marks[0,0]=lead
			for i in range(sd.shape[0]):
				marks[2*i+1,0]=me[i]+lead
				marks[2*i+1,1]=i+1
				marks[2*i+2,0]=sd[i]+me[i]+lead
				marks[2*i+2,1]=i+1			
			n=self.tgraph.addPlot(marks, style="raster", offset=sd.shape[0]+2, height=sd.shape[0]+1, width=1, spacing=0, order=0) 
		try: 
			self.tgraph.fullScale()
			self.tgraph.DrawAll()
		except:
			pass
		self.showing='template'	

	def showTemplate(self, event=None):
		self.displayTemp('template')

	def saveTemplate(self, event):
		ti=self.ss.getTemp('template')
		if not ti[1]:
			self.report("No current template")
			return
		name=self.askParam([{"Name":"Label for Template", "Value":"old"}])
		if not name:
			return
		name="%s_template" % name
		tc=ti[1].clone()
		tc.setName(name)
		ti[1].container.newElement(tc)
		self.report('copied template to %s' % tc.dpath())
		
	def showDiffTemplate(self, event):
		t=self.ss.getTemp(None)
		temps=t.getElements('Data', depth=1)
		temps=[t.name() for t in temps if "template" in t.name()]
		if not len(temps)>1:
			self.report('No stored Templates')
			return
		d=self.askParam([{'Name':"Starting template", 'Type':'List', 'Value':temps}, {'Name':"Subtract template", 'Type':'List', 'Value':temps}])
		if not d:
			return
		ti=self.ss.getTemp(d[0])
		tid=ti[1].getData()
		s2=ti[1].shape()
		if s2[0]!=tid.shape[0] or s2[1]!=tid.shape[1]:
			self.report("these templates don't have the same size: %s vs %s" % (repr(tid.shape), repr(s2)))
			return
		ti=self.ss.getTemp(d[1])
		tid=tid-ti[1].getData()
		self.displayTemp(tid)
	
	def showStoredTemplate(self, event):
		t=self.ss.getTemp(None)
		temps=t.getElements('Data', depth=1)
		temps=[t.name() for  t in temps if "template" in t.name()]
		if not temps:
			self.report('No stored Templates')
			return
		d=self.askParam([{'Name':"Which template", 'Type':'List', 'Value':temps}])
		if not d:
			return
		self.displayTemp(d[0])

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
		self.showing='resid'

	def showJitter(self, event=None):
		sjt=self.ss.getTemp('shiftjitter')
		if not sjt[1]:
			self.ss.djTemp(None)
			sjt=self.ss.getTemp('shiftjitter')
			if not sjt[1]:
				return
		out=sjt[1].getData()
		me=round(out.mean(1)) #should we consider propogation lengths?
		sv=me.min()
		h=hist2(me, 1, sv)
		self.tgraph.plots={}
		self.tgraph.fs=1.0
		n=self.tgraph.addPlot(h, style="hist", start=sv, binwidth=1) 
		self.tgraph.fullScale()
		self.tgraph.DrawAll()
		self.showing='jitter'


	def bounceStats(self, event):
		reload(wavestats)
		for k in WAVESTATS.keys():
			if not wavestats.FUNCTIONS.has_key(k):
				del(WAVESTATS[k])
		WAVESTATS.update(wavestats.FUNCTIONS)

	def showThreshSurvey(self, event=None):
		dat=self.ss.discriminant
		mi=dat.min()
		me=dat.mean()
		sd=dat.std()
		ht=me-3*sd
		#ht=me   
		if ht<mi:
			self.report("Data are too noisy to survey")
			print lt, ht, mi, me, sd
			return
		ns=50
		ts=(ht-mi)/ns
		tv=arange(mi+ts, ht, ts)
		#print tv
		sc=zeros_like(tv)
		for i in range(tv.shape[0]):
			thresh=tv[i]
			sp=ngtc(dat, thresh)
			sc[i]=sp.shape[0]
		self.tgraph.fs=1.0/ts
		self.tgraph.plots={}
		self.tgraph.addPlot(sc, start=tv[0]) 
		self.tgraph.fullScale()
		self.tgraph.DrawAll()
		
	def getSpikeWaves(self):
		'''return an array "waves" or None if there are none defined. The array has three dimensions, (samples, channels, events)'''
		waves=self.ss.getTemp('waves')
		if not waves[1]:
			self.report("Waves are not defined. Can't continue")			
			return None
		wd=waves[1].getData()
		reps=waves[1].attrib('Reps')	
		waves=reshape(wd, (wd.shape[0],-1,reps))
		return waves
		
	def getWaveformStats(self, whichstat):
		w=self.getSpikeWaves()
		if w==None:
			return w
		st=WAVESTATS[whichstat](w, self.ss)
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
		self.showing='stats'	
	
	def kkSep(self, event=None):
		import sep.klustakwikfuncs as kk
		import numpy as n
		from sep.spikesortfile import best_of_N
		d=self.askParam([{"Name":"Select Stats", "Type":"Select", "Value":WAVESTATS.keys()}])
		if not d:
			return
		if not d[0]:
			d[0]=WAVESTATS.keys()
		print self.ss.getTemp('spikes')
		for n in d[0]:#why are there potentially multiple WAVESTATS.keys()?
			st=self.getWaveformStats(n)
			if st==None:
				self.report("Can't get stat %s" % n)
				continue
			groups = kk.run_KlustaKwik(st,'localtest')
			print groups 
		if len(unique(groups)) > 2:#if KK reads multiple goups according to selected metric
			#find the largest group
			counts=[]
			for m in range(max(groups)):
				counts.append(sum(groups==m))
			goodval = n.argmax(counts)
			goods = []
			for c in range(len(groups)):
				if groups[c]==goodval:
					goods.append(c)
			#REMOVE GIVEN SPIKES 
			spi = self.ss.getTemp('spikes')
                        evts = spi[1].getData()
			evts = evts[goods]
			spi[1].datinit(evts, spi[1].header())
			self.ss.update_all(object=spi[1], nossrecalc=True, calc_offsets=False)
			self.ss.calc_templ()
	
	def subPlot(self, s="Plot"):
		bar = {'size':(400,400), 'style':wx.DEFAULT_FRAME_STYLE|wx.NO_FULL_REPAINT_ON_RESIZE, 'title':s}
		f=wx.Frame(self, -1, **bar)
		g=Graph(f, -1)
		f.Show(True)
		g.killframe = f.Destroy
		self.subplot=g
		g.contextMenuContents.append(("SpikeSort: Select Events",self.selectEvents))
		wx.EVT_MIDDLE_UP(g, self.subAltClick)
		g.OnAltClick=lambda x:self.subAltClick(x)
		return g
	
	def subAltClick(self, event):
		x=event.GetX()
		y=event.GetY()
		dat=self.subplot.plots['SSStats']['data']
		dat=self.subplot.graphCoords(dat)
		spike=argmin(eucd(dat, array([x,y])))
		self.ss.current_spike=spike
		self.ss.show_spike()
		c=zeros(dat.shape[0])
		c[spike]=1.0
		self.subplot.plots["SSStats"]['colorlist']=colorscale(c, 'hot', (-1,1.2))
		self.subplot.DrawAll()
		
	
	def cacheEvents(self, event=None):	
		waves=self.ss.getTemp('waves')
		if not waves[1]:	
			return None
		evts=self.ss.getTemp('spikes')
		if not evts[1]:
			return None
		self.dataRefs['cachedevents']=evts[1].getData()[:,0]
		self.report("Cached spike times")
		return True
		
		
		
	def showStats2(self, event=None):
		check=self.cacheEvents()
		if not check:
			self.report("No waveform or event templates")
			return 
		stats=WAVESTATS.keys()
		optstats=["None"]+stats
		d=self.askParam([{"Name":"X Axis", "Type":"List", "Value":stats},
						 {"Name":"Y Axis", "Type":"List", "Value":stats},
						 {"Name":"Color",  "Type":"List", "Value":optstats},
						 {"Name":"Point Size",  "Type":"List", "Value":optstats},
						  ])
		if not d:
			return
		print d[0]
		x=self.getWaveformStats(d[0])	
		self.report("X axis is %s: %.4g to %.4g" % (d[0], x.min(), x.max()))
		y=self.getWaveformStats(d[1])	
		self.report("Y axis is %s: %.4g to %.4g" % (d[1], y.min(), y.max()))
		x=column_stack([x, y])
		c=None
		w=None
		g=self.subPlot("%s vs %s" % (d[1], d[0]))
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
		n=g.addPlot(x, style="points", width=6, name="SSStats")
		if c:
			g.plots[n]['colorlist']=c
		if w!=None:
			g.plots[n]['widthlist']=w
		g.fullScale()
		g.DrawAll()
		
	
	def clearSelect(self, evt):
		self.dataRefs['cachedevents']=None
		self.selected_events=[]
	
	def selectEvents(self, event, append=False):
		xm=[m['loc'] for m in self.subplot.xmarkers]
		ym=[m['loc'] for m in self.subplot.ymarkers]
		if len(xm)>2 or len(ym)>2:
			self.report("Please use no more than 2 markers in each dimension for this function")
			return 	
		dat=self.subplot.plots['SSStats']['data']
		if len(xm)==0:
			mask=ones(dat.shape[0])
		elif len(xm)==1:
			d=self.askParam([{"Name":"On X axis: select", "Type":"List", "Value":["Left of marker", "Right of marker"]}])
			if not d:
				return
			if d[0].startswith("L"):	
				mask=dat[:,0]<xm[0]
			else:
				mask=dat[:,0]>xm[0]
		elif len(xm)==2:
			mask=logical_and(dat[:,0]>min(xm), dat[:,0]<max(xm))
		if len(ym)==1:
			d=self.askParam([{"Name":"On Y axis: select", "Type":"List", "Value":["Below marker", "Above marker"]}])
			if not d:
				return
			if d[0].startswith("B"):	
				mask=logical_and(mask, dat[:,1]<ym[0])
			else:
				mask=logical_and(mask, dat[:,1]>ym[0])
		elif len(ym)==2:
			mask=logical_and(mask, logical_and(dat[:,1]>min(ym), dat[:,1]<max(ym)))
		sel=nonzero(mask)[0]
		if append and len(self.selected_events):
			self.selected_events=union1d(self.selected_events, sel)
		else:
			self.selected_events=sel
		self.showSelectedEvents()
		self.report("Selected %i events" % (self.selected_events.shape[0]))
		
	def showSelectedEvents(self, event=None):
		try:
			p=self.subplot.plots['SSStats']
			if len(self.selected_events):
				c=zeros(p['data'].shape[0])
				put(c, self.selected_events, 1)
				p['colorlist']=colorscale(c, 'hot', (-1,1.2))
			else:
				p['colorlist']=None
			self.subplot.DrawAll()
		except:
			pass
		evts=self.ss.getTemp('spikes')
		if evts[1] and len(self.selected_events):
			for n in self.ss.rgraph.plots.keys():
				if self.ss.rgraph.plots[n]['style']=='evts':
					del(self.ss.rgraph.plots[n])
			evts=evts[1].getData()
			sel=take(evts, self.selected_events, 0)
			unsel=take(evts, setdiff1d(arange(evts.shape[0]), self.selected_events), 0)
			st=domain(self.ss.dv.data)[0]
			self.ss.rgraph.addPlot(sel,style="evts", start=0, color=(250, 0, 0))
			self.ss.rgraph.addPlot(unsel,style="evts", start=0, color=(125, 125, 125))
			self.ss.rgraph.DrawAll()
		
			
	def flipSelect(self, event):
		spikes=arange(self.dataRefs['cachedevents'].shape[0])
		self.selected_events=setdiff1d(spikes, self.selected_events)
		self.showSelectedEvents()
		
	def revertSelect(self, event):
		self.ss.setDetectedEvents(self.dataRefs['cachedevents'])
	
	def useSelect(self, event):
		if not len(self.selected_events):
			self.report("No selection")
		spikes=take(self.dataRefs['cachedevents'], self.selected_events)
		self.ss.setDetectedEvents(spikes)
		
		
