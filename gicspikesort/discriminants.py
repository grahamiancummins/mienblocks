#!/usr/bin/env python
# encoding: utf-8
#Created by Graham Cummins on 2007-05-17.

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

from errors import *
from mien.math.array import shift
from numpy import mean as npmean
from numpy import argmin as npargmin

def mean_per_std(dat, pars=(), template=None):
	sd=dat.std(1)
	sdm=sd.mean()
	if sd.min()<(sdm*.03):
		sd+=sdm*.03		
	disc=dat.mean(1)/sd
	return disc

def mean_per_opt(dat, pars=(), template=None):	
	disc=dat.mean(1)
	e=optmin(dat, pars, template)
	mv=disc.min()
	e+=10*mv*(e==0)
	disc=-1*disc/e
	#print "mpo: %.5f" % mv
	#disc=mv*disc/e
	disc=minimum(disc, 0)
	return disc

def mean_mean_per_opt(dat, pars=(), template=None):	
	disc=dat.mean(1)
	e=optmin(dat, pars, template)
	mv=disc.min()
	e+=10*mv*(e==0)
	disc=disc*disc/e
	#disc=mv*disc/e
	disc=minimum(disc, 0)
	return disc

def thresh_mean_per_opt(dat, pars=(), template=None, mvinput=None):	
	disc=dat.mean(1)
	if len(pars)==0:
		thresh=.1
	else:
		thresh, pars=pars[0], pars[1:]		
	e=optmin(dat, pars, template)
	if mvinput:#to make the minimum consistant across different files
		mv=mvinput
	else:
		mv=disc.min()
	print(mv)
	tv=thresh*mv
	disc=where(disc>tv, 0, disc)
	e+=10*mv*(e==0)
	disc=-1*disc/e
	#disc=mv*disc/e
	disc=minimum(disc, 0)
	return disc
	
def	spike_match(dat, pars=(), template=None):
	try:
		spi=template.getElements("Data", "idealspike", depth=1)[0]
	except:
		print "Spike matching mode requires seting an 'ideal' spike first. Using Mean instead"
		return None	
	evt=spi.getData()
	disc=zeros(dat.shape[0], dat.dtype)
	for i in range(dat.shape[1]):
		dc=dat[:,i]
		tem=evt[:,i]
		err=match(dc, tem)		
		md=sum(tem**2)
		err=minimum(err, md)
		disc+=err
	disc=shift(disc, round(-.5*tem.shape[0]))
	return disc

def tem_match(dat, pars=(), template=None):
	try:
		tem=template.getElements("Data", "template", depth=1)[0]
	except:
		print "Matching requires a template. Defaulting to Mean"	
		return None				
	td=tem.getData()
	disc=zeros(dat.shape[0], dat.dtype)
	for i in range(dat.shape[1]):
		dc=dat[:,i]
		tem=td[:,2*i]
		err=match(dc, tem)		
		md=sum(tem**2)
		err=minimum(err, md)
		disc+=err
	lead, length = getLL(pars, template)
	mid = length - lead
	tempoff = npmean(npargmin(td[mid-15:mid+15,range(0,dat.shape[1],2)]*2, axis=0))#since the template tends to be offest a touch
	xtralen = length - (mid -(15-round(tempoff)))
	disc = concatenate([disc[xtralen:], max(disc)*ones(xtralen)])
	return disc
			
def mahal_match(dat, pars=(), template=None):
	try:
		tem=template.getElements("Data", "template", depth=1)[0]
	except:
		print "Matching requires a template. Defaulting to Mean"	
		return None				
	td=tem.getData()
	disc=zeros(dat.shape[0], dat.dtype)
	for i in range(dat.shape[1]):
		dc=dat[:,i]
		tem=td[:,2*i]
		var=td[:,2*i+1]
		var=var**2
		err=mahal(dc, tem, var)		
		md=sum(tem**2/var)
		err=minimum(err, md)
		disc+=err
	return disc	
	
	
def single_channel(dat, pars=(), template=None):
	if len(pars)==0:
		c=0
	else:
		c=pars[0]
	disc=dat[:,c]
	return disc
			
			
def dot(dat, pars=(), template=None):
	lead, length= getLL(pars, template)
	disc=zeros(dat.shape[0], dat.dtype)
	for i in range(lead, disc.shape[0]-length+lead):
		dseg=dat[i-lead:i-lead+length, :]
		p=multiply.reduce(dseg, 1)
		disc[i]=-1*abs(p.sum())
	return disc
	
def prod(dat, pars=(), template=None):
	if dat.shape[1]%2:
		sgn=1
	else:
		sgn=-1
	disc=sgn*multiply.reduce(dat, 1)
	return disc
	

DISC_FUNCTIONS={"Mean/Std":mean_per_std,"Mean/OptMin":mean_per_opt, "Mean^2/OptMin":mean_mean_per_opt, 'Spike Match':spike_match, "Template Match":tem_match, "Mahalanobis Match":mahal_match, "Mean/OptMin+threshold":thresh_mean_per_opt, "Dot Power":dot, "Dot Product":prod, "Single Channel":single_channel}
			
