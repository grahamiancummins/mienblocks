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
from numpy.random import normal
import time

class STransform:
	'''Implement the  transformations for a layer of a map seeking circuit'''

	def __init__(self, space, bias=1):
		'''space is a DiscreteVectorField instance, and bias may be callable or an integer. 

Bias is used to specify obstacles, gradients, and other values that modify the density of the vector field. If bias is callable, self.applyBias(space) will call bias(space), which should modify a space in place. If bias is an integer it specifies the index of a colum in the space value array that is used as a bias. Bias arrays should use the "add" rule, and should have a minimum value of -1. The bias will be applied by multiplying the space values by bias+1. Consequently a bias of -1 will result in a final value of 0, a bias of 0 will not change the final value, and a bias greater than zero will increase the final value (e.g. .2 will increase it 20%). This somewhat conterintuitive notation is needed since the DiscreteVectorField is sparse, and undefined locations are assumed to have a value of 0, consequently, applying a bias channel directly as a scalar multiplier would result in zeroing the final value wherever the bias field is not explicitly defined (i.e. almost everywhere)'''
		self.space=space
		self.bias=bias
		self.tvec=zeros(0)

	def __len__(self):
		'''return the number of transformations (this is also the length of the list returned by apply). This class assumes that all transforms are represented by an array member "tvec", and the number of transforms is self.tvec.shape[0]. Subclasses using these semantics for tvec will not need to redefine this.'''
		return self.tvec.shape[0]

	def apply(self, inp, g, target=None, inv=1):
		'''input is a space (of the same dimension as self.space[inv]). g is a vector of gains. return is a list of length len(self) containing arrays of points (of dimension self.odims) resulting from each transformation (some of these may be empty lists, based on the gains). If inv is -1, apply the transforms in reverse.
		The apply method calls all the registered hard limits, but only when run in the forward direction. (limits are ignored in the reverse direction).'''
		out=self.space.new()
		if target!=None:
			q=zeros(len(self))
		if not inp:
			if target==None:
				return out
			else:
				return (out,q)
		eg=g/g.sum()		
		for i in nonzero1d(g):
			o=self.ithtransform(inp, i, inv)
			if target!=None:
				q[i]=self.match(o, target)
			o.weight(eg[i])
			out.add(o)	
		self.applyBias(out)	
		out.val[:,0]/=out.val[:,0].sum()
		if target==None:
			return out
		else:
			return (out,q)
		
	def inverse(self, inp, g):
		'''call self.apply with inv=-1 and target=None'''
		return self.apply(inp, g, None, -1)
			
	def info(self, show=True):
		l=[self.get(i) for i in range(len(self))]
		if not show:
			return l
		for i,v in enumerate(l):
			print "%i: %s" % (i, str(v))
		
	def get(self, i):
		'''return information about the ith tranformation. Default is to return self.tvec[0]'''
		return self.tvec[i]
			
	def match(self, image, target):
		'''Calculate overlap between the input image and target image (both of these should be of the same type as self.space). This method also applies any biases to the input image befor matching. This default version of the method assumes that the match is based only on the first column of values in the vector space.'''
		if not image or not target:
			return 0.0
		if self.bias:
			image=image.clone()
			self.applyBias(image)
		return target.dot(image)

	def applyBias(self, space):
		if self.bias!=None:
			if callable(self.bias):
				self.bias(space)
			elif type(self.bias)==int:	
				space.val[:,0]*=(1+space.val[:,self.bias])
			else:
				space.mul(self.bias)	

	def getSpace(self, input=True):
		return self.space.new()			


class SMapSeeker:
	'''Class that implements the iterative processing in a map seeking circuit.'''

	def __init__(self, bias, transforms, source, target, opts=None):
		'''This MSC is simpler and faster than the generic MapSeeker, but it is restricted to the case where every layer maps a given space onto itself. '''
		default={'maxiter':200, 'kappa':.5, 'precondition':2, 'checkdomain':True,
			'gdiscard':0.001, 'persist':True, 'rule':'kappa', 'mdiscard':0.0}
		default.update(opts or {})
		self.opts=default	
		self.layers=[]
		self.track=blank_track
		self.solv=None
		self.nlayers=len(transforms)
		self.layers.append({'for':None})
		for k in transforms:
			self.layers.append({'trans':k})		
	
	def getSpace(self, layer, input=True):
		return self.bias
	
	def prep(self, source, target):
		for l in self.layers[1:]:
			s=len(l['trans'])
			l['gain']=ones(s, float32)
			l['match']=zeros(s, float32) 
			l['for']=None
			l['rev']=None
		self.layers[0]['for']=source
		self.layers[-1]['rev']=target
		self.iter=0
		if self.opts['precondition']:
			for li in range(1, int(len(self.layers)/2)+2):
				tran=self.getTrans(li)
				self.layers[li]['for']=tran.apply(self.layers[li-1]['for'], self.layers[li]['gain'])
			if self.opts['precondition']>1:
				return self.checkConnect()
		return 0
		
	def report(self, s, important=1):
		sil=self.opts.get('silent', 0)
		if not important>sil:
			return
		print(s)			
	
	def run(self, source, target):
		'''source and target are 2D arrays aranged as a list of nD points. The first index is across a set of samples. The second contains coordinates in the search space'''
		state = self.prep(source, target)
		st=time.time()
		while not state and self.iter<self.opts['maxiter']:
			self.report("Iteration %i" % self.iter, 3)
			state=self.iterate()
		st= time.time()-st	
		self.report("Run complete (%.2f sec)" % st, 10)
		if state<1:
			self.report("Algorithm did not converge", 10)
			solv=None
		else:
			self.report("convergence reached", 5)
			solv=[argmax(self.layers[li]['gain']) for li in range(1, len(self.layers))] 
		return solv	
		
	def getTrans(self, layer):
		return self.layers[layer]['trans']
		
	def getSpace(self, layer, input=True):
		if input:
			lt='for'
		else:
			lt='rev'
		try:
			s=self.layers[layer][lt]
			return s.new()
		except:
			if layer==0:
				layer=1
			t=self.getTrans(layer)
			return t.getSpace(input)
	
	def checkConnect(self):
		''' '''
		self.opts['dryrun']=True

		self.iterate()
		self.opts['dryrun']=False
		tlist=[]
		for li in range(1, len(self.layers)):
			nsm=nonzero1d(self.layers[li]['match'])
			if len(nsm)==0:
				self.report("!!! No mapping is possible at %i !!!" % li, 10)
				return -1
			else:
				g=self.layers[li]['gain']
				g[:]=0.0
				g[nsm]=1.0
				self.report("layer %i: %i viable maps (of %i total)" % (li+1, g.sum(), g.shape[0]),2)
		return 0
		
	def learnkappa(self, l):
		q=l['match']/l['match'].max()
		q=self.opts['kappa']*(1-q)
		g=where(l['match']==0.0, 0.0, l['gain']-q)
		return g
		
	def matchproportional(self, l):
		return 	l['match']*l['gain']	
	
	def minkappaqp(self, l):
		q=l['match']/l['match'].max()
		q=self.opts['kappa']*(1-q)
		g=minimum(l['match']*l['gain'], l['gain']-q)
		return g
			
	def onfail(self, li):
		p=self.opts['persist']
		self.opts['persist']=False		
		self.report("resetting g",2)
		self.iter-=1
		for l in self.layers[1:]:
			l['gain']+=.05
			l['gain']/=l['gain'].max()
		conv=self.iterate()	
		self.opts['persist']=p
		return conv
		
		
	def iterate(self):
		'''Does the work in each iteration. Called by "run".'''
		converged=1
		ts=time.time()
		for li in range(len(self.layers)-1, 1, -1):
			l=self.layers[li]
			tran=self.getTrans(li)
			self.layers[li-1]['rev']=tran.inverse(l['rev'], l['gain'])
			if self.opts['checkdomain'] and li<=len(self.layers)/2 and self.layers[li-1]['for']!=None:# and len(self.layers[li-1]['for'])<len(self.layers[li-1]['rev']):
				self.layers[li-1]['rev'].onDomain(self.layers[li-1]['for'], check=True)
		self.iter+=1		
		for li in range(1, len(self.layers)):
			l=self.layers[li]
			tran=self.getTrans(li)
			l['for'], l['match']=tran.apply(self.layers[li-1]['for'], l['gain'], l['rev'])
			if self.opts['checkdomain'] and li>len(self.layers)/2: # and len(l['rev'])<len(l['for'])
				l['for'].onDomain(l['rev'], check=True)
			if self.opts['mdiscard']:
				l['match']=where(l['match']<(l['match'].max()*self.opts['mdiscard']), 0, l['match'])
			self.report("%i %i %i" % (li, len(l['for']), len(nonzero1d(l['match']))), 1)
			#print len(self.layers[li-1]['for']), len(nonzero1d(l['gain'])), len(l['for'])
			if not self.opts.get('dryrun'):
				self.track(self, self.iter, li, True)
				if not any(l['match']):
					self.report("No overlap possible at layer %i." % (li, ), 9)
					if self.opts['persist']:
						return self.onfail(li)
					else:						
						self.report("Unsolvable", 9)
						return -1
				g=self.learningrules[self.opts['rule']](self, l)	
				g=maximum(0, g/g.max())
				if self.opts['gdiscard']:
					g=where(g<self.opts['gdiscard'], 0.0, g)
				if g.sum()>1.5:
					converged=0	
					if all(abs(g-l['gain'])<.001):
						self.report("noise at %i" % li, 2)
						g=g+normal(0, .1, g.shape)
						g=clip(g, 0, 1)
				l['gain']=g
			self.track(self, self.iter, li, False)
		return converged

	
	learningrules={
		'kappa':learnkappa,
		'qp':matchproportional,
		'fast':minkappaqp,
		}	