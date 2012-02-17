#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2008-09-05.

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
from hexmsc import HexNavMSC
from hexgrid import pathSeparation, xyToHexI
		
class ElasticMSC(HexNavMSC):
	algtype = 'elasticmsc'
	
	default={'maxiter':200, 'kappa':.5, 'precondition':2, 'checkdomain':True,
			'gdiscard':0.001, 'persist':True, 'rule':'kappa', 'mdiscard':0.0,
			'layercost':1.0}
			
			
	def __init__(self, n, source, target, bias, opts=None):
		self.minn = self.nsteps(source, target, bias)
		self.maxn = 3*self.minn
		n = max(n, self.minn)
		HexNavMSC.__init__(self, n, source, target, bias, opts)
			
	def nsteps(self, source, target, bias):
		w = bias.attrib('width')
		e = bias.attrib('edge')
		ps = []
		if not hasattr(source[0], '__getitem__'):
			source= [source]
		if not hasattr(target[0], '__getitem__'):
			target = [target]
		for i in range(len(source)):
			for j in range(len(target)):
				p1 = xyToHexI(source[i], w, e)
				p2 = xyToHexI(target[j],w, e)
				ps.append(pathSeparation(p1,p2,w))
		return min(ps)
				
	
	def prep(self, n, source, target):
		HexNavMSC.prep(self, n, source, target)
		self.ndead = -1
		 	
	def iterate(self):
		ndead = array([l['dead'].sum() for l in self.layers]).sum()
		if ndead > self.ndead:
			self.stretch()
			self.ndead = array([l['dead'].sum() for l in self.layers]).sum()
		HexNavMSC.iterate(self)
		
	def allMaps(self, source, gain, forward):
		maps=[]
		for mi, g in enumerate(gain):
			if g:
				maps.append(self.scaleImage(self.doMap(0, mi, forward, source), g))
		image = self.normImage(self.applyBias(0, self.addImages(maps)))
		return image
		

	def stretch(self, last=None):
		print 'stretch called'
		ml = int(round(len(self.layers)/2.0))
		image = self.layers[-1]['target']
		for li in range(len(self.layers)-1, ml, -1):
			image = self.allMaps(image, self.layers[li]['gain'], False)
		source = self.source
		for li in range(ml):
			source = self.allMaps(source, self.layers[li]['gain'], True)
		mv = self.matchImage(source, image)
		l0 = self.allMaps(source, self.layers[ml]['gain'], True)
		m0 = self.matchImage(l0, image)
		if len(self.layers)>=self.minn and last!='grow' and mv*self.opts['layercost']>m0:
			self.layers.pop(ml)
			self.report('removing layer. now have %i' % (len(self.layers),))
			self.stretch('shrink')
			return
		if last=='shrink' or len(self.layers)>=self.maxn:
			return 
		gain = ones(ones(self.nMaps(0)))
		l1 = self.allMaps(l0, self.layers[ml]['gain'], True)
		m1 = self.matchImage(l1, image)
		print mv, m0, m1
		if m1>m0*self.opts['layercost']:
			self.layers.insert(ml+1, {'source':None, 'target':None, 'gain':ones(self.nMaps(0)),  'dead':zeros(self.nMaps(0))})
			self.report('adding layer. now have %i' % (len(self.layers),))
			self.stretch('grow')
		else:
			print 'noop'
			
