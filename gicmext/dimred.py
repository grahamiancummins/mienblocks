#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2008-07-14.

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
from mien.datafiles.dataset import *
import scipy.optimize as opt
from mien.math.fit import regress
from mien.math.sigtools import drawFromHist

def _guass(x, mean, std):
	g=exp( -1*(x-mean)**2 / std**4 )
	g/=g.sum()
	return g



def _o4(x, m=.1, gamp=1.0, mean=1.0, std=1.0, e=2.0):
	md = x-mean
	l = gamp*(md*m + 1)
	z=l*exp( -1*(abs(md))**e / std**4 )
	return maximum(z, 0.0)

def _var_e(x, mean, std, e):
	if type(x)==tuple and len(x)==3:
		x=arange(x[0], x[1], 1.0/x[2])
	z=exp( -1*(abs(x-mean))**e / std**4 )
	return maximum(z, 0.0)
	
def _o4v(v, y, x):
	yest=apply(_o4, [x]+list(v)) - y
	return yest


	
def _sho(x, RI, SI):
	return 1.0/sqrt( (RI*x)**2 + (SI-x**2)**2 )
	
def _guess(y, x):
	z = []
	reps= maximum(round(10*y/y.max()),0).astype(int32)
	#print reps
	for i in range(y.shape[0]):
		val = x[i]
		z.extend([val]*reps[i])
	z = array(z)
	mean = z.mean()
	std=z.std()
	gm=y.sum()*_guass(x, mean, std)
	gamp=gm.max()
	return array([0, gamp, mean, std, 2.0])

def _lstsqO4(y, x):
	initp=_guess(y,x)
	fp=opt.leastsq(_o4v, initp, (y, x), maxfev = 4000)
	v=fp[0]
	c=apply(_o4, [x]+list(v))
	return (v, c)

def _domain(ds):
	x = arange(ds.data.shape[0])/ds.fs()
	if ds.start():
		x+=ds.start()
	return x

def genO4(ds, dpath="/", m=0.0, gamp=1.0, mean=50.0, std=10.0, e=2.0):
	ds = ds.getSubData(dpath)
	x = _domain(ds)
	y=_o4(x, m, gamp, mean, std, e)
	h={'SampleType':'timeseries', 'SamplesPerSecond':ds.fs()}
	ds.datinit(y, h)
	
def genSHO(	ds, dpath="/zeros", RI=000000001, SI=10000.0):
	ds = ds.getSubData(dpath)
	x = _domain(ds)
	y=_sho(x, RI, SI)
	h={'SampleType':'timeseries', 'SamplesPerSecond':ds.fs()}
	ds.datinit(y, h)
	
	
def genVarE(ds, l=1000, fs=500, start=0, mean=1.0, std=.5, e=2.0):
	x=start+arange(l)/float(fs)
	y=_var_e(x, mean, std, e)
	h={'SampleType':'timeseries', 'SamplesPerSecond':fs}
	ds.datinit(y, h)	
	
def fitO4(ds, select=(None, [0], None), newpath='/o4'):
	dat=getSelection(ds, select)
	h=getSelectionHeader(ds, select)
	fs=h['SamplesPerSecond']
	start=h.get('StartTime', 0)
	x = arange(dat.shape[0])
	if start:
		x+=start
	v=_lstsqO4(dat[:,0], x)
	if newpath:
		np=ds.getSubData(newpath)
		if not np:
			np=ds.createSubData(newpath)
		np.datinit(v[1], h)	
	else:
		setSelection(ds, select, v[1])

def fitExp(ds, select=(None, [0], None), newpath='/o4'):
	dat=getSelection(ds, select)
	h=getSelectionHeader(ds, select)
	fs=h['SamplesPerSecond']
	start=h.get('StartTime', 0)
	ld=log(ravel(dat))
	m, b = regress(ld, fs, start)
	x=start+arange(ld.shape[0])/fs
	y=exp(m*x+b)
	v=((m, b), y)
	if newpath:
		np=ds.getSubData(newpath)
		if not np:
			np=ds.createSubData(newpath)
		np.datinit(v[1], h)	
	else:
		setSelection(ds, select, v[1])
			



