#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2007-12-19.

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

from stattests import *
from mien.datafiles.dataset import *

def gaussianModel(ds, select=(None, [0], None), newpath='/gmod', nsamps=1000, modlength=2):
	dat=getSelection(ds, select)
	h=getSelectionHeader(ds, select)
	m, c, sp = summary(dat,  modlength, nsamps)
	dat=column_stack([m,c])
	h['NumberOfSamples']=sp
	ds.createSubData(newpath, data=dat, head=h, delete=True)
	
def deviation(ds, dpathModel='/gmod', select=('/stats', [0], None), newpath="/pval"):
	mod=ds.getSubData(dpathModel)
	sp=mod.attrib('NumberOfSamples')	
	h=getSelectionHeader(ds, select)
	md=mod.getData()
	m=md[:,0]
	cov=md[:,1:]
	dev=deviationVector(getSelection(ds, select), (ravel(m), cov, sp))
	ds.createSubData(newpath, data=dev, head=h, delete=True)
	
def getLocalPeaks(ds, select=(None, [0], None), newpath='/peaks'):
	dat=getSelection(ds, select)
	h=getSelectionHeader(ds, select)
	h['SampleType']='events'
	gl=dat>shift(dat, 1)
	gr=dat>shift(dat, -1)
	lm=logical_and(gl, gr)
	lm=nonzero(lm)[0]
	ds.createSubData(newpath, lm, h, True)
	
	
def peakOffsetHistogram(ds, dpath1="/peaks", dpath2='/peaks', length=.020, newpath='/peakoffset'):
	pd1=ds.getSubData(dpath1)
	length=ds.fs()*length
	hist=zeros(length)
	pd1=ravel(pd1.getData()).astype(int32)
	pd2=ds.getSubData(dpath2)
	pd2=ravel(pd2.getData()).astype(int32)
	ind=pd2.searchsorted(pd1)
	for i, n in enumerate(pd1):
		j=ind[i]
		d=pd2[j]-n
		while d<length:
			hist[d]+=1
			j+=1
			try:
				d=pd2[j]-n
			except IndexError:
				break	
	ds.createSubData(newpath, hist, {'SampleType':"histogram"}, True)
			
				
		
	
		