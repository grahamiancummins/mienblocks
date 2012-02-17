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
import mien.blocks
import mien.parsers.matfile as mf
import mien.parsers.fileIO as io
from gicmext.graphserv import graph, graphts

def read(fname):
	return mf.readmatfile(fname)

def _buildModel(dat, mtype='Full'):
	mean = dat.mean(1)
	cv = cov(dat)
	if mtype == 'Diag':
		cv = cv*identity(cv.shape[0])
	mod={'components':[{'prop':1.0, 'mean':mean, 'cov':cv}]}
	return mod

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
	return array(dist)

	
	

def t(modtype="Full"):
	sdat = transpose(read('rawsingletdata.mat')['rawwaves'])
	ddat = [transpose(x) for x in read('rawdoubletdata.mat')['stimsamps']]
	res = {'llr':[], 'tdat':[], 'mix':[]}
	for i in range(7):
		isi = i+2
		n = int(round(ddat[i].shape[1]*.9))
		dat = ddat[i][:,:n]
		tdat = ddat[i][:,n:]
		dmod = _buildModel(dat)
		smod1 = _buildModel(sdat[8:8+dat.shape[0]])
		smod2 = _buildModel(sdat[8-isi:8-isi+dat.shape[0]])
		smod = _addMod(smod1, smod2, dmod)
		dl = _lkly(tdat, dmod)
		sl = _lkly(tdat, smod)
		print "Likelihood doublet data under doublet model: %G" % (dl.sum(),)
		print "Likelihood doublet data under synthetic model: %G" % (sl.sum(), ) 
		print "Log likelihood ratio: %G" % ((dl - sl).mean(), )
	










