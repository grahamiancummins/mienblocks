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
from gicmext.graphserv import graph, graphts


def read(fname):
	return mf.readmatfile(fname)

def matgmm2py(d):
	mods = []
	for i in range(d['ncentres']):
		mods.append((d['centres'][i, :],d['covars'][:,:,i]))
	return mods

def evalGaus(pts, mean, cov):
	norm = 1.0 / ( sqrt(linalg.det(cov))*(2*pi)**(mean.shape[0]/2.0))
	icov = linalg.inv(cov)
	g = []
	for i in range(pts.shape[1]):
		x = pts[:,i] - mean
		out = -.5*dot(dot(x, icov), x)
		out = norm*exp(out)
		g.append(out)
	return log(array(g))

def evalMat(fname='testmods.mat'):
	d = read(fname)
	l= [d['llr'], d['tdat'], [matgmm2py(x) for x in d['mix']]]
	z = []
	for i in range(len(l[2])):
		dat = transpose(l[1][i])
		dm  = l[2][i][0]
		sm  = l[2][i][1]
		dl = evalGaus(dat, dm[0], dm[1])
		sl = evalGaus(dat, sm[0], sm[1])
		z.append((dl - sl).mean())
	print l[0]
	print z

def plot(a):
	if len(a.shape) < 2:
		a = a.reshape( (-1, 1))
	graphts(a, 1000)

def buildModel(dat, mtype="Full"):
	mean = dat.mean(1)
	cv = cov(dat)
	if mtype == 'Diag':
		#cv = cv*identity(cv.shape[0])
		cv = dat.var(1)*identity(cv.shape[0])
	mod=(mean, cv)
	return mod

def covFix(c, rc):
	td = linalg.det(rc)
	cd = linalg.det(c)
	c = c/(cd**(1.0/c.shape[0]))
	c = c * (td**(1.0/c.shape[0]))
	return c
	
def addMod(s1, s2, d, cFix):
	mean = s1[0] + s2[0]
	cov = s1[1] + s2[1]
	if cFix:
		cov = covFix(cov, d[1])
	return (mean, cov)

def buildMods(mtype="Full", covFix=False):
	sdat = transpose(read('rawsingletdata.mat')['rawwaves'])
	ddat = [transpose(x) for x in read('rawdoubletdata.mat')['stimsamps']]
	res = {'llr':[], 'tdat':[], 'mix':[]}
	for i in range(7):
		isi = i+2
		n = int(round(ddat[i].shape[1]*.9))
		dat = ddat[i][:,:n]
		tdat = ddat[i][:,n:]
		dmod = buildModel(dat, mtype)
		#zane uses 10 (matlab -> 9 python) as the offset
		#but by measurement it is 8 (python) for low isi
		offset = 9	
		smod1 = buildModel(sdat[offset:offset+dat.shape[0]], mtype,)
		smod2 = buildModel(sdat[offset-isi:offset-isi+dat.shape[0]], mtype)
		smod = addMod(smod1, smod2, dmod, covFix)
		dl = evalGaus(tdat, dmod[0], dmod[1])
		sl = evalGaus(tdat, smod[0], smod[1])
		res['llr'].append((dl - sl).mean())
		res['tdat'].append(tdat)
		res['mix'].append((dmod, smod))
	print res['llr']	
	return res






