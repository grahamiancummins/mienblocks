#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-04-09.

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
'''Functions for preprocessing data from non-neuroscience sources '''

import numpy as N
from mien.datafiles.dataproc import getSelection, combineData
from mien.math.array import uniformsample

def useExplicitX(ds, dpath='/', chanX=0):
	ds = ds.getSubData(dpath)
	dat = ds.getData()
	head = ds.header()
	chan = dat[:,chanX]
	steps = chan[1:]-chan[:-1]
	smin= steps.min()
	sdev = (steps.max()-smin)/smin
	nonmono=False
	if smin < 0:
		print("data are not monotonic increasing. Sorting")
		nonmono = True		
		smin = abs(steps).min()
		sdev = abs(sdev)
	head["StartTime"] = chan.min()
	head['Labels']=[head['Labels'][i] for i in range(dat.shape[1]) if not i==chanX ]
	if smin <= 0:
		print("Data do not represent a function on the indicated X variable. Aborting.")
		return 
	head["SamplesPerSecond"] = 1.0/smin	
	if sdev < .001:
		if nonmono:
			dat = dat[N.arange(dat.shape[0]-1, -1, -1), :]
		print("Data are uniformly sampled")
		dat = dat[:, [x for x in range(dat.shape[1]) if not x==chanX]]
	else:
		print("Data are not uniformly sampled. Interpolating")
		if chanX!=0:
			ind = [chanX] + [x for x in range(dat.shape[1]) if not x==chanX]
			dat = dat[:,ind]
		dat = uniformsample(dat, smin)
	ds.datinit(dat, head)
	
def combineWithResample(ds, dpathAddTo="/", dpathAdd="/new", delete=True):
	'''Add data in dpathAdd to the element dpathAddTo. If delete is True, destroy the source element.
SWITCHVALUES(delete)=[True, False]
	'''
	d1 = ds.getSubData(dpathAddTo)
	d2 = ds.getSubData(dpathAdd)
	combineData(d1, d2)

	
	
	