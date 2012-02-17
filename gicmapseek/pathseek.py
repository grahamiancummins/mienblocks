#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2008-08-19.

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
import time

class PathSeeker(object):
	def __init__(self, bias, source, target, params=None):
		if not params:
			params={}
		self.params={'closeenough':0, 'impossible':0, 'optimism':1.0}
		self.params.update(params)
		self.space=(bias.attrib('width'), bias.attrib('edge'), bias.attrib('blanks'))
		
		self.bias=bias.getData()
		if self.bias.shape[1]!=6:
			if self.bias.shape[1]==3:
				self.bias=nd2d(self.bias, self.space[0], self.space[2])
			else:
				raise StandardError('pathseeker requires that the bias field be a directed (6D) or non-directed (3D) hexgrid')
		biasvalues=self.bias[self.bias!=self.space[2]]
		self.bias_stats=(biasvalues.min(), biasvalues.max(), biasvalues.mean(), biasvalues.sum())
		if self.bias_stats[0]<=0:
			raise StandardError('pathseeker requires that the bias field be strictly positive')
		self.expectation=self.bias_stats[2]
		if self.params['optimism']:
			mea = self.bias_stats[2] 
			if self.params['optimism']>0:
				extr = self.bias_stats[0]
				opti = self.params['optimism']
			else:
				extr = self.bias_stats[1]
				opti =  -self.params['optimism']
			self.expectation=mea + (extr-mea)*opti
		#print self.expectation, self.bias_stats, self.params['optimism']
		self.move=0
		self.fpaths={}
		self.ftips=[]
		self.rpaths={}
		self.rtips=[]
		self.contact=[]
		self.best=None
		self.term=None
		
		for i in range(source.shape[0]):
			spi=xyToHexI(source[i,:2], self.space[0], self.space[1])
			self.fpaths[spi]=[source[i,2], [spi], self.move]
			self.ftips.append(spi)
		for i in range(target.shape[0]):
			tpi=xyToHexI(target[i,:2], self.space[0], self.space[1])
			self.rpaths[tpi]=[target[i,2], [tpi], self.move]
			self.rtips.append(tpi)
		
	def report(self, s):
		print s	
		
	def step(self, reverse=0):
		self.contact=[]
		self.move+=1
		if not reverse:
			paths=self.fpaths
			tips=self.ftips
			explored=self.rpaths
		else:
			paths=self.rpaths
			tips=self.rtips
			explored=self.fpaths
		try:	
			sp=tips.pop(0)
		except IndexError:
			self.term=('exhausted space', (reverse, self.move))
			self.report('no more active path tips!!')
			return
		targets=getAdjacentPoints(sp, self.space[0])
		#print sp, targets, self.bias.shape
		costs=self.bias[sp,:]
		for j in range(6):
			if costs[j]==self.space[2]:
				continue
			if self.params['impossible'] and costs[j]>=self.params['impossible']:
				continue
			if targets[j]>self.bias.shape[0]-1:
				continue
			t=targets[j]	
			if t in paths[sp][1]:
				continue
			nc=paths[sp][0]+costs[j]
			if not paths.has_key(t) or paths[t][0]>nc:
				#found a new path
				paths[t]=[nc, paths[sp][1]+[t], self.move]
				if explored.has_key(t):
					self.contact.append(t)
				elif not t in tips:
					tips.append(t)
			
	def findFullPaths(self):
		for p in self.contact:
			pcost=self.fpaths[p][0]+self.rpaths[p][0]
			pfp = self.rpaths[p][1][:-1]
			pfp.reverse()
			path=tuple(self.fpaths[p][1]+pfp)
			if not self.best or pcost<self.best[1]:
				self.best=(path, pcost)
		self.contact=[]
	
	def pruneTips(self, cost):
		#remove any growth tips that have 0 chance of contributing to the optimal solution
		if not self.ftips or not self.rtips:
			return
		if self.params['closeenough']:
			cost-=self.params['closeenough'] 
		ftc = [self.fpaths[t][0] for t in self.ftips]
		rtc = [self.rpaths[t][0] for t in self.rtips]
		mftc=min(ftc)
		mrtc=min(rtc)
		if mftc+mrtc>=cost:
			self.ftips=[]
			self.rtips=[]
			return
		killft=[]
		rtips=[]	
		for i in range(len(self.ftips)):
			if ftc[i]+mrtc >= cost:
				killft.append(self.ftips[i])
			else:
				gotone=False
				for j in range(len(self.rtips)):
					if ftc[i]+rtc[j]<=cost:
						fp=self.ftips[i]
						rp=self.rtips[j]
						r=pathSeparation(fp, rp, self.space[0])
						tc=ftc[i]+rtc[j]+self.expectation*r
						if tc<=cost:
							if not rp in rtips:
								rtips.append(rp)
							gotone=True
				if not gotone:
					killft.append(self.ftips[i])
		if killft:
			self.ftips=[i for i in self.ftips if not i in killft]
		self.rtips=rtips	
			
			
	def checkForBetterPath(self):
		pcost = self.best[1]
		self.pruneTips(pcost)
		if self.ftips and self.rtips:
			pass
		else:
			self.term=True
			
	def solve(self):
		while not self.term:
			self.step(self.move%2)
			if self.contact:
				self.findFullPaths()
			if self.best:
				self.checkForBetterPath()
		if self.best:
			return ('solved', self.best)
		return self.term	
		
	def expandPath(self, p):
		path=[]
		for pt in p:
			path.append(hexItoXY(pt, self.space[0], self.space[1], False))
		return array(path)
				

class TimedPathSeeker(PathSeeker):
	def __init__(self, bias, source, target, params=None):
		PathSeeker.__init__(self, bias, source, target, params)
		if not 'step_time' in self.params:
			self.params['step_time']=.2
		self.true_path=[]
		self.target=self.rtips[0]
		self.current_location = self.ftips[0]
		
		
	def nextPoint(self, path):
		try:
			return path[path.index(self.current_location)+1]
		except (IndexError, ValueError):
			return -1	
			
	def failsafe(self):
		emin = None
		for i in range(6):
			v = self.bias[self.current_location, i]
			if v!=self.space[2]:
				if not emin:
					emin = (i, v)
				elif v<emin[1]:
					emin = (i,v)
		return followEdge(self.current_location, emin[0], self.space[0])
				
	def guess(self):
		'''Return a list of points containing the current best estimate of a solution path. If the algorithm is finished, this will be usually be the solution. If not, it is the path that is currently judged to have the best chance of being the optimal solution. The choice will depend on the algorithm's "optimism" parameter.'''
		if self.term and self.best:
			return (self.best[0], [])
		elif not self.ftips or not self.rtips:
			print "Warning: no active tips, but no complete solution", self.term, self.best
			return []
		if self.best:
			path, cost = self.best
			if self.nextPoint(path)==-1:
				cost = self.bias_stats[3]
		else:
			path, cost = [], self.bias_stats[3]
		ftc = [self.fpaths[t][0] for t in self.ftips]
		rtc = [self.rpaths[t][0] for t in self.rtips]
		mftc=min(ftc)
		mrtc=min(rtc)
		if mftc+mrtc>=cost:
			return (path, []) 
		rpath = []	
		for i in range(len(self.ftips)):
			fp=self.ftips[i]
			if self.nextPoint(self.fpaths[fp][1])==-1:
				continue	
			if ftc[i]+mrtc < cost:
				for j in range(len(self.rtips)):
					if ftc[i]+rtc[j]<cost:
						rp=self.rtips[j]
						r=pathSeparation(fp, rp, self.space[0])
						tc=ftc[i]+rtc[j]+self.expectation*r
						if tc<cost:
							path = self.fpaths[fp][1]
							rpath = self.rpaths[rp][1]
							cost = tc 
		return (path, rpath)
					
	def nextMove(self):
		'''Make the best estimate of a move of steps edges, using at most seconds seconds of compute time '''
		if self.term and self.best:
			p = self.nextPoint(self.best[0])
			if p!=-1:
				self.last_guessed_path = self.best[0]
				return p
			self.best=None
			self.term=None	
		start = time.time()
		while not self.term:
			self.step(self.move%2)
			if self.contact:
				self.findFullPaths()
			if self.best:
				self.checkForBetterPath()
			if time.time()-start>=self.params['step_time']:
				break	
		if self.term and self.best:
			path = self.best[0]
			self.last_guessed_path = path
		else:
			path, rpath = self.guess()	
			self.last_guessed_path = path+rpath
		p=self.nextPoint(path)
		#print path, p
		if p==self.current_location:
			print path
			raise
		if p!=-1:
			return p
		else:
			print 'no path. Using failsafe'
			return self.failsafe()

	def moveTo(self, point):
		'''Change the current location to "point" (a hexgrid 1D index). This destroys all forward paths and tips that don't pass through point, and adds a new tip at point. Point must be already visited by the algorithm, or a StandardError is raised.'''
		print "moving to %i" % point 
		self.current_location=point
		self.true_path.append(point)
		if self.term or point==self.target:
			return 
		if not self.fpaths.has_key(point):
			raise StandardError('attempt to move to an unknown point')
		costp = self.fpaths[point][0]
		for k in self.fpaths.keys():
			p = self.fpaths[k][1]
			if not point in p:
				del(self.fpaths[k])
		for tip in self.ftips[:]:
			if not self.fpaths.has_key(tip):
				self.ftips.remove(tip)
		if not point in self.ftips:
			self.ftips.append(point)

	def costOfPath(self, p):
		cost=0
		loc = p[0]
		for point in p[1:]:
			e = findConnectingEdge(loc, point, self.space[0])
			cost+=self.bias[loc, e]
			loc=point
		return cost		

	def solve(self):
		'''Construct a solution while forced to make a move of every t seconds '''
		while not self.current_location == self.target:
			try:
				point = self.nextMove()
				self.moveTo(point)
			except:
				raise
				return ('solution failed', (0, self.move))
		return ('solved', (self.true_path, self.costOfPath(self.true_path) ))
			
		