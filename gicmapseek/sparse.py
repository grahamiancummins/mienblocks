#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2008-08-14.

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

from mien.math.array import *
from copy import deepcopy
try:
	import gicmapseek.optext as oe
except:
	import mb_binary.loader
	oe=mb_binary.loader.load('optext')
import time




class Sparse1D(object):
	'''Class for storing a 1D vector of values that may be sparse. The underlying data are stored in the element self.data, which is a 2-element list. If more than the fraction MAX_SPARSE of the values are non-zero, the data are stored in full mode, where the first value in the list is the string "full", and the second value is the 1D vector. In the sparse case, the first value is an integer vector of indexes, and the second is a float vector of corresponding values. In the sparse case, all non-specified values are assumed to be 0'''
	MAX_SPARSE=.2
	
	def __init__(self, dat, size=-1, sort=True):
		'''Create a new sparse object from the data in dat. This should be None, a 1D array, or a 2-element list, as descirbed in the class documentation string. It may be either sparse ([indexes, values]), or full (['full', values]). A 1D array will be converted to a "full" type list. None will be converted to an empty sparse list ([zeros(0, int32), zeros(0, float32)]). If the data are sparse, size will be used to determine the maximum size of the full vector (default is the largest index value in dat plus 1), and if sort is true, the indexes will be sorted. Sorting the indexes is required for correct operation of the class, so specify sort=True unless the calling function is certain the indexes are already sorted.'''
		if dat==None:
			dat=[zeros(0, int32), zeros(0, float32)]
		elif type(dat)!=list:
			if len(dat.shape)>1:
				dat=ravel(dat)
			dat=['full', dat]
		if dat[0]=='full':
			self.size = dat[1].shape[0]
		else:
			if sort:
				ind=argsort(dat[0])
				dat=[dat[0][ind], dat[1][ind]]
			if not dat[1].shape[0] or size>dat[1][-1]:
				self.size=size
			else:
				self.size=dat[1][-1]+1
		self.data=dat
		self.shape=(self.size,)
 	
	def _new(self, dat, size=None):
		if not size:
			size=self.size
		return Sparse1D(dat, size, False)	
		
	def clone(self):
		'''Return an identical Sparse instance to self, but with no side effects (essentially a deep copy)'''
		return self._new(deepcopy(self.data))
		
	def full(self, copy=False):
		'''return a 1D array that is the full version of self.data, no matter how the data are currently stored. If copy is true, make sure that this is a copy not a reference. Otherwise, if the data are stored as full, a reference is returned.'''
		if self.data[0]=='full':
			if copy:
				return self.data[1].copy()
			return self.data[1]
		d=zeros(self.size)
		d[self.data[0]]=self.data[1]
		return d	

	def __str__(self):
		s="Sparse array of size %i\n" % (self.size,)
		if self.data[0]=='full':
			s+='Full representation\n'
			s+=str(self.full())
		else:
			s+='Sparse representation\n'
			a=self.sparse()
			a=column_stack([a[0].astype(float32), a[1]])
			s+=str(a)
		return s
		
	def __repr__(self):
		return "Sparse1D(%s, %i)" % (repr(self.data), self.size)

	def sparse(self, copy=False):
		'''return a tuple that is the sparse version of self.data, no matter how the data are currently stored (and ignoring the density of the data and the value of MAX_SPARSE). If copy is true, make sure that this is a copy not a reference. Otherwise, if the data are stored as sparse, a reference is returned.'''
		if self.data[0]!='full':
			if copy:
				return deepcopy(self.data)
			return self.data
		ind=nonzero(self.data[1])[0]
		return (ind, self.data[1][ind])
	
	def max(self):
		return self.data[1].max()

		
	def getpt(self, i):
		'''Return the value at index i (i integer) '''
		if self.data[0]=='full':
			return self.data[1][i]		
		i=nonzero(self.data[0]==i)[0]
		if i.shape[0]:
			return self.data[1][i[0]]
		else:
			return 0.0
		
	def setpt(self, i, v):
		'''Set the value at index i (integer) to v (float)'''
		if self.data[0]=='full':
			self.data[1][i]=v
			return	
		ind=nonzero(self.data[0]==i)[0]
		if ind.shape[0]:
			self.data[1][ind[0]]=v
		else:
			il=searchsorted(self.data[0], i)
			self.data=[concatenate([self.data[0][:il], [i], self.data[0][il:]]), 
					concatenate([self.data[1][:il], [v], self.data[1][il:]])]
		
	def get(self, ind):
		'''return a 1D array of values at the indexes given in the 1D array ind (ind must be sorted)'''
		if self.data[0]=='full':
			return self.data[1][ind]
		val=zeros(ind.shape[0])	
		has=union1d(ind, self.data[0])
		myind=oe.findindex(has, self.data[0])
		ind=oe.findindex(has, ind)
		val[ind]=self.data[1][myind]
		return val
	
	def set(self, dat):
		'''sets values in self.data according to the list dat, which should be either a 1D full array, or [indexes, values]. The indexes must be sorted. No size checking is done by this method. Use self.condition if you need it. Note that setting with a full array will entirely overwrite existing data, and may change self.size.'''
		if type(dat)==ndarray:
			if len(dat.shape)>1:
				dat=ravel(dat)
			self.data=['full', dat]
			self.size = self.data.shape[0]
			return
		myind=setdiff1d(self.data[0], dat[0])
		if not myind.shape[0]:
			self.data=deepcopy(dat)
			return
		ind = union1d(dat[0], self.data[0])
		vals=zeros(ind.shape[0], self.data[1].dtype)
		mynewindex=oe.findindex(myind, ind)
		vals[mynewindex]=self.data[1][myind]
		newind = oe.findindex(dat[0], ind)
		vals[newind]=dat[1][dat[0]]
		self.data=[ind, vals]
		
	def dot(self, s):
		'''Return a scalar that is the dot product of self with the sparse instance s'''	
		if self.data[0]=='full' and s.data[0]=='full':
			return dot(self.data[1], s.data[1])
		s = self.mul(s)
		return s.data[1].sum()

	def mul(self, s):
		'''Return a Sparse instance that is the product of self*s, where s is another sparse instance'''
		if self.data[0]=='full' and s.data[0]=='full':
			v=self.data[1]*s.data[1]
			return self._new(['full', v])
		sd = self.data
		od= s.data	
		if sd[0]=='full':
			sd = [od[0], sd[1][od[0]]]
		elif od[0]=='full':
			od = [sd[0], od[1][sd[0]]]
		ind=intersect1d(sd[0], od[0])
		si=oe.findindex(ind, sd[0])
		oi=oe.findindex(ind, od[0])
		v=[ind, sd[1][si]*od[1][oi]]
		return self._new(v)
		
	def __mul__(self, s):
		if isinstance(s, Sparse1D):
			return self.mul(s)
		out=self.clone()
		out.data[1]*=s
		return out	
		
	def __div__(self, s):
		if isinstance(s, Sparse1D):
			s = 1.0/s
			return self.mul(s)
		return self._new([self.data[0], self.data[1]/s])
			
	def __rdiv__(self, s):
		if self.data[0]!=full:
			if self.data[0].shape[0]<self.size:
				raise ZeroDivisionError('Dividing by a sparse space with implicit zeros')
			else:
				self.data=['full', self.data[1]]
		dat = self._new(['full', s/self.data[1]])
		
		
	def __add__(self, s):
		if isinstance(s, Sparse1D):
			return self.add(s)
		out=self.clone()
		out.data[1]+=s
		return out	
		
	def __eq__(self, f):
		if f in [None, False]:
			return False
		if self.data[0]=='full':
			eq=nonzero(self.data[1]==f)[0]
		else:
			if f!=0:
				eq=self.data[0][self.data[1]==f]
			else:
				nzi=self.data[0][nonzero(self.data[1])]
				ai = arange(self.size)
				eq=setdiff1d(ai, nzi)
		dat = self.condition([eq, ones(eq.shape, self.data[1].dtype)])
		return self._new(dat)	
	
	def __invert__(self):
		if self.data[0]=='full':
			nd = ['full', logical_not(self.data[1])]
		else:
			nzi=self.data[0][nonzero(self.data[1])]
			ai = arange(self.size)
			eq=setdiff1d(ai, nzi)
			nd=[eq, ones(eq.shape, self.data[1].dtype)]
		dat = self.condition(nd)
		return self._new(dat)	
	
	def __ne__(self, f):
		if f in [None, False]:
			return True
		if self.data[0]=='full':
			eq=nonzero(self.data[1]!=f)[0]
		else:
			if f!=0:
				eq=self.data[0][self.data[1]==f]
				ai = arange(self.size)
				eq=setdiff1d(ai, eq)
			else:
				eq=self.data[0][nonzero(self.data[1])]
		dat = self.condition([eq, ones(eq.shape, self.data[1].dtype)])
		return self._new(dat)	
		
	def __getitem__(self, i):
		if type(i)==ndarray:
			return self.get(i)
		else:
			return self.getpt(i)
		
	def __setitem__(self, i, v):
		if type(i)==ndarray:
			if type(v) in [float, int]:
				v = ones_like(i)*v
			self.set([i,v])
		else:
			self.setpt(i,v)		
		
	def sum(self):
		return self.data[1].sum()
		
	def add(self, s):
		'''Return a Sparse instance that is the sum of self+s, where s is another sparse instance'''
		if self.data[0]=='full' and s.data[0]=='full':
			v=self.data[1]+s.data[1]
			return self._new(['full', v])	
		sd = self.data
		od= s.data	
		if sd[0]=='full':
			v=sd[1].copy()
			v[od[0]]+=od[1]
			return self._new(['full', v])	
		elif od[0]=='full':
			v=od[1].copy()
			v[sd[0]]+=sd[1]
			return self._new(['full', v])	
		ind = union1d(sd[0], od[0])
		msize=max(self.size, s.size)
		if ind.shape[0] > self.MAX_SPARSE * msize:
			v=zeros(msize, sd[1].dtype)
			v[sd[0]]=sd[1]
			v[od[0]]+=od[1]
			return self._new(['full', v])	
		v = zeros(ind.shape[0], sd[1].dtype)
		oi=oe.findindex(od[0], ind)
		si=oe.findindex(sd[0], ind)
		v[si]=sd[1]
		v[oi]+=od[1]
		return self._new([ind, v], msize)	
		
		
	def squeeze(self):
		'''Optimize storage. If storage is full, check to see that there are more than MAX_SPARSE non-zeros, and convert to sparse if not. If storage is sparse, and there are more than MAX_SPARSE non-zeros, convert to full. Otherwise remove any explicit storage of zeros in the sparse list.'''	
		if self.data[0]=='full':
			nnz=nonzero(self.data[1])[0]
			if nnz.shape[0]<self.MAX_SPARSE*self.data[1].shape[0]:
				self.size=self.data[1].shape[0]
				self.data=[nnz, self.data[1][nnz]]
		else:
			nnz=nonzero(self.data[1])[0]
			if nnz.shape[0]>self.MAX_SPARSE*self.size:
				v=zeros(self.size, self.data[1].dtype)
				v[self.data[0]]=self.data[1]
				self.data=['full', v]
			elif nnz.shape[0]<self.data[1].shape[0]:
				self.data=[self.data[0][nnz], self.data[1][nnz]]
					
	def condition(self, dat):
		'''dat may be a 1D full vector or a sparse list. Return either a 1D full vector or a sparse list, whichever is more appropriate, to represent dat. This will also remove any indexes in dat that are <0 or >self.size, or that refer to values of 0, in the case that the return is a sparse list.'''	
		if type(dat)==list:
			if dat[0]=='full':
				dat=dat[1]
			else:
				gi=nonzero(logical_and(dat[1], logical_and(dat[0]>=0, dat[0]<self.size)))[0]
				if gi.shape[0]<dat[0].shape[0]:
					dat=[dat[0][gi], dat[1][gi]]
				if dat[0].shape[0]>self.MAX_SPARSE*self.size:
					v=zeros(self.size, self.data[1].dtype)
					v[dat[0]]=dat[1]
					return ['full', v]
				return dat
		if type(dat)!=list:
			nnz=nonzero(dat)[0]
			if nnz.shape[0]<self.MAX_SPARSE*dat.shape[0]:
				dat=[nnz, dat[nnz]]
			return dat
			
	def maximum(self, s):
		'''Return a sparse space that contains the maximum value of self and the space s at each index '''
		sd = self.data
		od = s.data
		if sd[0]=='full':
			if not od[0]=='full':
				od = ['full', s.full()]
			v=maximum(sd[1], od[1])
			return self._new(['full', v])	
		elif od[0]=='full':
			v=maximum(self.full()+od[1])
			return self._new(['full', v])	
		ind = union1d(sd[0], od[0])
		nti=ind.shape[0]
		if nti > self.MAX_SPARSE * self.size:
			v = maximum(self.full(), s.full())
			return self._new(['full', v])	
		v = zeros(nti, sd[1].dtype)
		v2 = zeros(nti, sd[1].dtype)
		oi=oe.findindex(od[0], ind)
		si=oe.findindex(sd[0], ind)
		v[si]=sd[1]
		v2[oi]=od[1]
		v=maximum(v,v2)
		return self._new([ind, v])	
			
			 
class Sparse(Sparse1D):
	'''Modification of the Sparse1D class that allows any shape of the array data. Underlying storage is done in identically to Sparse1D, but the init and accessor methods are overloaded to allow multi-d indexing. Returned Full arrays are simply ND arrays, and sparse tuples are as described in the parent class, but the index component is 2D, N rows by D columns, where N=number of non-zero elements, and D=number of dimensions. Internal math methods (eg dot and add) are still implemented in 1D mode.'''
	
	def __init__(self, dat, shape=-1, sort=True, flat=False):
		'''Like the parent class method, but shape (rather than size) is a shape tuple, and dat, if sparse, is as described in the main doc string of this class. As in the parent class, shape is ignored if dat is full, and if dat is sparse and shape is -1, the default shape is the smallest one (in all dimensions) that can contain the specified data. Sort still acts as in the parent class, since the underlying storage mode is 1D and must be sorted.
		The "flat" flag is  used by internal methods. If True, then if dat is sparse, it is flat indexed (1D). In general, clients should never use this flag. It exists to avoid the overhead of converting from flat to ND indexes and back when making copies of self and returning the results of math operations
		'''
		if flat:
			pass
		elif dat==None:
			if type(shape)!=tuple:
				raise StandardError('Init of Sparse class with no data requires a shape tuple')
			dat=[zeros(0, int32), zeros(0, float32)]
			flat=True
		elif type(dat)!=list:
			shape=dat.shape
			dat=['full', dat]
		elif dat[0]=='full':
			shape=dat[1].shape
		elif shape==-1:
			shape=tuple(dat[1].max(0)+1)
		self.shape=shape
		self.size=multiply.reduce(self.shape)
		rs = tuple(take(self.shape, arange(len(self.shape)-1,-1,-1)))
		self.strides=concatenate([[1], cumprod(rs)[:-1]])
		self.strides=self.strides[arange(self.strides.shape[0]-1, -1, -1)]
		if not flat:
			dat = self.to1d(dat)
		if sort and dat[0]!='full':
			ind=argsort(dat[0])
			dat=[dat[0][ind], dat[1][ind]]
		self.data=dat	
	
	
	def changesize(self, newshape, insertat, optimize = True):
		new = Sparse(None, newshape)
		dat = self.sparse()
		dat[0] = dat[0] + array(insertat)
		new.set(dat)
		if optimize:
			new.squeeze()
		return new
	
	
	def __repr__(self):
		return "Sparse(%s, %s)" % (repr(self.data), repr(self.shape))
			
	def to1d(self, dat):
		if dat[0]=='full':
			return ['full', dat[1].ravel()]
		fi=(dat[0]*self.strides).sum(1)
		return [fi, dat[1]]
		
	def toNd(self, dat=None):
		''' Converts the sparse list dat to a representation with self.shape. This method may also be used for data retrieval by clients (if they are careful). If dat is unspecified, self.dat is used, and shaped appropriately. Note that the return value will always be a sparse list, and will be sparse or full according to the current internal representation, so the client will need to use functions that are polymorphic on sparse lists.'''
		if dat==None:
			if self.data[0]=='full':
				dat=deepcopy(self.data)
			else:
				dat=self.data
		if dat[0]=='full':
			return ['full', reshape(dat[1], self.shape)]
		ind=dat[0]
		op=zeros((ind.shape[0], len(self.shape)), ind.dtype)
		for c in range(len(self.shape)):
			co, ind = divmod(ind, self.strides[c])
			op[:,c]=co.astype(op.dtype)
		return [op, dat[1]]
		
	def _new(self, dat, size=None):
		if any(isnan(dat[1])):
			raise StandardError("NaN")
		if size and self.size!=size:
			raise StandardError('Multi-d sparse arrays may not be dynamically resized')
		return Sparse(dat, self.shape, False, True)
	
	def __getitem__(self, t):
		if type(t[0])==ndarray:
			return self.get(column_stack(t))
		else:
			return self.getpt(t)
		
	def __setitem__(self, t, v):
		if type(t[0])==ndarray:
			if type(v) in [float, int]:
				v = ones_like(t[0])*v
			self.set([column_stack(t),v])
		else:
			self.setpt(t,v)
		
	def getpt(self, t):
		'''Return the value at indexes t (t is a tuple) '''
		i = (array(t)*self.strides).sum()
		return Sparse1D.getpt(self, i)
		
	def setpt(self, t, v):
		'''Set the value at indexes t (tuple) to v (float)'''
		i = int((array(t)*self.strides).sum())
		return Sparse1D.setpt(self, i, v)
		
	def get(self, ind):
		'''return a 1D array of values at the indexes given in the 2D array ind.'''
		ind = self.to1d([ind, None])[0]
		return Sparse1D.get(self, ind)
	
	def set(self, dat):
		'''sets values in self.data according to the list dat, which should be either a 1D full array, or [indexes, values]. The indexes must be sorted. No size checking is done by this method. Use self.condition if you need it. Note that setting with a full array will entirely overwrite existing data, and may change self.size.'''
		dat = self.to1d(dat)
		return Sparse1D.set(self, dat)			
	
	def full(self, copy=False):
		'''return a nD array that is the full version of self.data'''
		d = Sparse1D.full(self, copy)
		return reshape(d, self.shape)	

	def sparse(self, copy=False):
		'''return a tuple that is the sparse version of self.data'''
		d = Sparse1D.sparse(self, copy)
		return self.toNd(d)