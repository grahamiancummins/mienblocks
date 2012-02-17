#!/usr/bin/env python

## Copyright (C) 2005-2006 Graham I Cummins
## This program is free software; you can redistribute it and/or modify it under 
## the terms of the GNU General Public License as published by the Free Software 
## Foundation; either version 2 of the License, or (at your option) any later version.
## 
## This program is distributed in the hope that it will be useful, but WITHOUT ANY 
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
## PARTICULAR PURPOSE. See the GNU General Public License for more details.
## 
## You should have received a copy of the GNU General Public License along with 
## this program; if not, write to the Free Software Foundation, Inc., 59 Temple 
## Place, Suite 330, Boston, MA 02111-1307 USA
## 

from mien.datafiles.dataset import *
from numpy.random import randint
import sysChar as sc
from mien.math.sigtools import bandpass
import calibration as cal

def _evalGaus(pt, mea, cov):
	norm = 1.0 / ( sqrt(linalg.det(cov))*(2*pi)**(mean.shape[0]/2.0))
	icov = linalg.inv(cov)
	x = pt - mean
	out = -.5*dot(dot(x, icov), x)
	out = norm*exp(out)
	return out


def make1ptGaussModel(ds, dpathDist="/", dpathModel="/gm", length=20, offset=4, mu=1.0, sigma=0.1):
	'''Make a multivariate gaussian model with dimension length. This model is similar to a spherical model with mean = mean of the data in dpathDist and covariance = I*var(dpathDist), except that the value of mean[length-offset] is mu, and cov[length-offset,length-offset] is sigma. The model is stored as a lengthX(length+1) array at dpathModel.'''
	dat = ds.getSubData(dpathDist).getData()
	bvar = dat.var()
	bmu = dat.mean()
	gm = zeros((length, length + 1))
	gm[:,0] = bmu
	gm[-offset,0] = mu
	for i in range(length):
		if i == length - offset:
			gm[i, i+1] = sigma
		else:
			gm[i,i+1] = bvar
	h = {"SampleType":'gaussian'}
	ds.createSubData(dpathModel, gm, h, True)
		

def slidingGaussLikelihood(ds, dpathInput="/", dpathModel="/gm", dpathOutput="/gl"):
	'''dpathModel is a multivariate Gaussian, represented as an NxN+1 array (first channel is the mean, remaining N channels are the cov matrix). For each offset in dpathInput, calculate the likelihood that the previous N samples were drawn from this Gaussian. Store the resulting sequence of likelihoods in dpathOutput.'''
	gm = ds.getSubData(dpathModel).getData()
	mea = gm[:,0].ravel()
	N = mea.shape[0]
	cov = gm[:,1:]
	icov = linalg.inv(cov)
	inp = ds.getSubData(dpathInput)
	idat = inp.getData()[:,0].ravel()
	odat = zeros_like(idat)
	norm = 1.0 / ( sqrt(linalg.det(cov))*(2*pi)**(mea.shape[0]/2.0))
	for i in range(N,idat.shape[0]):
		x = idat[i-N:i] - mea
		odat[i] = -.5*dot(dot(x, icov), x)
	ds.createSubData(dpathOutput, odat, inp.header(), True)
	

def onePtWithLag(ds, dpathInput="/", dpathOutput="/gl", offset=4, mu=1.0, sigma=0.1):
	inp = ds.getSubData(dpathInput)
	idat = inp.getData()[:,0].ravel()
	odat = zeros_like(idat)
	for i in range(offset,idat.shape[0]):
		v = idat[i-offset] - mu
		odat[i] = -.5*v**2/sigma
	ds.createSubData(dpathOutput, odat, inp.header(), True)
		

def twoPtsimilar(ds, dpathInput="/", dpathOutput="/gl", offset=4, mu=1.0, sigma=0.1):
	inp = ds.getSubData(dpathInput)
	idat = inp.getData()[:,0].ravel()
	odat = zeros_like(idat)
	for i in range(offset,idat.shape[0]):
		v = idat[i-offset] - mu
		odat[i] = -.5*v**2/sigma
		v = idat[i] - mu
		odat[i] = odat[i] -.5*v**2/sigma
	ds.createSubData(dpathOutput, odat, inp.header(), True)
	
	
def differencing2Pt(ds, dpathInput="/", dpathOutput="/gl", offset=4):
	inp = ds.getSubData(dpathInput)
	idat = inp.getData()[:,0].ravel()
	odat = zeros_like(idat)
	for i in range(offset,idat.shape[0]):
		v = idat[i] - idat[i-offset]
		odat[i] = v
	ds.createSubData(dpathOutput, odat, inp.header(), True)

def differencing4Pt(ds, dpathInput="/", dpathOutput="/gl", offset=4, separation=8):
	inp = ds.getSubData(dpathInput)
	idat = inp.getData()[:,0].ravel()
	odat = zeros_like(idat)
	for i in range(offset+separation,idat.shape[0]):
		v = idat[i] - idat[i-offset]
		v2 = idat[i-separation] - idat[i-separation-offset]
		odat[i] = v+v2
	ds.createSubData(dpathOutput, odat, inp.header(), True)


def _sfilt(npts):
	#mu = -sin(linspace(0,2*pi, npts))-sin(linspace(pi, 2*pi, npts))
	x = linspace(-1, 1, npts)
	mu = exp(-2*x**2) - exp(-4*abs(x))
	n = random.randn(npts, 200)
	n = .1*n*mu[:,newaxis]
	e = n + mu[:,newaxis]
	sig = cov(n)
	return (mu, sig, e)	
	
def filtMod(ds, dpathInput="/", dpathOutput="/gl", npts = 20):
	inp = ds.getSubData(dpathInput)
	idat = inp.getData()[:,0].ravel()
	odat = zeros_like(idat)
	mu, sig, e = _sfilt(npts)
	ds.createSubData("/model", e, {'SampleType':'ensemble', 'Reps':e.shape[1], 'SamplesPerSecond':1000}, True)
	for i in range(npts,idat.shape[0]):
		v = idat[i-npts:i]
		odat[i] = dot(v, mu)
	ds.createSubData(dpathOutput, odat, inp.header(), True)

def oneDG(ds, dpathInput="/", dpathOutput="/gl", npts = 20):
	inp = ds.getSubData(dpathInput)
	idat = inp.getData()[:,0].ravel()
	odat = zeros_like(idat)
	mu, sig, e = _sfilt(npts)
	sig = diag(sig)
	ds.createSubData("/model", e, {'SampleType':'ensemble', 'Reps':e.shape[1], 'SamplesPerSecond':1000}, True)
	for i in range(npts,idat.shape[0]):
		v = idat[i-npts:i]
		v = v - mu
		v = -.5*v**2/sig
		odat[i] = v.sum()
	ds.createSubData(dpathOutput, odat, inp.header(), True)
	
def nDG(ds, dpathInput="/", dpathOutput="/gl", npts = 20):
	inp = ds.getSubData(dpathInput)
	idat = inp.getData()[:,0].ravel()
	odat = zeros_like(idat)
	mu, sig, e = _sfilt(npts)
	icov = linalg.inv(sig)
	norm = 1.0 / ( sqrt(linalg.det(sig))*(2*pi)**(npts/2.0))
	ds.createSubData("/model", e, {'SampleType':'ensemble', 'Reps':e.shape[1], 'SamplesPerSecond':1000}, True)
	for i in range(npts,idat.shape[0]):
		v = idat[i-npts:i]
		v = v - mu
		odat[i] = -.5*dot(dot(v, icov), v)
	ds.createSubData(dpathOutput, odat, inp.header(), True)
		
	
		