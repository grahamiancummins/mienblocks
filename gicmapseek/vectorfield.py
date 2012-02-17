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
from mien.math.array import combinations, eucd

try:
	import gicmapseek.optext as oe
except:
	import mb_binary.loader
	oe=mb_binary.loader.load('optext')
import time

def nonzero1d(a):
	return nonzero(a)[0]
	
def sparsedot_int(v1, v2):
	'''v1 and v2 are tuples of (indexes, values) arrays. Return a float that is the sparse dot product'''
	ci=intersect1d(v1[0], v2[0])
	v1=take(v1[1], oe.findindex(ci, v1[0]))
 	v2=take(v2[1], oe.findindex(ci, v2[0]))
	return dot(v1, v2)	

	
class DiscreteVectorField:
	'''This class represents a set of (sparse) points in a finite and discrete linear space. Each point may have an associated vector of values. 
	In addition, there is an atribute "rules" that points to a list of strings. These specify how columns in values behave when combined (e.g when fields are superposed). The labels may be  "add", "min", "max", "mul", "replace" or "av". "Add" gets the expected superposition behavior. An "av" rule must be in a column immeadiately preceeded by an add rule (this preceding column is assumed to be a count the number of samples or a weight). This rule takes a weighted average, weighted by the value in the preceding column value.'''
	indexdtype=int32
	valuedtype=float64
	debug=False
	
	def __init__(self, dims, rules=1, **opts):
		'''dims is a tuple of dimensions. rules is an integer (the order of the vector field), or a list of strings if dimensions of the value field have superposition rules other than "add".'''
		if type(rules)==int:
			rules=['add']*rules
		self.nvals=len(rules)
		self.rules=rules
		self.dims=array(dims)
		self.shape=tuple(dims)
		self.constants=opts.get('constants', {})
		if not opts.get('nosetup'):
			self.setup()	
		
	def setup(self):	
		dims=self.dims
		self.width=len(dims)
		self.size=multiply.reduce(dims)
		self.strides=concatenate([[1], cumprod(dims)[:-1]]).astype(int64)
		self.set(None)
		
	def new(self, dat=None, check=True):
		foo=self.__class__(self.dims, self.rules, nosetup=True, constants=self.constants)
		foo.width=self.width
		foo.size=self.size
		foo.strides=self.strides
		foo.set(dat, False, check)
		return foo	
						
	def clone(self):
		return self.new(self.get(copy=True), False)
	
	def array(self):
		return column_stack([self.ind, self.val])	
		
	def full(self):
		'''return a full array'''
		a=zeros(self.dims)
		a[self.ind[:,0],self.ind[:,1]]=self.val[:,0]
		return a	
		
	def fromFull(self, a, vector=False):
		if vector:
			#FIXME
			print "not implemented"
		else:
			sp=self.__class__(a.shape)
			ind=[]
			x = nonzero(a)
			v= reshape(a[x], (-1,1))
			ind=transpose(array(x))
			sp.set((ind, v))
			return sp
		
		
	def val2str(self, i):
		return "%.5g "*self.val.shape[1] % tuple(self.val[i,:])
		
	def __len__(self):
		return self.val.shape[0]
		
	def __str__(self):
		if self.debug:
			return self.longstr()
		elif len(self)==0:
			return "<empty discrete space>"
		l=[]
		for i in range(len(self)):
			l.append("%s=%s" % (str(self.ind[i,:]), self.val2str(i)))
		return ', '.join(l)
	
	def allPoints(self):
		'''Return an array of indexes that could be used as self.ind if every point in the space was specified'''
		l=[]
		for d in self.dims:
			l.append(arange(d))
		return combinations(l)
	
	def longstr(self):
		l=['---Discrete Space %s ---'  % (self.dims,)]
		lablen=len(l[0])
		for i in range(len(self)):
			l.append("%s -> %s" % (str(self.ind[i,:]), self.val2str(i)))
		if len(self)==0:
			l.append('|'+' '*(-2+lablen/2)+'empty')
		l.append('-'*lablen)	
		l.append('\n')
		return "\n".join(l)	
		
	def getPointValue(self, ind, col=0):
		n=nonzero(all(array(ind)==self.ind, 1)	)[0]
		if n.shape[0]==0:
			return 0.0
		else:
			return self.val[n[0],col]
	
		
	def set(self, dat, flat=False, check=True):
		'''If dat is true it should be a tuple of (index, value) arrays. If flat is True, the input is using 1D indexing. If check is True (default) points outside the bounds of the space are removed. Setting this to False can save some time if the points are already bounds checked (for example because they are drawn from another space of the same dimensions)'''
		if not(dat):
			self.ind=zeros((0, self.width), self.indexdtype)
			self.val=zeros((0, self.nvals), self.valuedtype)
		else:	
			if flat:
				dat=list(dat)
				dat[0]=self.fullindex(dat[0])
			if check:	
				dat=self.inspace(dat)
			self.ind=dat[0]
			self.val=dat[1]
	
	def get(self, flat=False, copy=False):
		'''return a tuple of (index, value) arrays. If flat is True, indexes use 1D indexing'''
		if flat:
			i=self.flatindex()
		elif copy:
			i=self.ind.copy()
		else:
			i=self.ind
		v=self.val
		if copy:
			v=self.val.copy()
		else:
			v=self.val
		return (i,v)
		
	def getSorted(self):
		'''return and (index, value) array using a flat index, such that idex is sorted (and set operations work with it). The returned arrays are alays a copy.'''
		if self.ind.shape[0]==0:
			return (self.ind.sum(1), self.val.copy())
		i=self.flatindex()
		ind=i.argsort()
		return (i[ind], self.val[ind,:])
	
	def addpt(self, coords, vals=None):
		'''Add a point to the space with the indicated coordinates and density. If this point is already in the space, the density of the point is incremented. If the point is outside the bounds of the space, nothing happens, and a warning is printed '''
		if vals==None:
			vals=ones(self.nvals)
		coords=array(coords)
		if all(coords>=0) and all(coords<self.dims):
			ii=nonzero1d(all(self.ind==coords, 1))
			if ii.shape[0]==0:
				self.ind=vstack([self.ind, coords.astype(self.indexdtype)])
				self.val=vstack([self.val, vals])
			else:
				self._addtopoint(ii, vals)
		else:
			print "Warning: %s is outside the space" % (str(coords),)
			print self.dims
			
	def killpt(self, coords):
		'''removes the point at coords from the space (if it was in the space)'''
		coords=array(coords)
		ii=nonzero1d(all(self.ind==coords, 1))
		if ii.shape[0]:
			self.remove(ii)
	
	def _addtopoint(self, i, vals):
		'''Combine the indicated values with the point at i (i is an index into self.vals). USed internally by addpt. Should not need to be called by clients.'''
		for j, t in enumerate(self.rules):
			if t=='add':
				self.val[i,j]+=vals[j]
			elif t=='max':
				self.val[i,j]=max(vals[j], self.vals[i,j])
			elif t=='min':
				self.val[i,j]=min(vals[j], self.vals[i,j])
			elif t=='mul':
				self.val[i,j]=vals[j]*self.vals[i,j]
			elif t=='replace':
				self.val[i,j]=vals[j]
			elif t=='av':
				lcs=self.val[i, j-1]
				lco=val[i, j-1]
				m=(self.val[i,j]*lcs+vals[i, j]*lco)/(lcs+lco)
				self.val[i, j]=m
	
	def onDomain(self, space, thresh=None, check=False):
		'''Edit self so that self.ind is a subset of space.ind. Space must be on the samp dimensions as self for this to work. If thresh is not None, restrict space such that only indexes corresponding to primary values greater than thresh are included (priary values are those defied in the 0 colum of space.val). If Check is true, the domain reduction is only applied if it results in a non-empty space'''
		oi, ov=space.getSorted()
		if thresh!=None:
			oi=oi[nonzero(ov>thresh)]
		if check and len(oi)==0:
			return	
		si, sv=self.getSorted()
		iio=nonzero1d(setmember1d(si, oi))
		self.set((si[iio], sv[iio]), True, False)
		

	def inspace(self, dat):
		'''From a point tuple, rutern a new tuple of points that are in the bounds of the space'''
		if not dat:
			return dat
		pts=dat[0]
		gz=all(pts>=0, 1)
		lb=all(pts<self.dims, 1)
		ind=nonzero1d(logical_and(gz, lb))
		pts=take(pts, ind, 0)
		vals=take(dat[1], ind, 0)
		return (pts.astype(self.indexdtype), vals.astype(self.valuedtype))
		
	def boundscheck(self):
		self.set(self.get(), check=True)
		
	def flatindex(self, ind=None):
		'''Return a 1d array of int64 specifying the indexes into a flattened version of the discrete space (these are 1 to 1 with the multi-D indexes). If the input argument is unspecified, use self.ind'''
		if ind==None:
			ind=self.ind
		return (ind*self.strides).sum(1)
	
	def fullindex(self, ind=None):
		'''The reverse of flatindex. Takes an array of 1D indexes, and returns M-d points. If the input is unspecified, returns a copy of self.ind'''
		if ind==None:
			return self.ind.copy()
		op=zeros((ind.shape[0], self.width), self.indexdtype)
		for c in range(self.width-1, -1, -1):
			co, ind = divmod(ind, self.strides[c])
			op[:,c]=co.astype(op.dtype)
		return op
		
	def add(self, new):
		'''combine the points in self with the points in new (a space of the same type) using the rules in self.rules''' 
		if not new:
			return self
		sp=self.getSorted()
		op=new.getSorted()			
		cp=self._combineValues(sp, op)
		self.set(cp, True, False)
	
	def reset(self, new):
		'''set any points (in self) specified in the space new to the values they have in new'''
		r=self.rules
		self.rules=['replace']*len(r)
		self.add(new)
		self.rules=r
					
	def dot(self, space):
		'''ignores mul, min and max values. Dots "add" values unless they precede "av" values (in that case, dots the averages)'''
		if not space:
			return 0.0
		s=self.getSorted()
		o=space.getSorted()
		dp=0.0
		for i, t in enumerate(self.rules):
			if t=='add':
				if i+1<len(self.rules) and self.rules[i+1]=='av':
					dp+=sparsedot_int( (s[0], s[1][:,i+1]), (o[0], o[1][:,i+1]))
				else:
 					dp+=sparsedot_int( (s[0], s[1][:,i]), (o[0], o[1][:,i]))		
 		return dp
	
	def weight(self, wt):
		'''apply a weighting scalar to self.values'''
		for i, t in enumerate(self.rules):
			if t=='add':
				self.val[:,i]*=wt
			elif t in ['max', 'min', 'av', 'mul', 'replace']:
				pass		
				
	def mul(self, space):
		'''weight the "add" values in self by the values in space'''
		sp=self.flatindex()
		op=space.flatindex()		
		both=intersect1d(sp, op)
		si=oe.findindex(both, sp)
		oi=oe.findindex(both, op)
		nv=zeros((both.shape[0], len(self.rules)))
		for i, t in enumerate(self.rules):
			if t=='add':
				nv[:,i]=self.val[si,i]*space.val[oi,i]
			else:
				nv[:,i]=self.val[si,i]	
		self.set((both, nv), True, False)		
		
	def remove(self, ind):
		'''delete the points with the indicated indexes. These indexes are the actual values of the first index into self.ind, _not_ indexes into the sparse space'''
		pts, vals=self.get()
		pts=delete(pts, ind, 0)		
		vals=delete(vals, ind, 0)
		self.set((pts, vals), False, False)
	
	def _combineValues(self, t1, t2):
		if t1[0].shape[0]==0:
			return t2
		elif t2[0].shape[0]==0:
			return t1
		both=intersect1d(t1[0], t2[0])
		if both.shape[0]==0:
			ind=concatenate([t1[0], t2[0]])
			val=vstack([t1[1], t2[1]])
			return (ind, val)
		t1u=setdiff1d(t1[0], both)
		t2u=setdiff1d(t2[0], both)
		ind=concatenate([t1u, t2u, both])
		valr=zeros((ind.shape[0], t1[1].shape[1]), t1[1].dtype)
		t2u=oe.findindex(t2u, t2[0])		
		t1u=oe.findindex(t1u, t1[0])
		valr[:t1u.shape[0]]=t1[1][t1u]
		valr[t1u.shape[0]:-both.shape[0]]=t2[1][t2u]
		cv1=delete(t1[1], t1u, 0)
		cv2=delete(t2[1], t2u, 0)
		for i, t in enumerate(self.rules):
			if t=='ignore':
				continue
			c1=cv1[:,i]
			c2=cv2[:,i]
			if t=='add':
				v=c1+c2
			elif t=='max':
				v=maximum(c1, c2)
			elif t=='min':
				v=minimum(c1, c2)
			elif t=='mul':
				v=c1*c2
			elif t=='replace':
				v=c2
			elif t=='av':
				lc1=cv1[:, i-1]
				lc2=cv2[:, i-1]
				v=(c1*lc1+c2*lc2)/(lc1+lc2)
			valr[-both.shape[0]:,i]=v	
		return (ind, valr)		
		
	def removezeros(self):
		z=nonzero1d(self.val[:,0]==0.0)
		if z.shape[0]:
			self.remove(z)	
			
	def exclude(self, space):
		'''remove from self any indexes in space'''	
		oi, ov=space.getSorted()
		if oi.shape[0]==0:
			return
		si, sv=self.getSorted()
		iio=nonzero1d(setdiff1d(si, oi))
		if iio.shape[0]==0:
			self.set(None)
		else:	
			self.set((si[iio], sv[iio]), True, False)	
	
	



def to1D(a):
	mini=a.min(0)
	a=a-mini
	dims=a.max(0)+1
	strides=concatenate([[1], cumprod(dims)[:-1]])
	return ((a*strides).sum(1), mini, dims)
	

def toND(a, mins, dims):
	strides=concatenate([[1], cumprod(dims)[:-1]])
	op=zeros((a.shape[0], len(dims)), int32)
	for c in range(op.shape[1]-1, -1, -1):
		co, a = divmod(a, strides[c])
		op[:,c]=co
	return op+mins	

def uniqueND(a):
	a,mins,dims=to1D(a)
	a=unique1d(a)
	return toND(a,mins,dims)

def quadrants(pts):
	'''renders the locus pts symmetric around the origin (pts should contain strictly non-negative values)'''
	z=[pts]
	quad=combinations([arange(-1,2,2) for x in range(pts.shape[1])])
	for t in quad:
		if all(t>0):
			continue
		z.append(pts*t)
	z=row_stack(z)
	return uniqueND(z)
	
	

class LocalizingVectorField(DiscreteVectorField):
	def local(self, ind, r):
		'''returns a space of the same type as self, in which all the points within radius r of point ind have value 1.0, and all other points are not defined.'''
		allpts=combinations([arange(0,r+1) for x in range(len(self.dims))])
		allpts=allpts[(allpts**2).sum(1)<=r**2]
		allpts= quadrants(allpts)
		allpts+=ind
		dat=(allpts, ones((allpts.shape[0], len(self.rules))))
		dat=self.inspace(dat)
		return self.new(dat,False)

	def boundary(self, ind, r):
		'''like local, but return only the points on the boundary of the local'''
		allpts=combinations([arange(0,r+1) for x in range(len(self.dims))])
		allpts=allpts[(allpts**2).sum(1)<=r**2]
		allpts=allpts[(allpts**2).sum(1)>(r-1)**2]
		allpts= quadrants(allpts)
		allpts+=ind
		dat=(allpts, ones((allpts.shape[0], len(self.rules))))
		dat=self.inspace(dat)
		return self.new(dat,False)

	def localValues(self, space):
		'''return a new space containing the values of self on the domain of space'''
		oi, ov=space.getSorted()
		si, sv=self.getSorted()
		iio=nonzero1d(setmember1d(si, oi))
		s=self.new()
		if iio.shape[0]:
			s.set((si[iio], sv[iio]), True, False)
		return s

	def set(self, dat, flat=False, check=True):
		'''If dat is true it should be a tuple of (index, value) arrays. If flat is True, the input is using 1D indexing. If check is True (default) points outside the bounds of the space are removed. Setting this to False can save some time if the points are already bounds checked (for example because they are drawn from another space of the same dimensions)'''
		if not(dat):
			self.ind=zeros((0, self.width), self.indexdtype)
			self.val=zeros((0, self.nvals), self.valuedtype)
		else:	
			if flat:
				dat=list(dat)
				dat[0]=self.fullindex(dat[0])
			if check:	
				dat=self.inspace(dat)
				l=self.constants.get('local')
				if l:
					dat=self.restrict(dat, l[0], l[1])
			self.ind=dat[0]
			self.val=dat[1]
			
	def restrict(self, dat, pt, r):
		'''Removes points form the index tuple dat where the points are more than r away from pt'''
		inr=eucd(dat[0],pt)<=r
		inr=nonzero1d(inr)
		if inr.shape[0]<dat[0].shape[0]:
			dat=(dat[0][inr,:], dat[1][inr,:])
		return dat
		
			