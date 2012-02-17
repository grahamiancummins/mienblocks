#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-07-03.

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
import sys, os, re
import mien.blocks
from numpy import *
import mien.parsers.fileIO as io
import mien.nmpml.data as miendata
import mien.parsers.nmpml as nmpml
from mien.datafiles.dataset import resample, crop

EXCLUDE = ('imp', 'ps', 'wn')

# def getMatch(f, l):
#	'''version for Bree's data and spring 2009 data'''
# 	nn = f + ".bin"
# 	if nn in l:
# 		return nn
# 	try:
# 		i = int(f)
# 	except:
# 		return None
# 	for fn in l:
# 		bn = os.path.splitext(fn)[0]
# 		try:
# 			i2 = int(bn)
# 			if i2 == i:
# 				return fn
# 		except:
# 			pass
# 	return None
# 

def getMatch(f, l):
	ob=re.compile('AOS')
	p=ob.search(f)
	m=p.span()
	nn = f[0:m[0]] + f[m[1]:] + ".bin"
	# print nn
	if nn in l:
		return nn
	return None
	
def cropMicroflown(dat,tch=4):
	'''Removes pretrigger time.'''
	trig = dat.getData()[:,tch]
	ind = argmax(trig[1:] - trig[:-1])+1
	crop(dat,[ind,':'])
	return dat


def knit(dname):
	if os.path.isfile(os.path.join(dname, 'concat_ex.mdat')):
		os.unlink(os.path.join(dname, 'concat_ex.mdat'))
	if os.path.isfile(os.path.join(dname, 'concat.mdat')):
		os.unlink(os.path.join(dname, 'concat.mdat'))		
	print("=== processing directory %s ===" % dname)
	dat_all = []
	dat_ex = []
	mf_allch = []
	mdat = [f for f in os.listdir(dname) if f.endswith("_ts.mdat")]
	date = mdat[0][:10]
	if all([f[:10] == date for f in mdat]):
		if os.path.isfile(os.path.join(dname, date+'concat_ex.mdat')):
			os.unlink(os.path.join(dname, date+'concat_ex.mdat'))
		if os.path.isfile(os.path.join(dname, date+'concat.mdat')):
			os.unlink(os.path.join(dname, date+'concat.mdat'))		
	else:
		print "Multiple experiments present -- aborting. Put separate experiments in different folders."
		return None	
	bin = [f for f in os.listdir(dname) if f.endswith(".bin")]
	for f in mdat:
		ff1=os.path.join(dname, f)
		f2 = getMatch(f[:-8], bin)
		if not f2:
			print("can't match %s" % (f,))
			continue
		ff2 = os.path.join(dname, f2)
		print("adding file pair %s, %s" % (f, f2))
		dat1 = io.read(ff1).getElements("Data")[0]
		dat2 = io.read(ff2).getElements("Data")[0]
		dat2 = cropMicroflown(dat2)
		# crpd = dat2.getData()
		# ds = miendata.newData(crpd, {'SampleType':'timeseries', 'SamplesPerSecond':10000})
		# doc = nmpml.blankDocument()
		# doc.newElement(ds)
		# io.write(doc, os.path.join(dname, 'crpd.mdat'))
		resample(dat1, 1000)
		resample(dat2, 1000)
		dat1 = dat1.getData()
		dat2 = dat2.getData()[:,2]
		if dat1.shape[0] < dat2.shape[0]:
			dat2 = dat2[:dat1.shape[0]]
		elif dat1.shape[0] > dat2.shape[0]:
			dat1 = dat1[:dat2.shape[0]]
		dat1 -=  dat1.mean()
		dat2 -= dat2.mean()
		dd = column_stack([dat1, dat2])
		dat_all.append(dd)
		if not any([q in f.lower() for q in EXCLUDE]):
			dat_ex.append(dd)
	dat = row_stack(dat_all)
	ds = miendata.newData(dat, {'SampleType':'timeseries', 'SamplesPerSecond':1000})
	doc = nmpml.blankDocument()
	doc.newElement(ds)
	io.write(doc, os.path.join(dname, date+'concat.mdat'))
	if len(dat_ex) < len(dat_all):
		dat = row_stack(dat_ex)
		ds.datinit(dat)
		io.write(doc, os.path.join(dname, date+'concat_ex.mdat'))
	

if __name__ == '__main__':
	for dname in sys.argv[1:]:
		knit(dname)
