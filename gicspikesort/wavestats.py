#!/usr/bin/env python
# encoding: utf-8
#Created by Graham Cummins on 2007-09-10.

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
from sorter import parseParams


def residPow(waves, gui=None):
	td=waves.mean(2)
	res=waves-td[:,:,newaxis]
	return sqrt((res**2).sum(0).sum(0))

def ampStd(waves, gui=None):
	return waves.min(0).std(0)

def tempDot(waves, gui=None):
	td=waves.mean(2)
	res=zeros(waves.shape[2], float32)
	for i in range(res.shape[0]):
		pr=0
		for j in range(waves.shape[1]):
			pr+=dot(waves[:,j,i], td[:,j])
		res[i]=pr
	return res

def totPow(waves, gui=None):	
	return sqrt((waves**2).sum(0).sum(0))

def reshiftD(waves, gui=None):
	td=waves.mean(2)
	res=zeros(waves.shape[2], float32)
	for i in range(res.shape[0]):
		pr=0
		for j in range(waves.shape[1]):
			pr+=abs(argmin(waves[:,j,i])-argmin(td[:,j]))
		res[i]=pr
	return res
		
def powR(waves, gui=None):
	td=tempDot(waves)
	tp=totPow(waves)
	return td/tp
	
def meanMin(waves, gui=None):
	res=zeros(waves.shape[2], float32)
	for i in range(res.shape[0]):
		res[i]=min(waves[:,:,i].mean(1))
	return res
	
def mahaldist(waves, gui=None):
	td=waves.mean(2)
	sd=waves.std(2)
	res=zeros(waves.shape[2], float32)
	for i in range(res.shape[0]):
		pr=0
		d=waves[:,:,i]-td
		d=d/sd
		res[i]=sqrt(ravel(d**2).sum())
	return res
	

from sorter import parseParams

def dfStat(dfn, df, waves, gui):	
	if dfn==gui.inMode:
		pars=parseParams(gui.discPars.GetValue())
	elif dfn==gui.errMode:
		pars=parseParams(gui.errPars.GetValue())
	else:
		pars=()
	temp=gui.getTemp(None)
	ll=gui.getLL()
	temp._cache={'ll':ll}
	
	# prettier, but doesn't work
	# s=waves.shape
	# ccw=reshape(transpose(waves, [2,0,1]), (s[0]*s[2],s[1]))
	# dfr=df(ccw, pars, temp)
	# dfr=reshape(dfr, (-1, s[2]))
	# res=dfr.min(0)
	
	try:
		evts=gui.getTemp('spikes')[1].getData()[:,0]
	except:
		print "Can't find spike template"
		return 
	if evts.shape[0]!=waves.shape[2]:
		print "Events don't correspond to saved waveforms"
		return
	print "calculating %s" % dfn
	dfr=df(gui.dv.data.getData(), pars, temp)
	res=zeros(waves.shape[2], float32)
	evts=evts-ll[0]
	for i in range(res.shape[0]):
		res[i]=dfr[evts[i]:evts[i]+ll[1]].min()
	
	del(temp._cache)
	return res

FUNCTIONS={'residual power':residPow, "Stddev of Minima":ampStd, "Template Projection":tempDot, "Total Power":totPow, 'Misalignment at minima':reshiftD, "Ratio of projection to Power":powR, "Min of Mean":meanMin, "Mahalanobis Distance from Template":mahaldist}

import discriminants
reload(discriminants)

def makeCallback(dfn, df):
	def func(waves, gui):
		return dfStat(dfn, df, waves, gui)
	return func

for dfn in discriminants.DISC_FUNCTIONS.keys():
	df=discriminants.DISC_FUNCTIONS[dfn]
	mdf = makeCallback(dfn, df)
	FUNCTIONS["DM: %s" % dfn]=mdf
	
for dfn in discriminants.ERROR_FUNCTIONS.keys():
	df=discriminants.ERROR_FUNCTIONS[dfn]
	mdf = makeCallback(dfn, df)
	FUNCTIONS["ERR: %s" % dfn]=mdf

