#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-06-04.

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
def deltaFunction(ds, nsamp=2000, loc=800):
	dat = zeros(nsamp)
	dat[loc]=1.0
	ds.datinit(dat, {"SampleType":"timeseries", "SamplesPerSecond":1000})

def differencingFilter(ds, dpath='/'):
	sig = ds.getSubData(dpath)
	head =sig.header()
	sig=sig.data[:,0]
	filt = array([0, 0, -1, 1, 0, 0,])
	out = _applyfilter(sig, filt)
	ds.createSubData('test', data=out, head=head, delete=True)

def singleSineCycleFilter(ds, dpath='/', freq=50, phase=90):
	sig = ds.getSubData(dpath)
	head =sig.header()
	sig=sig.data[:,0]
	filt = _makeCos(head["SamplesPerSecond"], freq, phase, 1.0)
	out = _applyfilter(sig, filt)
	ds.createSubData('test', data=out, head=head, delete=True)

def wedgeFunction(ds, nsamp=2000, loc=800):
	dat = zeros(nsamp)
	dat[loc:loc+100]=linspace(1,-1,100)
	ds.datinit(dat, {"SampleType":"timeseries", "SamplesPerSecond":1000})

def wedgeFilter(ds, dpath='/'):
	sig = ds.getSubData(dpath)
	head =sig.header()
	sig=sig.data[:,0]
	filt = linspace(1, -1, 100)
	out = _applyfilter(sig, filt)
	ds.createSubData('test', data=out, head=head, delete=True)

def makeCosWave(ds, freq=50, phase=90, ncycles=1):
	fs = ds.fs()
	filt = _makeCos(fs, freq, phase, 1.0)
	ds.datinit(filt)

def ifftTest(ds):
	gain = ds.data[:,0]
	phase = ds.data[:,1]
	fs, start = ds.fs(), ds.start()
	nyquist = start + gain.shape[0]/fs
	if start:
		print "start"
		npad = int(round(start*fs))
		gain = concatenate([ones(npad)*gain[0], gain])
		phase = concatenate([zeros(npad), phase])
	c = gain*exp(1j*phase)
	ts = irfft(c)
	head = {"SampleType":"timeseries", "SamplesPerSecond":nyquist*2}
	ds.createSubData('ts1', data=ts, head=head, delete=True)	
	f, a, p = _quickFFT(ts, nyquist*2)
	head = {"SampleType":"timeseries", "SamplesPerSecond":1.0}
 	ds.createSubData('fs2', column_stack([a, p]), head=head, delete=True)

def convertAccel(ds, dpath='/', channel=1, accSens = 0.0999):
	ds = ds.getSubData(dpath)
	dat = ds.getData()
	ch = dat[:,channel]/accSens
	ch = rfft(ch, len(ch))
	freq = arange(ch.shape[0])*ds.fs()/(2*ch.shape[0])
	freq[0]=1
	amp=abs(ch)
	phase=arctan2(ch.imag, ch.real)
	phase -= pi/2
	amp/=(2*pi*freq)
	amp[0]=0
	ch = amp*exp(1j*phase)
	ch = irfft(ch, dat.shape[0])
	dat[:,channel] = ch
	ds.datinit(dat)

def resampleTest(ds, dpathFilt='/', useWindowedFFT=True, targetfs=25000):
	analyzeFilterWN(ds, dpathFilt, useWindowedFFT)
	filt = ds.getSubData(dpathFilt)
	ffs = filt.fs()
	fdat = filt.getData(copy=True)[:,0]
	head = filt.header()
	fdat = _filterResample(fdat, ffs, targetfs)
	head["SamplesPerSecond"]=targetfs
	fdat-=fdat.mean()
	ds.createSubData('/resamplefilt', data=fdat, head=head, delete=True)
	analyzeFilterWN(ds, '/resamplefilt', useWindowedFFT, '/filterResponseWN/resampleResponseWN')
	doc = io.read('xferSmoothed.mdat')
	dat = doc.getElements("Data")[0]
	d = ds.getSubData('/filterResponseWN/resampleResponseWN')
	d.newElement(dat)














