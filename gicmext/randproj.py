#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-04-22.

# Copyright (C) 2009 Graham I Cummins
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
from numpy import reshape, transpose, array, zeros, column_stack, alltrue, unique, log, arange, argmin
from numpy.random import permutation



def _ens23d(dat, r):
	'''convert array dat, mien 2D ensemble, with reps = r, to a 3D ensemble with (samples, channels, repetitions)'''
	chans = dat.shape[1]/r
	dat = dat.reshape((dat.shape[0],chans,r))
	return dat
	
def _ens22d(d):
	''' convert array d (3D ensemble) to MIEN 2D ensemble'''
	return d.reshape((d.shape[0], -1))

def _prob(a , i):
	'''probability of occurrence of row i in array a (NxM)''' 
	if len(a.shape)==1:
		noc = (a==a[i]).sum()
	else:	
		noc =alltrue(a==a[i,:], 1).sum()
	return float(noc)/a.shape[0]

def slidingWindows(ds, xcoordLength=.05, xcoordPeriod=0, dpath="/", newpath='/windows'):
	"""Generate an evenly spaced sequence of events starting at xccordLength, and repeating with period xcoordPeriod (this is a float value, but if it is zero, it will default to the reciprocal of the sampling rate, giving an event on every sample). Extract timeseries data from dpath, and convert to ensemble data by selecting a window of length xcoordLength preceding each event."""
	dat=ds.getSubData(dpath)
	head=dat.header()
	dat=dat.getData()
	#print dat.shape
	fs=head['SamplesPerSecond']
	length=int(round(xcoordLength*fs))
	if xcoordPeriod <=0:
		period = 1
	else:
		period=int(round(xcoordPeriod*fs))
	wins = []
	ei = length
	while ei<dat.shape[0]:
		wins.append(dat[ei-length:ei,:])
		ei+=period
	head['Reps']=len(wins)
	dat = reshape(transpose(array(wins), [1,2,0]), (length,-1))
	head['SampleType']='ensemble'
	head["Lead"]=xcoordLength
	head["conditionedOn"]="Fixed period"
	ds.createSubData(newpath, dat, head, True)

def flattenEnsemble(ds, dpath="/ens"):
	'''Transform the ensemble data in dpath from multi-channel to single-channel, by concatenating the recordings from each channel within each event'''
	ds=ds.getSubData(dpath)
	head=ds.header()
	dat=ds.getData()	
	head["Labels"]=["ConcatenatedChannels"]
	reps = head['Reps']
	dat = _ens23d(dat, reps)
	dat = dat.transpose([1,0,2]).reshape(-1,reps)
	ds.datinit(dat, head)


def _rcent_single(dat, ncenters):
	centers = permutation(dat.shape[2])[:ncenters]
	dist = zeros((dat.shape[2], ncenters), dat.dtype)
	closest = zeros((dat.shape[2], 1), "i4")
	for i in range(ncenters):
		dist[:,i] = ((dat - dat[:,:,centers[i]:centers[i]+1])**2).sum(0).sum(0)
	for j in range(dat.shape[2]):
		nc	= dist[j, :].argmin()
		closest[j,0]=centers[nc]
	return closest	

def _all_dist(dat):
	dist = zeros((dat.shape[1], dat.shape[1]))
	for i in range(dist.shape[0]-1):
		xi = dat[:,i:i+1]
		dist[i,i+1:] = ((dat[:,i+1:]- dat[:,i:i+1])**2).sum(0)
	for i in range(1,dist.shape[0]):
		dist[i,0:i] = dist[:i,i]
	return dist

def _rcent(dat, ncenters, nproj):
	dist = _all_dist(dat)
	indexes = arange(dat.shape[1])
	closest = zeros((dat.shape[1], nproj), "i4")
	for i in range(nproj):
		centers = permutation(indexes)[:ncenters]
		dtc = dist[:,centers]
		closest[:,i]=argmin(dtc, 1)
	return closest


def randCenters(ds, dpath="/", ncenters=20, newpath="/rp" ):
	'''dpath should specify an ensemble data set. This function implements a random hashing function that chooses ncenters examples in the '''
	ens = ds.getSubData(dpath) 
	reps = ens.attrib("Reps")
	dat = _ens23d(ens.getData(), reps)
	closest = _rcent_single(dat, ncenters)
	head = {"Source":dpath, "SampleType":"indexes"}
	ds.createSubData(newpath, closest, head, True)
		
def concatChan(ds, dpath1="/rp", dpath2="/rpo"):
	''' column_stack the channels of dpath2 onto dpath1 (regardless of data type), and delete dpath2 '''
	ds1 = ds.getSubData(dpath1)
	ds2 = ds.getSubData(dpath2)
	head = ds1.header()
	head['Labels']=ds1.getLabels()+ds2.getLabels()
	if head.get("Source"):
		head['Source']=[ds1.attrib("Source"), ds2.attrib("Source")] 
	dat = column_stack([ds1.data, ds2.data])
	ds1.datinit(dat, head)
	ds2.sever()	


def _mi(dat):
	xp = {}
	yp ={}
	jp ={}
	mi = 0
	for i in range(dat.shape[0]):
		x, y = dat[i,:]
		if (x,y) in jp:
			continue
		jp[(x,y)]=_prob(dat, i)
		if not x in xp:
			xp[x]=_prob(dat[:,0], i)
		if not y in yp:
			yp[y]=_prob(dat[:,1], i)
		la = jp[(x,y)] / (xp[x]*yp[y])
		mi += jp[(x,y)] * log(la)
	mi = mi/log(2)	
	return mi
		
def mutualInfo(ds, dpath1="/rp"):
	'''dpath specifies an Nx2 array. Calculates the MI between the two channels, and stores it in the attribute "MI". '''
	ds = ds.getSubData(dpath1)
	dat = ds.getData()
	mi = _mi(dat)
	ds.setAttrib("MI", mi)

def rpSimMat(ds, dpath1='/', dpath2='/output', nproj=2000, ncenters=20, keep = .2, newpath = "/sim"):
	'''construct a similarity matrix  between dpath1 and dpath2 (ensemble data with the same number of reps) using the method of random projections. Use nproj projections, use a euclidean bucket similarity hash function with ncenters, and use collisions from the top fraction of mutual informations determined by keep. Store the similarity matrix in newpath.'''
	ds1 = ds.getSubData(dpath1)
	reps = ds1.attrib("Reps")
	idat= _ens23d(ds1.getData(), reps)[:,-1,:]
	ds2 = ds.getSubData(dpath2)
	odat= _ens23d(ds2.getData(), reps)[:,-1,:]	
	proj = zeros((idat.shape[1], 2, nproj), 'i4')
	mi = zeros(nproj)
	proj[:,0,:]=_rcent(idat, ncenters, nproj)
	proj[:,1 ,:]=_rcent(odat, ncenters, nproj)
	for i in range(nproj):
		mi[i] = _mi(proj[:,:,i])
	keep = int(keep*nproj)
	inds = mi.argsort()
	inds = inds[-keep:]
	proj = proj[:,:,inds]
	smat = zeros((idat.shape[1], odat.shape[1]), 'i4')
	ds.createSubData("/proj", proj, {"SampleType":'generic'}, True)
	for p in range(proj.shape[2]):
		print "c", p
		for i in range(proj.shape[0]):
			collide = alltrue(proj[i,:,p] == proj[i:,:,p], 1)
			smat[i,i:] += collide.astype(smat.dtype)
	for i in range(1,smat.shape[0]):
		smat[i,0:i] = smat[:i,i]
	ds.createSubData(newpath, smat, {"SampleType":'image'}, True)
	
	
	
	
	