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
from numpy.random import randint
import sysChar as sc
from mien.math.sigtools import bandpass
import calibration as cal




def calcRealWaveMatch(ds, dpathg='/rg', noise=.1):
	sd = ds.getSubData(dpathg)
	fs = ds.fs()
	g = sd.getData()[:,0]
	match = []
	for i in range(10):
		evts = _gtoSpikes(g, noise, fs)
		hit = g[evts]
		d3 = setdiff1d(arange(g.shape[0]), unique1d(evts))
		miss = g[d3]
		hit = hit.mean()
		miss = miss.mean()
		s = g.std()
		dist = (hit - miss)/s
		print "hit mean %g, miss mean %g, std %g, score %g" % (hit, miss, s, (hit - miss)/s)
		match.append(dist)
	print match
	m = mean(array(match))
	print m
	ds.setAttrib('real_wavematch', m)

def calcRealVictorDist(ds, dpathg='/rg', noise=.1, cost=.01):
	sd = ds.getSubData(dpathg)
	fs = ds.fs()
	g = sd.getData()[:,0]
	match = []
	nspikes = []
	for i in range(5):
		evts1 = _gtoSpikes(g, noise, fs)
		evts2 = _gtoSpikes(g, noise, fs)
		dist = sc.victorDistance(evts1, evts2, cost)
		print dist
		ns = (evts1.shape[0] + evts2.shape[0])/2
		m = dist / ns
		print m
		match.append(m)
	m = mean(array(match))
	print m
	ds.setAttrib('real_victordist', m)
	
		
def _gtoSpikes(g,  noise, fs):
	noise = noise * (g.max() - g.min())
	if noise > 0:
		wn=normal(0, noise, g.shape[0])
		nqf=fs/2	
		bandMax=200
		bandMin = 5	
		wn=bandpass(wn, bandMin, bandMax, fs)
		g = g + wn
	g = g - g.min()
	g = g/g.max()
	g = 1.0/(1.0+exp( (-1*(g-.5))*40))
	ht=.7
	lt=.3
	evts = []
	hit=nonzero1d(g>ht)
	if len(hit)==0:
		return array(evts)
	fcross=take(hit, nonzero1d((hit-shift(hit, 1))!=1))
	evts.append(hit[0])
	for j in range(1, fcross.shape[0]):
		if any(g[fcross[j-1]:fcross[j]]<lt):
			evts.append(fcross[j])
	return array(evts)
	
def shortToyOne(ds, newpath="/rg"):
	dat = ds.getData()[:,0]
	fs = ds.fs()
	start = ds.start()
	h = {'SampleType':'timeseries', 'SamplesPerSecond':fs, 'StartTime':start}	
	k = array([0,0,0,0,-1,1,-1,1,0,0,0,0])
	ds.createSubData('/k', k, h, delete=True)
	g = cal._applyFilterWithTR(dat, k)
	g = shift(g, 6)
	g = g/g.max()
	ds.createSubData(newpath, g, h, delete=True)
		
	
def toyWithInvariance(ds, klen = 200, noise=.05, newpath="/spikes", returnG=False):
	dat = ds.getData()[:,0]
	fs = ds.fs()
	start = ds.start()
	h = {'SampleType':'timeseries', 'SamplesPerSecond':fs, 'StartTime':start}	
	q = int(klen/4.0)
	k = zeros(klen)
	k[:2*q] = -1
	k[:q] = 1
	ds.createSubData('/k', k, h, delete=True)
	g = cal._applyFilterWithTR(dat, k)
	g = shift(g, int(klen/2))
	g = g/g.max()
	# g = zeros(ds.data.shape[0])
	# for i in range(klen, g.shape[0]):
	# 	g[i] = dat[i-2*third:i-third].mean() - dat[i-3*third:i-2*third].mean()
	if returnG:
		ds.createSubData(newpath, g, h, delete=True)
	else:
		h['SampleType']='events'
		evts = _gtoSpikes(g, noise, fs)
		ds.createSubData(newpath, evts, h, delete=True)

def compoundToy(ds, klen = 200, newpath="/rg"):
	dat = ds.getData()[:,0]
	fs = ds.fs()
	start = ds.start()
	h = {'SampleType':'timeseries', 'SamplesPerSecond':fs, 'StartTime':start}
	x=arange(klen)/fs
	k2=sin( 2*pi*100*x)
	k1=sin( 2*pi*400*x)
	g = cal._applyFilterWithTR(dat, k1)
	g = shift(g, int(klen/2))
	g = g - g.min()
	g = g/g.max()
	g2 = -1*sc.match(dat, k2)
	g2 = g2 - g2.min()
	g2 = g2/g2.max()
	g =  g + g2
	ds.createSubData('/k', column_stack([k1, k2]), h, delete=True)
	ds.createSubData(newpath, g, h, delete=True)

def shortToyTwo(ds, newpath="/rg"):
	dat = ds.getData()[:,0]
	fs = ds.fs()
	start = ds.start()
	h = {'SampleType':'timeseries', 'SamplesPerSecond':fs, 'StartTime':start}
	k2 = array([0,0,0,0,-1,1,-1,1,0,0,0,0])
	k1 = array([-1,1,-1,1,0,0,0,0,-1,1,-1,1])
	g = cal._applyFilterWithTR(dat, k1)
	g = shift(g, 6)
	g = g - g.min()
	g = g/g.max()
	g2 = -1*sc.match(dat, k2)
	g2 = g2 - g2.min()
	g2 = g2/g2.max()
	g =  g + 3*g2
	ds.createSubData('/k', column_stack([k1, k2]), h, delete=True)
	ds.createSubData(newpath, g, h, delete=True)

def zeroEnds(ds, dpath="/dp"):
	sd = ds.getSubData(dpath)
	dat = sd.getData()
	dat[0,:] = 0
	dat[-1,:]=0
	

def gToSpikes(ds, dpathg="/rg", noise=.1, newpath='/spikes'):
	sd = ds.getSubData(dpathg)
	fs = ds.fs()
	g = sd.getData()[:,0]
	evts = _gtoSpikes(g, noise, fs)
	if evts.shape[0] == 0:
		print "no events"
	h = {'SampleType':'events', 'SamplesPerSecond':fs, 'StartTime':sd.start()}
	ds.createSubData(newpath, evts, h, delete=True)	
	
	

def random(ds, rate=100, start=None, dur=None, newpath="/randspikes"):
	'''Generate random events at rate (Hz) and place them in an Event Data element at newpath. if specified, start determines a time when the events begin, and dur a duration (in seconds) over which the events continue to be generated. If not specified, start is ds.start() and dur is the length of the domain of ds. Spikes are generated as indexes, and sampling rate is ds.fs()'''
	if not dur:
		t = domain(ds)
		dur=t[-1]-t[0]
	howmany=round(dur*rate)
	dsamp=round(dur*ds.fs())
	if start==None or start==False:
		start=ds.start()
	f = randint(0, dsamp, howmany)
	f.sort()
	ds.createSubData(newpath, f, {'SampleType':'events', 'SamplesPerSecond':ds.fs(), 'Labels':["Spikes"], 'StartTime':start}, delete=True)
	return ds

			
def lif(ds, select=(None, None, None), refract=1.0, leak=1.0, threshold=.5, rnoise=0, newpath='/lif', returnv=False):
	'''Use the data from select (this should be 1 channel, and if it isn't, only the first channel is used) as a driver potential for a leaky integrate and fire model with the indicated parameters. Place the output spike train in newpath. 

	Refract: The amount to reduce the driver potential when an event occurs
	Leak: The "current" which returns the accumulated potential to 0. Units are in exitation units per DP per sample
	Threshold: The potential at which events trigger
	rnoise: The stdev of the distribution of Refract (default 0) - non-zero values will make things slow
	returnv: if true, the data element stored in newpath will be a timeseries type element containing the actual voltages, rather than the resulting events - currently prevents using the c implementation, and this will make things slow. 
	
		SWITCHVALUES(returnv)=[False, True]'''
#	print select, leak, threshold, refract, rnoise, newpath, returnv
#	if returnv:
#		raise
	vdp=getSelection(ds, select)
	if not rnoise and not returnv:
		nei=sc.lif(vdp[:,0], refract, leak, threshold)
	else:
		nei = []
		v=0
		storev = []
		
		for i in range(vdp.shape[0]):
			v-= v*leak
			v+= vdp[i]
			storev.append(v)
			if v>= threshold:
				nei.append(i)
				v-=refract
				if 	rnoise:
					v -= normal(0, rnoise)
		nei=array(nei)	
	h=getSelectionHeader(ds, select)
	if returnv:
		h['SampleType']='timeseries'
		ds.createSubData(newpath, array(storev), h, delete=True)
	else:
		h['SampleType']='events'
		ds.createSubData(newpath, nei, h, delete=True)
		print "LIF results --"

		if len(nei)==0:
			print "No Events"
		else:
			if len(nei)>1:
				delays=nei[1:]-nei[:-1]
			else:
				delays=array([0.0,1])
			print len(nei), delays.min(), 1.0/delays.mean()		
	return ds
	
