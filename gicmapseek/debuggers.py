#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2008-09-04.

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

import wx
from numpy import *
from gicmapseek.sparse import Sparse, Sparse1D

def makeCB(gui, n):
	def cbf(event=None):
		gui.functions[n](gui)
	return cbf
	
def makeSCB(gui, n, w):
	def cbf(event=None):
		gui.spinners[n](gui, w)
	return cbf

class DebugViewer(wx.Dialog):
	
	def __init__(self, viewer, alg):
		self.viewer=viewer
		self.alg=alg
		self.graph = viewer.graph
		wx.Dialog.__init__(self, viewer)
		sizer = wx.BoxSizer(wx.VERTICAL)
		for foo in self.functions.keys():
			btn = wx.Button(self, -1, foo)
			wx.EVT_BUTTON(self, btn.GetId(), makeCB(self, foo))
			sizer.Add(btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		for foo in self.spinners.keys():
			bs = wx.BoxSizer(wx.HORIZONTAL)
			bs.Add(wx.StaticText(self, -1, foo), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
			btn = wx.SpinCtrl(self, -1, style = wx.SP_ARROW_KEYS, min = -1, max = 1000)
			wx.EVT_SPINCTRL(self, btn.GetId(), makeSCB(self, foo, btn))
			bs.Add(btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
			sizer.Add(bs, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		
		
		self.chooseMode = wx.Choice(self, -1, choices=self.displays.keys())
		sizer.Add(self.chooseMode, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		wx.EVT_CHOICE(self, self.chooseMode.GetId(), self.doDisplay)

		btn = wx.Button(self, -1, " Refresh View ")
		wx.EVT_BUTTON(self, btn.GetId(), self.doDisplay)
		sizer.Add(btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)						
		#quit
		btn = wx.Button(self, -1, " Close ")
		wx.EVT_BUTTON(self, btn.GetId(), lambda x:self.Destroy())
		sizer.Add(btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		
		self.SetSizer(sizer)
		self.SetAutoLayout(True)
		sizer.Fit(self)
	
	def null_function(self):
		print 'testing'
				
	def doDisplay(self, event=None):
		dt =  self.chooseMode.GetStringSelection()
		self.displays[dt](self)
		
	def null_display(self):
		print "this is a stub"

	def report(self, s):
		self.viewer.report(s)
	
	functions = {'example':null_function}
	spinners = {}
	displays = {'null':null_display}	
		
		

class psDebug(DebugViewer):
	pass
	

class sarDebug(DebugViewer):	
	def __init__(self, viewer, alg):
		DebugViewer.__init__(self, viewer, alg)
		self.layer=0
		self.xform = 0
		self.matchvals = {}
		self.alg.opts['dryrun']=True
		self.alg.iterate()
		self.alg.opts['dryrun']=False
		
	
	def runMSC(self):
		self.matchvals = {}
		print self.alg.iter
		state=self.alg.iterate()
		self.doDisplay()
		if state:
			self.report('algorithm done ' + str(state))	
	
	def setL(self, widg):
		l = widg.GetValue()
		if l<0:
			l = len(self.alg.layers) -1
			widg.SetValue(l)
		elif l >= len(self.alg.layers):
			l = 0
			widg.SetValue(l)
		self.layer=l
		self.doDisplay()
			
	def setT(self, widg):
		l = widg.GetValue()
		if l<-1:
			l = len(self.alg.tvec) -1
			widg.SetValue(l)
		elif l >= len(self.alg.tvec):
			l = -1
			widg.SetValue(l)
		self.xform=l
		self.doDisplay()
	
	def plotSpace(self, s, cr = None):
		self.graph.plots={}	
		self.graph.addSpacePlot(s, crange=cr)
		self.graph.limits=array([-1,s.shape[0]+2, -1.0, s.shape[1]+2])	
		self.graph.DrawAll()
	
	
	
	
	def gspace(self, layer):
		g=self.alg.layers[layer]['gain']
		match = self.getQs(layer)[:,0]
		if self.alg.opts['mdiscard']:
			nq = where(match<(match.max()*self.alg.opts['mdiscard']), 0, match)
		else:
			nq = match
		ng=self.alg.learningrules[self.alg.opts['rule']](self.alg, g, nq)	
		ng=maximum(0, ng/ng.max())
		ss =Sparse(None, (3,3))
		gs = ss.clone()
		ms = ss.clone()
		ngs = ss.clone()
		ss.setpt((1, 1), 1.0)
		match = match/match.max()
		for i in range(len(self.alg.tvec)):
			s  = self.alg.doMap(layer, i, True, ss) 
			gs = gs + s * g[i]
			ms = ms + s * match[i]
			ngs = ngs + s* ng[i]		
		ss =Sparse(None, (11,3))
		s = gs.changesize((11,3), (0,0), False) + \
			ms.changesize((11,3), (4,0), False) + \
			ngs.changesize((11,3), (8,0), False)
		s.setpt((1,1), .5)
		s.setpt((5,1), .5)
		s.setpt((9,1), .5)
		return s
		
	
	def gplot(self):
		s = self.gspace(self.layer)
		s.data = Sparse1D.sparse(s)
		self.plotSpace(s)
	
			
	def all_g(self, retspace = False):
		nl = len(self.alg.layers)
		s = Sparse(None, (11,4*nl))
		for i in range(nl):
			igs = self.gspace(i)
			s = s + igs.changesize((11,4*nl), (0, 4*i), False)
		if retspace:
			return s
		self.plotSpace(s, (0,1))
			
		
	def forward(self):		
		if self.layer==0:
			s = self.alg.source
		else:
			s=self.alg.layers[self.layer-1].get('source')
		if not s:
			self.report('no image')
			return
		s=s.clone()	
		self.plotSpace(s)			
		
	def reverse(self):		
		s=self.alg.layers[self.layer].get('target')
		if not s:
			self.report('no image')
			return
		s=s.clone()	
		self.plotSpace(s)	
	
	def reset(self):
		self.matchvals = {}
		apply(self.alg.prep, self.alg._params)
		self.alg.opts['dryrun']=True
		self.alg.iterate()
		self.alg.opts['dryrun']=False
		self.report('reset')		
		
	def plot_xform(self):
		if self.xform == -1:
			self.forward()
			return
		if self.layer==0:
			s = self.alg.source
		else:
			s=self.alg.layers[self.layer-1].get('source')
		if not s:
			self.report('no image')
			return
		g = self.alg.layers[self.layer]['gain'][self.xform]
		s = self.alg.applyBias(self.layer, self.alg.scaleImage(self.alg.doMap(self.layer, self.xform, True, s), g))
		s=s.clone()	
		self.plotSpace(s)	
	
	
	def get_overlap(self, layer, tf):
		if layer==0:
			s = self.alg.source
		else:
			s=self.alg.layers[layer-1].get('source')
		if not s:
			self.report('no image')
			return
		if tf > -1:
			g = self.alg.layers[layer]['gain'][tf]
			s = self.alg.applyBias(layer, self.alg.scaleImage(self.alg.doMap(layer, tf, True, s), g))
		t=self.alg.layers[layer].get('target')
		s = s*t
		q = s.sum()
		return (s, q)		
	
	def getQs(self, layer=None):
		if layer==None:
			layer=self.layer
		if layer in self.matchvals:
			return self.matchvals[layer]
		mv = []
		for i in range(len(self.alg.tvec)):
			s, q = self.get_overlap(layer, i)
			if q:
				mv.append( (q, s.data[1].max()))
			else:
				mv.append( (0, 0))
		self.matchvals[layer] = array(mv)
		#print self.matchvals[self.layer]
		return self.matchvals[layer]
		
		
	def plot_overlap(self):
		s, q = self.get_overlap(self.layer, self.xform)
		s=s.clone()
		s.squeeze()	
		if s.data[1].shape[0] == 0:
			self.graph.plots={}	
			self.graph.DrawAll()
		mv = self.getQs()[:,1].max()
		s.data[1] = s.data[1]/mv
		self.plotSpace(s, (0, 1.0))		
	
	def spacenorm(self, space):
		dat=space.full()
		nz = dat>0
		if not any(nz):
			return Sparse(None, dat.shape)
		mnz = dat[nz].min()
		huge = mnz*1000
		dat = minimum(dat, huge)
		dat = dat/dat.max()
		return Sparse(dat)
		
	
	def spaceToByte(self, s, factor=0):
		factor = 256**factor
		s.squeeze()
		ind, dat = s.sparse()
		if ind.shape[0] == 0:
			return s
		dat = log(dat)
		dat = dat - dat.min() + 1
		dat = maximum(1, (dat/dat.max())*255)
		dat = factor*dat.astype(int64)
		s.data = s.to1d([ind, dat] )
		return s
	
	def rawSpaceColors(self, r, g, b):
		r = self.spaceToByte(r, 0)
		g = self.spaceToByte(g, 1)
		b = self.spaceToByte(b, 2)
		v = r + g + b
		ind, v  = v.sparse()
		b, v = divmod(v, 65536)
		g, r = divmod(v, 256)
		c = column_stack([r, g, b]).astype('uint8')
		c = [apply(wx.Color, a) for a in c]
		return (ind, c)
		
		
		
	def plot_full(self):
		if self.layer==0:
			forw = self.alg.source.clone()
		else:
			forw =self.alg.layers[self.layer-1].get('source').clone()
		rev=self.alg.layers[self.layer].get('target').clone()
		g = self.alg.layers[self.layer]['gain'][self.xform]
		if self.xform == -1:
			xform = forw
		else:
			xform = self.alg.applyBias(self.layer, self.alg.scaleImage(self.alg.doMap(self.layer, self.xform, True, forw), g))
		overlap  = rev * xform
		ind, color = self.rawSpaceColors(rev, overlap, xform)
		self.graph.plots={}	
		self.graph.addRawSpacePlot(ind, color)
		self.graph.limits=array([-1, rev.shape[0]+2, -1.0, rev.shape[1]+2])	
		self.graph.DrawAll()
		
		# final.data = Sparse1D.sparse(final)
		# self.plotSpace(final)
		
	def plot_xform(self):
		if self.layer==0:
			s = self.alg.source
		else:
			s=self.alg.layers[self.layer-1].get('source')
		if not s:
			self.report('no image')
			return
		g = self.alg.layers[self.layer]['gain'][self.xform]
		s = self.alg.applyBias(self.layer, self.alg.scaleImage(self.alg.doMap(self.layer, self.xform, True, s), g))
		s=s.clone()	
		self.plotSpace(s)	
		pass

		
	displays = {'g':gplot,
				'forward':forward,
				'reverse':reverse,
				'xform':plot_xform,
				'overlap':plot_overlap,
				'layer_full':plot_full,
				'all_g':all_g}		
	
	spinners = {'layer':setL,
				'transform':setT}
	
	functions = {
				'iterate':runMSC,
				'reset':reset}
		
class bpmscDebug(sarDebug):
	

	def local(self):
		if self.alg.iter==0:
			print len(self.alg.trajectory)
			state=self.alg.iterate()
		else:
			state=0
		while self.alg.iter and not state:
			print self.alg.iter
			state=self.alg.iterate()
		if state:
			self.report('algorithm done ' + str(state))	
		else:
			self.report('local step done ' + str(self.alg.location))	
	
	def bp(self):
		s=self.alg.bp.full()
		print s.min(), s.max()
		mask = s==0
		s[mask]=s.mean()
		s-=s.min()
		s/=s.max()
		s+=2.0
		s=log(s)
		s[mask]=0
		self.graph.plots={}	
		self.graph.addArrayPlot(s)
		self.graph.limits=array([-1,s.shape[0]+2, -1.0, s.shape[1]+2])	
		self.graph.DrawAll()


	def traj(self):
		t=self.alg.getTrajectory()
		s=self.alg.space()
		s[t[:,0], t[:,1]]=1
		self.plotSpace(s)
		
		
	def reset(self):
		self.alg.prepstep()
		
		self.report('reset step')
		
	displays = {'g':sarDebug.gplot,
				'forward':sarDebug.forward,
				'reverse':sarDebug.reverse,
				'trajectory':traj,
				'bp':bp}		
	
	functions = {'set layer':sarDebug.setL,
				'iterate':sarDebug.runMSC, 
				'reset':reset,
				'global reset':sarDebug.reset,
				'solve local':local}
				
				
class BlurDB(DebugViewer):
	def __init__(self, viewer, alg):
		DebugViewer.__init__(self, viewer, alg)
		self.angle = 60.0
		self.anglewidth = 15.0
		self.depth = .1
	
	def setPars(self):
		p = self.viewer.askParam([{'Name':'Center Angle', 'Value':self.angle}, {'Name':'Angle Width', 'Value':self.anglewidth}, {'Name':'Depth', 'Value':float(self.depth)}])
		if not p:
			return 
		self.angle = p[0]
		self.anglewidth = p[1]
		self.depth = p[2]
		self.doDisplay()
		
		
	def showWedge(self):
		bp = self.alg.getWedge(self.angle, self.anglewidth)
		self.plot(bp)
	
	def showGroup(self):
		bp = self.alg.getRegion(self.angle, self.anglewidth, self.depth)
		self.plot(bp)
	
	def showRing(self):
		bp = self.alg.getRing(self.depth)
		self.plot(bp)
		
	def showBlur(self):
		bp = self.alg.getBlur(self.anglewidth, self.depth)
		self.plot(bp)	
		
	def showDev(self):
		bp = self.alg.getBlurDev(self.anglewidth, self.depth)
		self.plot(bp)	
		

	def plot(self, bp):
		self.graph.plots={}
		self.graph.plotNavData(bp)
		self.graph.DrawAll()	
		
		
	displays = {'wedge':showWedge,
				'group':showGroup,
				'ring':showRing,
				'blur':showBlur,
				'blurdev':showDev
		}
	
	functions = {'set params':setPars}	
				
	
from hexgrid import hexItoXY	
		
class BlurPS(DebugViewer):
	def __init__(self, viewer, alg):
		DebugViewer.__init__(self, viewer, alg)
		self.angle = 60.0
		self.anglewidth = 15.0
		self.depth = .1
		self.steps = 2

		
	def bias(self):
		self.plot(self.alg.bias)
		
		
	def plot(self, s):
		self.graph.plots={}
		w, e, b = self.alg.space
		self.graph.hexGridPlot(s, w, e, b, name='bias')
		self.graph.limits=array([-1,w*e+2, -1.0, .866*e*(s.shape[0]/w)+2])	
		loc = self.alg.current_location
		loc = hexItoXY(loc, w, e)
		print loc
		self.graph.markup(array([loc]), 'circle', int(max(15, min(s.shape)/50.)))
		self.graph.DrawAll()
			
		
	def step(self):
		point = self.alg.nextMove()
		self.alg.moveTo(point)
		self.doDisplay()
		
	def movie(self):
		i=0
		while self.alg.current_location!=self.alg.target:
			point = self.alg.nextMove()
			self.alg.moveTo(point)
			self.path()
			self.graph.dumpFile(fname="frame%03d.png" % i)
			i+=1
			
	def unknown(self):
		self.plot(self.alg.uncertainty )
	
	def ur(self):
		self.plot(self.alg.ur )			
				
				
	def certain(self):
		b = zeros_like(self.alg.true_bias)-1
		known = self.alg.uncertainty == 0
		b[known]=self.alg.true_bias[known]
		self.plot(b)
				
	def path(self):
		from hexgrid import findConnectingEdge
		try:
			path = self.alg.last_guessed_path
		except:
			self.bias()                             
			return
		b = self.alg.bias.copy()
		hv = b.max()+.1*(b.max()-b.min())
		sp = path[0]
		for p in path[1:]:
			edge = findConnectingEdge(sp, p, self.alg.space[0])
			if edge!=-1:
				b[sp, edge]=hv
			sp=p	
		self.plot(b)
				
		
	displays = {'bias mean':bias,
				'bias std':unknown,
				'ur':ur,
				'path':path,
				'certain':certain,
		}
	
	functions = {'step':step,
				'movie':movie}			
		
		
DEBUGGERS={'PathSeeker':psDebug, 'BackpropMSCRect':bpmscDebug,  'AdjacentPointRect':sarDebug, 'TestMe':BlurDB, 'BlurredPathSeeker':BlurPS}