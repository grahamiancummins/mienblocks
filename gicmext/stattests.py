#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2007-12-18.

# Copyright (C) 2007 Graham I Cummins
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
from scipy.special import gamma

def _windows(dat, evts, lead, length):
	window=arange(length)-lead
	window=resize(window, (evts.shape[0], window.shape[0]))
	window=window+reshape(evts, (-1, 1))
	dat=take(dat, ravel(window.astype(int32)), 0)
	dat=transpose(reshape(ravel(transpose(dat)), (-1, length)))
	return dat	

def _winTrig(dat, length, nsp):
	if nsp<1 or nsp>=dat.shape[0]-length:
		evts=arange(0, dat.shape[0]-length+1)
	else:
		evts=random.randint(0, dat.shape[0]-length+1, nsp)	
	dat=_windows(dat, evts, 0, length)
	return dat


def estgr(v1, v2):
	v1, v2 = (max(v1, v2), min(v1,v2))
	vs2=(v1+v2)/2
	num=multiply.reduce(arange(v1/2, vs2))
	return num/gamma(v2)

def fcdf(x, v1, v2, dt=.001, cache=None):
	v1=float(v1)
	v2=float(v2)
	vs2=(v1+v2)/2
	if cache in [None, 'get']:
		if max(v1, v2)>200:
			gr=estgr(v1,v2)
		else:
			gr=gamma(vs2)/(gamma(v1/2)*gamma(v2/2))	
		const=(v1/v2)**(v1/2)
		const=const*gr
		if cache=='get':
			return const
	else:
		const=cache		
	t=arange(0,x,dt)
	ig=t**((v1-2)/2)
	ig=ig/( (1+(v1/v2)*t)**vs2 )
	ig=add.reduce(ig)*dt
	#print const, ig
	return const*ig
		
def summary(x, n, sp=0):
	ens=_winTrig(x, n, sp)
	sp=ens.shape[1]
	c=cov(ens)
	m=mean(ens, 1)
	return (m, c, sp)
	
def qform(vec, mat, inv=False):
	vec=matrix(vec.flat)
	mat=matrix(mat)
	if inv:
		mat=mat.I
	q=vec*mat*vec.T
	return ravel(q)[0]

def mahal(x, mod):
	x=ravel(x)-ravel(mod[0])
	return qform(x, mod[1], True)

		
def sigdev(x, mod):
	md=mahal(x,mod)
	n=mod[2]
	p=mod[1].shape[0]
	mv=md*-2*((p*(p-n))/(n*(p-1)))
	pval=1-fcdf(mv,p,n-p)
	return pval
	
def windowDev(x, index, length):
	return sigdev(x[index:index+length], summary(x, length))		
	
	
def deviationVector(data, mod):
	pv=ones_like(data)
	length=mod[1].shape[0]
	N=mod[2]-length
	gc=fcdf(0, length, N, cache='get')
	#print gc
	for i in range(0, pv.shape[0]-length):
		x=data[i:i+length]
		md=mahal(x, mod)
		mv=md*-2*((length*(length-mod[2]))/(mod[2]*(length-1)))
		pv[i]=1-fcdf(mv, length, N, cache=gc)
		#pv[i]=mv
	return pv	

def deviationVectorS(data, mod):
	m=mod[0].mean()
	v=diag(mod[1]).mean()
	pv=ones_like(data)
	length=mod[1].shape[0]
	N=mod[2]-length
	gc=fcdf(0, length, N, cache='get')
	for i in range(0, pv.shape[0]-length):
		md=(data[i]-m)**2/v
		mv=md*-2*((length*(length-mod[2]))/(mod[2]*(length-1)))
		pv[i]=1-fcdf(mv, length, N, cache=gc)
		#pv[i]=md
	return pv		
		