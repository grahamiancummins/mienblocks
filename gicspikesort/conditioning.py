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

from mien.datafiles.dataset import *

def _takewindows(dat, evts, lead, length):
	#print dat.shape, evts.shape, lead, length
	window=arange(length)-lead
	window=resize(window, (evts.shape[0], window.shape[0]))
	window=window+reshape(evts, (-1, 1))
	dat=take(dat, ravel(window.astype(Int32)), 0)
	dat=transpose(reshape(ravel(transpose(dat)), (-1, length)))
	return dat	

def _takeevents(dat, evts, length):
	if len(evts.shape)>1:
		evts = evts[:,0]
	nreps = len(evts)
	if dat.shape[1]==1:
		 dat=column_stack([dat, zeros_like(dat)])
	#print evts.shape, dat.shape
	ei = searchsorted(evts, dat[:,0], 'right')
	nevts=[]
	for i in range(dat.shape[0]):
		if ei[i]==0:
			continue
		index=ei[i]-1
		evt = evts[index]
		while 1:
			if evt+length>dat[i,0]:
				nevts.append((dat[i,0]-evt, dat[i,1]*(nreps+1)+index))
				break
			index+=1
			if index>=evts.shape[0]-1:
				break
			evt = evts[index]
			if evt>=dat[i,0]:
				break
	return array(nevts)	
		
def _putwindows(dat, ins, evts, offset=0, mode="subtract", cumulative=True):
	'''target, insert, indexes, offset
SWITCHVALUES(mode)=['subtract', 'add', 'cumreplace', 'replace', 'smoothreplace']'''		
	id=zeros_like(dat)
	if cumulative:
		l=ins.shape[0]
		for ei in range(evts.shape[0]):
			si=evts[ei]-offset
			id[si:si+l, :]+=ins
	else:
		window=arange(ins.shape[0])-offset
		window=resize(window, (evts.shape[0], window.shape[0]))
		window=window+reshape(evts, (-1, 1))
		window=ravel(window.astype(Int32))
		ins=resize(ins, (ins.shape[0]*evts.shape[0], ins.shape[1]))
		for ci in range(dat.shape[1]):
			chan=zeros(dat.shape[0], dat.dtype)
			put(chan, window, ins[:,ci])
			id[:,ci]=chan
	if mode=='subtract':
		dat=dat-id
	elif mode=='add':
		dat+=id
	elif mode=='replace':
		s=dat.shape
		dat=ravel(dat)
		id=ravel(id)
		put(dat, nonzero1d(id), id)
		dat=reshape(dat, s)
	else:
		print "edge-warping modes not implemented yet"
		return
	return dat	


def _swin(a, ran):
	'''Return a 2D array containing sequential sliding windows of into a, obtained by applying every passible shift described by the range ran. Return shape will be (ran.sum()+1, a.shape[0]-ran.sum()-1)'''
	out=zeros((ran[0]+ran[1]+1, a.shape[0]-ran[0]-ran[1]-1), a.dtype)
	for i in range(-ran[0], ran[1]+1):
		si= ran[1]-i
		out[i+ran[0],:]=a[si:si+out.shape[1]]
	return out

def _shift(dat, indexes, ran=None):
	'''shift each column in dat by the integer in indexes. If not ran, return an array of the same shape as "indexes" with appropriate edge filling. Otherwise, select a central region that will be fully specified by shifts in range ran (This will have shape dat.shape[0]-ran.sum()-1)'''
	if not ran:
		dat=dat.copy()
		for i in range(indexes.shape[0]):
			dat[:,i]=shift(dat[:,i], indexes[i])
		return dat
	l=dat.shape[0]-ran[0]-ran[1]-1
	a=ran[1]
	ret=zeros((l, dat.shape[1]), dat.dtype)
	for i in range(ret.shape[1]):
		si=a-indexes[i]
		ret[:,i]=dat[si:si+l,i]
	return ret


def _loggausact(mea, var, inp):
	'''equivalent of matlab loggmmactive for "diag" covar type with 1 gaussian in mea.shape[0] dimensions. var and mea are 1D arrays of the same shape (N), specifying the means and varriances of the gaussian. inp is an SxN array of inputs. The return value is a 1D length S array of activation values.'''
	lnorm = log(2*pi)*(mea.shape[0]/2.0)
	ls = log(sqrt(var)).sum()
	diffs = inp - mea
	a = (-0.5* (diffs**2 / var)).sum(1) -(lnorm+ls)
	return a
  

def _realign(dat, mea, vars, ran, pv, mm='gmmact'):
	'''return a set of shift indexes (1D array of ints, length=dat.shape[1]) that optimally aligns the columns of dat.
If "mm" is "gmmact", alignment is to an independent gaussian model with the indicated mean and variance. If mm is 'dot', alignment is by dot product with the mean

 Alignment must conform to the hard limits in the tuple ran and a penalty vector pv (pv specifies the penalty for using each shift in the range (-ran[0], ran[1]). It is used as an additive penalty, so setting it to zeros provides no soft limits).
	mean and vars must have length dat[ran[1]:-ran[0],:].shape[0]. The use of ran is described by _align_indexes, which is an iterating wrapper around this function. This function performs a single alignment.'''
	matches=zeros((ran[0]+ran[1]+1, dat.shape[1]), dat.dtype)
	n=mea.shape[0]
	for s in range(matches.shape[1]):
		inp=_swin(dat[:,s], ran)
		if mm=='gmmact':
			matches[:,s]=_loggausact(mea, vars, inp)
		elif mm=='dot':
			matches[:,s]=dot(mea, transpose(inp))
		else:
			raise StandardError('unknown match function')
	matches+=pv	
	sndx=argmax(matches, 0)-ran[0]
	if all(sndx==sndx[0]):
		sndx-=sndx[0]
	return sndx
	

def _align_indexes(dat, ran, es, match):
	'''If dat is an s by n array, calculate and return an n element vector of integers such that shifting each column in dat by the corresponding number of samples will align the waveforms as well as possible. 

	ran is a 2-tuple (b, f) of positive integers specifying the allowed range of shift indexes. b specifies the limit of negative shifts (shifts to earlier times), and f the limit of positive shifts, so max(shifts)<=f and max(-1*shifts)<=b.

	Overlap is only calculated between regions that are certain to be fully specified even after maximum shifts. This means that the alignment window is dat[f:-b,:]. It is an error to specify inputs such that ran[0]+ran[1]>=dat.shape[0].
	
	Es is a parameter used to penalize large shift indexes. It can be interpreted as the expectation standard deviation of shifts. Shifts improbable under this expectation are penalized. This is a number of samples (int), The std dev of the distribution of shifts, for unstructured input, will approximately equal this (if ran is large enough). Optimal alignment is certain only if es>>dat.shape[0]. Es=0 is treated as es=Inf.
	'''
	nd=dat[ran[1]:-ran[0]-1,:]
	lp=0
	if es:
		ev=es**2
		pv=arange(-ran[0],ran[1]+1)
		pv=pv**2
		es=2*es**2
		pv=(-pv/es)-log(pi*es)*.5
		pv=pv[:,NewAxis]
	else:
		pv=zeros((ran[0]+ran[1]+1,1))		
	for i in range(200):
		mea=nd.mean(1)
		vars=nd.var(1)
		pow=vars.mean()
		if i>1 and (all(vars<1e-8) or (lp and abs(pow-lp)/lp < 1e-5)):
			print "alignment converged in %i iterations" % i
			break
		elif any(vars<1e-8):
			vars=maximum(vars, 1e-8)
		lp=pow		
		sndx=_realign(dat, mea, vars, ran, pv, match)
		#print sndx
		nd=_shift(dat, sndx, ran)
	else:
		raise StandardError("Alignment did not converge")		
	return sndx	



def dejitter(ds, dpath='/evtcond', maxleftshift=80, maxrightshift=20, shiftsd=15, newpathTemplate='/dejitterTemplate', newpathShifted='/dejitteredEvents', match='gmmact'):
	'''Takes ensemble data and temporally aligns (dejitters) the columns using a gausian model activation distance measure. Max/eftshift and maxright shift specify hard limits for shifts to the left (earlier times) and right in sample points. Shiftsd specifies a regularization constraint that penalizes large shifts. It is applied such that the standard deviation of the resulting shift indexes tends to this value (in sample points). A very large value results in the best absolute alignment. If this is a False value (including 0), it is treated as infinite (no penalty term). 
	newpathTemplate specifies a path to store the shift indexes. newpathShifted specifies a path to store the final dejittered waveforms. If either of these arguments is False, the corresponding component is not stored (in the case of the waveforms, they are also not calculated).
	If dejittered waveforms are calculated, they will be shorter than the original ensemble events, since they will be extracted from the middle of those events as events[maxrightshift:-maxleftshift] such that all the values will be well specified after shifting.

SWITCHVALUES(match)=['gmmact', 'dot']	
	'''
	dat=ds.getSubData(dpath)
	h=dat.header()
	dat=dat.getData()
	ran=( maxleftshift, maxrightshift)
	sndx= _align_indexes(dat, ran, shiftsd, match)
	if newpathTemplate:
		ds.createSubData(newpathTemplate,sndx[:,NewAxis], {'SamplesPerSecond':1.0, "SampleType":'timeseries'}, True)
	if newpathShifted:
		sd=_shift(dat, sndx, ran)
		ds.createSubData(newpathShifted, sd, h, True)
	return ds		

def eventCondition(ds, dpathEvents='/evts', dpathDataToCondition='/', lead=15.0, length=20.0, newpath='/evtcond', milliseconds=True):
	'''Use the events in dpath to condition the data in select. Each
event will trigger a block of data that starts lead ms before the 
event (lead may be negative) and is length ms long. These data
will be compiled into an "ensemble" type data instance stored in 
newpath.

See also mien.datafiles.dataset.alignEvents, which this function calls.
In particular, there is no need to strip "edge" events that do not 
generate a full length window - these are filtered out automatically

SWITCHVALUES(milliseconds)=[True, False]
'''
	if type(dpathDataToCondition) in [tuple, list]:
		dat = getSelection(ds, dpathDataToCondition)
		head = getSelectionHeader(ds, dpathDataToCondition)
		select = dpathDataToCondition
	else:
		dat=ds.getSubData(dpathDataToCondition )
		head=dat.header()
		dat=dat.getData()
		select = (dpathDataToCondition, None, None)
	fs=head['SamplesPerSecond']
	if milliseconds:
		lead=round(lead*fs/1000.)
		length=round(length*fs/1000.)
	else:
		lead=round(lead*fs)
		length=round(length*fs)
	evts=alignEvents(ds, select , dpathEvents, lead, length-lead)
	if not evts.shape[0]:
		print "No Events"
		return
	if "events" in head['SampleType']:
		evts=evts-lead
		dat=_takeevents(dat, evts, length)
		head['SampleType']='labeledevents'
	else:
		head['SampleType']='ensemble'	
		dat=_takewindows(dat, evts, lead, length)
	head["Lead"]=lead
	head["conditionedOn"]=dpathEvents
	head['Reps']=evts.shape[0]
	ds.createSubData(newpath, dat, head, True)
	
def randomEnsemble(ds, 	dpath="/", length = .020, nevents = 5000, newpath='/UE'):
	sd = ds.getSubData(dpath)
	fs = sd.fs()
	dat = sd.getData()
	start = sd.start()
	length = int(round(length*fs))
	evts = randint(length, dat.shape[0], nevents)
	head = {"StartTime":start, "SamplesPerSecond":fs}
	if "events" in sd.attrib('SampleType'):
		evts=evts-length
		dat=_takeevents(dat, evts, length)
		head['SampleType']='labeledevents'
	else:
		head['SampleType']='ensemble'	
		dat=_takewindows(dat, evts, length, length)
	head["Lead"]=length
	head["conditionedOn"]='random events'
	head['Reps']=evts.shape[0]
	ds.createSubData(newpath, dat, head, True) 
	 
	
def repeatedWindows(ds, xcoordPeriod=.05, dpathDataToFold="/", newpath='/windows'):
	"""Create an ensemble of samples, similar to eventCondition. Unlike eventCondition, these waves are not based on an 'event' data set. Instead, the ensemble is created by selecting sequential windows of length xcoordPeriod, covering the entire data data set specified in select. The resulting ensemble data is stored in newpath. Also unlike eventCondition, xcoordPeriod is _not_ in ms (use normal units for the x axis - usually seconds)"""
	dat=ds.getSubData(dpathDataToFold )
	head=dat.header()
	dat=dat.getData()
	#print dat.shape
	fs=head['SamplesPerSecond']
	length=float(xcoordPeriod*fs)
	if "events" in head['SampleType']:
		evts=around(reshape(arange(0, dat[:,0].max()+1, length), (-1,1))).astype(int64)
		dat=_takeevents(dat, evts, int(round(length)))
		head['SampleType']='labeledevents'
	else:
		evts=around(reshape(arange(0, dat.shape[0]-length+1, length), (-1,1))).astype(int64)
		dat=_takewindows(dat, evts, 0, int(round(length)))
		head['SampleType']='ensemble'
	head["Lead"]=0
	head["conditionedOn"]="Fixed length windows"
	head['Reps']=evts.shape[0]
	ds.createSubData(newpath, dat, head, True)
	

	
def ensembleStats(ds, dpath='/evtcond', newpath='/stats', order=2):
	'''Create a new timeseries in newpath that contains the statistics for
each channel of the ensemble in dpath. If order=1, include only the mean.
Higher orders include higher moments (2= std deviation, 3=skewness, etc)'''
	dat=ds.getSubData(dpath)
	data=dat.getData()
	head=dat.header()
	head['SampleType']='timeseries'
	del(head['Reps'])
	head['Labels']=[]
	new=None
	for i in range(dat.shape()[1]):
		de=channel(dat, i)
		name=dat.getChanName(i)
		head['Labels'].append("%s - mean" % name)
		me=reshape(mean(de, 1), (-1, 1))
		if new==None:
			new=me
		else:
			new=concatenate([new, me], 1)	
		if order>1:
			sd=reshape(std(de, 1), (-1, 1))
			head['Labels'].append("%s - std" % name)
			new=concatenate([new, sd], 1)	
		if order>2:
			print "Orders 3 and higher not implemented yet"
	ds.createSubData(newpath, new, head)	
		
def triggeredInsert(ds, dpath='/evts', selectInsert=('/stats', None, None), selectTarget=(None, None, None), offset='auto', mode="subtract", cumulative=True):
	'''Use the events in dpath to insert the waveforms determied by 
selectInsert into the data determined by selectTarget. One copy of selectInsert
will be inserted for each event. selectInsert must specify the same number of
channels as selectTarget. Offset determines the number of samples before the 	
an event to begin each insert (may be negative). The special value "auto" 
will attemp to use the header entry "Lead" (which is set by eventCondition
and similar functions), and defaults to 0 otherwise. Mode determines 
how to apply the inserts. Legal values are:
"subtract" - subtracts the "insert" from the signal
"add" - adds the insert from the signal
"replace" - sets the signal to equal the insert
"smoothreplace" - sets the signal to equal the insert, using an edge smoothing 
	algorithm.	
If cumulative is true, then when several inserts overlap, their effects add 
(otherwise the second insert overrides the first). Using cumulative makes 
computation slower, so if events don't overlap anyway, set this to False
	
SWITCHVALUES(mode)=['subtract', 'add', 'cumreplace', 'replace', 'smoothreplace']
SWITCHVALUES(cumulative)=[True, False]
'''
	ins=getSelection(ds, selectInsert)
	if offset=='auto':
		ii=ds.getSubData(selectInsert[0])
		offset=ii.attrib('Lead')
		if offset==None:
			print "no stored offset found, using 0"
			offset=0			
	evts=alignEvents(ds, selectTarget, dpath, offset, ins.shape[0]-offset)
	dat=getSelection(ds, selectTarget)
	dat=dat.copy()
	dat=_putwindows(dat, ins, evts, offset, mode, cumulative)
	if dat!=None:
		setSelection(ds, dat, selectTarget)




def isolateSpikes(ds, dpath='/evts', newpath='/sparseevts', timeBefore=25.0, timeAfter=0.0, absolute=True):
	'''Drops all events that are too close to other events. 
	Events are taken from dpath, and a new event object is placed in
	newpath (overwriting any previous object with that path. The new
	object contains the same events as the old object, except that
	events with another event less than timeBefore (in ms) before them
	or timeAfter after them are removed.

	If absolute is False, spikes are processed one at a time, so a later
	spike may not be dropped if the earlier spike close to it is dropped
	first.
	
	SWITCHVALUES(cumulative)=[True, False]
	'''				
	evts=ds.getSubData(dpath).clone(False)
	if not evts.stype()=='events':
		print "requires dpath to reference event type data (not labeledevents)"
		return
	ed=sort(evts.getData(),0)
	sb=int(evts.fs()*timeBefore/1000.0)
	sa=int(evts.fs()*timeAfter/1000.0)
	lind=-1
	kill=[]
	for i in range(len(ed)-1):
		eind=ed[i,0]
		nind=ed[i+1,0]
		if eind-lind<sb:
			kill.append(i)
		elif nind-eind<sa:
			kill.append(i)
		else:
			lind=eind
		if absolute:
			lind=eind
	edl=list(ed)
	ln=len(kill)-1	
	for m in range(ln+1):
		slnce=edl.pop(kill[ln-m])
	new=array(edl, ed.dtype)
	print len(kill), new.sum()			
	np=ds.createSubData(newpath, data=new, head=evts.header(), delete=True)
	return ds

			

# import mien.math.sigtools
# reload(mien.math.sigtools)
# from mien.math.sigtools import *
# from mien.datafiles.dataset import fromFile, DataSet, isADataSet
# 
# import mien.math.matlab
# reload(mien.math.matlab)
# from mien.math.matlab import callMatlab
# import os
# 
# def createISIHistogram(ds, cindex=-1, binwidth=.0015, sKey="isi"):
# 	'''Generate a typical isi histogram for the indicated channel 
# 	(must be a raster channel), with bins of the indicated width
# 	in ms and store it in the indeicated key. The histogram always
# 	starts at 0'''
# 	try:
# 		evts=ds.getEvents(cindex, check=True)
# 	except:
# 		print "Can't get discreet events from channel %i" % cindex
# 		return ds
# 	isi=evts-shift(evts, 1)
# 	isi=isi[1:]
# 	r=(0, isi.max())
# 	h=histFromEvents(isi, binwidth, r)
# 	h=DataSet(h)
# 	h.fs=1.0/binwidth
# 	h.start=0
# 	ds.special[sKey]=h
# 	return ds
# 
# def isiStats(ds, cindex=1, length=.02, bins=40, sKey='isidist'):
# 	'''Characterizes the distribution of isis in the indicated channel, out to the 
# 	indicated time'''
# 	rast=ds.getChannel(cindex)
# 	if rast.max()>1:
# 		print "Warning, using an event channel with values greater than one. Results may be odd"
# 	bins=int(round(length*ds.fs))
# 	lis=float(bins)/ds.fs
# 	if lis!=length:
# 		print "actual event length is %.3g" % lis
# 	accum=shift(convolve(rast, ones(bins, rast.dtype.char), 1), int(bins/2))
# 	nosh={}
# 	for i in range(accum.min(), accum.max()+1):
# 		nosh[i]=(accum==i).sum()
# 		p=(accum==i).sum()/float(accum.shape[0])
# 		print "%i spikes preceed %.5f of samples" % (i, p)
# 	ind = nonzero(rast)
# 	ind-=bins
# 	dat=ds.takeWindows(cindex, ind, bins)
# 	nevts=dat.shape[1]
# 	ns={}
# 	q=sum(dat)
# 	for i, n in enumerate(q):
# 		if not ns.has_key(n):
# 			ns[n]=[]
# 		ns[n].append(i)
# 	if ns.has_key(0):
# 		p=float(len(ns[0]))/nevts
# 		tp=float(len(ns[0]))/nosh[0]
# 		print "%i -> %.3f of all spikes, %.3f probability of spike" % (0, p, tp)
# 		psib=tp
# 		del(ns[0])
# 	else:
# 		psib=0.0
# 	nclass=len(ns)	
# 	isidist=zeros((bins+2,len(ns)), Float32)
# 	for i, k in enumerate(ns.keys()):
# 		p=float(len(ns[k]))/nevts
# 		tp=float(len(ns[k]))/nosh[k]
# 		print "%i -> %.3f of all spikes, %.3f probability of spike" % (k, p, tp)
# 		isidist[0,i]=k
# 		isidist[1,i]=p
# 		insts=take(dat, ns[k], 1)
# 		isidist[2:,i]=sum(insts, 1)/insts.shape[1]
# 	isids=DataSet(isidist, {"SamplesPerSecond":ds.fs})
# 	isids.special['psib']=psib
# 	ds.special[sKey]=isids
# 	return ds
# 
# def RandomEvents(ds, howmany=100, cnameEvents="EventTimes"):
# 	'''Add a channel to ds containing howmany randomly located delta
# 	functions'''
# 	t = ds.domain()
# 	f = uniform(t[0], t[-1], howmany)
# 	c=zeros(ds.data.shape[0], ds.data.dtype.char)
# 	ind=ds.setChannel(cnameEvents, c)
# 	ds.setRaster(ind, f)
# 	return ds
# 
# def SpikeDetectSchmidtAbove(ds, channel, thresh1, thresh2, cnameEvents="EventTimes"):
# 	'''add a binary channel to ds containig the events detected
# 	by applying a schmidt trigger searching for events above
# 	the two specified thresholds'''
# 	a=ds.data[:,channel]
# 	evts= detectSchmit(a, [thresh1, thresh2])
# 	evts=take(ds.get_x(), evts)
# 	c=zeros(len(ds), ds.data.dtype.char)
# 	ind=ds.setChannel(cnameEvents, c)
# 	ds.setRaster(ind, evts)
# 	return ds
# 
# def JitterSpikes(ds, sd=.001, cindexInput=1, cindexOutput=1):
# 	'''Produce a raster channel by moving each event in cindexInput
# 	by a random time shift drawn from a normal distribution with standard deviation 
# 	sd'''
# 	evts=ds.getChannel(cindexInput)
# 	evts = nonzero(evts)
# 	evts = take(ds.get_x(), evts)
# 	
# 	evts+=normal(0, sd, evts.shape)
# 	c=zeros(len(ds), ds.data.dtype.char)
# 	ind=ds.setChannel(cindexOutput, c)
# 	ds.setRaster(ind, evts)
# 	return ds
# 
# 	
# def calcSTA(ds, channelsStimulus, cnameEvents="EventTimes", length=30.0, offset=20.0,
# 			sKeyKernel="STA"):
# 	'''calculates the spike triggered average stimulus using the indicated input 
# 	channels and output channel. The average begins offset ms before the spike and is 
# 	length ms in total length. The result is stored in the named special key.'''
# 	nevts=0
# 	stalen=int(length*ds.fs/1000.0)
# 	stalead=int(offset*ds.fs/1000.0)
# 	sta=zeros((stalen, len(channelsStimulus)), Float32)
# 	evts=ds.getEvents(ds.labels.index(cnameEvents), returnTimes=False)
# 	stim=take(ds.data, channelsStimulus, 1)
# 	for ind in evts:
# 		ind=ind-stalead
# 		sind=ind+stalen
# 		if not 0<=ind:
# 			continue
# 		if not stim.shape[0]>sind:
# 			break
# 		sta=sta+stim[ind:sind]
# 		nevts+=1
# 	sta=sta/float(nevts)
# 	ds.special[sKeyKernel]=sta
# 	return ds
# 
# 
# 
# def eventConditionedWavesTosKey(ds, cindex=0, cnameEvents="EventTimes", length=.020, lead=.020, sKey="EvtCond"):
# 	'''Grab waveforms from channel cindex, of length (in seconds) starting lead seconds each 
# 	event in the named event channel. Make a DataSet with each of these waveforms as a channel, 
# 	and store it in the indicated sKey'''
# 	rast=ds.getChannel(cnameEvents)
# 	thresh = (rast.max()-rast.min())/2.0
# 	ind = nonzero(rast>thresh)
# 	ind-=int(round(lead*ds.fs))
# 	length=int(round(length*ds.fs))
# 	dat=ds.takeWindows(cindex, ind, length)
# 	ds2=DataSet(dat)
# 	ds2.fs=ds.fs
# 	ds.special[sKey]=ds2
# 	return ds
# 
# 
# def eventStatsToKey(ds, sKeyWaves="EvtCond", sKeyStats="Kernel"):
# 	'''make a ds in sKeyStats with the first channel containing the mean of the channels
# 	in sKeyWaves, and the second channel the stddev'''
# 	ds2=ds.special[sKeyWaves]
# 	m=mean(ds2.data, 1)
# 	std=stddev1(ds2.data)
# 	ds3=DataSet(concatenate([m[:,NewAxis], std[:,NewAxis]], 1))
# 	ds.special[sKeyStats]=ds3
# 	return ds
# 
# 
# def dejitterStimuliToKey(ds, cindex=0, cnameEvents="EventTimes", length=.020, lead=.020, djlength=.010, djlead=.013, sKeyDejit="EvtCondDJ", sKeyShifts="ShiftIndex"):
# 	'''Like eventConditionedWavesTosKey, but applies dejittering to the waves before storing them. 
# 	The shift times are also stored in the indicated key. The parameters length and lead 
# 	determine the size and possition of the resulting stimulus ensemble. The parameters djlength
# 	and djlead determine (in the same coordinate system) the portion of these stimuli that is 
# 	considered during dejittering (the function will work correctly if this interval is longer
# 	than the primary interval, but this is not recommended)'''
# 	rast=ds.getChannel(cnameEvents)
# 	thresh = (rast.max()-rast.min())/2.0
# 	ind = nonzero(rast>thresh)
# 	pad=int(round(10*(ds.fs/1000.0)))
# 	djlead=int(round(djlead*ds.fs))+pad
# 	djlength=int(round(djlength*ds.fs))+2*pad
# 	djind=ind-djlead
# 	dat=ds.takeWindows(cindex, djind, djlength)
# 	ds2=DataSet(dat, {"SamplesPerSecond":ds.fs})
# 	out=callMatlab("dejitter_pa", [ds2])
# 	shifts=out['sindex'].data[0]
# 	ds.special[sKeyShifts]=shifts
# 	lead=int(round(lead*ds.fs))
# 	length=int(round(length*ds.fs))
# 	dat=zeros((length, shifts.shape[0]), ds.data.dtype.char)
# 	for i, s in enumerate(shifts):
# 		si=int(ind[i]-lead+s)
# 		dat[:,i]=ds.data[si:si+length,cindex]
# 	ds2=DataSet(dat, {"SamplesPerSecond":ds.fs})
# 	ds.special[sKeyDejit]=ds2
# 	return ds		
# 
# def alignDJEvts(ds, cindex=0, sKeyDejit="EvtCondDJ", cnameEvents="EventTimes",sKeyRaw="EvtCond", sKeyShifts='ShiftIndex', lead=0.020):
# 	'''Compensates for the shift in the max of the mean waveform during dejittering by aligning the
# 	dejittered waveforms so that the max(mean) occurs in the same place as for the raw waveforms. 
# 	(the relative dejitter times are not affected)'''
# 	rast=ds.getChannel(cnameEvents)
# 	thresh = (rast.max()-rast.min())/2.0
# 	ind = nonzero(rast>thresh)
# 	dj=ds.special[sKeyDejit]
# 	djm=mean(dj.data, 1)
# 	raw=ds.special[sKeyRaw]
# 	rm=mean(raw.data, 1)
# 	off=argmax(rm)-argmax(djm)
# 	shifts=ds.special[sKeyShifts]
# 	length=djm.shape[0]
# 	lead=int(round(lead*ds.fs))
# 	lead+=off
# 	dat=zeros((length, shifts.shape[0]), ds.data.dtype.char)
# 	for i, s in enumerate(shifts):
# 		si=int(ind[i]-lead+s)
# 		dat[:,i]=ds.data[si:si+length,cindex]
# 	ds2=DataSet(dat, {"SamplesPerSecond":ds.fs})
# 	ds.special[sKeyDejit]=ds2
# 	return ds		
# 
# def forgroundSpecials(ds):
# 	keys=ds.special.keys()
# 	nds=None
# 	for k in keys:
# 		val=ds.special[k]
# 		if type(val)==ArrayType:
# 			if len(val.shape)==1:
# 				val=reshape(val, (-1,1))
# 			elif val.shape[1]>val.shape[0]:
# 				val=transpose(val)
# 			val=DataSet(val, {"SamplesPerSecond":ds.fs, "Labels":[""]})
# 		if isADataSet(val):
# 			val.labels=[k+s for s in val.labels]
# 			if nds==None:
# 				nds=val
# 			else:
# 				nds.addData(val)
# 			del(ds.special[k])
# 	ds.special["OldData"]=ds.data
# 	ds.data=nds.data
# 	ds.labels=nds.labels
# 	ds.fs=nds.fs
# 	return ds
