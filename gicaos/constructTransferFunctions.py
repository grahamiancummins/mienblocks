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
from mien.math.array import uniformsample
import mien.nmpml.data as mdat
import mien.parsers.nmpml as nmpml

SIGFS = 1000


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
			#print "abort line freq"
			# print b[i,0]
			continue
		if b[i,1]< mamp1*.05 or b[i,4]<mamp2*.05:
			#print "abort line amp"
			#print mamp1, b[i,1], mamp2, b[i,4]
			continue
		if abs(b[i,0] -b[i-1,0])>.5:
			#print "abort line freq"
			# print(b[i,0])
			continue
		f = int(round(b[i,0]))
		if not f in vals:
			vals[f]=[]
		phase = (b[i,2] -b[i,5]) % (2*pi)
		if phase > pi:
			phase -= 2*pi
		vals[f].append((b[i,1]/b[i,4], phase ))
	tf = []
	for k in sorted(vals):
		tfv = array(vals[k])
		tfv = tfv.mean(0)
		tf.append((k, tfv[0], tfv[1]))
	return array(tf)
	


def tf1ft(ds):
	cal.genericTransferFuncFromWN(ds, dpath="/", chanFrom=1, chanTo=0, newpath="/xfer", useWindowedFFT=True, zfill=1)
	tf = ds.getSubData("/xfer")
	return tf
	
def tffmax(ds, usamp=True):
	ftt.scanForTFValues(ds, window=.2, minFreq=4.9, maxFreq = 250.0)
	tfv = ds.getSubData('/ftvals')
	tf = _cleanupTFV(tfv.getData())
	if tf.shape[0]==0:
		print("No values in fmax tf")
		return None
	if usamp:
		sv = tf[:,0].min()
		tf = uniformsample(tf, 1.0)
		dat = mdat.newData(tf, {'SampleType':'timeseries', 'SamplesPerSecond':1.0, "StartTime":sv})
	else:
		dat = mdat.newData(tf, {'SampleType':'function'})
	return dat
	

tfmethods={'1ft':tf1ft,
		   'fmax':tffmax,
		
			}

def constructTFs(fname):
	if fname.endswith("_tf.mdat"):
		return
	print("====%s====" % fname)
	doc = io.read(fname)
	ds = doc.getElements("Data", depth=1)[0]
	bn=os.path.splitext(fname)[0]
	ndoc = nmpml.blankDocument()
	for mn in tfmethods:
		tf = tfmethods[mn](ds)
		if not tf:
			continue
		tf.setName(mn)
		ndoc.newElement(tf)
	ofn = bn + "_tf.mdat"
	io.write(ndoc, ofn)


def allTFs(fnames):
	ndoc = nmpml.blankDocument()
	for fname in fnames:
		doc = io.read(fname)
		ds = doc.getElements("Data", depth=1)[0]
		bn=os.path.splitext(fname)[0]
		tf = tffmax(ds, False)
		if not tf:
			continue
		if fname.startswith("2009") or fname.startswith("2010"):
			tf.data[:,2]+=pi
			tf.data[:,2] = tf.data[:,2] -  ( 2*pi*(tf.data[:,2]>pi))
		tf.setName(bn)
		ndoc.newElement(tf)
	io.write(ndoc, "allTFs.mdat")
	
def allTFsRs(fnames):
	ndoc = nmpml.blankDocument()
	for fname in fnames:
		doc = io.read(fname)
		ds = doc.getElements("Data", depth=1)[0]
		bn=os.path.splitext(fname)[0]
		tf = tffmax(ds, False)
		if not tf:
			continue
		tf = tf.getData()
		if fname.startswith("2009") or fname.startswith("2010"):
			tf[:,2]+=pi
			tf[:,2] = tf[:,2] -  ( 2*pi*(tf[:,2]>pi))
		tf = row_stack( [array([[0,0,0]]), tf, array([[250,tf[-1,1],tf[-1,2]]])])
		tf = uniformsample(tf, 1.0)
		tf = mdat.newData(tf, {'Name':bn, 'SampleType':'timeseries', 'SamplesPerSecond':1.0, "StartTime":0})
		ndoc.newElement(tf)
	io.write(ndoc, "allTFsResamp.mdat")		
	


if __name__ == '__main__':
	# for fname in sys.argv[1:]:
	# 	constructTFs(fname)
	allTFs(sys.argv[1:])