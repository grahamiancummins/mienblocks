#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2008-07-17.

# Copyright (C) 2008 Graham I Cummins
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
import sys
import mien.parsers.fileIO as io
from mien.datafiles.dataset import *
from numpy import *


# JBND='/Users/gic/Desktop/neuron_code'
# 
# if not JBND in sys.path:
# 	sys.path.append(JBND)
# 
# import fitsearch
# 
# if __name__=='__main__':
# 	epsarray = linspace(0.01,0.4,10)
# 	f = fitsearch.network_fitness(epsarray=epsarray) 
# 	print f
# 
# def getJBFit(ds, e1, e2, e3, e4, e5, e6, e7, e8, e9, e10, g_ExIn, g_InEx, g_InIn):
# 	epsarray= array([e1, e2, e3, e4, e5, e6, e7, e8, e9, e10])
# 	f=fitsearch.network_fitness(epsarray=epsarray, g_ExIn=g_ExIn, g_InEx=g_InEx, g_InIn=g_InIn)
# 	print f[2]
# 	ds.setAttrib('fitness', f[2])
# 	#a = arange(6000)
# 	#b=convolve(a, epsarray, 'same') 
# 	#print b.mean()
# 	#ds.setAttrib('fitness', b.mean())


def _intSigShift(dens, delay, sig, fs):
	out=zeros_like(sig)
	dens=dens/dens.sum()
	delay=round(delay*fs).astype(int32)
	for i in range(dens.shape[0]):
		out+=dens[i]*shift(sig, delay[i])
		#out+=(1.0/dens.shape[0])*shift(sig, delay[i])
	return out
	

def _getA(dat, w):
	d=dat.getData()
	de=.005*arange(d.shape[0])/d.shape[0]
	

def sinResponse(ds, selectDensity=('/dens', (0,), None), freq=100, newpath='/'):
	#dd=getSelection(ds, selectDensity)
	dd=getSelection(ds, ('/dens', [0], None))
	de=.005*arange(dd.shape[0])/dd.shape[0]
	fs=10000
	sw=sin(freq*2*pi*arange(0,1.0,1.0/fs))
	out=_intSigShift(dd, de, sw, fs)	
	np=ds.getSubData(newpath)
	if not np:
		np=ds.createSubData(newpath)
	np.datinit(out, {'SampleType':'timeseries', 'SamplesPerSecond':fs})


def getGain(ds, selectDensity=('/dens', (0,), None), newpath='/'):	
	dd=getSelection(ds, ('/dens', [0], None))
	de=.005*arange(dd.shape[0])/dd.shape[0]
	fs=10000
	freq=arange(0,500, 4.0)
	gain=zeros((600,1))
	for i, f in enumerate(freq):
		sw=sin(f*2*pi*arange(0,1.0,1.0/fs))
		out=_intSigShift(dd, de, sw, fs)
		sw=sw[int(.01*fs):]
		out=out[int(.01*fs):]
		g=sqrt((out**2).sum()) / sqrt((sw**2).sum())
		gain[i]=g	
	np=ds.getSubData(newpath)
	if not np:
		np=ds.createSubData(newpath)
	np.datinit(gain, {'SampleType':'timeseries', 'SamplesPerSecond':4.0})
	
	

# if __name__=='__main__':
# 	doc=io.read(sys.argv[1])
# 	dat=doc.getElements('Data')[0]
# 	getA(dat, 100)
	
