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
import sysChar as sc
import _sclusttools as clust
import time
#import cPickle

def _spikeDistance(e1d, e2d, cost):
	if cost==0:
		print  "0 cost"
		d=abs(e1d.shape[0]-e2d.shape[0])
	elif cost>=2:
		print  "Inf cost"
		d=union1d(e1d, e2d).shape[0]
	elif not (e1d.shape[0] and e2d.shape[0]):
		print  "One sequence empty"
		d=max(e1d.shape[0], e2d.shape[0])
	elif abs(e1d.shape[0]-e2d.shape[0])>3*e1d.shape[0]:
		print "excessive miss"
		d=2*abs(e1d.shape[0]-e2d.shape[0])
	else:
		d=sc.victorDistance(e1d, e2d, cost)
	return d	
		
def victorDistance(ds, cost, dpath1='/spikes', dpath2='/modelspikes', attrib="Error"):
	'''calculate the Victor/Purpura metric space spike distance between event data elements in <dpath1> and <dpath2>. The result is stored as an attribute of ds named <attrib>
	
	cost is the cost per millisecond to shift a spike. 
	
	Due to issues with float comparison, the calculation is performed on the integer-valued raw event data. This means that both event elements must have the same sampling rate. It also means that there can be some round off error in the cost for coarsly sampled data. A cost value that results in the cost of shifting a spike by one sample bin being >=2 is treated as a cost of infinity.
'''
	#st=time.time()
	evts1=ds.getSubData(dpath1)
	evts2=ds.getSubData(dpath2)
	fs=evts1.fs()
	if evts2.fs()!=fs:
		raise StandardError("victorDistance requires both event elements to have the same sampling rate")
	cost=cost*1000.0/fs
	e1d=evts1.getData()[:,0]
	e2d=evts2.getData()[:,0]
	if evts1.start():e1d+=round(evts1.start()*fs)
	if evts2.start():e2d+=round(evts2.start()*fs)
	d=_spikeDistance(e1d, e2d, cost)
	print "%i evts => %i evts, distance %.4f" % (e1d.shape[0], e2d.shape[0], d) 
	ds.setAttrib(attrib, d)
	return ds
		
	
def testOptimizer(ds, par1=1.0, par2=1.0):
	'''Test function for optimizers. Sets an attribute "Error" to 
	a value that is abs(number of points in ds > par1 - number of points in ds < par2). ds must have local data, and should probably be a timeseries.'''
	dat=ds.getData()
	
	#print "pars", par1, par2
	gp1=(dat>par1).sum()
	gp2=(dat<par2).sum()
	v=abs(gp1-gp2)
	#print gp1, gp2, v
	ds.setAttrib("Error", v)
	return ds

def multiDistance(ds, cost, dpath='/', newpath='/distances'):
	'''Calculate the Victor distance between all pairs of spike trains in the labledEvent element at <dpath>. Store the output at newpath.'''
	d=ds.getSubData(dpath)
	cost=cost*1000.0/d.fs()
	dat=d.getData()
	si=unique1d(dat[:,1])
	dist=zeros((si.shape[0],si.shape[0]), float32)
	for i in si:
		for j in si:
			if j<i:
				dist[i,j]=dist[j,i]
			elif j==i:
				dist[i,j]=0
			else:
				ei=take(dat[:,0], nonzero1d(dat[:,1]==i))
				ej=take(dat[:,0], nonzero1d(dat[:,1]==j))
				dist[i,j]=_spikeDistance(ei, ej, cost)
	head={'SampleType':'timeseries', 'Source':dpath, 'Cost':cost, 'SamplesPerSecond':1, 'Labels':list(si)} 
	ds.createSubData(newpath, dist, head, True)

def clusterTrains1(ds, dpath='/distances', newpath='/cluster', mode='cluster'):
	'''attempts to caluculate the minimal perturbations required to convert a single most representative spike train in the labeled event data at <dpath> into every other spike train. These transformations are then used to relabel the spikes in each spike train. The data element written at newpath is a labeledevents set with two label columns'''
	dists = ds.getSubData(dpath)
	cost=float(dists.attrib('Cost'))
	dpathSpikes=str(dists.attrib('Source'))
	labs=array(map(int, dists.attrib('Labels')))
	dists=dists.getData()
	m=argmin(dists.sum(1))
	print m
	spikes=ds.getSubData(dpathSpikes).getData()
	#labs=unique1d(spikes[:,1])
	rows=range(dists.shape[0])
	st=spikes[nonzero1d(spikes[:,1]==labs[m]),0]
	spikelabs=[]
	traverse=[m]
	rows.remove(m)
	spikelabs.append(column_stack([st, arange(st.shape[0])]))
	maxlab=st.shape[0]-1
	while rows:
		#get best transform
		#print dists.shape, rows, traverse
		if mode=='cluster':
			sd=take(take(dists, array(rows), 0), array(traverse),1)
			mi=argmin(sd)
			mi=unravel_index(mi, sd.shape)
			if len(mi)==1:
				mi=(mi[0], 0)
		else:
			sd=take(dists[traverse[0]], array(rows))
			mi=argmin(sd)
			mi=(mi,0)
		print mi, traverse[mi[1]], rows[mi[0]]
		#best transform is traverse[mi[1]] to rows[mi[0]]
		st= spikes[nonzero1d(spikes[:,1]==labs[traverse[mi[1]]]),0]
		tt= spikes[nonzero1d(spikes[:,1]==labs[rows[mi[0]]]),0]
		#calculate transform
		c, m=sc.transformSpikes(st, tt, cost)
		mf=st[m[:,0]]
		mt=tt[m[:,1]]
		a=setdiff1d(tt, mt)
		if a.shape[0]!=0:
			nl=arange(maxlab+1, maxlab+1+a.shape[0]).astype(tt.dtype)
			maxlab=nl.max()
		sl=zeros_like(tt)-1
		sl[tt.searchsorted(a)]=nl
		ii=tt.searchsorted(mt)
		#print sl.shape, m.shape, ii.shape, ii.max(), ii.min()
		jj=st.searchsorted(mf)
		sl[ii]=spikelabs[mi[1]][jj,1]
		#store event labels 
		traverse.append(rows[mi[0]])
		rows.remove(rows[mi[0]])
		spikelabs.append(transpose(vstack([tt, sl])))
	newlabs=[]
	spikes=zeros((spikes.shape[0], 3), spikes.dtype)
	index=0
	for i in range(len(spikelabs)):
		newlabs.append(labs[traverse[i]])
		ns=spikelabs[i].shape[0]
		spikes[index:index+ns,0]=spikelabs[i][:,0]
		spikes[index:index+ns,1]=i
		spikes[index:index+ns,2]=spikelabs[i][:,1]
		index+=ns
	head={'SampleType':'labeledevents', 'Source':dpathSpikes, 'Cost':cost, 'SamplesPerSecond':ds.getSubData(dpathSpikes).fs(), 'Labels':newlabs} 
	ds.createSubData(newpath, spikes, head, True)
		
def _track(id, tm):
	s1=nonzero1d(tm[:,0]==id)
	s2=nonzero1d(tm[:,1]==id)
	if s1.shape[0]==0 and s2.shape[0]==0:
		return (zeros(0), tm)
	s=concatenate([tm[s1,1], tm[s2,0]])
	s.sort()
	tm=delete(tm, s1, 0)
	tm=delete(tm, s2, 0)
	for ci in s[:]:
		cs, tm=_track(ci, tm)
		s=union1d(s, cs)
		if tm.shape[0]==0:
			break	
	return (s, tm)

def _getClusters(tm):
	sids=unique1d(ravel(tm))
	sids=column_stack([sids, zeros_like(sids)-1])
	si=0
	while tm.shape[0]>0:
		id=tm[0,0]
		s, tm=_track(id, tm)
		ind=sids.searchsorted(s)
		sids[ind,1]=si
		si+=1
	return sids	
				
def clusterTrains2(ds, cost=.1, avoid=.2, require=.2, simthresh=.5, dpath='/', newpath='/cluster'):
	'''attempts to cluster spikes in the labeledevent instance at dpath. Cost is the cost per ms to move a spike and is required because spike correspondance is determined by converting between spike trains using a Victor algorithm. "avoid" is a fraction of spike trains comparisons that are not considered. These are the comparisons with the longest pairwise distances. require is a fraction of the total presentations in which a spike must exist, and simthresh is the level of group similarity required to assign spikes to the same event (high values will result in more unique events, lower values in more permissive event groups).'''
	d=ds.getSubData(dpath)
	cost=cost*1000.0/d.fs()
	dat=d.getData()
	trainIDs=unique1d(dat[:,1])
	nst=trainIDs.shape[0]
	dist=zeros((trainIDs.shape[0],trainIDs.shape[0]), float32)
	st=[]
	trans={}
	ntr =0
	for i, l in enumerate(trainIDs):
		st.append(take(dat[:,0], nonzero1d(dat[:,1]==l)))
		for j in range(0,i):
			dist[j,i], trans[(j,i)]=sc.transformSpikes(st[j], st[i], cost)
			ntr+=trans[(j,i)].shape[0]
	td=dist.sum(1)
	order=argsort(td)
	trainIDs=trainIDs[order]
	if avoid:
		uw=dist.min()
		mw=dist.max()
		avoid=mw-(mw-uw)*avoid
	ia=0
#	foo={'order':order, 'Labels':trainIDs, 'spikes': st, 'avoid':avoid, 'trans':trans, 'dist':dist}
# 	import cPickle
# 	f=file('foo.pickle', 'wb')
# 	cPickle.dump(foo, f)	
	if require:
		require=round(require*nst)
	b=clust.combine(trans, dist, avoid, nst)
	c=clust.getequiv(b, require)
	#c2=clust.fixcor(c, require)
	sev=lambda x, y, z: clust.simgrp(x, y, z, simthresh)
	id=clust.group(c,sev)
	id=clust.unravel(id, nst)
	clust.resolve(id, st)
	head={'SampleType':'labeledevents', 'Source':dpath, 'Cost':cost, 'SamplesPerSecond':ds.getSubData(dpath).fs(), 'Labels':trainIDs, 'avoid':avoid, 'require':require, 'simthresh':simthresh} 
	ds.createSubData(newpath, id, head, True)

