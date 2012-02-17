#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-06-17.

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

from numpy import *
from numpy.linalg import eig, inv
from numpy.random import randn
from tempfile import mkdtemp
import os
from mien.parsers.nmpml import createElement, forceGetPath
from mien.math.array import combinations
import ccbcv.dircolors

CLASS_DENSITIES ={
1 : 0.054237    ,
12: 0.070056    ,
6 : 0.055593    ,
2 : 0.014915    ,
3 : 0.0090395   ,
10: 0.018079    ,
4 : 0.021695    ,
11:0.039322     ,
7 :0.04113      ,
5 :0.03887      ,
9 :0.024859     ,
8 :0.0076836    ,
13:.02,   #FIXME: don't know this
0 :.05

}


def _parsemm(l):
	mods = []
	lsingle = None
	cmod = {}
	for line in l:
		line = line.strip()
		if not line:
			continue
		line = map(float, line.split(" "))
		if len(line) == 1:
			if lsingle:
				if cmod:
					mods.append(cmod)
				cmod = {'bic':lsingle, 'components':[]}
				mods.append(cmod)
			lsingle = line[0]
		elif lsingle:
			ccomp = {'prop':lsingle, 'mean':line, 'cov':[]}
			cmod['components'].append(ccomp)
			lsingle = None
		else:
			ccomp['cov'].append(line)
	return mods
	

def _parsemm1d(l):
	mods = []
	cmod = {}
	tdens = 0
	ccomp=[]
	for line in l:
		line = line.strip()
		if not line:
			continue
		line = map(float, line.split(" "))
		if len(line) != 1:
			raise IOError("parsemm1d called an multi-d data")
		v = line[0]
		if not cmod:
			cmod = {'bic':v, 'components':[]}
			tdens = 0
			ccomp = []
			continue
		ccomp.append(v)
		if len(ccomp)>=3:
			tdens+=ccomp[0]
			cmod['components'].append({'prop':ccomp[0], 'mean':[ccomp[1]], 
				'cov':[[ccomp[2]]]})
			ccomp=[]
		if tdens>=.999:
			mods.append(cmod)
			cmod = {}
	return mods

def _writeMixControl(dn, data, clusters, model, weighted=False):
	curdir = os.getcwd()
	os.chdir(dn)
	if weighted:
		wt = data[:,-1]
		data = data[:,:-1]		
	cf = open('control.xem', 'w')
	cf.write("NbLines\n\t%i\n" % (data.shape[0],))
	cf.write("PbDimension\n\t%i\n" % (data.shape[1],))
	cf.write("NbNbCluster\n\t%i\n" % (len(clusters),))
	cf.write("ListNbCluster\n\t%s\n" % (" ".join(map(str, clusters)),))
	cf.write("NbModel\n\t1\n")
	cf.write("ListModel\n\t%s\n" % model)
	cf.write("DataFile\n\tdata.dat\n")
	if weighted:
		cf.write("WeightFile\n\twt.wgt\n")
	cf.close()
	df = open('data.dat', 'w')
	for i in range(data.shape[0]):
		l = " ".join(map(str, list(data[i,:])))
		df.write(l+"\n")
	df.close()	
	if weighted:
		wf=open('wt.wgt', 'w')
		for n in wt:
			wf.write(str(n)+"\n")
	os.chdir(curdir)
	
		

def _mmcall(data, clusters, model="Gaussian_pk_Lk_Ck", weighted=False):
	dn = mkdtemp()
	_writeMixControl(dn, data, clusters, model, weighted)
	curdir = os.getcwd()
	os.chdir(dn)
	os.system("mixmod control.xem")
	out = open('numericComplete.txt').readlines()
	if data.shape[1]==1:
		mod = _parsemm1d(out)
	else:
		mod = _parsemm(out)
	os.chdir(curdir)
	os.system('rm -rf %s' % dn)
	open('test.txt', 'w').write("".join(out))
	best = 0
	bic = mod[0]['bic']
	for i in range(1, len(mod)):
		if mod[i]['bic'] < bic:
			best = i
			bic = mod[i]['bic']
	return mod[best]
	
	
def _test(shape=(77,3), clusters = (1,2,3,4,5), model="Gaussian_pk_Lk_Ck"):
	dat = apply(randn, shape)
	mods = _mmcall(dat, clusters, model, True)
	print _mod2par(mods)

def _mod2par(mod):
	comp = mod['components']
	w = []
	m = []
	c = []
	for co in comp:
		w.append(co['prop'])
		m.extend(co['mean'])
		for l in co['cov']:
			c.extend(l)
	return (w, m, c)

def densityEstimatesForClasses(doc, minCenters=12, maxCenters=20, model="Gaussian_pk_Lk_Ck", useDiameters=0):
	els = doc.getElements('Fiducial', {"Style":'spheres'})
	if not els:
		return
	centers = range(minCenters, maxCenters+1)
	classes = {}
	metas = ['meta_class', 'meta_cercus', 'meta_length', 'meta_directional_tuning', 'meta_instar']
	for e in els:
		if not any([m in e.getInheritedAttributes() for m in metas]):
			print('metadata not defined for %s. Skipping' % e.upath())
			continue
		e.setAttrib('meta_directional_tuning', e.attrib('meta_directional_tuning', True) % 360, True)
		sig = tuple([(m, e.attrib(m, True)) for m in metas])
		if not sig in classes:
			classes[sig]=[]
		classes[sig].append(e.getPoints())
	for cl in classes:
		dat = row_stack(classes[cl])
		print cl, len(classes[cl]), dat.shape[0]
		if not useDiameters:
			dat=dat[:,:3]
		mod = _mmcall(dat, centers, model, useDiameters)
		name = "density%i_%i_%s%s%sgmm" % (cl[0][1], int(cl[4][1]), cl[2][1][0].upper(), cl[1][1][0].upper(), cl[3][1])
		try:
			mm = doc.getInstance("/AbstractModel:%s" % name)
			mmb = mm.getInstance("MienBlock:gmm")
			par = mmb.getElements("Parameters", depth=1)[0]
		except:
			mm = createElement("AbstractModel", {"Name":name})
			for pair in cl:
				mm.setAttrib(pair[0], pair[1])
			mmb = createElement('MienBlock', {"Name":"gmm",'Function':'ccbcv.gmm.gmm'})
			par= createElement("Parameters", {})
			mmb.newElement(par)
			mm.newElement(mmb)
			doc.newElement(mm)
		total_weight = CLASS_DENSITIES[cl[0][1]]
		mm.setAttrib('total_weight', total_weight)
		w, m, c = _mod2par(mod)
		args = {'weights':w, 'means':m, 'covs':c}
		par.setValue(args, override=True)

		
def _getGMMBB(am, minval=.001):
	gmm = am.getElements('MienBlock', {'Function':'ccbcv.gmm.gmm'})[0]
	args = gmm.getArguments()
	weights = array(args['weights'])
	means = reshape(args['means'], (weights.shape[0], -1))
	covs = reshape(args['covs'], (means.shape[0], means.shape[1], means.shape[1]))
	rads = []
	for i, w in enumerate(weights):
		if w <= minval:
			continue
		nsd = -log(minval/w)
		m = means[i]
		rang = sqrt(diag(covs[i]))*nsd
		rads.append(m - rang)
		rads.append(m + rang)
	rads = array(rads)
	bb = (rads.min(0), rads.max(0))
	return bb
	
	
def gmmToSpatialField(doc, upathAbstract="/AbstractModel:class1LLdensity", edge = 5.0, minvalue=.01, maxvalue=.1):
	am = doc.getInstance(upathAbstract)
	bb = _getGMMBB(am, minvalue)
	origin = bb[0]
	rang = bb[1]-bb[0]
	rang = ceil(rang/edge).astype(int32)
	indexes = combinations([arange(rang[0]), arange(rang[1]), arange(rang[2])])
	dat = indexes*edge + array(origin)
	ds = createElement("Data", {"Name":'points', "SampleType":"generic"})
	ds.datinit(dat)
	am.run(ds)
	sfs = ds.getSubData('gmmout').getData()
	md = sfs.max()
	keep = nonzero(sfs>=minvalue*sfs.max())[0]
	if keep.shape[0]<indexes.shape[0]/2.0:
		indexes = indexes[keep, :]
		values = sfs[keep, 0]
		mindex = indexes.min(0)
		indexes -= mindex
		maxdex = indexes.max(0)+1
		origin = tuple(array(origin) + edge*mindex)
		sfd = zeros(maxdex)
		sfd[indexes[:,0], indexes[:,1], indexes[:,2]]=values
	else:
		sfd = zeros((rang[0], rang[1], rang[2]))
		sfd[indexes[:,0], indexes[:,1], indexes[:,2]]=sfs[:,0]
	name = am.name()+"_sf"
	sf = doc.getElements('SpatialField', name)
	if sf:
		sf[0].sever()
	sf = createElement('SpatialField', {"Name":name})
	ds = createElement('Data', {"Name":"sfd"})
	sfd = sfd/sfd.max()
	sfd = sfd*am.attributes.get('total_weight', .07)/.07
	ds.datinit(sfd, {"SampleType":"locus"})
	sf.newElement(ds)
	for an in am.attributes:
		if an.startswith("meta_"):
			sf.setAttrib(an, am.attrib(an))
	sf.setAttrib("Origin", origin)
	sf.setAttrib("mindensity", minvalue)
	sf.setAttrib("maxdensity", maxvalue)
	ang = sf.attrib('meta_directional_tuning') % 360
	ang = ang *pi/180
	c = ccbcv.dircolors._getAngleColor(ang)
	pycol=ccbcv.dircolors.convertColor(c, 'py')
	sf.setAttrib('color', pycol)
	sf.setAttrib("Edge", edge)
	doc.newElement(sf)
	

def gmmOverlapNumerical(doc, upathGMM1="/AbstractModel:class1LLdensity",  upathGMM2="/AbstractModel:class2LLdensity", edge = 5.0, minvalue=.01):
	am1 = doc.getInstance(upathGMM1)
	am2 = doc.getInstance(upathGMM2)
	bb1 = _getGMMBB(am1, minvalue)
	bb2 = _getGMMBB(am2, minvalue)
	bb = (minimum(bb1[0], bb2[0]), maximum(bb1[1], bb2[1]))
	origin = bb[0]
	rang = bb[1]-bb[0]
	rang = ceil(rang/edge).astype(int32)
	indexes = combinations([arange(rang[0]), arange(rang[1]), arange(rang[2])])
	dat = indexes*edge + array(origin)
	ds = createElement("Data", {"Name":'points', "SampleType":"generic"})
	ds.datinit(dat)
	am1.run(ds)
	sfs1 = ds.getSubData('gmmout').getData()
	am2.run(ds)
	sfs2 = ds.getSubData('gmmout').getData()
	sfs1 = sfs1 / sfs1.sum()
	sfs2 = sfs2 / sfs2.sum()
	sfs = minimum(sfs2 ,sfs1)
	val = sfs.sum()
	print "Overlap is %.2g" % val
	

def spatialFieldOverlap(doc, upathSF1,  upathSF2):
	am1 = doc.getInstance(upathSF1)
	am2 = doc.getInstance(upathSF2)
	e = am1.attrib('Edge')
	if not e == am2.attrib('Edge'):
		print("Can't compare spatial fields with different edge lengths. Aborting")
		return
	d1 = am1.getElements('Data')[0].getData()
	d2 = am2.getElements('Data')[0].getData()
	d1 = d1 / d1.sum()
	d2 = d2 / d2.sum()
	z1 = array(am1.attrib('Origin'))
	z2 = array(am2.attrib('Origin'))
	z = minimum(z1, z2)
	os1 = around((z1 -z)/e).astype(int32)
	os2 = around((z2 -z)/e).astype(int32)
	s1 = os1 + array(d1.shape)
	s2 = os2 + array(d2.shape)
	s = maximum(s1, s2)
	q1 = zeros(s)
	q2 = zeros(s)
	q1[os1[0]:s1[0], os1[1]:s1[1], os1[2]:s1[2]] = d1
	q2[os2[0]:s2[0], os2[1]:s2[1], os2[2]:s2[2]] = d2
	q = minimum(q1, q2)
	val = q.sum()
	print "Overlap is %.2g" % val
	
	
def spatialFieldKL(doc, upathSF1,  upathSF2):
	am1 = doc.getInstance(upathSF1)
	am2 = doc.getInstance(upathSF2)
	e = am1.attrib('Edge')
	if not e == am2.attrib('Edge'):
		print("Can't compare spatial fields with different edge lengths. Aborting")
		return
	d1 = am1.getElements('Data')[0].getData()
	d2 = am2.getElements('Data')[0].getData()
	d1 = d1 / d1.sum()
	d2 = d2 / d2.sum()
	z1 = array(am1.attrib('Origin'))
	z2 = array(am2.attrib('Origin'))
	z = minimum(z1, z2)
	os1 = around((z1 -z)/e).astype(int32)
	os2 = around((z2 -z)/e).astype(int32)
	s1 = os1 + array(d1.shape)
	s2 = os2 + array(d2.shape)
	s = maximum(s1, s2)
	q1 = zeros(s)
	q2 = zeros(s)
	q1[os1[0]:s1[0], os1[1]:s1[1], os1[2]:s1[2]] = d1
	q2[os2[0]:s2[0], os2[1]:s2[1], os2[2]:s2[2]] = d2
	q1 = ravel(q1)
	q2 = ravel(q2)
	ind = logical_and(q1!=0, q2!=0)
	z = q1[ind] * log(q1[ind]/q2[ind])
	val = z.sum()
	print "KL divergence is %.4g" % val	
	

	

def amplifySpatialFields(doc, factor=2.0):
	for el in doc.getElements("SpatialField"):
		ds = el.getElements('Data', depth=1)[0]
		dat = ds.getData()
		dat=dat*factor
		ds.datinit(dat)
	
def setFieldDensityLimits(doc, mindens=.001, maxdens=.1):
	for el in doc.getElements("SpatialField"):
		el.setAttrib('mindensity', mindens)
		el.setAttrib('maxdensity', maxdens)

def normalizeSpatialFields(doc):
	for el in doc.getElements("SpatialField"):
		ds = el.getElements('Data', depth=1)[0]
		dat = ds.getData()
		dat=dat/dat.max()
		ds.datinit(dat)
			
def allVaricsToData(doc, upath="/Data:CombinedVaricData"):
	els = doc.getElements('Fiducial', {'Style':'spheres'})
	ds = forceGetPath(doc, upath)
	dat = row_stack([e.getPoints()[:,:3] for e in els])
	ds.datinit(dat, {'SampleType':'points'})

	
def allGMMsToSFs(doc, edge=5.0, minvalue=.005, maxvalue=.1):
	ams = doc.getElements("AbstractModel", depth=1)
	for a in ams:
		if a.getElements('MienBlock', {'Function':'ccbcv.gmm.gmm'}):
			gmmToSpatialField(doc, a.upath(), edge, minvalue, maxvalue)


def _drawGaus(me, co, ntc):
	#print me, co
	z = randn(me.shape[0], ntc)
	ev, em = eig(co)
	z = dot(em, sqrt(ev)[:,newaxis]*z)
	z = z.transpose() + me
	#print mean(z, 0), cov(z.transpose())
	return z

def _sampleGMM(wts, means, covs, n):
	pts = []
	wts = wts/wts.sum()
	for i,w in enumerate(wts):
		ntc = int(round(w*n))
		pts.append(_drawGaus(means[i], covs[i], ntc))
	return row_stack(pts)

import gmm

def _sampleSF(sf, n):
	cpd = cumsum(sf.flat)
	r = random.uniform(0, cpd[-1], n)
	l = searchsorted(cpd, r)
	return array( [unravel_index(a, sf.shape) for a in l] )

def sampleGMM(doc, upathModel="/AbstractModel:MixtureModel", upathNewFiducial="/Fiducial:Sampled", n = 1000):
	am = doc.getInstance(upathModel)
	g = gmm._gmmFromAM(am)
	pts = _sampleGMM(g[0], g[1], g[2], n)
	pts = column_stack([pts, 3*ones(pts.shape[0])])
	fid = forceGetPath(doc, upathNewFiducial)
	fid.setAttrib('Style','spheres')
	fid.setPoints(pts)
		

def sampleSF(doc, upathSF="/SpatialField:MixtureModel_sf", upathNewFiducial="/Fiducial:Sampled", n = 1000):
	sf = doc.getInstance(upathSF)
	pts = _sampleSF(sf.getElements("Data")[0].data, n)
	pts = pts.astype(float32)*sf.attrib('Edge')
	pts = pts + array(sf.attrib('Origin'))
	pts = column_stack([pts, 3*ones(pts.shape[0])])
	fid = forceGetPath(doc, upathNewFiducial)
	fid.setAttrib('Style', 'spheres')
	fid.setPoints(pts)



if __name__ == '__main__':
	_test()
