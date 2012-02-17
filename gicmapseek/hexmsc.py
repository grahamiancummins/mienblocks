#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2008-09-25.

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

from numpy import *
from genericmsc import MapSeeker
from sparse import Sparse1D
import hexgrid as hg

class HexNavMSC(MapSeeker):
	transforms = [[0],[1],[2],[3],[4],[5]]
	algtype = 'hexmsc'
	
	def __init__(self, n, source, target, bias, opts=None):
		MapSeeker.__init__(self, opts)
		self.bias = bias.getData()
		self.hexedge=bias.attrib('edge')
		self.size = self.bias.shape[0]
		self.width = bias.attrib('width')
		if self.bias.shape[1]!=6:
			if self.bias.shape[1]==3:
				self.bias=hg.nd2d(self.bias, self.width, bias.attrib('blanks'))
			else:
				raise StandardError('Hex Nav MSC requires that the bias field be a directed (6D) or non-directed (3D) hexgrid')		
		self._space = Sparse1D(None, self.size)
		self.map = hg.hexMap(self.size, self.width, self.bias==bias.attrib('blanks'))
		self.prep(n, source, target)
	
	def space(self):
		return self._space.clone()
	
	def prep(self, n, source, target):
		ss = self.space()
		if not hasattr(source[0], '__getitem__'):
			source= [source]
		self.source=ss
		for pt in source:
			spi=hg.xyToHexI(pt[:2], self.width, self.hexedge)
			ss[spi]=pt[2]
		ts = self.space()
		if not hasattr(target[0], '__getitem__'):
			target = [target]
		for pt in target:
			tpi=hg.xyToHexI(pt[:2], self.width, self.hexedge)
			ts[tpi]=pt[2]                                                                                                                         
		self.layers=[]
		self.iter=0
		for i in range(n):
			self.layers.append({'source':None, 'target':None, 'gain':ones(self.nMaps(i)),  'dead':zeros(self.nMaps(i))})
		self.layers[-1]['target']=ts	
		#print self.layers


	def applyBias(self, layer, source):
		''' In the hexgrid representation, biases are associated only to the cost of a transformation, not to particular grid locations. An "uninhabitable" grid point is represented by making the edges leading to the point uncrossable, rather than biasing the point. Consequently, this function, which is used to implement classic MSC biasing, where images are multiplied by a bias weight after a transformation, should always do nothing in hexgrid implementations.'''
		return source

	def getTrajectory(self):
		path = self.bestPath()
		ind, v = self.source.sparse()
		s=ind[argmax(v)]
		pts = [hg.hexItoXY(s, self.width, self.hexedge)]
		for i in path:
			t = self.transforms[i]
			for j in t:
				s = self.map[s, j]
				pts.append(hg.hexItoXY(s, self.width, self.hexedge))
		return array(pts)
	
	def nMaps(self, layer):
		return len(self.transforms)
		
	def describeMap(self, layer, index, forward):
		m = self.transforms[index]
		if not forward:
			m=[hg.INVERSES[i] for i in m]
		if len(m)==1:
			return "Follow edge %i" % (m[0],)
		else:
			return "Follow edges %s" % (','.join(map(str, m)),)
		
	def step(self, s, j):
		i, v = s.sparse()
		i = self.map[i, j]
		ind = (i!=-1)	
		i=i[ind].astype(int32)
		v=v[ind]
		v=v*self.bias[i,j]
		ind=(v>0)
		i=i[ind]
		v=v[ind]
		return Sparse1D([i,v], s.size)
	
	def doMap(self, layer, index, forward, input):
		m = self.transforms[index]
		if not forward:
			m=[hg.INVERSES[i] for i in m]
		for i in m:
			input=self.step(input, i)
		return input
		

class HexTwoStep(HexNavMSC):
	transforms = [	[0],
						[1],
						[2],
						[3],
						[4],
						[5],
						[0, 5], [0,0],[0,1],
						[1,0],[1,1],[1,2],
						[2,1],[2,2],[2,3],
						[3,2],[3,3],[3,4],
						[4,3],[4,4],[4,5],
						[5,4],[5,5],[5,0]]
	algtype='hex2s'
		
		
	def addImages(self, loi):
		sv=loi[0]
		for rv in loi[1:]:
			sv=sv.maximum(rv)
		return sv
	

	