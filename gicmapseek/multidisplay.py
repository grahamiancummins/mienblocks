#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2008-08-20.

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

from mien.wx.base import *
from gicmapseek.graphers import SpaceGraph, EVT_RETURN_PT
from mien.dsp.gui import editBlock
from mien.nmpml.data import newData
from numpy import array, zeros, around
import time
import debuggers


class NavGui(BaseGui):
	
	def __init__(self, master=None, model=None, **kwargs):
		BaseGui.__init__(self, master, title="Navigational Solver UI", menus=["File", "Build", "Run", "Display", "Debug"], pycommand=not bool(master),height=4, showframe=False)
		if master:
			self.document=master.document	
		if model:
			self.alg=model
		else:
			self.alg=None
		
		controls=[
					  ["Build", "Select/Create Model", self.setModel],
					  ["Build", "Set Bias Field", self.setBias],
					  ["Build", "Configure Bias Field Conditioning", self.confBias],
					  ["Build", "Save Conditioned Field as Base", self.swapBias],
					  ["Build", "Set Start and Target Points", self.setGoal],
					  ["Build", "Choose Algorithm", self.setAlg],
					  ["Build", "Configure Algorithm", self.config],
					  ["Run", "Full Solve", self.runAll],
					  ["Display", "Show Raw Bias Field", self.rawBias],
					  ["Display", "Show Conditioned Bias Field", self.condBias],
					  ["Debug", "Reload Blocks", self.bounceDSP],
					  ["Debug", "Launch Debugger", self.debug],
				 ]
		if not master:
			controls.append(["Build", 'Launch Data Editor', self.launchEditor])
		self.fillMenus(controls)
		self.stdFileMenu()	
		self.biasmode='raw'
		
		self.displaytype='bias'
		
		self.mainSizer = wx.BoxSizer(wx.VERTICAL)
		self.main.SetSizer(self.mainSizer)
		self.main.SetAutoLayout(True)
		
		self.graph=SpaceGraph(self.main)
		self.graph.report=self.report
		# self.graph.OnShiftClick=self.selectPoint
		
		self.mainSizer.Add(self.graph, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		self.graph.Show(True)
		self.graph.SetDropTarget(self.dropLoader)

		self.mainSizer.Fit(self.main)
		self.SetSize(wx.Size(600,700))
		if not self.alg:
			try:
				self.setModel()
			except:
				self.report('you may need to build or debug the model')


						
	def launchEditor(self, event=None):
		from mien.interface.main import MienGui
		d=MienGui(self)
		d.newDoc(self.document)
		

	def bounceDSP(self, event):
		import mien.dsp.modules
		fl=mien.dsp.modules.refresh()
		if fl:
			self.report('Reload generated some errors: %s' % (str(fl),))
		else:
			self.report("Reload complete")	

	def setModel(self, event=None):
		if not self.document:
			self.report('no document (create one with file->New)')
			return
		df=self.document.getElements('AbstractModel', depth=1)	
		if not df:
			self.report("There are no navigational models in this document. Creating blank model")
			abst=self.createElement('AbstractModel', {'Name':'NavModel'})
			self.document.newElement(abst)
			self.alg=abst
		elif len(df)==1:
			self.alg=df[0]
		else:
			amp={}
			for a in df:
				amp[a.upath()]=a
			d=self.askParam([{'Name':'Which Model?', 'Type':'List', 'Value':amp.keys()}])
			if d:
				self.model=amp[d[0]]
			else:
				abst=self.createElement('AbstractModel', {'Name':'NavModel'})
				self.document.newElement(abst)
				self.alg=abst
		self.scrubModel()
		
		
	def _verify_component(self, index, function):
		if not len(self.alg.elements)>index:
			obj=self.createElement('MienBlock', {'Function':function[0]})
			self.alg.newElement(obj)
			return True
		o=self.alg.elements[index]
		if o.__tag__=='MienBlock' and o.attrib('Function') in function:
			return True
		print index, function, o.attributes
		a=self.askUsr('Component %i is not appropriate for a nav problem' % index, ['Rebuild it', 'Select a different model', 'Create a new model', 'Abort'])
		if a.startswith("R"):
			if o.__tag__=='MienBlock':
				for e in o.elements[:]:
					e.sever()
				o.setAttrib('Function', function[0])
			else:
				o.sever()
				obj=self.createElement('MienBlock', {'Function':function[0]})
				self.alg.newElement(obj)
				self.arg.reorderElement(obj, index)
			self.report('Model element has been rebuilt. You will need to configure the new element')
			return True
		if a.startswith('S'):
			self.setModel()
		elif a.startswith('C'):
			self.report("Creating blank model")
			abst=self.createElement('AbstractModel', {'Name':'NavModel'})
			self.document.newElement(abst)
			self.alg=abst
			self.scrubModel()
			self.update_all(object=self.alg, event='create')
			self.report('New model created. You will need to set the bias, conditions, and algorithm now')
		else:
			self.alg=None
			self.report("No model is selected. All operations other than loading a new document will fail!!")
		return False
			
		
	def scrubModel(self):
		l=[['mien.dsp.nmpml.receiveData'], ['gicmapseek.dsp.setGoals'] ,['gicmapseek.dsp.conditionBias'], self.getAlgList()]
		for i, fl in enumerate(l):
			if not self._verify_component(i, fl):
				break

	def onNewDoc(self):
		self.setModel()
		try:
			self.drawBias(True)
		except:
			self.report('Not able to show problem (model is not complete?)')
		
	def setBias(self, event):
		if not self.alg:
			self.setModel()
		g=self.alg.elements[0]
		d = self.load(returndoc=True)
		d=d.getElements('Data', depth=1)[0]
		if d.stype()=='image':
			self.report('converting image to 2D bias')
			dat = d.getData()
			dat = dat.mean(3)
			dat = dat.mean(2)
			h = d.header()
			h['SampleType']='sfield'
			d.datinit(dat, h)
		de=g.getElements('Data')
		if de:
			de[0].mirror(d, True)
		else:
			g.newElement(d)
		dp=g.getElements('Data')[0].upath()
		editBlock(g, self, args={'upath':dp, 'dpath':'/', 'recurse':False})
		self.biasmode='raw'
		self.drawBias()
		
	def setGoal(self, event):
		EVT_RETURN_PT(self, self.continueSetGoal)
		if self.biasmode!='raw':
			self.biasmode='raw'
			self.drawBias()
		elif not self.graph.plots.has_key('bias'):
			self.drawBias()
		sd, td = self.getSandT()
		# if sd.shape[0]!=0:
		# 	a=self.askUsr("The current source is %s." % (str(sd[0],),), ['Keep', 'Change'])
		# 	if a == 'Keep':
		# 		self.continueSetGoal('keep')
		# 		return
		self.report('Select (click on) source point')
		self.graph.getAPoint(self, 'source')
			
	def continueSetGoal(self, event):
		if type(event)==str:
			mode=event
		else:
			mode=event.mode
		g=self.alg.elements[1]
		if mode=='source':
			print event.pt
			source=g.getElements('Data', {'Name':'Source'}, depth=1)[0]
			source.datinit( array([[event.pt[0], event.pt[1], 0]]), {"SampleType":'locus'})
		targ=g.getElements('Data', {'Name':'Target'}, depth=1)[0]
		if mode!='target':
			td=targ.getData()
			# if td.shape[0]!=0:
			# 	a=self.askUsr("The current target is %s." % (str(td[0],),), ['Keep', 'Change'])
			# 	if a == 'Keep':
			# 		return
			self.report('Select (click on) target point')
			self.graph.getAPoint(self, 'target')
		if mode=='target':
			print event.pt
			targ.datinit( array([[event.pt[0], event.pt[1], 0]]), {"SampleType":'locus'})
			self.drawBias(True)
			
		
		
	
	def getSandT(self):
		g=self.alg.elements[1]		
	 	par=g.getElements("Parameters")
		if par:
			par=par[0]
		else:
			par=self.createElement("Parameters", {})
			g.newElement(par)
		par.setValue({'upathSource':g.upath()+"Data:Source", 'upathTarget':g.upath()+"Data:Target"})
		source=g.getElements('Data', {'Name':'Source'}, depth=1)
		if source:
			source=source[0].getData()
		else:
			source=zeros((0,3))
			s=self.createElement('Data', {'Name':'Source'})
			g.newElement(s)
			source=zeros((0,3))
			s.datinit(source, {"SampleType":'locus'})
		targ=g.getElements('Data', {'Name':'Target'}, depth=1)
		if targ:
			targ=targ[0].getData()
		else:
			s=self.createElement('Data', {'Name':'Target'})
			g.newElement(s)
			targ=zeros((0,3))
			s.datinit(targ, {"SampleType":'locus'})
		return (source, targ)	
		
	
	def getAlgList(self, withmod=True):
		import mien.blocks as mb
		dsp=mb.functionIndex('gicmapseek.dsp')
		algs=[]
		for f in dsp.keys():
			fnt=f.split('.')[-1]
			if not fnt in ['noop', 'setGoals', 'conditionBias']:
				if withmod:
					algs.append(f)
				else:
					algs.append(fnt)
		return algs
		
	
	def setAlg(self, event):
		algs=self.getAlgList(False)
		a=self.askUsr('select algorithm', algs)		
		a="%s.%s" % ('gicmapseek.dsp', a)	
		o=self.alg.elements[3]	
		o.setAttrib('Function', a)
		self.report('selected %s' % a)
		self.config(None)
		
	
	def config(self, event):
		editBlock(self.alg.elements[3], self)
		self.report('edit finished')

	def rawBias(self, event):
		self.biasmode='raw'
		self._getBiasData(True)
		self.drawBias()
		
	def condBias(self, event):
		self.biasmode='conditioned'
		self._getBiasData(True)
		self.drawBias()
		
		
	def _getBiasData(self, rerun=False):
		bd=self.document.getElements('Data', 'BiasField', depth=1)
		if bd and not rerun:
			return bd[0]
		if bd:
			bd=bd[0]
			bd.datinit(None, {'SampleType':'group'})
		else:
			bd=newData(None, {'Name':'BiasField', 'SampleType':'group'})
			self.document.newElement(bd)
		els=[0,1]
		if self.biasmode=='conditioned':
			els.append(2)
		try:	
			bd=self.alg.run(bd, els)
		except:
			raise
			bd=self.alg.run(bd, [0])
		return bd

	def drawBias(self, recalc=False):
		self.graph.plots={}
		try:
			bd=self._getBiasData(recalc)
		except:
			self.report('can not run model')
			self.graph.DrawAll()
			return
		try:
			self.graph.plotNavData(bd)
		except:
			self.report('bias cant be plotted')
			raise
		sd = self.document.getElements('Data', {'NavSolution':1}, depth=1)
		if sd:
			sd=sd[0].getData()
			self.graph.addPlot(sd, style='line', width=4, order=1)
		self.graph.DrawAll()
		
	def runAll(self, event=None):
		st=time.time()
		self.alg.run()
		self.report('Run completed in %.2f sec' % (time.time()-st),)
		self.drawBias()
		
	def confBias(self, event):
		editBlock(self.alg.elements[2], self)
		self.condBias(None)
		
	def swapBias(self, event):
		self.biasmode='conditioned'
		bd=self._getBiasData(True)
		g=self.alg.elements[0]
		d=g.getElements('Data', depth=1)[0]
		#print bd.data.shape, bd.attributes
		#print d.data.shape, d.attributes
		d.mirror(bd, False)
		#print d.data.shape, d.attributes

		editBlock(self.alg.elements[2], self, args={'width':0, 'hexagonal':False, 'maptorange':(), 'invert':False, 'power':0, 'minBelow':0, 'maxAbove':0.0})
		self.biasmode='raw'
		bd=self._getBiasData(True)
		base=bd.getSubData('/base')
		if base:
			base.sever()
		self.drawBias()
		
	def debug(self, event):
		reload(debuggers)
		mod=self.alg.elements[3]
		args=mod.getArguments()
		args['debug']=True
		mod.setArguments(args)
		ds=self.alg.run()
		dbc=debuggers.DEBUGGERS[ds.navalg.__class__.__name__]
		dbv=dbc(self, ds.navalg)
		dbv.Show(True)
		args['debug']=False
		mod.setArguments(args)
		self.db = dbv
		


if __name__=='__main__':
	app=wx.PySimpleApp()
	z= NavGui()
	z.Show(True)
	import sys
	if len(sys.argv)>1:
		z.load(fname=sys.argv[1])
	app.MainLoop()	