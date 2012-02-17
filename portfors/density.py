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
from numpy.random import randn
from tempfile import mkdtemp
import os
from mien.parsers.nmpml import createElement
from mien.math.array import combinations
from mien.datafiles.dataset import getSelection


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
		if min(wt)<=0.0:
			print("WARNING: Weight vector must be strictly positive. Switching weighted mode off")
			weighted = False
		else:
			wt = wt/wt.min()
			wt = wt.round().astype(int64)
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
	
		

def _mmcall(data, clusters, model="Gaussian_pk_Lk_Ck", weighted=False, reps=1):
	dn = mkdtemp()
	_writeMixControl(dn, data, clusters, model, weighted)
	curdir = os.getcwd()
	os.chdir(dn)
	#print dn 
	bbic = 0
	for i in range(reps):
		os.system("mixmod control.xem")
		out = open('numericComplete.txt').readlines()
		if data.shape[1]==1:
			mod = _parsemm1d(out)
		else:
			mod = _parsemm(out)
		#open('test.txt', 'w').write("".join(out))
		best = 0
		bic = mod[0]['bic']
		for i in range(1, len(mod)):
			if mod[i]['bic'] < bic:
				best = i
				bic = mod[i]['bic']
		if bic > bbic:
			bmod = mod[best]
			bbic = bic
	os.chdir(curdir)
	os.system('rm -rf %s' % dn)
	return bmod
	
	
def _test(shape=(77,3), clusters = (1,2,3,4,5), model="Gaussian_pk_Lk_Ck", wt=False):
	dat = apply(randn, shape)
	if wt:
		dat[:,-1] = dat[:,-1] - dat[:,-1].min()+.1
	mod = _mmcall(dat, clusters, model, wt, 5)
	print _mod2par(mod)
	return mod

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

def mixtureModel(ds, select=(None, None, None), minCenters=3, maxCenters=10, model="Gaussian_pk_Lk_Ck", name="MixtureModel", runs=5):
	centers = range(minCenters, maxCenters+1)
	dat = getSelection(ds, select)
	mod = _mmcall(dat, centers, model, False, runs)
	doc = ds.getInstance('/')
	try:
		mm = doc.getInstance("/AbstractModel:%s" % name)
		mmb = mm.getInstance("MienBlock:gmm")
		par = mmb.getElements("Parameters", depth=1)[0]
	except:
		mm = createElement("AbstractModel", {"Name":name})
		mmb = createElement('MienBlock', {"Name":"gmm",'Function':'ccbcv.gmm.gmm'})
		par= createElement("Parameters", {})
		mmb.newElement(par)
		mm.newElement(mmb)
		doc.newElement(mm)
		mm.setAttrib('total_weight', 1.0)
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

def gmmToSpatialField(doc, upathAbstract='/AbstractModel:MixtureModel/', npts = 30, minvalue=.01, maxvalue=.1):
	am = doc.getInstance(upathAbstract)
	bb = _getGMMBB(am, minvalue)
	origin = bb[0][:3]
	rang = bb[1][:3] - origin
	edge = rang.max()/npts
	pts = [arange(origin[i], bb[1][i], edge) for i in range(3)]
	pts = combinations(pts)
	ds = createElement("Data", {"Name":'points', "SampleType":"generic"})
	ds.datinit(pts)
	am.run(ds)
	sfs = ds.getSubData('gmmout').getData()
	pts = ((pts-origin)/edge).round().astype(int32)
	md = sfs[:,0].max()
	keep = nonzero(sfs[:,0]>=minvalue*md)[0]
	if keep.shape[0]<pts.shape[0]/2.0:
		pts = pts[keep, :]
		sfs = sfs[keep, :]
		mindex = pts.min(0)
		pts -= mindex
		origin = tuple(array(origin) + edge*mindex)
	maxdex = pts.max(0)+1
	fshape = list(maxdex) + [sfs.shape[1]]
	sfd = zeros(fshape )
	sfd[ pts[:,0], pts[:,1], pts[:,2], : ] = sfs
	sfd[...,0] = maxvalue*sfd[...,0]/md
	if sfd.shape[3] == 1:
		sfd = sfd[...,0]
	name = am.name()+"_sf"
	sf = doc.getElements('SpatialField', name)
	if sf:
		sf[0].sever()
	sf = createElement('SpatialField', {"Name":name})
	ds = createElement('Data', {"Name":"sfd"})
	sfd = sfd*am.attributes.get('total_weight', 1.0)
	ds.datinit(sfd, {"SampleType":"sfield"})
	sf.newElement(ds)
	sf.setAttrib("Origin", origin)
	sf.setAttrib("colormap", 'hot')
	sf.setAttrib("colordimension", 1)
	sf.setAttrib("colorrange", (minvalue, maxvalue))
	sf.setAttrib("mindensity", minvalue)
	sf.setAttrib("Edge", edge)
	doc.newElement(sf)

def scaleSpatialFieldDens(doc, upath='/SpatialField:MixtureModel_sf/', newMax = .5):
	sf = doc.getInstance(upath)
	dat = sf.getData().data

	dat[...,0] = newMax*dat[...,0]/dat[...,0].max()



