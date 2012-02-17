#!/usr/bin/env python

## Copyright (C) 2005-2006 Graham I Cummins
## This program is free software; you can redistribute it and/or modify it under 
## the terms of the GNU General Public License as published by the Free Software 
## Foundation; either version 2 of the License, or (at your option) any later version.
## 
## This program is distributed in the hope that it will be useful, but WITHOUT ANY 
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
## PARTICULAR PURPOSE. See the GNU General Public License for more details.
## 
## You should have received a copy of the GNU General Public License along with 
## this program; if not, write to the Free Software Foundation, Inc., 59 Temple 
## Place, Suite 330, Boston, MA 02111-1307 USA
## 

__all__=[]

try:
	import gicmext.gicconvolve as gc
except:
	import mb_binary.loader
	gc=mb_binary.loader.load('gicconvolve')
	
from numpy import union1d, intersect1d, transpose
#print gc.__file__

from numpy import union1d, zeros_like, nonzero, array
		
def match(dat, tem):
	dat=dat.astype('=f4')	
	tem=tem.astype('=f4')
	rec=dat.copy()
	gc.match(dat, tem, rec)
	return rec

def mahal(dat, tem, var):
	dat=dat.astype('=f4')	
	tem=tem.astype('=f4')
	var=var.astype('=f4')
	rec=dat.copy()
	if tem.shape!=var.shape:
		raise TypeError("var and tem must have same shape")
	gc.mhnd(dat, tem, var, rec)
	return rec

def invar(dat, tem, var, adjamp=False):
	dat=dat.astype('=f4')	
	tem=tem.astype('=f4')
	var=var.astype('=f4')
	rec=dat.copy()
	gc.invar(dat, tem, var, rec, adjamp)
	return rec

def pcafilt(dat, comp):
	dat=dat.astype('=f4')	
	comp=comp.astype('=f4')
	rec=dat.copy()
	gc.pcafilt(dat, comp, rec)
	return rec
			
def lif(dat, refract, leak, thresh):
	dat=dat.astype('=f4')		
	return gc.lif(dat, refract, leak, thresh)

def pcaproj(dat, comp):
	dat=dat.astype('=f4')	
	comp=comp.astype('=f4')
	rec=dat.copy()
	gc.pcaproj(dat, comp, rec)
	return rec

def apply2dkern(dat, kern):
	dat=dat.astype('=f4')	
	kern=kern.astype('=f4')
	match=dat.copy()
	gc.apply2dkern(dat,kern, match)
	return match
	

def victorDistance(d1, d2, cost):
	'''d1 (int or float array), d2 (int or float array), cost (float)
	The cost is for moving a spike by 1.0 units'''
	if cost==0:
	   d=abs(d1.shape[0]-d2.shape[0])
	elif cost>=2:
		d=union1d(d1, d2).shape[0]
	elif not (d1.shape[0] and d2.shape[0]):
		d=max(d1.shape[0], d2.shape[0])
	else:
		d1=d1.astype('=f4')
		d2=d2.astype('=f4')
		
		#tested (correct) python implementation
		#Direct copy of Victor's matlab version. Memory use is stupid
		
# 		from numpy import zeros, arange
# 		big=zeros((d1.shape[0]+1, d2.shape[0]+1), d1.dtype)
# 		big[:,0]=arange(d1.shape[0]+1)
# 		big[0,:]=arange(d2.shape[0]+1)
# 		for i in range(1, d1.shape[0]+1):
# 			for j in range(1, d2.shape[0]+1):
# 				big[i,j]=min([big[i-1,j]+1, big[i,j-1]+1, big[i-1,j-1]+cost*abs(d1[i-1]-d2[j-1])])
# 		return big[-1,-1]

		#tested better python implementation 
		#Memory use is less stupid. Template for C version
		
# 		from numpy import zeros, arange, float32		
# 		lasti=arange(d2.shape[0]+1).astype(float32)
# 		dist=0
# 		for i in range(1, d1.shape[0]+1):
# 			if i>1:
# 				lasti[-1]=last
# 			last=i
# 			for j in range(1, d2.shape[0]+1):
# 				dist=min([lasti[j]+1, last+1, lasti[j-1]+cost*abs(d1[i-1]-d2[j-1])])
# 				lasti[j-1]=last;
# 				last=dist;

		return gc.spikeDistance(d1, d2, cost)


def transformSpikes(e1, e2, cost):
	'''return (cost, move) '''
	if cost==0:
		if e2.shape[0]==e1.shape[0]:
			return [0.0, transpose(vstack([e1,e2]))]
		elif e2.shape[0]> e1.shape[0]:
			return [e2.shape[0]-e1.shape[0],transpose(vstack([e1,e2[:e1.shape[0]]]))]
		else:
			return [e1.shape[0]-e2.shape[0],transpose(vstack([e1[:e2.shape[0]],e2]))]
	elif cost>=2: 
		cm=intersect1d(e1, e2)
		cm=transpose(vstack([cm, cm]))
		return [e1.shape[0]+e2.shape[0]-2*cm.shape[0], cm]
	elif not e1.shape[0]:
		return [e2.shape[0], zeros((0,2))]
	elif not e2.shape[0]:
		return [e1.shape[0], zeros((0,2))]
	t=gc.evttransform(e1,e2,cost)
	d, t= t[0], t[1:]
	t.reverse()
	return [d, array(t)]
	
def getindex(a, v, sort=False):
	'''return an array of shape v that contains the indexes into a at which the elements of v occur. -1 is returned where elements of v are not in a. If a and v are unique and sorted, set the  sort flag to True to get much faster performance.'''
	if sort:
		return gc.getindex_set(a, v)
	else:
		return gc.getindex_full(a, v)
		
	

