#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2008-01-30.

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
from navmsc import AdjacentPointRect, maxPt
from hexmsc import HexNavMSC
from sparse import Sparse, Sparse1D
from numpy import *
from mien.math.array import combinations
				
class BackpropMSCRect(AdjacentPointRect):
	algtype='bpmsc'
	default={'maxiter':200, 'kappa':.5, 'precondition':0, 'gdiscard':0.2,
			'rule':'kappa', 'mdiscard':0.0, 'checkdomain':True,
			'persist':True, 'maxnbpl':100, 'layersperpoint':1.0}
			
	def getTrans(self, layer=None):
		return self.trans			
	
	def prep(self, n, source, target):
		if  hasattr(source[0], '__getitem__'):
			source = source[0]
		self.initiallocation = source[:2]
		self.location = source[:2]
		if hasattr(target[0], '__getitem__'):
			target = target[0]
		self.target = target[:2]
		self.layers=[]
		self.iter=0
		self.bp=None
		self.trajectory = []
		self.maps=[]
		self.nlayers = n
		self.localsize = int(round(n/self.opts['layersperpoint']))
		self.prepstep()
		
	def iterate(self):
		if self.layers[-1]['target']==None:
			self.prepstep()
		state = AdjacentPointRect.iterate(self)
		if state:
			self.applystep()
			if self.inrange():
				self.solv = self.maps[:]
			else:
				self.prepstep()
				state=0
		if state:
			print state, self.solv
		return state
	
	
	
	def inrange(self):
		d = max( abs(self.target[0]-self.location[0]), abs(self.target[1]-self.location[1]))
		print self.location, self.target, d
		if d<self.nlayers:
			return True
		return False
	
	def prepstep(self):
		ss = self.space()
		ss[self.location]=1.0
		self.source = ss
		self.layers=[]
		self.solv=[]
		for i in range(self.nlayers):
			self.layers.append({'source':None, 'target':None, 'gain':ones(self.nMaps(i)),  'dead':zeros(self.nMaps(i))})
		self.iter = 0
		self.layers[-1]['target']=self.findTarget()

	def applystep(self):
		path = self.bestPath()
		s= self.space()
		s[self.location]=1.0
		pts = [self.location]
		for i, p in enumerate(path):
			self.maps.append(p)
			s = self.doMap(i, p, True, s)
			pts.append(maxPt(s))
		self.location = pts[-1]
		self.trajectory.append(pts)
		self.report( "moved to %s" % (str(self.location),) )
		print self.maps

	def local(self, a=None):
		ls = self.space()
		xmin = max(self.location[0]-self.localsize, 0)
		xmax = min(self.location[0]+self.localsize+1, ls.shape[0]) 
		ymin = max(self.location[1]-self.localsize, 0)
		ymax = min(self.location[1]+self.localsize+1, ls.shape[1])
		lpts = combinations([arange(xmin, xmax), arange(ymin, ymax)])
		ls[lpts[:,0], lpts[:,1]]=1.0
		if a!=None:
			ls = ls*a
		return ls
		
	def findTarget(self):
		if self.bp==None:
			self.nbpl=0
			ts = self.space()
			ts[self.target]=1.0
			self.bp=ts
			self.backprop()
		t=self.local(self.bp)
		return self.normImage(t)
		
	def backprop(self):
		lex = 0
		ex = nonzero(self.bp.data[1])[0].shape[0]
		while ex>lex:
			self.nbpl+=1
			if self.nbpl>self.opts['maxnbpl']:
				break
			maps=[]
			for mi in range(self.nMaps(0)):
				maps.append(self.doMap(0, mi, False, self.bp))
			self.bp = self.normImage(self.applyBias(0, self.addImages(maps)))
			lex = ex
			ex = nonzero(self.bp.data[1])[0].shape[0]

	def getTrajectory(self):
		path =self.maps
		s= self.space()
		s[self.initiallocation]=1.0
		pts = [self.initiallocation]
		for i, p in enumerate(path):
			s = self.doMap(i, p, True, s)
			pts.append(maxPt(s))
		return array(pts)	
			
	