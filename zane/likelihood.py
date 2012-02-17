#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-07-17.

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
import bree.clusters as clust

# def _mod2par(mod):
# 	comp = mod['components']
# 	w = []
# 	m = []
# 	c = []
# 	for co in comp:
# 		w.append(co['prop'])
# 		m.extend(co['mean'])
# 		for l in co['cov']:
# 			c.extend(l)
# 	return (w, m, c)

maxisi = 8

def _splitData(d, bu):  
	n = d.shape[1]
	p = random.permutation(n)
	nt = int(round(n*bu))
	build = d[:,p[:nt]]
	test = d[:,p[nt:]]
	return (build, test)

def _buildStaticModel(dat, mtype):
	mean = dat.mean(1)
	cv = cov(dat)
	if mtype == 'Diag':
		cv = cv*identity(cv.shape[0])
	mod={'components':[{'prop':1.0, 'mean':mean, 'cov':cv}]}
	return mod

def _buildModel(dat, mod):
	if mod.startswith('static'):
		return _buildStaticModel(dat, mod[6:])
	return clust._mmcall(dat, [1], mod, False)

def _covFix(c, rc):
	td = linalg.det(rc)
	cd = linalg.det(c)
	c = c/(cd**(1.0/c.shape[0]))
	c = c * (td**(1.0/c.shape[0]))
	return c
	
def _addMod(s1, s2, d):
	mod = {'components':[]}
	for i in range(len(s1['components'])):
		m1 = s1['components'][i]
		m2 = s2['components'][i]
		comp = {'prop':(m1['prop']+m2['prop'])/2.0 , 'mean':m1['mean']+m2['mean'], 'cov':m1['cov']+m2['cov']}
		comp['cov'] = _covFix(comp['cov'], d['components'][i]['cov'])
		mod['components'].append(comp)
	return mod


def _evalGaus(pt, gaus):
	w = gaus['prop']
	mean = array(gaus['mean'])
	cov = array(gaus['cov'])
	norm = 1.0 / ( sqrt(linalg.det(cov))*(2*pi)**(mean.shape[0]/2.0))
	icov = linalg.inv(cov)
	x = pt - mean
	out = -.5*dot(dot(x, icov), x)
	out = w*norm*exp(out)
	return out

		
def _lkly(data, mod):
	dist = []
	for i in range(data.shape[1]):
		lmdist = []
		for c in mod['components']:
			lmdist.append(_evalGaus(data[:,i], c))
		dist.append(log(add.reduce(lmdist)))
	return add.reduce(dist)

def likelyhood(ds, dpathData="/cell6", dpathSinglet="/rawwaves", buildUsing=.9, modeltype='staticDiag'):
	'''
SWITCHVALUES(modeltype)=['staticDiag', 'staticFull', 'Gaussian_p_L_I', 'Gaussian_p_L_B', 'Gaussian_p_L_C']	
	'''
	dat = ds.getSubData(dpathData)
	isi = dat.attrib('isi')
	dat = dat.getData()
	sing = ds.getSubData(dpathSinglet).getData()
	build, test = _splitData(dat, buildUsing)
	dmod = _buildModel(build, modeltype)
	smod1 = _buildModel(sing[8:8+dat.shape[0]], modeltype)
	smod2 = _buildModel(sing[8-isi:8-isi+dat.shape[0]], modeltype)
	smod = _addMod(smod1, smod2, dmod)
	dl = _lkly(test, dmod)
	sl = _lkly(test, smod)
	print "Likelihood doublet data under doublet model: %G" % (dl,)
	print "Likelihood doublet data under synthetic model: %G" % (sl, ) 
	print "Log likelihood ratio: %G" % (dl - sl, )
	

def allLkL(ds, dpathSinglet="/rawwaves", buildUsing=.9, modeltype='staticDiag'):
	'''
SWITCHVALUES(modeltype)=['staticDiag', 'staticFull', 'Gaussian_p_L_I', 'Gaussian_p_L_B', 'Gaussian_p_L_C']	
	'''
	dats = ds.getHierarchy()
	for dpath in dats:
		di = dats[dpath]
		if di.stype() == 'ensemble' and di.attrib('isi'):
			print dpath, di.attrib('isi'), "------------"
			likelyhood(ds, dpath, dpathSinglet, buildUsing, modeltype)
















	
	
	
	
