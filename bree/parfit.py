#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-07-06.

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
import bree, os, time
import mien.parsers.fileIO as io
from mien.dsp.nmpml import matlabCall
import scipy.optimize as opt
from numpy import *
from bree.matlabService import mservicecall, mserviceclose

moddir = os.path.split(bree.__file__)[0]
tffn = os.path.join(moddir, 'hairTFs.mdat')
mfiledir = os.path.join(moddir, 'matlab')

# % freqs  = vector of frequencies to test
# % R  = value of the model constant "R" (viscous resistance) to test 
# % S  = value of the model contsant "S" (spring constant) to test
# % L  = length of the hair to model
# % D  = diameter of the cercus to model
# % P  = resting hair position

# matlabCall(ds, mfile='testmien', args={} ,dpath='/', recurse=True, newpath='/', safe=True, mfiledir='')

def _getExpTf(name):
	doc = io.read(tffn)
	tf = doc.getElements("Data", name)[0]
	return tf

	

def matchTF(ds, tfname='090522_4', R=0.0, S=0.0, newpath='/'):
	tf = _getExpTf(tfname)
	freqs = tf.getData()[:,0:1]
	L = tf.attrib('length')/1.0e6
	D = tf.attrib('cercaldiam')/1.0e6
	P = tf.attrib('restangle')
	if not R:
		R = 2.88e-14*(L*1.e3)**(2.77)
	if not S:
		S = 1.9e-11*(L*1.e3)**(1.67)
	h = {'SampleType':'function', 'R':R, 'L':L, 'D':D, 'P':P, 'R':R, 'S':S}	
	ds.createSubData(newpath, freqs, h, True)
	ds = ds.getSubData(newpath)
	new = mservicecall(ds)
	ds.mirror(new)
	n = ds.getSubData(tf.name())
	if n:
		n.sever()
	ds.newElement(tf)


def _e_eucd(exp, calc, phaseWt):	
	err = calc[:,1] - exp[:,1] + phaseWt*(calc[:,2]-exp[:,2])
	return err
	
def _e_extr(exp, calc, phaseWt):
	exp = exp[:,1]
	calc = calc[:,1]
	amc = calc.argmax()
	emc = exp.argmax()
	err = [calc[0] - exp[0], calc[-1] - exp[-1], calc[amc] - exp[emc], amc - emc]
	return err

	
def _e_norm(exp, calc, phaseWt):
	exp = exp[:,1]
	exp = exp / exp.max()
	calc = calc[:,1]
	calc = calc/calc.max()
	err = calc - exp 
	return err
	

ERRFUNC ={
	'eucd':_e_eucd,
	'extrema':_e_extr,
	'normed':_e_norm,

}

def _tfresid(pars, tfname, ds, phaseWt, efunc):
	R, S = pars
	matchTF(ds, tfname, R, S, '/')
	exp = ds.getSubData(tfname).getData()
	calc = ds.getData()
	err = ERRFUNC[efunc](exp, calc, phaseWt)
	return err

def _pregress(ds, tfname, phaseWt):
	tf = _getExpTf(tfname)
	L = tf.attrib('length')/1.0e6
	R = 2.88e-14*(L*1.e3)**(2.77)
	S = 1.9e-11*(L*1.e3)**(1.67)
	res = opt.leastsq(_tfresid, (R, S), (tfname, ds, phaseWt))
	if res[1]>4:
		raise StandardError("No Solution")
	return res[0]


	
def leastSQfit(ds, tfname='090522_4', phaseWt=1.0):
	res =  _pregress(ds, tfname, phaseWt)
	R, S = res
	matchTF(ds, tfname, R, S, '/')
	print R, S
	

def closeMatlabService(ds):
	mserviceclose(ds)

def getRSerror(ds, tfname='090522_4', R=0.0, S=0.0, phaseWt=.2, efunc='eucd'):
	'''r and s are exponents. True values are 1eR, and 1eS'''
	R = 10.0**R
	S = 10.0**S 
	matchTF(ds, tfname, R, S, '/')
	exp = ds.getSubData(tfname).getData()
	calc = ds.getData()
	err = ERRFUNC[efunc](exp, calc, phaseWt)
	err = (err**2).sum()
	ds.setAttrib('error', err)
	


def fakeRSerror(ds, tfname='090522_4', R=0.0, S=0.0, phaseWt=.2):
	'''r and s are exponents. True values are 1eR, and 1eS'''
	print R, S
	R = 10.0**R
	S = 10.0**S 
	err = 2*R+.5*S
	print R, S, err
	ds.setAttrib('error', err)


def gridSearch(ds, tfname='090522_4', minR=-15, minS=-12, maxR=-14, maxS=-10.6, stepR=.05, stepS=.05, phaseWt=0, efunc="eucd"):
	r = arange(minR, maxR, stepR)
	s = arange(minS, maxS, stepS)
	for R in r:
		for S in s:
			getRSerror(ds, tfname, R, S, phaseWt, efunc)
			ds.createSubData("%G_%G" % (R, S), ds.getData(), ds.header(), True)
			err = ds.attrib('error')
			amp = ds.getData()[:,1]
			print R, S, err
			if err < 5:
				print amp.max(), amp.argmax()
			elif amp.argmax()<25:
				print amp.argmax(), amp.max()


def errorPlot(ds):
	doc = ds.xpath(True)[0]
	funcs = doc.getElements('Data', {'SampleType':'function'})
	errd = {}
	rv = set([])
	sv = set([])
	for f in funcs:
		R = f.attrib("R")
		S = f.attrib("S")
		err = f.attrib('error')
		if all([R, S, err]):
			errd[(R,S)]=err
			rv.add(R)
			sv.add(S)
	rv = sorted(rv)
	sv = sorted(sv)
	grid = zeros([len(rv), len(sv)])
	for i, r in enumerate(rv):
		for j, s in enumerate(sv):
			try:
				grid[i, j] = errd[(r,s)]
			except:
				pass
	print grid
	ds.createSubData('/gridplot', grid, {"SampleType":"timeseries", "SamplesPerSecond":1.0}, True)
		
	

def makeErrorPlotGrid(ds, norm=0):
	doc = ds.xpath(True)[0]
	funcs = doc.getElements('Data', {'SampleType':'function'})
	gain = {}
	mh = 0
	mw = 0
	rv = set([])
	sv = set([])
	for f in funcs:
		R = f.attrib("R")
		S = f.attrib("S")
		err = f.attrib('error')
		if all([R, S, err]):
			f.data=f.data[:,:2]
			f.data[:,1]-=f.data[:,1].min()
			f.setAttrib("style", "line")
			gain[(R,S)]=f
			mh = max(mh, f.data[:,1].max())
			mw = max(mw, f.data[:,0].max())
			rv.add(R)
			sv.add(S)
	rv = sorted(rv)
	sv = sorted(sv)	
	mw+=1
	if norm:
		mh = norm+1
	else:
		mh+=1
	for i, r in enumerate(rv):
		for j, s in enumerate(sv):
			try:
				f = gain[(r,s)]
			except:
				continue
			if norm:
				f.data[:,1] = norm*f.data[:,1]/f.data[:,1].max()
			xoff = i*mw
			yoff = j*mh
			f.data[:,0]+=xoff
			f.data[:,1]+=yoff
	



