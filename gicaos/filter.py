#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-07-05.

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
import sys, os
import mien.blocks
from numpy import *
import mien.parsers.fileIO as io
import gicaos.fttools as ftt
import gicmext.calibration as cal

SIGFS = 1000

def smooth(a):
	cent = a[1:-1]
	lra = (a[:-2] + a[2:])/2
	skew = abs(cent - lra)
	sme = skew.mean()
	sma = skew.max()
	ran = a.std()
	if sma < .5 * a.std():
		print "already smooth"
		return a
	thresh = sme + .6 * (sma - sme)
	sdp = nonzero(skew > thresh)[0]
	print "%i clicks" % (sdp.shape[0],)
	sdp_vals = lra[sdp]
	a[sdp+1] = sdp_vals
	return a
	

def process(doc, filt):
	ds = doc.getElements("Data", depth=1)[0]
	dat = ds.getData()
	dat[:,1] = cal._applyfilter(dat[:,1], filt)
	dat[:,0] = smooth(dat[:,0])
	

if __name__ == '__main__':
	mff=os.path.join(os.path.split(ftt.__file__)[0], 'MicroflownCalib.ncl')
	fd = io.read(mff)
	filt = fd.getElements('Data')[0]
	filt = cal._filterResample(filt.data[:,0], filt.fs(), SIGFS)

	for dname in sys.argv[1:]:	
		dname = dname.strip("/")	
		if os.path.isfile(os.path.join(dname, 'concat_ex.mdat')):
			ifn = os.path.join(dname, 'concat_ex.mdat')
			ofn = dname+"_sin.mdat"
			doc = io.read(ifn)
			print("Handling %s" % ifn)
			process(doc, filt)
			io.write(doc, ofn)
		if os.path.isfile(os.path.join(dname, 'concat.mdat')):
			ifn = os.path.join(dname, 'concat.mdat')
			ofn = dname+"_all.mdat"
			doc = io.read(ifn)
			print("Handling %s" % ifn)
			process(doc, filt)
			io.write(doc, ofn)