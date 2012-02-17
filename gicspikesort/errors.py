#!/usr/bin/env python
# encoding: utf-8
#Created by Graham Cummins on 2007-05-17.

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

from numpy import *
try:
	import gicspikesort.ssbe as ssbe
except:
	import mb_binary.loader
	ssbe=mb_binary.loader.load('ssbe')



def getReference(tem):
	z=tem.attrib('ReferenceTemplate')
	if z:
		d=tem.getSubData('/spikesort_'+z)
		if d:
			return d
	d=tem.getSubData('/spikesort_all')
	if d:
		return d
	print "Warning: reference template not explicitly defined, using unit 0"
	d=tem.getSubData('/spikesort_unit0')
	if not d:
		raise StandardError('A Reference Template can not be found')
	return d

def getLL(pars, template):
	print(pars)
	if len(pars)==2:
		lead, length=pars
	elif len(pars)==1:
		lead=pars[0]
		length=lead*2
	else:
		try:
			tem=template.getElements("Data", "template", depth=1)[0]
			lead=tem.attrib('Lead')
			length=tem.getData().shape[0]
		except:	
			try:
				lead, length=template._cache['ll']
			except:
				print "All modes of checking template size failed. This is probably bad. Guessing..."
				lead, length = (75, 150)
	return (lead, length)			


def match(dat, tem, pars=None):
	dat=dat.astype('=f4')	
	tem=tem.astype('=f4')
	rec=dat.copy()
	ssbe.match(dat, tem, rec)
	return rec

def mahal(dat, tem, var):
	dat=dat.astype('=f4')	
	tem=tem.astype('=f4')
	var=var.astype('=f4')
	rec=dat.copy()
	if tem.shape!=var.shape:
		raise TypeError("var and tem must have same shape")
	ssbe.mhnd(dat, tem, var, rec)
	return rec

def std_dev(dat, pars=(), template=None):
	return dat.std(1)

def optmin(dat, pars=(), template=None):
	print(pars)
	lead, length=getLL(pars, template)
	print "optmin", lead, length
	e=ssbe.optmin(dat[:,1:], int(lead), int(length))
	e=dat[:,0]+e
	e=e/dat.shape[1] 
	e[:length]=0.0
	e[-length:]=0.0
	return e	

def resid(dat, pars=(), template=None):
	try:
		tem=template.getElements("Data", "template", depth=1)[0]
		spi=template.getElements("Data", "spikes", depth=1)[0]
	except:
		raise
		print "Residual requires a waveform template and spikes."	
		return None		
	nc=dat.shape[1]
	dat=mean(dat,1)
	foo=zeros_like(dat)
	evts=spi.getData()[:,0]
	lead=tem.attrib('Lead')
	td=tem.getData()
	mc=range(0, td.shape[1], 2)
	td=sum(td[:,mc], 1)
	window=arange(td.shape[0])-lead
	window=resize(window, (evts.shape[0], window.shape[0]))
	window=window+reshape(evts, (-1, 1))
	window=ravel(window.astype(int32))
	print td.shape, window.shape
	td=resize(td, window.shape[0])
	put(foo, window, td)
	foo=foo/nc
	return abs(dat-foo)

def pcaProj(dat, pars=(), template=None):
	rt=getReference(template)
	pca=rt.getSubData('pcs').getData()
	c=1
	if pars:
		c=pars[0]
	pca=pca[:,c]
	nc=dat.shape[1]
	pca=reshape(pca, (-1, dat.shape[1]))
	rv=zeros(dat.shape[0], dat.dtype)
	for i in range(dat.shape[1]):
		filt = pca[arange(pca.shape[0]-1,-1, -1), i]
		rv+=convolve(dat[:,i], filt, 'same')
	return rv

def pcaProjAlpha(dat, pars=(), template=None):
	rt=getReference(template)
	pca=rt.getSubData('pcs').getData()
	c=1
	pca=pca[:,c]
	nc=dat.shape[1]
	pca=reshape(pca, (-1, dat.shape[1]))
	rv=zeros(dat.shape[0], dat.dtype)
	for i in range(dat.shape[1]):
		filt = pca[arange(pca.shape[0]-1,-1, -1), i]
		rv+=convolve(dat[:,i], filt, 'same')
	return rv

def pcaProjBeta(dat, pars=(), template=None):
	rt=getReference(template)
	pca=rt.getSubData('pcs').getData()
	c=2
	pca=pca[:,c]
	nc=dat.shape[1]
	pca=reshape(pca, (-1, dat.shape[1]))
	rv=zeros(dat.shape[0], dat.dtype)
	for i in range(dat.shape[1]):
		filt = pca[arange(pca.shape[0]-1,-1, -1), i]
		rv+=convolve(dat[:,i], filt, 'same')
	return rv	
	
def pcaProjGamma(dat, pars=(), template=None):
	rt=getReference(template)
	pca=rt.getSubData('pcs').getData()
	c=3
	pca=pca[:,c]
	nc=dat.shape[1]
	pca=reshape(pca, (-1, dat.shape[1]))
	rv=zeros(dat.shape[0], dat.dtype)
	for i in range(dat.shape[1]):
		filt = pca[arange(pca.shape[0]-1,-1, -1), i]
		rv+=convolve(dat[:,i], filt, 'same')
	return rv
		
ERROR_FUNCTIONS={'Std':std_dev, "Residual":resid, "OptMin":optmin, "PCA Projection": pcaProj,"PCA 1 Projection": pcaProjAlpha, "PCA 2 Projection": pcaProjBeta, "PCA 3 Projection": pcaProjGamma}
