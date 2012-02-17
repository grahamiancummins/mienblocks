#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-07-09.

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

import bree, os
import mien.parsers.fileIO as io
from numpy import *
import ccbcv.density as dens
from mien.math.array import uniformsample
import gicmext.dimred as DR

moddir = os.path.split(bree.__file__)[0]
tffn = os.path.join(moddir, 'hairTFs.mdat')


def _mmcall(data, clusters, model="Gaussian_pk_Lk_Ck", weighted=False):
	return dens._mmcall(data, clusters, model, weighted)

def loadTransferFunctions(ds, parts="both", trimLF=10.5):
	'''
SWITCHVALUES(parts)=["both", "gain", "phase"]
	'''
	d2 = io.read(tffn)
	tfs = d2.getElements('Data')
	for de in ds.getElements("Data", {"SampleType":"function"}, depth=1):
		de.sever()
	for t in tfs:
		if trimLF:
			ind = t.data[:,0]>=trimLF
			t.data = t.data[ind, :]
		if parts == "gain":
			t.data=t.data[:,:2]
		elif parts == "phase":
			t.data = t.data[:,[0,2]]
		ds.newElement(t)

def clusterAttribute(ds, attrib="length", minclusters=1, maxclusters=8, modeltype='Gaussian_pk_Lk_I'):
	dats = ds.getElements('Data', {"SampleType":"function"})
	vals = array([e.attrib(attrib) for e in dats])
	vals = vals.reshape(-1, 1)
	# dn = 'mixmodtest'
	# if not os.path.isdir(dn):
	# 	os.mkdir(dn)
	# dens._writeMixControl(dn, vals, range(minclusters, maxclusters+1), modeltype)
	mod = _mmcall(vals, range(minclusters, maxclusters+1), modeltype)
	print mod



def _evalGaus(pt, gaus):
	w = gaus['prop']
	mean = array(gaus['mean'])
	cov = array(gaus['cov'])
	norm = 1.0 / ( sqrt(linalg.det(cov))*(2*pi)**(mean.shape[0]/2.0))
	icov = linalg.inv(cov)
	x = pt - mean
	out = -.5*dot(dot(x, icov), x)
	out = w*norm*exp(array(out))
	return out

def _whichCluster(pt, mod):
	lkly = []
	for c in mod:
		lkly.append(_evalGaus(pt, c))
	return array(lkly).argmax()

def clusterData(ds, dpath='/attribs', columns=(1,2,3,4,5), minclusters=1, maxclusters=5, modeltype='Gaussian_pk_Lk_Bk'):
	vals = ds.getSubData(dpath).data
	vals = vals[:,columns]
	mod = _mmcall(vals, range(minclusters, maxclusters+1), modeltype)
	mod = mod['components']
	for i in range(vals.shape[0]):
		if len(columns)>1:
			print "%i -> %i" % (i, _whichCluster(vals[i,:], mod))
		else:
			print "%i (%G)-> %i" % (i, vals[i,0], _whichCluster(vals[i,:], mod))

	

def attributeListToData(ds, newpath='/attribs', attribs = ('length', 'm', 'gamp', 'mean', 'std', 'e')):
	dats = ds.getElements('Data', {"SampleType":"function"})
	dats = [d for d in dats if all([a in d.attributes for a in attribs])]
	vals = array([[e.attrib(a) for a in attribs] for e in dats])
	h = {"SampleType":"generic", 'Labels':attribs}
	ds.createSubData(newpath, vals, h, True)
	
def orderPlotsByAttribute(ds, 	attrib="length", channel=1):
	dats = ds.getElements('Data', {'SampleType':'function'})
	ifv = min([d.data[:,0].min() for d in dats])
	mfv = max([d.data[:,0].max() for d in dats])
	vals = array([e.attrib(attrib) for e in dats])
	order = vals.argsort()
	chans = []
	for i in order:
		t = dats[i].data[:, [0, channel]]
		ii = t[:,0].argmin()
		iv = t[ii,0]
		if iv > ifv:
			t = row_stack([ array([ifv, t[ii,1]]), t])
		mi = t[:,0].argmax()
		mv = t[mi,0]
		if mv < mfv:
			t = row_stack([ t, array([mfv, t[mi,1]])])
		d = uniformsample(t, 5.0)[:,0]
		chans.append(d)
	d = column_stack(chans)
	ds.datinit(d, {"SampleType":"timeseries", "SamplesPerSecond":.2})

def fitTSO4(ds, newpath=""):
	chans = []
	h= ds.header()
	fs=h['SamplesPerSecond']
	start=h.get('StartTime', 0)
	for i in range(ds.data.shape[1]):
		dat=ds.data[:,i]
		v=DR._lstsqO4(dat, fs, start)
		chans.append(v[1])
	if newpath:
		ds.createSubData(newpath, column_stack(chans), h, True)
	else:
		echans = []
		for i in range(ds.data.shape[1]):
			echans.extend([ds.data[:,i], chans[i]])
		ds.datinit(column_stack(echans), {'SampleType':'ensemble', 'Reps':2, 'SamplesPerSecond':fs}, True)
		

	

def o4sToTimeSeries(ds, dpath='/attribs'):
	chans = []
	dat = ds.getSubData(dpath).data
	x = arange(0, 200)
	for i in range(dat.shape[0]):
		c = apply(DR._o4, [x]+list(dat[i,1:]))
		chans.append(c)
	dat = transpose(array(chans))
	ds.datinit(dat, {"SampleType":"timeseries", "SamplesPerSecond":1.0})
	
	
def resampFunctions(ds):
	attribs = ('m', 'gamp', 'mean', 'std', 'e')
	dats = ds.getElements('Data', {'SampleType':'function'})
	dats = [d for d in dats if all([a in d.attributes for a in attribs])]
	mfv = 200
	x = arange(0, 200)
	vals = array([e.attrib('length') for e in dats])
	order = vals.argsort()
	off = 0 
	for i in order:
		pars = [dats[i].attrib(a) for a in attribs]
		c = apply(DR._o4, [x]+pars)
		cx = x+off
		dats[i].data=column_stack([cx, c])
		off+=mfv
	
		
		
def fitFunctionsO4(ds):
	dats = ds.getElements('Data', {'SampleType':'function'})
	mfv = max([d.data[:,0].max() for d in dats])
	vals = array([e.attrib('length') for e in dats])
	order = vals.argsort()
	off = 0 
	for i in order:
		f = dats[i]
		print i, f.attrib('length'), f.name()
		h = f.header()
		x = f.data[:,0]
		y = f.data[:,1]
		pars, vals = DR._lstsqO4(y, x)
		f.data[:,0]+=off
		off+=mfv
		x = f.data[:,0]
		h.update(dict(zip(['m', 'gamp', 'mean', 'std', 'e'], pars)))
		d = column_stack([x, vals])
		h['style']='line'
		path = f.dpath()+"_fit"
		ds.createSubData(path, d, h, True)
				
	
	