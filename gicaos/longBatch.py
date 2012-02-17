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

#convert video to timeseries
#actually, use longMovieToAngle for this

import sys, os
import mien.blocks
import gicmext.calibration as cal
from mien.dsp.subdata import combine
import gicaos.fttools as ftt
from numpy import *
import mien.parsers.fileIO as io

MFCHAN=2

def _cleanupTFV(a):
	b = zeros((a.shape[1], 6))
	b[:,:3] = a[0]
	b[:, 3:] = a[1]
	mamp1 = b[:,1].mean()
	mamp2 = b[:,4].mean()
	vals = {}
	for i in range(1, b.shape[0]):
		#print " ".join(map(str, b[i]))
		if abs(b[i,0] - b[i, 3]) > .5:
			print "abort line freq"
			continue
		if b[i,1]< mamp1*.2 or b[i,4]<mamp2*.2:
			#print "abort line amp"
			#print mamp1, b[i,1], mamp2, b[i,4]
			continue
		if abs(b[i,0] -b[i-1,0])>.5:
			#print "abort line freq"
			continue
		f = int(round(b[i,0]))
		if not f in vals:
			vals[f]=[]
		phase = (b[i,5] -b[i,2]) % (2*pi)
		vals[f].append((b[i,1]/b[i,4], phase ))
	tf = []
	for k in sorted(vals):
		if len(vals[k])>1:
			tfv = array(vals[k])
			tfv = tfv.mean(0)
		tf.append((k, tfv[0], tfv[1]))
	return array(tf)
	

def getTF(vidfn, mffn):
	mff=os.path.join(os.path.split(ftt.__file__)[0], 'MicroflownCalib.ncl')
	doc = io.read(mffn)
	mfds = doc.getElements('Data')[0]
	mfds.delChans([z for z in range(mfds.data.shape[1]) if not z==MFCHAN])
	fd = io.read(mff)
	fd = fd.getElements('Data')[0]
	mfds.newElement(fd)
	fd.setName('filter')
	cal.applyFilterToSignal(mfds, dpathSig='/', dpathFilt="/filter", channel=0, newpath='velocity')
	vdoc = io.read(vidfn)
	vds = vdoc.getElements('Data')[0]
	vds.newElement(mfds.getSubData('velocity'))
	combine(vds, '/', '/velocity', False)
	ftt.scanForTFValues(vds)
	tfv = vds.getSubData('/ftvals')
	tf = _cleanupTFV(tfv.getData())
	f=open('trans_func.txt', 'w')
	for i in range(tf.shape[0]):
		f.write(" ".join(map(str, tf[i]))+"\n")
	f.close()
	

if __name__ == '__main__':
	getTF(sys.argv[1], sys.argv[2])
#convert MF voltage to velocity
#load and resampled those data
#calculate silding FT for both data sets
#extract measurements from sliding FT
#average repeated measurements and convert to TF
#save to file

