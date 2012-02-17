#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2010-01-17.

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


import sys, os, re
import mien.blocks
from numpy import *
import mien.parsers.fileIO as io
import mien.nmpml.data as miendata
import mien.parsers.nmpml as nmpml
from mien.datafiles.dataset import resample, crop
import gicaos.fttools as ftt
import gicmext.calibration as cal
import gicaos.constructTransferFunctions as ctf

SIGFS = 1000
TRIGCHAN = 4
MFCHAN = 2

MFF=os.path.join(os.path.split(ftt.__file__)[0], 'MicroflownCalib.ncl')
MFF= io.read(MFF)
MFF= MFF.getElements('Data')[0]
MFF= cal._filterResample(MFF.data[:,0], MFF.fs(), SIGFS)  

def smooth(a,fs):
	#find clicks
	ad = a[1:]-a[:-1]
	adm = ad.mean()
	adv = ad.std()
	cd = nonzero(abs(ad) > abs(adm) + 4*adv)[0] # FREE PARAMETER HERE
	# each 1 time point click is associated with 2 entries in cd, k and k+1
	# each 2 pt time click is associated with 2 entries in cd, k and k+2
	# replace clicks with averages 
	c=0;
	clicks=0;
	for k in cd:
		c=c+1
		if (k== cd[0]) or ( (k < cd[-1]) and (k-cd[c-2] > 2) and (cd[c] - k ==1) ) or ( (k == cd[-1]) and (k-cd[c-2] > 2) ): 
			a[k+1] = (a[k] + a[k+2])/2.
			clicks=clicks+1
		elif ( (k < cd[-1]) and (cd[c] - k ==2) ):
			a[k+1] = (a[k-1] + a[k+3])/2.
			clicks=clicks+1
		elif (k-cd[c-2] == 2):
			a[k] = (a[k-2] + a[k+2])/2.
			clicks=clicks+1			
		else:
			pass
	print "%i clicks" % (clicks,)
	return a
	

def smoothphase(d):
	while d[0] > pi:
		d[0] = d[0] - 2*pi
	while d[0] < -pi:
		d[0] = d[0] + 2*pi
	for i in range(1, d.shape[0]):
		df = d[i] - d[i-1]
		while abs(df) > pi: 
			if df > 0:
				d[i] = d[i]-2*pi
			elif df < 0:
				d[i] = d[i] + 2*pi
			df = d[i] - d[i-1]
	return d



def getDataPairs(dname):
	ts = [f for f in os.listdir(dname) if f.endswith("_ts.mdat")]
	stim = [f for f in os.listdir(dname) if f.endswith(".bin")]
	expts = {}
	for n in stim:
		pref = n[:10]
		if not pref in expts:
			expts[pref]=[]
		lab = n[10:-4]
		m = [f for f in ts if f.startswith(pref+"AOS") and f[13:-8] == lab in f]
		if len(m)==1:
			if lab.endswith('ala') or (lab.endswith('a') and not lab.endswith('la')):
				if not pref+"A" in expts:
					expts[pref+"A"]=[]
				expts[pref+"A"].append((n,m[0]))
			else:
				expts[pref].append((n, m[0]))
	return expts


def assemble(filepairs, dname):
	dat_all = []
	for fp in filepairs:
		bfn = os.path.join(dname, fp[0])
		afn = os.path.join(dname, fp[1])
		dbin = io.read(bfn).getElements("Data")[0]
		daos = io.read(afn).getElements("Data")[0]
		trig= dbin.getData()[:,TRIGCHAN]
		ind = argmax(trig[1:] - trig[:-1])+1
		mfd = dbin.getData()[ind:,MFCHAN]
		dbin.datinit(mfd, {"SampleType":"timeseries", "StartTime":0.0, 
			"Labels":["MicroFlownVoltage"], "SamplesPerSecond":dbin.fs()})
		tsd = smooth(daos.getData(),daos.attrib("SamplesPerSecond"))  #remove clicks BEFORE resampling
		daos.datinit(tsd, {"SampleType":"timeseries", "StartTime":0.0, 
			"Labels":["HairPosition"], "SamplesPerSecond":daos.fs()})
		resample(dbin, SIGFS)
		resample(daos, SIGFS)
		dat2 = dbin.getData()
		dat1 = daos.getData()
		if dat1.shape[0] < dat2.shape[0]:
			dat2 = dat2[:dat1.shape[0]]
		elif dat1.shape[0] > dat2.shape[0]:
			dat1 = dat1[:dat2.shape[0]]
		dat1 -=  dat1.mean()
		dat2 -= dat2.mean()
		dd = column_stack([dat1, dat2])
		dat_all.append(dd)
	dat = row_stack(dat_all)
	ds = miendata.newData(dat, {'SampleType':'timeseries', 'SamplesPerSecond':SIGFS,
		'StartTime':0.0, "Labels":['HairPosition', 'MicroFlownVoltage']})
	return ds

def getSinTF(dname):
	dp = getDataPairs(dname)
	for exp in dp:
		dpl = dp[exp]
		print "Analyzing Sin Data for experiment %s" % exp
		dpl = [p for p in dpl if p[0][10]=='S' and not p[0][11]=='T']
		ds = assemble(dpl, dname)
		dat = ds.getData()
		dat[:,1] = cal._applyfilter(dat[:,1], MFF)
		# dat[:,0] = smooth(dat[:,0]) #This now occurs in assemble BEFORE resampling
		ds.datinit(dat, {"SampleType":"timeseries", "StartTime":0.0, 
			"Labels":["HairPosition","MicroFlownVelocity"], "SamplesPerSecond":SIGFS})
		nfn = '%s_compositSinData.mdat' % exp
		io.write(ds, nfn, newdoc=True)
		tfds = ctf.tffmax(ds, False)
		if not tfds:
			continue
		tfds.data[:,2]+=pi
		tfds.data[:,2] = smoothphase(tfds.data[:,2])
		io.write(tfds, "%s_SinTF_Function.mdat" % exp, newdoc=True)
		tf = tfds.getData()
		tf = row_stack( [array([[0,0,0]]), tf, array([[250,tf[-1,1],tf[-1,2]]])])
		tf = ctf.uniformsample(tf, 1.0)
		tfds = miendata.newData(tf, {'Name':exp+"SinTF", 'SampleType':'timeseries', 'SamplesPerSecond':1.0, "StartTime":0})
		io.write(tfds, "%s_SinTF_ResampledTimeseries.mdat" % exp, newdoc=True) 
		
def getWNTF(dname):
	dp = getDataPairs(dname)
	for exp in dp:
		dpl = dp[exp]
		print "Analyzing all data (using FT) for experiment %s" % exp
		ds = assemble(dpl, dname)
		dat = ds.getData()
		dat[:,1] = cal._applyfilter(dat[:,1], MFF)
		# dat[:,0] = smooth(dat[:,0]) #This now occurs in assemble BEFORE resampling
		ds.datinit(dat, {"SampleType":"timeseries", "StartTime":0.0, 
			"Labels":["HairPosition","MicroFlownVelocity"], "SamplesPerSecond":SIGFS})
		nfn = '%s_compositData.mdat' % exp
		io.write(ds, nfn, newdoc=True)
		tfds = ctf.tf1ft(ds)
		if not tfds:
			continue
		tfds.data[:,1]+=pi
		tfds.data[:,1] = smoothphase(tfds.data[:,1])
		io.write(tfds, "%s_FTTF.mdat" % exp, newdoc=True)
			
		
if __name__ == '__main__':
	dt = sys.argv[1]
	getSinTF(dt)
	getWNTF(dt)