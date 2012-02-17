#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2007-12-17.

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

from mien.wx.base import *
from mien.wx.graphs.graphFSR import GraphFSR
from numpy import *
from gicspikesort.conditioning import eventCondition
import evtdet, stattests
reload(evtdet)
reload(stattests)

class ThreshTool(BaseGui):
	def __init__(self, dv):
		self.dv=dv
		self.dat=self.dv.data
		BaseGui.__init__(self, dv, title="Threshold Tool", menus=["Data", "Search"], pycommand=True,height=4, showframe=False)
		commands=[
			['Data', 'Close', lambda x:self.Destroy()],
			['Data', 'Set Prefs', self.setPreferences]
			]		  
		self.fillMenus(commands)
		id = wx.NewId()
		
		self.preferences={"Threshold Min":.08, 
			"Threshold Steps":100, 
			"Template Lead (ms)":.5,
			"Template Length":9.0,
			"Dpath":'/evtcon',
			"Trigger Channel":0,
			"Output Channel":1,
			"Window Samples":10,
			"Model Samples":1000,
			"Ensemble Display Mode":'Stats'}
		self.preferenceInfo=[{"Name":'Ensemble Display Mode',
			'Type':'List',
			'Value':['Stats', 'Overlay', 'Sequential', 'Image', "Hist"]}]
		self.current_spike=-1	

		lpan=wx.BoxSizer(wx.VERTICAL)
		self.main.SetSizer(lpan)
		cbox = wx.BoxSizer(wx.HORIZONTAL) 
		modes = evtdet.DETECTORS.keys()
		cbox.Add(wx.StaticText(self.main, -1, "Source Detector"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		self.chooseMode1 = wx.Choice(self.main, -1, choices=modes)
		cbox.Add(self.chooseMode1, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		cbox.Add(wx.StaticText(self.main, -1, "Params"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		self.discPars1= wx.TextCtrl(self.main, -1, ".01,.4", style=wx.TE_PROCESS_ENTER, size=(12,-1))
		wx.EVT_TEXT_ENTER(self.main, self.discPars1.GetId(), lambda x:self.update_self())
		cbox.Add(self.discPars1, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		
		modes = ['Stats', 'Overlay', 'Sequential', 'Image', "Hist"]
		cbox.Add(wx.StaticText(self.main, -1, "Ensemble Display"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		self.chooseMode2 = wx.Choice(self.main, -1, choices=modes)
		cbox.Add(self.chooseMode2, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		self.chooseMode2.SetSelection(modes.index(self.preferences['Ensemble Display Mode']))
		wx.EVT_CHOICE(self.main, self.chooseMode2.GetId(), self.doSetMode)
		cbox.Add(wx.StaticText(self.main, -1, "Params"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		self.discPars2= wx.TextCtrl(self.main, -1, "None", style=wx.TE_PROCESS_ENTER, size=(12,-1))
		wx.EVT_TEXT_ENTER(self.main, self.discPars2.GetId(), lambda x:self.update_self())
		cbox.Add(self.discPars2, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		
		
		btn = wx.Button(self.main, -1, " Detect ")
		cbox.Add(btn, 0, wx.ALIGN_BOTTOM|wx.ALL, 5)
		wx.EVT_BUTTON(self.main, btn.GetId(), self.run)

		
		lpan.Add(cbox, 1, wx.GROW|wx.ALIGN_TOP|wx.ALL, 5)
		cbox = wx.BoxSizer(wx.HORIZONTAL)
		self.graph1=GraphFSR(self.main, -1)
		
		cbox.Add(self.graph1, 3, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		self.graph2=GraphFSR(self.main, -1)
		cbox.Add(self.graph2, 3, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		lpan.Add(cbox, 12, wx.GROW|wx.ALIGN_BOTTOM|wx.ALL, 5)	
		
		self.graph1.SetSize((600,600))
		self.graph2.SetSize((600,600))
		self.graph1.fs=self.dv.graph.fs
		self.graph2.fs=self.dv.graph.fs
		self.SetSize((1300,800))
		self.main.SetSizerAndFit(lpan)
	
		
		self.load_saved_prefs()
		
		self.dv.preferences["Number of Undo Steps"]=0
		self.dv.data.setUndoLength(0, True)
		self.dv.report('Disabled Undo. Use Checkpoints Instead.')
		
		temps=self.dat.getSubData(self.preferences['Dpath'])
		if not temps:
			self.dat.createSubData(self.preferences['Dpath'])
		try:	
			self.makeModels()
		except:
			self.report('cant cache models. Try changing channel settings')	
		self.Show(True)
		
		
	def makeModels(self):
		self.models=[]
		length=self.preferences["Window Samples"]
		sp=self.preferences["Model Samples"]
		sd=self.dat.getData(chans=[self.preferences["Trigger Channel"]])
		self.models.append(stattests.summary(sd, length, sp))
		sd=self.dat.getData(chans=[self.preferences["Output Channel"]])
		self.models.append(stattests.summary(sd, length, sp))
			
	def onSetPreferences(self):
		self.makeModels()
		self.run()
		
	def showPV(self, g, i, p):
		dat=self.dat.getSubData(p)
		data=dat.getData()
		data=data.mean(1)
		mod=self.models[i]
		pv=stattests.deviationVector(data, mod)
		pn=g.addPlot(pv, style='envelope')
		g.fullScale()
		g.DrawAll()
	
		
	def showEvts(self, g, p):
		g.plots={}
		dat=self.dat.getSubData(p)
		data=dat.getData()
		mi=data.min()
		ma=data.max()
		pad=.025*ma-mi
		q=self.chooseMode2.GetSelection()
		q=self.chooseMode2.GetString(q)
		opts={}
		if q=='Stats':
			me=reshape(mean(data, 1), (-1, 1))
			sd=reshape(std(data, 1), (-1, 1))
			data=concatenate([me-sd, me, me+sd], 1)
			opts['style']='envelope'
		elif q=='Overlay':
			opts['style']='envelope'
		elif q=='Sequential':
			opts['style']='envelope'
			data=reshape(transpose(data), (-1, 1))
		elif q=='Image':
			opts['style']='image'
			opts['colorrange']=[mi, ma]
		pn=g.addPlot(data, **opts)
		g.fullScale()
		g.DrawAll()
		
		
	def doSetMode(self, event):
		self.showEvts(self.graph1, self.preferences["Dpath"]+'/evts1')
		self.showEvts(self.graph2, self.preferences["Dpath"]+'/evts2')		
		
	def run(self, event=None):
		i=self.chooseMode1.GetSelection()
		sdf=self.chooseMode1.GetString(i)
		sdf=evtdet.DETECTORS[sdf]
		pars=self.discPars1.GetValue()
		pars=eval(pars)
		if type(pars) in [float, int]:
			pars=(pars,)
		else:
			pars=tuple(pars)
		sel=(None, [self.preferences["Trigger Channel"]], None)
		path=self.preferences["Dpath"]+'/spikes1'
		if self.dat.getSubData(path):
			self.dat.getSubData(path).sever()
		sdf(self.dat, sel, pars, path)
		eventCondition(self.dat, dpath=path, select=sel, lead=self.preferences["Template Lead (ms)"], length=self.preferences["Template Length"], newpath=self.preferences["Dpath"]+'/evts1', milliseconds=True)
		sel=(None, [self.preferences["Output Channel"]], None)
		
		eventCondition(self.dat, dpath=path, select=sel, lead=self.preferences["Template Lead (ms)"], length=self.preferences["Template Length"], newpath=self.preferences["Dpath"]+'/evts2', milliseconds=True)
		
		self.showEvts(self.graph1, self.preferences["Dpath"]+'/evts1')
		self.showPV(self.graph1, 0, self.preferences["Dpath"]+'/evts1')
		self.showEvts(self.graph2, self.preferences["Dpath"]+'/evts2')
		self.showPV(self.graph2, 1, self.preferences["Dpath"]+'/evts2')
		
		
		
		
		
		
		
		
		