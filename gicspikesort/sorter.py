#!/usr/bin/env python
# encoding: utf-8
#Created by Graham Cummins on 2007-09-19.

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

from spikes import _blockShift
from mien.dsp.signal import *
import mien.dsp.subdata as subdata
from conditioning import *
from spikes import combine

def sortByOrder(x, y):
	if x.name()=='spikesorter_setup':
		return -1
	elif y.name()=='spikesorter_setup':
		return 1
	elif x.name()=='spikesorter_shiftstate':
		return -1
	elif y.name()=='spikesorter_shiftstate':
		return 1
	xv=x.attrib("Order")
	yv=y.attrib("Order")
	if xv==yv:
		print x, y, xv, yv
		raise StandardError('Order is not specified')
	elif xv==None:
		xv=0
	elif yv==None:
		yv=0
	return cmp(xv, yv)	

def schmitTrigger(dat, thresh1, thresh2):
	'''Apply a shmidt dual thresholding scheme to dat (1 Channel). Use negative-going threshold crossings. Return an array of event times (as indexes)
'''
	ht=max(thresh1, thresh2)
	lt=min(thresh1, thresh2)
	evts=[]
	hit=nonzero1d(dat<lt)
	if len(hit)==0 or len(hit)==len(dat):
		return zeros(0)
	fcross1=take(hit, nonzero1d((hit-shift(hit, 1))!=1))
	fcross2=take(hit, nonzero1d((hit-shift(hit, -1))!=-1))
	fcross = zeros((fcross1.shape))
	for m in range(len(fcross1)):
		fcross[m] = fcross1[m] + argmin(dat[fcross1[m]:fcross2[m]+1])
	#fcross=take(hit, nonzero1d((hit-shift(hit, 1))!=1))
	if fcross[0]>0:#only take the first hit when it has a lesser value in front of it
		evts.append(fcross[0])
	for j in range(1, fcross.shape[0]):
		if any(dat[fcross[j-1]:fcross[j]]>ht):
			evts.append(fcross[j])
	return array(evts)
	
def writeSpikeData(data, evts, dpath, append=False, lab="spikes"):
	if not (append and data.getSubData(dpath)):
		data.createSubData(dpath, evts, {'Name':lab, 'SampleType':'events', 'SamplesPerSecond':data.fs(), 'StartTime':data.start(), 'Labels':[lab]},  delete=True)
	else:
		ed=data.getSubData(dpath)
		if isSampledType(ed)!='e' or ed.fs()!=data.fs():
			print ed.header(), isSampledType(ed), ed.fs()!=data.fs()
			raise StandardError('Attempt to assign events to a data element that exists, but does not support storing these events')	
		head=ed.header()
		old=ed.getData()
		if ed.stype()=='events':
			head['SampleType']='labeledevents'
			old=concatenate([old, zeros(old.shape, old.dtype)], 1)
		id=old[:,1].max()+1
		evts = reshape(evts, (-1, 1))
		evts=concatenate([evts, ones(evts.shape, evts.dtype)*id], 1)
		if not evts.dtype==old.dtype:
			evts=evts.astype(old.dtype)
		evts = concatenate([old, evts])
		lab=ed.getLabels()+[lab]
		head["Labels"]=lab
		ed.datinit(evts, head)


def writeShifts(ds, temp, dpath="/spikesorter_shiftstate"):
	if len(temp.shape)!=2:
		temp=reshape(temp, (-1,1))
	st=ds.getSubData(dpath)
	if st:
		st.datinit(temp, st.header())
	else:
		h={'SampleType':'generic','ValuesAreTimes':False}
		n=ds.createSubData(dpath, temp, h, delete=True)
		st=ds.getSubData(dpath)
	return st

def alignMinima(ds, selectSearch=(None, None, None)):
	dat=getSelection(ds, selectSearch)
 	temp=zeros(dat.shape[1], Int32)
	for i in range(dat.shape[1]):
		temp[i]=argmin(dat[:,i])
	temp=-1*(temp-temp[0])
	return temp

def blockShift(ds, temp, rel=False):
	st=ds.getSubData("/spikesorter_shiftstate")
	shifts=st.getData()[:,0]
	if not shifts.shape==temp.shape:
		shifts = reshape(shifts,temp.shape)
	if rel:
		shifts=shifts+temp
	else:
		shifts, temp=temp, temp-shifts
	if any(temp):
		_blockShift(ds, temp)
		writeShifts(ds, shifts)

def ngtc(dat, thresh):
	hit=nonzero1d(dat<thresh)
	if len(hit)<2:
		return hit	
	hit=take(hit, nonzero1d((hit-shift(hit, 1))!=1))
	return hit

def report(s):
	print s

def templatePCA(ds, tname):
	import numpy.linalg as lam
	waves = ds.getSubData(tname+'/waves')
	dat=flattenEnsembleChannels(waves)
	pc0=mean(dat, 1)
	cv=cov(dat)
	val, vec=lam.eig(cv)
	val=val/val.sum()
	howmany=nonzero1d(cumsum(val)>=.9)[0]
	eigs=zeros((vec.shape[0],howmany), dat.dtype)
	labs=[0]*howmany
	order=argsort(val)
	order=reverseArray(order)
	for i in range(howmany):
		nth=order[i]
		eigs[:,i]=vec[:,nth]
		labs[i]=val[i]
	labs=['mean']+labs
	eigs=concatenate([pc0[:,NewAxis], eigs], 1)
	ds.createSubData(tname+'/cov', cv, {'SampleType':'image'} , True)
	head={'SampleType':'timeseries', 'SamplesPerSecond':waves.fs(), 'Labels':labs} 
	ds.createSubData(tname+'/pcs', eigs, head, True)
	return ds

def precondition(ds, ct, report=report):
	if ct.attrib('zeroMean'):
		zeromean(ds)
		report('removed means')
	if ct.attrib('zeroStart'):
		ds.setAttrib('StartTime', 0.0)
		report('set 0 start time')
	if ct.attrib('normalize'):
		nv=ds.data.std()
		normalize(ds, mode='std', normVal=nv)
		report('noise normalized')
	if ct.attrib('stimulus'):
		schan=ct.attrib('stimulus')
		subdata.extract(ds, (None, schan , None), "/hidden/stimulus", delete=True)
		report("Channels %s copied to stimulus" % (str(schan),))
	if ct.attrib('deleted'):
		kill=[ct.attrib('deleted')]
		delChans(ds, kill[0])
		report("Deleted channels %s" % (str(kill),))	

def subtractTemplate(dat, evts, tm, invert=False):
	if invert:
		mode='add'
	else:
		mode='subtract'
	ins=tm.getData()
	mc=range(0, ins.shape[1], 2)
	ins=ins[:,mc]
	offset=tm.attrib('Lead')
	#print(offset)
	l=ins.shape[0]
	dat=dat.getData()
	maxlen = dat.shape[0]
	for ei in range(evts.shape[0]):
		if evts[ei]<offset:#quickie way to deal with spikes near the begining
 			si=0
			clippedins=ins[offset-evts[ei]:,:]
			lloc=clippedins.shape[0]
			if invert:
				dat[si:si+lloc, :]+=clippedins
			else:
				dat[si:si+lloc, :]-=clippedins
		else:
			si=evts[ei]-offset
			if invert:
				dat[si:si+l, :]+=ins[:l-((si+l)-maxlen)]
			else:
				dat[si:si+l, :]-=ins[:l-((si+l)-maxlen)]
	
def parseParams(pars):
	try:
		if type(pars) in [str, unicode]:
			pars=eval(pars)
		if type(pars) in [tuple, list]:
			pars=map(float, pars)
		elif type(pars) in [float, int]:
			pars=[pars]
		elif type(pars)==type(None):
			pars=[]
		else:
			raise
	except:
		print "Parameters aren't parsable"
		pars=[]
	return pars
