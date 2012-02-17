#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-01-28.

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

from mien.datafiles.dataset import *

def _comb(dat, factor):
	out = zeros(dat.shape[0]*factor)
	ins = round(linspace(0, out.shape[0]-1, dat.shape[0])).astype(int32)
	out[ins] = dat
	return out

def nyquistUpsample(ds, dpathSource="/", factor=3, newpath=""):
	'''Upsample by factor using nyquist interpolation (sinc convolution). dpathSource specifies a source data element which must be a timeseries. All data in the source element are upsampled. The result is a timeseries element with sampling rate = factor*source.fs(). If newpath is empty, this new element replaces the source data. Otherwise it is stored at newpath.'''
	el = ds.getSubData(dpathSource)
	sfs = el.fs()
	dat = el.data
	targ = zeros((dat.shape[0]*factor, dat.shape[1]))
	f= 1.0/factor
	sf = sinc(arange(-5, 5, f))
	for c in range(dat.shape[1]):
		d = _comb(dat[:,c], factor)
		targ[:,c] = convolve(d, sf, mode='same')
	h = el.header()
	h['SamplesPerSecond']=el.fs()*factor
	if not newpath:
		el.datinit(targ, h)
	else:
		ds.createSubData(newpath, targ, h, True)
	
def deriv(ds, select=(None, [0], None), newpath="/deriv"):
	dat = getSelection(ds, select)
	d = ds.getSubData(select[0])
	fs, start = d.fs(), d.start()
	out = zeros_like(dat)
	for c in range(dat.shape[1]):
		out[:,c]=cdiff(dat[:,c], fs)
	h = {"SampleType":"timeseries", "SamplesPerSecond":fs, "StartTime":start}
	ds.createSubData(newpath, out, h, True)
	
def directionalProjection(ds, channels=[1, 2], angle=225):
	'''Project 2 stimulus channels onto a single preferred direction. Direction is interpreted as follows: The two selected stimulus channels are assumed to represent stimuli from 0->180 and 90->270 degrees in an angular coordinate system. The resultant (which replaces the selection) is the result of trigonometric projection of these coordinates onto a single coordinate axis that has "angle". Angle is interpreted CLOCKWISE (due to any existing convention in the labs of John Miller and Gwen Jacobs), which is NOT the mathematical standard, but the result is still that the projection is described by c = a*cos(thet) + b*sin(thet)'''
	dat = ds.getData()[:, channels]
	thet = pi*angle/180
	c = dat[:,0]*cos(thet) + dat[:,1]*sin(thet)
	z = [i for i in range(ds.data.shape[1]) if not i in channels]
	dat = concatenate([ds.getData()[:, z], c[:,newaxis]], 1)
	h = ds.header()
	labs = ds.getLabels()
	h['Labels'] = [labs[i] for i in z] + ['projection'] 
	ds.datinit(dat, h)
	
def _quick_integrate(dat,fs=1.):
    #takes a 1D array and a sampling frequency and returns a 1D array which is the integral of the input
    dat = array(dat)
    fs = float(fs)
    trapdat = (dat[:-1] + dat[1:])/(2*fs)
    out = zeros(len(dat))
    out[0] = dat[0]/fs
    for m in range(1,len(dat)):
        out[m]=out[m-1]+trapdat[m-1]
    return out 


def constantFrequencyModulation(ds, dpath='/', factor=1.0):
	sd = ds.getSubData(dpath)
	dat = sd.getData()
	chans = []
	for i in range(dat.shape[1]):
 		chans.append(array_resample(dat[:,i], 1.0, 1.0/factor, True))
 	dat=transpose(array(chans))	
	sd.datinit(transpose(array(chans)))	



def integrate(ds, select=(None, [0], None), newpath="/intgrl"):
    #returns the discrete integral of a data selection
    dat = getSelection(ds, select)
    d = ds.getSubData(select[0])
    fs, start = d.fs(), d.start()
    out = zeros_like(dat)
    for c in range(dat.shape[1]):
        out[:,c] = _quick_integrate(dat[:,c],fs)
    h = {"SampleType":"timeseries", "SamplesPerSecond":fs, "StartTime":start}
    ds.createSubData(newpath, out, h, True)	
