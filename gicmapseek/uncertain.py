
#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2008-10-10.

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
from pathseek import TimedPathSeeker

class HexRegionFinder(object):
	def __init__(self, npts, width, location):
		self.npts = npts
		self.w = width
		self.map = hexLocations(npts, width, 1.0)
		self.setLocation(location)
		
	def setLocation(self, location):
		self.locationIndex = location
		self.location = array(hexItoXY(location, self.w, 1.0))
	
	def nRing(self, radius, width=1.0):
		bound = width/2.0
		d = sqrt( ((self.map - self.location)**2).sum(2))
		mask = logical_and(d>=radius - bound, d <= radius + bound)
		return mask[:,:6]	
		
	def wedge(self, ang, width=60.0):
		'''ang is the center angle, and width is the total width of the wedge, both in degrees.'''
		width=width/2.0
		minang = ang - width
		minang = ((minang+180) % 360) - 180 
		minang= pi*minang/180.0
		maxang= ang+width
		maxang = ((maxang+180) % 360) - 180 
		maxang= pi*maxang/180.0
		z = self.map - self.location
		angs = angle(z[...,0]+z[...,1]*1j)[:,:6]
		if maxang<minang:
			mask = logical_or(angs>=minang, angs<=maxang)
		else:
			mask = logical_and(angs>=minang, angs<=maxang)
		return mask
		
	def blur(self, data, angw, ri=1.0):	
		r = 2
		rinc = 1
		rings = []
		while 1:
			ring = self.nRing(r, rinc)
			if not any(ring):
				break
			rings.append(ring)
			nw = min(data.shape[0], max(1.0, 1.0/exp(-ri*r))) 
			r = r + nw/2.0 + rinc/2.0
			rinc = nw
		meanbd = data.copy()
		stddv = zeros_like(data)
		ang = 0
		while ang<=360:
			wedge = self.wedge(ang, angw)
			for i, r in enumerate(rings):
				reg = logical_and(r, wedge)
				reg =logical_and(reg, data>-1)
				if not any(reg):
					continue
				dist = data[reg]
				stddv[reg]=dist.std()
				meanbd[reg]=dist.mean()
			ang+=angw
		return (meanbd, stddv)
		
	def occlude(self, data, angw, depth=None):
		r = 2
		rinc = 1
		rings = []
		while 1:
			ring = self.nRing(r, rinc)
			if not any(ring):
				break
			rings.append(ring)
			r = r + rinc
			
		cval=data[self.locationIndex].mean()
		meanbd = data.copy()
		stddv = zeros_like(data)
		ang = 0
		dat = data[data>0]
		mval = dat.mean()
		mstdd = dat.std()*2
		while ang<=360:
			wedge = self.wedge(ang, angw)
			maxval = 0
			for i, r in enumerate(rings):
				reg = logical_and(r, wedge)
				reg =logical_and(reg, data>-1)
				if not any(reg):
					continue
				stddv[reg]=mstdd
				meanbd[reg]=mval
				if maxval>cval:
					viewed = logical_and(reg, data>maxval)
				else:
					viewed = reg
				if not any(viewed):
					continue
				dist = data[viewed]
				stddv[viewed]=dist.std()
				dmv = dist.mean()
				meanbd[viewed]=dmv
				maxval  = max(maxval, dmv)
			ang+=angw
		return (meanbd, stddv)
		
	def fog(self, data, angw, depth):
		r = 3
		rinc = 1
		rings = []
		while 1:
			ring = self.nRing(r, rinc)
			if not any(ring):
				break
			rings.append(ring)
			r = r + rinc
		meanbd = data.copy()
		mval= data[data>0].min()
		stddv = zeros_like(data)
		ang = 0
		while ang<=360:
			wedge = self.wedge(ang, angw)
			fog = 0
			for i, r in enumerate(rings):
				reg = logical_and(r, wedge)
				reg =logical_and(reg, data>-1)
				if not any(reg):
					continue
					
				dist = data[reg]
				fog+=depth
				stddv[reg]=dist.std()+fog
				v = dist.mean()+random.normal(0, fog,1)[0]
				v = max(v, mval)
				meanbd[reg]=v
			ang+=angw
		return (meanbd, stddv)	
		
	def foggyocclude(self, data, angw, depth):
		r = 2
		rinc = 1
		rings = []
		while 1:
			ring = self.nRing(r, rinc)
			if not any(ring):
				break
			rings.append(ring)
			r = r + rinc
			
		cval=data[self.locationIndex].mean()
		meanbd = data.copy()
		dat = data[data>0]
		mval = dat.mean()
		minival= dat.min()
		stddv = zeros_like(data)
		ang = 0
		while ang<=360:
			wedge = self.wedge(ang, angw)
			maxval = 0
			fog = 0
			for i, r in enumerate(rings):
				reg = logical_and(r, wedge)
				reg =logical_and(reg, data>-1)
				if not any(reg):
					continue
				stddv[reg]=inf
				meanbd[reg]=mval
				if maxval>cval:
					viewed = logical_and(reg, data>maxval)
				else:
					viewed = reg
				if not any(viewed):
					continue
				dist = data[viewed]
				fog+=depth
				stddv[viewed]=dist.std()+fog
				dmv = dist.mean()
				v = dmv+random.normal(0, fog,1)[0]
				v = max(v, minival)
				meanbd[viewed]=v
				maxval  = max(maxval, max(v, dmv))
			ang+=angw
		return (meanbd, stddv)		
		

class TestMe(object):
	def __init__(self, bias, loc):
		self.w=bias.attrib('width')
		self.bias=bias
		self.n = self.bias.getData().shape[0]
		if self.bias.getData().shape[1]!=6:
			self.bias = self.bias.clone()
			self.bias.datinit(nd2d(self.bias.getData(), self.w, bias.attrib('blanks')))
		self.loc = xyToHexI(loc[0,:2], self.w, bias.attrib('edge'))
		self.finder = HexRegionFinder(self.n, self.w, self.loc)	
		
	def getBlur(self, angw, ri):
		m = self.finder.blur(self.bias.getData(), angw, ri)[0]
		b = self.bias.clone()
		b.datinit(m)
		return 	b
		
	def getBlurDev(self, angw, ri):
		m = self.finder.blur(self.bias.getData(), angw, ri)[1]
		b = self.bias.clone()
		b.datinit(m)
		return 	b
		
	def getWedge(self, ang, angw):
		z = self.finder.wedge(ang, angw)
		return self.highlight(z)
	
	def getRegion(self, ang, angw, r):
		w = self.finder.wedge(ang, angw)
		rin = self.finder.nRing(r)
		return self.highlight(logical_and(w, rin))
		
	def getRing(self, r):
		z=self.finder.nRing(r)
		return self.highlight(z)
		
	def highlight(self, indexes):
		bi = self.bias.clone()
		bd = bi.getData()
		bd[indexes]+=bd.max()
		bi.datinit(bd)
		return bi
		
class BlurredPathSeeker(TimedPathSeeker):
	def __init__(self, bias, source, target, params=None):
		TimedPathSeeker.__init__(self, bias, source, target, params)
		if not 'angle_resolution' in self.params:
			self.params['angle_resolution']=15.0
		if not 'depth_fade' in self.params:
			self.params['depth_fade']=.1
		if not 'bias_optimism' in self.params:
			self.params['bias_optimism']=0
		if not 'blur_method' in self.params:
			self.params['blur_method']='blur'
		self.true_bias = self.bias.copy()
		self.finder = HexRegionFinder(self.bias.shape[0], self.space[0], self.ftips[0])
		self.uncertainty = ones((self.bias.shape[0], 6))*inf
		self.true_path=[]
		self.target=self.rtips[0]
		print 'target', self.target
		self.explore(self.ftips[0])	
		
	def explore(self, pt):	
		self.current_location = pt
		self.true_path.append(pt)
		last_edge = -1
		self.finder.setLocation(self.current_location)
		bmeth = getattr(self.finder, self.params['blur_method'])
		bmean, bdev  = bmeth(self.true_bias, self.params['angle_resolution'], self.params['depth_fade'])
		ur = bdev < self.uncertainty
		opt = self.params['bias_optimism']
		if "fog" in self.params['blur_method']:
			guessing = minimum(bdev, self.uncertainty) > 0
			certain = logical_not(guessing)
			self.bias[certain]=self.true_bias[certain]
			if self.params['impossible']:
				bmean = minimum(self.params['impossible']-1e-10, bmean)
			pweight = len(self.true_path)	
			if 'occlude' in self.params['blur_method']:
				clueless = logical_and(guessing, self.uncertainty == inf)
				guessing = logical_and(bdev!=inf, guessing)
				guessing = logical_and(guessing, logical_not(clueless))
				self.bias[clueless] = bmean[clueless]  	
			self.bias[guessing] = ( pweight*self.bias[guessing] + bmean[guessing] ) / (pweight+1)
		else:
			guessing = bdev < self.uncertainty
			self.bias[guessing]=bmean[guessing]	
		if opt:
			guessing = logical_and(guessing, bdev !=inf)
			self.bias[guessing] -= opt*bdev[guessing]
			self.bias[guessing] = maximum(self.bias[guessing], self.bias_stats[0])
		self.ur = guessing	
		self.uncertainty = minimum(bdev, self.uncertainty)
		for pt in self.true_path:
			v = self.bias_stats[1]
			if self.params['impossible']:
				v = self.params['impossible']-1e-10
			for i in range(6):
				if not self.bias[pt, i]==self.space[2]:
					self.bias[pt, i] = max(self.bias[pt, i], v) 
	
	
	def moveTo(self, pt):
		print "moving to %i" % pt
		self.current_location=pt
		if pt == self.target:
			self.best = (self.true_path, self.costOfPath(self.true_path))
			self.term = True
			return 
		self.explore(pt)
		self.ftips=[self.current_location]
		self.rtips=[self.target]
		self.best=None
		self.term=None
		self.fpaths={self.current_location:[0.0, [self.current_location], self.move]}
		self.rpaths={self.target:[0.0, [self.target], self.move]}
		self.contact=[]
		self.true_path.append(pt)
	

				
			
	
			
			
		
		
		
		
		
		
		
		