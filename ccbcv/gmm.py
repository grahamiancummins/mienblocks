#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-06-18.

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

def _evalGaussMix(dat, weights, means, covs):
	outs = []
	for i, w in enumerate(weights):
		mu = means[i, :]
		sig = covs[i, ...]
		norm = 1.0 / ( sqrt(linalg.det(sig))*(2*pi)**(mu.shape[0]/2.0))
		icov = linalg.inv(sig)
		x = dat - mu
		out = []
		for j in range(x.shape[0]):
			out.append(-.5*dot(dot(x[j], icov), x[j]))
		outs.append(w*norm*exp(array(out)))
		if any(isnan(outs[-1])):
			print 'nan',i
			print out
			print outs[-1]
			print x
			print sig
	return array(outs).sum(0)

def _foldPars(weights, means, covs):
	wts = array(weights)
	ms = reshape(array(means), (wts.shape[0], -1))
	cs = reshape(array(covs), (ms.shape[0], ms.shape[1], ms.shape[1]))
	return (wts, ms, cs)	

def _gmmFromAM(am):
	g = am.elements[0]
	d= g.getArguments()
	return _foldPars(d['weights'], d['means'], d['covs'])

def _gausMargCondFactory(mu, sig, split = 3):
	q = mu.shape[0] - split
	mu1 = mu[split:]
	mu2 = mu[:split]
	c11 = sig[split:, split:]
	c12 = sig[split:, :split]
	c21 = sig[:split, split:]
	c22 = sig[:split, :split]
	norm2 = 1.0 / ( sqrt(linalg.det(c22))*(2*pi)**(mu2.shape[0]/2.0))
	ic22 = linalg.inv(c22)
	def gMC(v):
		x = v - mu2
		marg = -.5*dot(dot(x, ic22), x)
		marg = norm2*exp(marg)	
		mucond = mu1 +  dot(dot(c12, ic22), x)
		ccond = c11 - dot(dot(c12, ic22), c21)
		return (marg, mucond, ccond)
	return gMC

def _gmmCond(dat, weights, means, covs):
	compts = [_gausMargCondFactory(means[i,:], covs[i,...], dat.shape[1]) for i in range(len(weights))]
	out = zeros((dat.shape[0], means.shape[1] - dat.shape[1]+1))
	for i in range(dat.shape[0]):
		ws = zeros(len(compts))
		dists = []
		for j in range(len(compts)):
			ma, muc, cc = compts[j](dat[i])
			ws[j] = ma*weights[j]
			dists.append(muc)
		out[i,0] = ws.sum()	
		mom = (ws[:,newaxis] * array(dists)).sum(0) / out[i,0]
		out[i,1:] = mom
	return out

def gmm(ds, weights=(0,), means=(0,0,0), covs=(1,0,0,0,1,0,0,0,1)):
	(weights, means, covs) = _foldPars(weights, means, covs)
	dat = ds.getData()
	if means.shape[1]>dat.shape[1]:
		out = _gmmCond(dat, weights, means, covs)
	else:
		out = _evalGaussMix(ds.getData(), weights, means, covs)
	ds.createSubData('gmmout', data=out, head={'SampleType':'generic'}, delete=True)

