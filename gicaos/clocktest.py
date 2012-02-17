#!/usr/bin/env python

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

import sys, struct, getopt, os, re
from numpy import *
import mien.parsers.fileIO as io
import mien.parsers.nmpml as nmp
import mien.nmpml.data as nmpdat
import mien.math.array as mma


def retrieveData(fn,sw):
	'''This function opens a file and returns the data members and sampling rate.'''
	speclist=[(b,sw[b]) for b in ['xmin','xmax','ymin','ymax','nframes'] if sw.has_key(b)]
	if len(speclist) > 0:
		select=dict(speclist)
	else:
		select=None
	if select:
		f=io.read(fn,select=select)
	else:
		f=io.read(fn)
	d=f.getElements('Data')[0]
	p=re.compile("((\w+/\w+)|(\w+))\.raw")
	if p.match(fn):
		fs = 1./d.header()['StackSpacing']
	else:
		try:
			fs=d.header()['SamplesPerSecond']
		except:
			print "File is not a timeseries or image stack. Setting sampling rate to None. May cause problems later..."
			fs = None
	dat = d.getData()
	return dat, fs


def sum_stack(fn,sw):
	'''Measures relative illumination between frames. Sums the values of each frame, divides by the number of pixels, and removes the mean.'''
	dat, fs = retrieveData(fn[0],sw)
	nframes = dat.shape[3]
	print('processing image stack: %ix%i, %i frames ...' % (dat.shape[0], dat.shape[1], nframes))
	s = zeros(nframes)
	for k in arange(nframes):
		s[k]=sum(dat[:,:,0,k])
	numpix = float32(dat.shape[0]*dat.shape[1])
	s = s/numpix
	s -= s.mean()
	if len(s.shape)==2:
		s=s.reshape(-1,)
	h = nmpdat.newHeader(fs=fs)
	nd = nmpdat.newData(s, h)
	doc = nmp.blankDocument()
	doc.newElement(nd)
	if sw.has_key('dir'):
		a = io.write(doc,sw['dir'] + '/' + sw['sum_file'])
	else:	
		a = io.write(doc,sw['sum_file'])
	if a:
		print "%s successfully written." % sw['sum_file']
	else:	
		print "%s failed to write." % sw['sum_file']
	
	return s, fs
		
def event_finder(s,fs,n1=5,n2=8,thresh=0):
	'''Takes a 1D array of spiky data and returns an array of times containing the downward spike of a square wave.  
	Defines highest peak as event in camera data.'''
	if not thresh:
		m=s.max()
		thresh=m/float(n1)
	if len(s.shape)==2 and s.shape[1] == 1:
		s=s.reshape(-1,)
	elif len(s.shape)!=1:
		print "Input must be a 1D array!"
		sys.exit()
	z = array([0],s.dtype)
	a = hstack([s,z])
	#Left difference means large negative slope to detect falling edge.
	df = a[1:]-a[:-1] # I only care about ordering -- I don't need the exact derivative 
	md = df.min()
	thdf = md/float(n2)
	times = []
	indices = []
	for k in arange(len(s)):
		if (s[k] > thresh) and (df[k] < thdf) and (k == 0 or not k-1 in indices):
			times.append(k/float(fs))
			indices.append(k)
	return array(times), indices
	
def near_event_finder(s,fs,thresh=None,stdnum=5,numback=2):
	'''Takes a 1D array of spiky data and returns an array of times containing the initial upward spike.
	Unlike event_finder(), this function tries to catch the earliest frame at which illumination can be 
	detected in camera data. The function is set up to detect the onset of events in the noisy camera data 
	without specifying thresh. For very clean data (like the stimulus generator), specify a threshold thresh.'''
	if len(s.shape)==2 and s.shape[1] == 1:
		s=s.reshape(-1,)
	elif len(s.shape)!=1:
		print "Input must be a 1D array!"
		sys.exit()
	#calculate std of noise level
	rawstd = std(s)
	ind = [k for k in arange(len(s)) if s[k]<rawstd/3]
	noiseSTD = std(s[ind])
	#take a left difference to find rising events
	z = array([0],s.dtype)
	a = hstack([z,s])
	df = a[1:]-a[:-1] # I only care about ordering -- I don't need the exact derivative 
	m=max(s)
	dm=max(df)
	times = []
	indices = []
	for k in arange(len(s)):
		if thresh != None:
			if ((s[k] > thresh) and (df[k] > (s[k]/m)*dm/2) and (k == 0 or not k-1 in indices)):
				times.append(k/float(fs))
				indices.append(k)
		else: 
			if ((s[k] > stdnum*noiseSTD and df[k] > 0) or (s[k] > noiseSTD and df[k] > 0 and s[k+1] > stdnum*noiseSTD)) and (k==0 or not any([j for j in arange(1,numback) if k-j in indices])):
				times.append(k/float(fs))
				indices.append(k)				
	return array(times), indices
	
	
def subfs_event_finder(s,fs,num=3):
	'''Uses weighted average to estimate peak location with sub-window resolution. Peak location is taken to be the center of square pulse signal.'''
	inittimes, initind = event_finder(s,fs)
	s-=min(s)
	slotnum=arange(-num,num+1)
	l = len(s)
	ll = len(slotnum)
	ind=[]
	for k in initind:
		if k == initind[len(initind)-1]:
			slotnum = [slotnum[j] for j in arange(ll) if slotnum[j]+k < l]
		appint = sum(s[slotnum+k])
		d = dot(slotnum,s[slotnum+k])/appint
		ind.append(k + d)
	times = array(ind)/float(fs)
	return times, ind	
				
	
def comp_series(fn,sw):
	'''Compares illumination of movie images to stimulus generator record running the LED.'''
	if 'n' in sw.keys():
		s, fs = retrieveData(fn[0],sw)
	else:
		s, fs = sum_stack(fn,sw)
	if len(s.shape)==2 and s.shape[1] == 1:
		s=s.reshape(-1,)
	b, fsb = retrieveData(fn[1],sw)
	if 'e' in sw.keys():
		es, esind = near_event_finder(s,fs,stdnum=5,numback=6)
		eb, ebind = near_event_finder(b[:,0],fsb,thresh=0.1)
	elif 'f' in sw.keys():
		es, esind = subfs_event_finder(s,fs)
		eb, ebind = subfs_event_finder(b[:,0],fsb,5)		
	else:
		es, esind = event_finder(s,fs)
		eb, ebind = event_finder(b[:,0],fsb,thresh=1)
	df = len(eb) - len(es)
	if df:
		z=zeros(df,s.dtype)
		es=hstack([es,z])
	tdiff = es-eb
	#Start: code to ensure all events are detected
	bb = b[:,0]
	z = zeros_like(bb)
	z[ebind] = 1
	btot = vstack([bb,z]).T
	hb = nmpdat.newHeader(fs=fsb, l=['RawStimulus','Events'])
	ndb = nmpdat.newData(btot, hb)
	docb = nmp.blankDocument()
	docb.newElement(ndb)
	if sw.has_key('dir'):
		a = io.write(docb,sw['dir'] + '/' + sw['stim_file'])
	else:	
		a = io.write(docb,sw['stim_file'])
	if a:
		print "%s successfully written." % sw['stim_file']
	else:	
		print "%s failed to write."  % sw['stim_file']
	zs = zeros_like(s)
	zs[esind] = 1
	stot = vstack([s,zs]).T
	hs = nmpdat.newHeader(fs=fs, l=['CameraSum','Events'])
	nds = nmpdat.newData(stot, hs)
	docs = nmp.blankDocument()
	docs.newElement(nds)
	if sw.has_key('dir'):
		a = io.write(docs,sw['dir'] + '/' + sw['cam_file'])
	else:	
		a = io.write(docs,sw['cam_file'])
	if a:
		print "%s successfully written." % sw['cam_file']
	else:	
		print "%s failed to write." % sw['cam_file']
	#End: code to ensure all events are detected
	tot = vstack([es,eb,tdiff]).T
	h = nmpdat.newHeader(fs=1.0, l=['VideoEvents','StimulusEvents','TimeDifference'])
	nd = nmpdat.newData(tot, h)
	doc = nmp.blankDocument()
	doc.newElement(nd)
	if sw.has_key('dir'):
		a = io.write(doc,sw['dir'] + '/' + sw['comp_file'])
	else:	
		a = io.write(doc,sw['comp_file'])
	if a:
		print "%s successfully written." % sw['comp_file']
	else:	
		print "%s failed to write." % sw['comp_file']
	
def batch_process(fn, switches):
	aosfiles=os.listdir(fn[0])
	fnn=re.compile("\w+\.((raw)|(mien))")
	p=re.compile("\.((raw)|(mien))")
	q=re.compile("\.")
	su=switches['sum_file']
	if not q.search(su):
		su=su+'.mien'
	co=switches['comp_file'] 
	if not q.search(co):
		co=co+'.mien'
	ca=switches['cam_file']  
	if not q.search(ca):
		ca=ca+'.mien'
	st=switches['stim_file'] 
	if not q.search(st):
		st=st+'.mien'
	for f in aosfiles:
		if fnn.match(f):
			print "processing file %s" % f
			switches['sum_file'] = re.split(p,f)[0] + '_' + su
			switches['comp_file'] = re.split(p,f)[0] + '_' + co
			switches['cam_file'] = re.split(p,f)[0] + '_' + ca
			switches['stim_file'] = re.split(p,f)[0] + '_' + st
			mfn=os.path.join(fn[1], os.path.splitext(f)[0]+".bin")
			if os.path.isfile(mfn):
				try:
					comp_series([os.path.join(fn[0], f),mfn], switches)
				except:
					print "error while processing %s" % f
					import traceback
					e= sys.exc_info()
					apply(traceback.print_exception, e)
			else:
				print "No matching bin file. Skipping %s." % f
				
def slip_script(direct = '/Users/bree/rsyncfolder/work/data/clocktest/clocktest4kHz_near_event_finder/'):
	'''mn1 is the minimal offset in tenths of milliseconds between the stimulus and camera response in the first half of the data.
	mn2 is the same for the second half. Hard-coded hack.'''
	firstdiff=[]
	absmin=[]
	actmin=[]
	meanval=[]
	runmean=[]
	standev=[]
	p=re.compile('((\w+_comp_clock)|(\w+_comp_clock\w+))\.mien')
	for f in os.listdir(direct):
		if p.match(f):
			dat, fs = retrieveData(os.path.join(direct, f),{})
			if dat[0,2]*10000 > 15:
				#Cut off first sample of stim data
				newcam=dat[:len(dat)-1,0]
				newstim=dat[1:,1]
				newdiff=newcam-newstim
				dat=vstack([newcam, newstim, newdiff]).T
			firstdiff.append(dat[0,2]*10000)
			a=argmin(abs(dat[:,2]))
			v=dat[a,2]
			absmin.append(abs(v)*10000)
			actmin.append(v*10000)
			ind=nonzero(dat[1:,0])[0]+1
			meanval.append(mean(dat[ind,2])*10000)
			standev.append(std(dat[ind,2])*10000)
			temp=convolve(ones(50),dat[ind,2]*(10000/50),mode='valid').reshape(-1,)
			runmean.append(temp)
	return firstdiff,absmin,actmin,meanval,runmean,standev
	
	
	
'''Usage: 
	clocktest.py [options] fname.raw [fname.bin]

	This module performs data analysis on the clocktest movies.
	
	OPTIONS:
	-h 	-- prints usage
	-n  -- peform only comparison between datafiles. Image file has been transformed into sum_clock.mien already.
	-b  -- perform the whole rigamarole on a group of files. In this case, the fname.raw argument should become 
	 		a directory containing several fname.raw files and likewise there should be a directory with .bin files
			that have matching file names.
	-e  -- use the near_event_finder to locate events in the summed camera data (i.e. locate first moment of 
			illumination instead of peak illumination)
	-f  -- use the subfs_event_finder to locate events in the summed camera data (i.e. locate approximate
			center of signal)
	-s  -- takes no arguments. Is a hard-coded script for looking at possible slippage.
	--dir  out  -- save output files in directory ./out/  Default is current directory.
	--sum_file fname  -- specifies the file name for saving the summed image data. 
					Default is "sum_clock.mien".
	--comp_file fname  -- specifies the file name for saving the comparison of summed image data to DataStreamer
	 				output. Default is "comp_clock.mien".
	--cam_file fname  -- specifies file name for saving detected events in the summed image data.
						Default is "camCheckEvents.mien".
	--stim_file fname  -- specifies file name for saving detected events in the stimulus data.
						Default is "stimCheckEvents.mien".
	*Note* for -b option: fname will be appended to the existing file name. For example, --sum_file sum.mien AOS1.raw as input
	will be saved as AOS1_sum.mien 
	
	Options to be able to open long files that exceed memory limits. 
	--nframes # 	-- finish processing video after nframes 
	--xmin # 	-- specify the bounding box of the region of interest
	--xmax #   
	--ymin #   
	--ymax #   
	Since this is a synchronization test, no startframe # other than 0 is allowed. Suggest values of 6500,100,300,75,225
	for 1 sec of 400x300 pixels at 1000Hz
'''

option_dtypes={
	'nframes':int,
	'xmin':int,
	'xmax':int,
	'ymin':int,
	'ymax':int
}

default_options={
	'sum_file':"sum_clock.mien",
	'comp_file':"comp_clock.mien",
	'cam_file':"camCheckEvents.mien",
	'stim_file':"stimCheckEvents.mien"
}

def parse_options(l,switches):
	try:
		options, files = getopt.getopt(l, "hnbefs", ['sum_file=','comp_file=','cam_file=','stim_file=','dir=', 'nframes=', 'xmin=','xmax=','ymin=','ymax='])
	except getopt.error:
		print("Options not recognized. Try -h for help")
		import traceback
		e= sys.exc_info()
		apply(traceback.print_exception, e)
		sys.exit()
	for o in options:
		if o=='-h':
			print usage
			sys.exit()
		switches[o[0].lstrip('-')]=o[1]
	return (switches, files)


def getParams():
	switches, files= parse_options(sys.argv[1:],default_options.copy())
	for o in switches.keys():
		if option_dtypes.has_key(o):
			switches[o]=option_dtypes[o](switches[o])
	return (files, switches)


if __name__=='__main__':
	fn, sw = getParams()
	if 'b' in sw.keys():
		batch_process(fn,sw)
	elif 's' in sw.keys():
		slip_script()
	else:
		comp_series(fn,sw)
