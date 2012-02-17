#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2008-08-20.

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
from hexgrid import toHexND, toHexGradND, toHexGrad, toHexP
from mien.math.array import eucd
from navmsc import AdjacentPointRect
from bpmsc import BackpropMSCRect
from hexmsc import HexNavMSC, HexTwoStep
from elasticmsc import ElasticMSC
from pathseek import PathSeeker, TimedPathSeeker
from uncertain import BlurredPathSeeker
from nn import LatencyNN


def _derezBias(a, r, pts):
	cw=a.shape[0]
	scale=int(ceil(cw/float(r)))
	nw=int(ceil(cw/float(scale)))
	ch=a.shape[1]
	nh=int(ceil(ch/float(scale)))
	nb=zeros((nw,nh))
	for i in range(nb.shape[0]):
		for j in range(nb.shape[1]):
			pix=a[i*scale:i*scale+scale,j*scale:j*scale+scale]
			nb[i,j]=pix.mean()
	
	xsc=float(cw)/nw
	ysc=float(ch)/nh
	for di in pts:
		d=di.getData()
		d[:,0]=around(d[:,0]/xsc)
		d[:,1]=around(d[:,1]/ysc)		
	return nb

def setGoals(ds, upathSource, upathTarget):
	sd=ds.getInstance(upathSource)
	n=ds.getSubData('/source')
	if not n:
		n=ds.createSubData('/source')
	n.mirror(sd, True)
	td=ds.getInstance(upathTarget)
	n2=ds.getSubData('/target')
	if not n2:
		n2=ds.createSubData('/target')
	n2.mirror(td, True)

def pathSeeker(ds, closeenough=0, impossible=0, optimism=1.0, debug=False):
	sd=ds.getSubData('/source').getData()
	td=ds.getSubData('/target').getData()
	p=PathSeeker(ds,sd,td, {'closeenough':closeenough, 'impossible':impossible, 'optimism':optimism})
	if debug:
		ds.navalg=p
		return
	s=p.solve()
	if s[0]=='solved':
		d=p.expandPath(s[1][0])
		ds.datinit(d, {"SampleType":'function', 'NavSolution':1})
	else:
		ds.datinit(None, {"SampleType":'group', 'Error':s[0], 'ErrorData':s[1]})

def timeForcedPathSeeker(ds, closeenough=0, impossible=0, optimism=1.0, time=.2,debug=False):
	sd=ds.getSubData('/source').getData()
	td=ds.getSubData('/target').getData()
	p=TimedPathSeeker(ds,sd,td, {'closeenough':closeenough, 'impossible':impossible, 'optimism':optimism,
							'step_time':time})
	if debug:
		ds.navalg=p
		return
	s=p.solve()
	print s
	if s[0]=='solved':
		d=p.expandPath(s[1][0])
		ds.datinit(d, {"SampleType":'function', 'NavSolution':1})
	else:
		ds.datinit(None, {"SampleType":'group', 'Error':s[0], 'ErrorData':s[1]})

def uncertainPathSeeker(ds, closeenough=0, impossible=0, optimism=1.0, time=.2 , anglew=15.0, depth=0.1, bias_optimism=0.0, blur_method='blur', debug=False):
	'''
SWITCHVALUES(blur_method)=['blur', 'occlude', 'fog', 'foggyocclude']
	'''
	sd=ds.getSubData('/source').getData()
	td=ds.getSubData('/target').getData()
	p=BlurredPathSeeker(ds,sd,td, {'closeenough':closeenough, 'impossible':impossible, 'optimism':optimism, 
		'angle_resolution':anglew, 'depth_fade':depth, 'step_time':time, 'bias_optimism':bias_optimism,
		'blur_method':blur_method})
	if debug:
		ds.navalg=p
		return
	s=p.solve()
	if s[0]=='solved':
		d=p.expandPath(s[1][0])
		ds.datinit(d, {"SampleType":'function', 'NavSolution':1})
	else:
		ds.datinit(None, {"SampleType":'group', 'Error':s[0], 'ErrorData':s[1]})

def gridBlur(ds, debug=True):
	if not debug:
		print "this algorithm type is only useful for debugging"
		return
	sd=ds.getSubData('/source').getData()
	from uncertain import TestMe
	p=TestMe(ds, sd)
	ds.navalg=p
	

def _msc(ds, mscclass, layers, biasisarray=True, opts=None, debug=False):
	if not opts:
		opts={}
	if biasisarray:
		bias = ds.getData()
	else:
		bias = ds
	sd=ds.getSubData('/source').getData()
	td=ds.getSubData('/target').getData()
	sd[:,2]=1-sd[:,2]
	td[:,2]=1-td[:,2]
	m=mscclass(layers, sd, td, bias, opts)
	if debug:
		ds.navalg=m
		return
	state=m.run()
	if not state or state[0]=='error':
		print 'run failed', state
		return
	m.describeSolution()
	d=m.getTrajectory()
	ds.datinit(d, {"SampleType":'function', 'NavSolution':1})
	

def simpleAdjacentMSC(ds, layers=20, maxiter=200, kappa=.5, precondition=2, checkdomain=1, gdiscard=0.001, persist=1, rule='kappa', mdiscard=0.0, debug=False):
	opts = {'maxiter':maxiter, 'kappa':kappa, 'precondition':precondition, 'checkdomain':checkdomain,
			'gdiscard':gdiscard, 'persist':persist, 'rule':rule, 'mdiscard':mdiscard}
	_msc(ds, AdjacentPointRect, layers, True, opts, debug)
	
def hexAdjacentMSC(ds, layers=20, maxiter=200, kappa=.5, precondition=2, checkdomain=1, gdiscard=0.001, persist=1, rule='kappa', mdiscard=0.0, debug=False):
	opts = {'maxiter':maxiter, 'kappa':kappa, 'precondition':precondition, 'checkdomain':checkdomain,
			'gdiscard':gdiscard, 'persist':persist, 'rule':rule, 'mdiscard':mdiscard}
	_msc(ds, HexNavMSC, layers, False, opts, debug)

def hex2StepMSC(ds, layers=20, maxiter=200, kappa=.5, precondition=2, checkdomain=1, gdiscard=0.001, persist=1, rule='kappa', mdiscard=0.0, debug=False):
	opts = {'maxiter':maxiter, 'kappa':kappa, 'precondition':precondition, 'checkdomain':checkdomain,
			'gdiscard':gdiscard, 'persist':persist, 'rule':rule, 'mdiscard':mdiscard}
	_msc(ds, HexTwoStep, layers, False, opts, debug)

def simpleBPMSCR(ds, layers=5, maxiter=200, kappa=.5, precondition=2, checkdomain=1, gdiscard=0.001, persist=1, rule='kappa', mdiscard=0.0, maxnbpl=100, layersperpoint=1.0, debug=False):
	opts = {'maxiter':maxiter, 'kappa':kappa, 'precondition':precondition, 'checkdomain':checkdomain,
			'gdiscard':gdiscard, 'persist':persist, 'rule':rule, 'mdiscard':mdiscard, 'maxnbpl':maxnbpl,
			 'layersperpoint':layersperpoint}
	_msc(ds, BackpropMSCRect, layers, True, opts, debug)

def elasticMSC(ds, layers=20, maxiter=200, kappa=.5, precondition=2, checkdomain=1, gdiscard=0.001, persist=1, rule='kappa', mdiscard=0.0, layercost=1.0, debug=False):
	opts = {'maxiter':maxiter, 'kappa':kappa, 'precondition':precondition, 'checkdomain':checkdomain,
			'gdiscard':gdiscard, 'persist':persist, 'rule':rule, 'mdiscard':mdiscard, 'layercost':layercost}
	_msc(ds, ElasticMSC, layers, False, opts, debug)	
	

def latencyNet(ds, debug=False):
	LatencyNN
	sd=ds.getSubData('/source').getData()
	td=ds.getSubData('/target').getData()
	p=LatencyNN(ds,sd,td)
	if debug:
		ds.navalg=p
		return
	s=p.solve()
	doc = ds.xpath(True)[0]
	doc.newElement(s[1])
	
	# if s[0]=='solved':
	# 	d=p.expandPath(s[1])
	# 	ds.datinit(d, {"SampleType":'function', 'NavSolution':1})
	# else:
	# 	ds.datinit(None, {"SampleType":'group', 'Error':s[0], 'ErrorData':s[1]})

	
	
def bogoSolver3000(ds, resolution=20):
	sd=ds.getSubData('/source').getData()
	td=ds.getSubData('/target').getData()
	s=arange(0,resolution+1)/float(resolution)
	s=column_stack([s, s])
	s=s*(td[:,:2]-sd[:,:2])+sd[:,:2]
	ds.datinit(s, {"SampleType":'function', 'NavSolution':1})
		
		
def conditionBias(ds, width=0, hexagonal=False, maptorange=(0, 1), invert=False, power=1.0, minBelow=0.0, maxAbove=1.0):
	'''Calculate an effective bias field to be used by the nav algorithm, from the input raw bias field. All parameters 
may take false values, which results in no action. If specified, the parameters cause the following actions:
width - reduce the resolution of the bias field to the specified number of horizontal pixels.
hexagonal - if width is specified, and this is one of 'hex', 'gradND', or 'grad', then the field is converted to a hexgrid representation. 'hex' weights the edges of the mesh according to the values in the field (generating a non-directed mesh). 'gradND' generates a non-directed mesh using the magnitude of the gradient along each edge. 'grad' generates a directed mesh using the actual projection of the gradient onto each edge. WARNING: nav algorithms usually require strictly positive valued biases, so particularly in the case of 'grad' hexagonalization, subsequent mapping to a strictly positive range is usually required.
maptorange - stretch and shift the bias values such that the min and max values are as specified in this tuple, but proportions are maintained
invert - invert the ordering of values in the field, maintaining current min and max (so values that previously had the min value now have the max value, etc.)
power - raise the field to the indicated exponential power.
minBelow - cut off the field so that all values below this value are set equal to the min value. This happens after maptorange, invert, and power.
maxAbove - like minBelow, but all values greater than this value have the max value. 

SWITCHVALUES(hexagonal)=['no', 'point', 'edge', 'gradND', 'grad']
SWITCHVALUES(invert)=[False, True]
'''	
	bias = ds.getData()
	
	if width:
		if hexagonal and hexagonal!='no':
			bd=ds.getSubData('/base')
			if not bd:
				bd=ds.createSubData('/base')
			bd.datinit(ds.getData(copy=True), ds.header())
			if hexagonal=='grad':
				toHexGrad(ds, width, blanks=-1e20)
			elif hexagonal=='gradND':
				toHexGradND(ds, width, blanks=-1)
			elif hexagonal=='point':
				toHexP(ds, width, blanks=-1)
			else:
				toHexND(ds, width, blanks=-1)
			bias = ds.getData()
		else:
			sdi=ds.getSubData('/source')
			tdi=ds.getSubData('/target')
			bias=_derezBias(bias, width, [sdi, tdi])
	elif hexagonal and not hexagonal=='no':
		print "WARNING: hexagonal mode %s ignored, since width is not specified" % hexagonal
	hexmask=None
	if ds.stype()=='hexgrid':
		blanks=ds.attrib('blanks')
		hexmask=nonzero(bias==blanks)
		bias[hexmask]=bias[bias!=blanks].mean() 			
	if maptorange:
		bias-=bias.min()
		bias=bias*(maptorange[1]-maptorange[0])/bias.max()
		bias+=maptorange[0]
	if invert:
		mv = bias.min()
		bias=-1*bias
		bias=bias+(mv-bias.min())
	if power and power!=1.0:
		bias=bias**power	
	if minBelow:
		bias = where(bias<minBelow, bias.min(), bias)	
	if hexmask!=None:
		bias[hexmask] = blanks
		if maxAbove:
			bias[bias>maxAbove]=blanks
	elif maxAbove:
		bias=where(bias>maxAbove, bias.max(), bias)
		
	ds.datinit(bias)
		
	
	