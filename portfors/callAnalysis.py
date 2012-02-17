#!/usr/bin/env python
# encoding: utf-8

#Created by gic on Tue Oct 19 10:08:26 CDT 2010

# Copyright (C) 2010 Graham I Cummins
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


import mien.parsers.fileIO as io
import mien.parsers.nmpml as nmp
from numpy import *
from mien.datafiles.dataset import resample
import sys, os
from mien.math.array import hist2

conditions = ['NoBIC', 'BIC']

def pytype(s):
	try:
		v = int(s)
	except ValueError:
		try:
			v = float(s)
		except ValueError:
			v = s
	return v

def respByClass(doc):
	''' class tree is:
		condition (NoDrug, Drug)
			Stimuli (Call2HarmDS, Call2HarmDSa, ....)
				Cell ID (1, 2 ...)
					attenuationLevel (60,40 ...)
	'''
	conds = {}	
	stims = {}
	cells = {}
	atten = {}
	data = []
	evts = doc.getElements('Data', {'SampleType':'labeledevents'})
	for e in evts:
		if not e.getTypeRef('Data'):
			#no file-based stimulus
			continue
		cond = e.attrib('Drug', True)
		stim = e.getTypeRef('Data')[0].target().name()
		cell = e.attrib('Cell_ID', True)
		att  = e.attrib('stim0_attenuation')
		if not conds.has_key(cond):
			conds[cond] = []
		if not stims.has_key(stim):
			stims[stim] = []
		if not cells.has_key(cell):
			cells[cell] = []
		if not atten.has_key(att):
			atten[att] = []
		for chan in range(e.attrib('nsweeps')):
			if e.noData():
				et = zeros(0)
			else:
				et = e.data[nonzero(e.data[:,1] == chan)][:,0]
				et = 1000 * ( et/e.fs()  - e.start() )- e.attrib('stim0_delay') 
			data.append(et)
			ln=len(data)-1
			conds[cond].append(ln)
			stims[stim].append(ln)
			cells[cell].append(ln)
			atten[att].append(ln)
	return (conds, stims, cells, atten, data)

def binnedResponses(da, binwidth=1.0, rstart = -20.0, rlen = 200.0):
	nbins = int(round(rlen/binwidth))
	#ntaces = max([len(l) for l in da.flat])
	out = {}
	for k in da:
		evts = da[k]
		z = zeros((nbins, len(evts)))
		for t in range(len(evts)):
			if evts[t].shape[0] > 0:
				z[:,t] = hist2(evts[t], binwidth, rstart, nbins)
		out[k] = z
	return out 

def getresp(d, k):
	''' d is a tuple as returned by respByClass.  K is a tuple one element shorter than d (4, currently), which specifies which elements to select. The return value is a list of arrays of event times. These events correspond to trials with conditions as set in k (drug, stimulus, cell, attenuation). Elements of k may be '*' which indicates that any value of that property matches, or lists, which indicates that any of the explicitly listed values match''' 
	els = set(range(len(d[4])))
	for i,par in enumerate(k):
		if par == '*':
			continue
		elif type(par) == str:
			rs = d[i][par]	
		else:
			rs = set(d[i][par[0]])
			for p in par[1:]:
				rs = rs.union(d[i][p])
		els = els.intersection(rs)
	resp = [d[-1][i] for i in els]
	return resp

def windowIter(doc, stim, condition, binwidth, nbins, includestim):
	pass



commands = {}

if __name__=='__main__':
	fn = sys.argv[1]
	doc = io.read(fn)
	cmd = commands[sys.argv[2]]
	ndoc = cmd(doc, *map(pytype, sys.argv[3:]))
	fn, ext = os.path.splitext(fn)
	nfn = fn+"_%s" % cmd + ext
	io.write(ndoc, nfn)

