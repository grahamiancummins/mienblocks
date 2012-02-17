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
from numpy import *
from genericmsc import MapSeeker
from sparse import Sparse


def maxPt(s):
	ind, v = s.sparse()
	return ind[argmax(v), :]

class SparseNavMSC(MapSeeker):
	def __init__(self, n, source, target, bias, opts=None):
		MapSeeker.__init__(self, opts)
		shape = bias.shape
		if not isinstance(bias, Sparse):
			bias = Sparse(bias)
			bias.squeeze()
		self.bias = bias
		self._params = (n, source, target)
		self._space = Sparse(None, shape)
		self.prep(n, source, target)
	
	def space(self):
		return self._space.clone()
		
	
	def prep(self, n, source, target):
		ss = self.space()
		if not hasattr(source[0], '__getitem__'):
			source = [source]
		for pt in source:
			ss[pt[:2]]=pt[2]
		self.source=ss
		ts = self.space()
		if not hasattr(target[0], '__getitem__'):
			target = [target]
		for pt in target:
			ts[pt[:2]]=pt[2]
		self.layers=[]
		self.iter=0
		for i in range(n):
			self.layers.append({'source':None, 'target':None, 'gain':ones(self.nMaps(i)),  'dead':zeros(self.nMaps(i))})
		self.layers[-1]['target']=ts
	
	def applyBias(self, layer, source):
		return source*self.bias	
	
	def getTrajectory(self):
		path = self.bestPath()
		s = self.source.clone()
		pts = [maxPt(s)]
		for i, p in enumerate(path):
			s = self.doMap(i, p, True, s)
			pts.append(maxPt(s))
		return array(pts)


def shiftArray(a, coords):
	s = a.shape
	newslice=[]
	oldslice=[]
	for i, c in enumerate(coords):
		if c>=0:
			ns = slice(c, s[i])
			os = slice(0, s[i]-c)
		else:
			ns = slice(0, s[i]+c)
			os = slice(-c, s[i])
		oldslice.append(os)
		newslice.append(ns)
	out = zeros_like(a)
	out[tuple(newslice)]=a[tuple(oldslice)]	
	return out
	
def indexShift(i, coords, shape):
	''' Apply an ND shift specified by coords to the flat (1D) indexes in i, representing ND data on a space of shape '''
	rs = tuple(take(shape, arange(len(shape)-1,-1,-1)))
	strides=concatenate([[1], cumprod(rs)[:-1]])
	strides=strides[arange(strides.shape[0]-1, -1, -1)]	
	return i+ dot(strides, array(coords))
	
def shiftSparse(s, coords):
	if s.data[0]=='full':
		a = s.full()
		a = shiftArray(a, coords)
		if any(isnan(a)):
			print "NaN in full shift"
		return Sparse(a)
	a, v = s.sparse()
	a += coords	
	gz=all(a>=0, 1)
	lb=all(a<s.shape, 1)
	ok=logical_and(gz, lb)
	dat = [a[ok], v[ok] ]
	if any(isnan(dat[1])):
		print "NaN in sparse shift"
		print dat
	return Sparse(dat, s.shape)


class AdjacentPointRect(SparseNavMSC):
	tvec = [(1,0), (1,1), (0,1), (-1,1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
	algtype='sarmsc'
	
	def doMap(self, layer, index, forward, input):
		t = self.tvec[index]
		if not forward:
			t = (-t[0], -t[1])
		s =  shiftSparse(input, t)
		if any(isnan(s.data[1])):
			print "NaN in adjpt"
			print s
		return s
		
	def describeMap(self, layer, index, forward):
		t = self.tvec[index]
		if not forward:
			t = (-t[0], -t[1])
		return "translate x by %i, y by %i" % t
	
	def nMaps(self, layer):
		return len(self.tvec)	


if __name__=='__main__':
	m=AdjacentPointRect(4, (1,1, 1), (3,3, 1), ones((5,5)) )
	r=m.run()
	print r
	m.describeSolution()
	