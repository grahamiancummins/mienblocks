#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-06-19.

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
import  gicmext.calibration as cal
from numpy import *

def scanForTFValues(ds, window=.1, minFreq=5.0, maxFreq = 500.0):
	fs = ds.fs()
	window = int(round(window*fs))
	dat = ds.getData()
	out = []
	for c in range(dat.shape[1]):
		out.append([])
		d = dat[:,c]
		# print "Channel %i" % c
		i = 0 
		while i < d.shape[0]:
			dw = d[i:i+window]
			dw = dw - dw.mean()
			f, a, p = cal._quickFFT(dw, fs)
			ind = logical_and( f>=minFreq, f<=maxFreq)
			f=f[ind]
			a=a[ind]
			p=p[ind]
			mav = argmax(a)
			f = f[mav]
			a = a[mav]
			p=p[mav]
			# print "Window %i: %G %G %G" % (i, f, a, p)
			out[-1].append((f, a, p))
			i+=window
	out = array(out)
	ds.createSubData('/ftvals', out, {"SampleType":'generic'}, True )


			
def concat(ds):
	dats = ds.getElements("Data", depth=1)
	dat =ds.getData()
	rem = dat.shape[0] % ds.fs()
	if rem:
		dat = dat[:-rem]
	dl = [dat]
	for d in dats:
		dat = d.getData()
		rem = dat.shape[0] % d.fs()
		if rem:
			dat = dat[:-rem]
		dl.append(dat)
		d.sever()
	dat = row_stack(dl)
	ds.datinit(dat)
				
	
