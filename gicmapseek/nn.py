#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2008-12-15.

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
from hexgrid import *
import gicnn.build as nnb

 
class LatencyNN(object):
	'''same API as pathseek.PathSeeker except that solve should return a tuple (solved, p) where p is equivalent to the result of PathSeeker.expandPath(s[1])'''
	def __init__(self, bias, source, target, params=None):
		if not params:
			params={}
		self.params ={}
		self.params.update(params)
		self.space=(bias.attrib('width'), bias.attrib('edge'), bias.attrib('blanks'))
		
		self.bias=bias.getData()
		if self.bias.shape[1]!=6:
			if self.bias.shape[1]==3:
				self.bias=nd2d(self.bias, self.space[0], self.space[2])
			else:
				raise StandardError('NN methods require that the bias field be a directed (6D) or non-directed (3D) hexgrid')
		biasvalues=self.bias[self.bias!=self.space[2]]
		self.bias_stats=(biasvalues.min(), biasvalues.max(), biasvalues.mean(), biasvalues.sum())
		if self.bias_stats[0]<=0:
			raise StandardError('NN methods require that the bias field be strictly positive')
		
		self.net=nnb.Network()
		sources = []
		targets = []
		for i in range(source.shape[0]):
			sources.append(xyToHexI(source[i,:2], self.space[0], self.space[1]))
		for i in range(target.shape[0]):
			targets.append(xyToHexI(target[i,:2], self.space[0], self.space[1]))			
		for i in range(self.bias.shape[0]):
			c = nnb.Cell("NeuronModel", 'IntFire1')
			x,y =hexItoXY(i, self.space[0], self.space[1], False)
			c.setPosition((x,y,0.0))
			cid=self.net.addCell(c)
			self.net.recordCell(cid, "m")
		for i in range(self.bias.shape[0]):
			reccon =False
			for j in range(6):
				if self.bias[i,j]==self.space[2]:
					continue
				ti=followEdge(i, j, self.space[0])
				if ti == -1 or ti >= self.bias.shape[0]:
					continue
				if ti >=len(self.net.cells):
					print self.bias.shape
					print ti, i, j
					print len(self.net.cells)
					raise
				d=self._bias2lag(self.bias[i,j])
				cid=self.net.addConnection(i, ti, 10.0, d)
				if not reccon:
					self.net.record(cid)
					reccon = True
					if i in sources:
						self.net.eventIn(cid, 0.0)
					if i in targets:
						self.net.terminateOn(cid)	

	def _bias2lag(self, b):
		milag = 1.0
		maxlag = 8.0
		b = b - self.bias_stats[0]
		b = b/(self.bias_stats[1]-self.bias_stats[0])
		b = milag + (maxlag-milag)*b
		return b
				
	def solve(self):
		net=self.net.run()
		return ('solved', net)
