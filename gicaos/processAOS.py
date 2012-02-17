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
import mien.datafiles.dataset as dd
import mien.nmpml.data as nmpdat

def imrotate(i, t):
	ind=transpose(array(nonzero(ones(i.shape[:2]))))	
	s=(i.shape[0]/2, i.shape[1]/2)
	rind=ind.astype(float32)-s
	rind=rotate(rind, t)+s
	rind=around(rind).astype(int32)
	gi=nonzero(logical_and(all(rind>=(0,0), 1), all(rind<i.shape[:2],1)))
	ind=ind[gi]
	rind=rind[gi]
	out=ones_like(i)*i.dtype.type(i.mean())
	out[ind[:,0], ind[:,1], :]=i[rind[:,0], rind[:,1], :]
	return out

def rotate(a, dir):
	'''Nx2 array, float => Nx2 array
convert a 2 col array to another representing the same stimulus rotated
dir degrees clockwise. 0-180 should be in the 0 column and  L-R in the 1
column.'''
	dir=pi*dir/180
	newy=a[:, 0]*cos(dir) - a[:, 1]*sin(dir)
	newx=a[:, 0]*sin(dir) + a[:,1]*cos(dir)
	return transpose(array([newy, newx]))
	
def getMaxDigit(dirname):
	diginame = re.compile('(\d+)_.*\.mien$')

	files = os.listdir(dirname)
	nums = [-1]
	for f in files:
		m = diginame.match(f)
		if m:
			nums.append(int(m.groups()[0]))
	return max(nums)


def retrieveData(fn,sw=(), header=False):
	'''This function opens a file and returns the data members and sampling rate.'''
	sw=dict(sw)
	speclist=[(b,sw[b]) for b in ['xmin','xmax','ymin','ymax','nframes','startframe'] if sw.has_key(b)]
	if len(speclist) > 0:
		select=dict(speclist)
	else:
		select=None
	if select:
		f=io.read(fn,select=select)
	else:
		f=io.read(fn)
	d=f.getElements('Data')[0]
	dat = d.getData()
	if dd.isSampledType(d):
		fs=d.header()['SamplesPerSecond']
	elif d.stype()=='image':
		fs = 1./d.header()['StackSpacing']
	else:
		print "File does not have sampling rate. Setting sampling rate to None. May cause problems later..."
		fs = None
	if header:
		return dat, fs, d.header()
	else:
		return dat, fs
	
def newFile(s,d=()):
	d=dict(d)
	nd = nmpdat.newData(s, d)
	doc = nmp.blankDocument()
	doc.newElement(nd)
	return doc
	

def cropbin(fn,sp,datsamprate=0):
	'''This functon crops a binary file from sp[0] to sp[1] in rows, unless datsamprate is specified 
	(datsamprate is the sampling rate of the video data).  If specified, then cropping occurs at 
	rows fs/datsamprate * (sp[0] to sp[1]). This will only work when fs/samprate is int. len(sp) == 1 
	means run to end of file.'''
	dat, fs = retrieveData(fn)
	sp=array(sp)
	if datsamprate:
		if abs(float(fs)/datsamprate - fs/datsamprate) > 1.e-6:
			print "Binary sampling rate is not multiple of video sampling rate. Binary cropping will fail; exiting."
			sys.exit()
		else:
			rat=round(fs/datsamprate)
			sp=rat*sp
	if len(sp) == 1:
		dat = dat[sp:,:]
	else:
		dat = dat[sp[0]:(sp[0]+sp[1]),:]
	return dat, fs, sp
	

def process(fn, sw):
	#gc.set_debug()
	print('loading image stack ...')
	f=io.read(fn)
	d=f.getElements('Data')[0]
	dat = d.getData()
	h = d.header()
	print('processing image stack: %ix%i, %i frames ...' % (dat.shape[0], dat.shape[1], dat.shape[3]))
	if sw.get('xmin'):
		xm=sw['xmin']
		dat=dat[xm:,:,:]
	else:
		xm=0
	if sw.get('ymin'):
		ym=sw['ymin']
		dat=dat[:, ym:,:,:]
	else:
		ym=0
	if sw.get('xmax', -1)!=-1:
		xx=sw['xmax']
		xr=xx-sw.get('xmin', 0)
		dat=dat[:xr, :,:,:]
	else:
		xx=dat.shape[0]
	if sw.get('ymax', -1)!=-1:
		yy=sw['ymax']
		yr=yy-sw.get('ymin', 0)
		dat=dat[:, :yr,:,:]
	else:
		yy=dat.shape[1]
	print 'cropped to %ix%i' % (xr,yr)
	h['OriginalDims'] = (dat.shape[0],dat.shape[1])
	h['XDims'] = (xm,xx)
	h['YDims'] = (ym,yy)
	if sw.has_key('subtract_mean'):
		print "calculating mean ..."
		dat=dat.astype(float32)-dat.mean(3)[:,:,:,newaxis]
		dat-=dat.min()
		dat/=dat.max()
		h['SubtractMean']=True
	else:
		h['SubtractMean']=False
	if sw.get('rotate'):
		print "rotating ..."
		dat=imrotate(dat, sw['rotate'])
		h['Rotated'] = sw['rotate']
	else:
		h['Rotated'] = 0
	print('writing image stack ...')
	f=newFile(dat,h)
	if sw.has_key('AOS_dir'):
		fname=sw['AOS_dir']+'/'+sw['AOS_file']
	else:
		fname=sw['AOS_file']
	a1=io.write(f,fname)	
	if a1:
		print "Wrote %s." % fname
	else:
		print "Failed to write %s." % fname
	
	
def splitstack(fn,sw):	
	if not sw.get('numframes'):
		print('loading image stack ...')
		dat,fs = retrieveData(fn[0],sw)
		print('writing image stack ...')
		f = newFile(dat,{'StackSpacing':1./fs,'SampleType': 'image','ParentFile':fn[0]})
		if sw.has_key('AOS_dir'):
			fname=sw['AOS_dir']+'/'+sw['AOS_file']
		else:
			fname=sw['AOS_file']
		a1=io.write(f,fname)	
		if a1:
			print "Wrote %s." % fname
		else:
			print "Failed to write %s." % fname
		if fn[1]:
			print "writing stimulus file..."
			if sw.get('startframe'):
				sf[0]=sw['startframe']
			else:
				sf[0]=0
			if sw.get('nframes'):
				sf[1] = sw['nframes']
			dat, fs=cropbin(fn[1],sf,fs)
			h=nmpdat.newHeader(fs=fs)
			b=newFile(dat,h)
			if sw.has_key('bin_dir'):
				fname=sw['bin_dir']+'/'+sw['bin_file']
			else:
				fname=sw['bin_file']
			a2=io.write(b,fname)	
			if a2:
				print "Wrote %s." % fname
			else:
				print "Failed to write %s." % fname
	else:
		n=sw['numframes']
		if sw.get('jumpframes'):
			j=sw['jumpframes']
		else:
			j=0
		if sw.get('nframes'):
			nf=sw['nframes']
		else:
			nf = 23000 # > max AOS buffer at 1000 Hz
		if sw.get('startframe'):
			sf=sw['startframe']
		else:
			sf=0
		if sw.has_key('AOS_dir'):
			basedig=getMaxDigit(sw['AOS_dir'])
		else:
			basedig=getMaxDigit(os.getcwd())
		k=1
		while sf + k*n + (k-1)*j <= nf: 
			sp= sf + (k-1)*(n + j)
			kk='%03d' % (k+basedig)
			s={'startframe':sp, 'nframes':n}
			try:
				print('loading image stack ...')
				dat,fs,h = retrieveData(fn[0],s,header=True)
				if k == 1:
					nf = h['OriginalNumberofFrames']
				print('writing image stack %03d...' %(k-1))
				f = newFile(dat,h)
				if sw.has_key('AOS_dir'):
					fname=sw['AOS_dir']+'/'+kk+'_'+sw['AOS_file']
				else:
					fname=kk+'_'+sw['AOS_file']
				a1=io.write(f,fname)	
				if a1:
					print "Wrote %s." % fname
				else:
					print "Failed to write %s." % fname
				if fn[1]:
					dat, fs, sp=cropbin(fn[1],(sp,n),fs)
					h={'SamplesPerSecond':fs,'OriginalFile':fn[1],'SampleType':'timeseries','StartTime':sp[0]/fs}
					print "writing stimulus file..."
					b=newFile(dat,h)
					if sw.has_key('bin_dir'):
						fname=sw['bin_dir']+'/'+kk+'_'+sw['bin_file']
					else:
						fname=kk+'_'+sw['bin_file']
					a2=io.write(b,fname)	
					if a2:
						print "Wrote %s." % fname
					else:
						print "Failed to write %s." % fname
			except:
				print "error while processing %s or %s" % (fn[0],fn[1])
				import traceback
				e= sys.exc_info()
				apply(traceback.print_exception, e)
			k+=1

def batch_process(fn, switches):
	if len(fn) == 1:
		aosfiles=os.listdir(fn[0])
		folder=True
	else:
		aosfiles=fn
		folder=False
	p=re.compile("\.((raw)|(mien))")
	base=switches['AOS_file']
	for f in aosfiles:
		if p.search(f):
			print "processing file %s" % f
			switches['AOS_file'] = re.split(p,os.path.split(f)[1])[0] + '_' + base
			if folder:
				fname=os.path.join(fn[0], f)
			else:
				fname=f
			try:
				process(fname, switches)
			except:
				print "error while processing %s" % f
				import traceback
				e= sys.exc_info()
				apply(traceback.print_exception, e)
		else:
			print "skipping file %s" % f		



usage='''Usage:
python processAOS.py [options] video.raw (or video.mien) [microflown.bin]

fname.raw needs to be a path to an AOS raw video generated by an 8 bit greyscale camera.
fname.mien needs to be a processed AOS raw video as above previously saved in mien format. 
microflown.bin is a streamer file containing the recorded output of the microflown sensor that
is only needed if temporal cropping occurs (-c option). Ignored if -p or -b specified.

REQUIRED OPTIONS:
One of:
-c  -- temporal cropping (frame removal); specify particular options under Temporal cropping below 
-p  -- within-frame processing, spatially crop within frames or perform rotations or mean removal;
					specify options under Spatial cropping or Other processing below. 
-b  -- batch within-frame processing. Same options as for -p, but the input argument video.raw 
		should be either a list of files (can use shell * syntax), or a directory with .raw ar .mien files 
		to be processed. If a directory is specified, ALL .mien or .raw files will be processed, so
		the list format is safer.
		Also note differences in --AOS_file below.

Only one of these options will execute. -c has priority over -p has priority over -b.

GENERAL OPTIONS:
-f fname -- name of a file containing additional parameters 
-t  -- run unit tests rather than main script 
-h    -- help

IMAGE CROPPING AND CONDITIONING OPTIONS:
NOTE: You may put these options in a space-delimited text file and specify -f nameofparameterfile instead.

Temporal cropping:
--startframe # -- start processing video frame # (default 0)
--nframes # 	-- finish processing video after nframes (default all frames).
--numframes #    -- split file into # frames segments starting at startframe and finishing after nframes, 
				skipping jumpframes between each segment. Each segment will be written to its own file.
				Default is no splitting.
--jumpframes #	-- skip # frames in between each segment of numframes. Will be ignored if --numframes not 
				specified.

Spatial cropping:
--xmin #
--xmax #
--ymin #
--ymax # -- specify the bounding box of the region of interest. Unspecified "min" parameters default to 
	0, and "max" parameters default to the full size of the image.
	
Other processing:
--rotate # -- rotate the images # degrees counterclockwise. Default is 0. 
--subtract_mean  -- if specified, remove the temporal mean of the image stack before processing. This 
	significantly improves contrast for non-rotated images, but may behave unexpectedly for rotated ones. If
	both rotate and subtract_mean are specified, subtract_mean operates first.
	
OUTPUT OPTIONS:
--AOS_file fname  -- write the output video files as #_fname, where # varies from 000 to the number of 
	segments extracted from the original file, unless there are already numbered files in the output folder. 
	Then numbering starts at highest number in folder +1. Default is "#_processed_AOS.mien".
	*Note* for -b option: fname will be appended to the existing file name. For example, --AOS_file new.mien AOS1.raw as input
	will be saved as AOS1_new.mien 
--bin_file fname  -- write the output stimulus files as #_fname, where # is as for AOS_file.
	Default is "#_processed_stim.mien".
--AOS_dir  outdir  -- save image output files in directory ./outdir/  Default is current directory.
--bin_dir  outdir  -- save stimulus output files in directory ./outdir/  Default is current directory.


example:
python ./processAOS.py -c --startframe 2325 --numframes 1000 --jumpframes 1200 --AOS_file 2009_05_22AOS_Prep1_SSW_lowproc.mien 
					--bin_file 2009_05_22stim_Prep1_SSW_lowproc.mien SSW_low.raw SSW_low.bin
This processing will extract however many 1000 frame segments will fit into SSW_low.raw starting at frame 2325 
and skipping 1200 frames after each segment. It will cut out analogous parts of SSW_low.bin and save the 
excised pieces as 00#2009_05_22AOS_Prep1_SSW_lowproc.mien and 00#2009_05_22stim_Prep1_SSW_lowproc.mien.


python ./processAOS.py -p -f batch_parameters.txt --AOS_file 2009_05_22AOS_Prep1_SSW_lowproc001.mien 
				2009_05_22AOS_Prep1_SSW_lowproc001.mien
where batch_parameters.txt contains:
--xmin 30 --xmax 320 --ymin 50 --ymax 270 --rotate 347 --subtract_mean

This processing will first spatially crop 2009_05_22AOS_Prep1_SSW_lowproc001.mien to the x and y limits specified. 
Then it will remove the sequence mean from each frame and rotate each frame 13 degrees clockwise. The file will 
then be overwritten.

 '''

option_dtypes={
	'startframe':int,
	'nframes':int,
	'numframes':int,
	'jumpframes':int,
	'xmin':int,
	'xmax':int,
	'ymin':int,
	'ymax':int,
	'rotate':float
}


default_options={
	'AOS_file':"processed_AOS.mien",
	'bin_file': "processed_stim.mien"
}

def parse_options(l,switches):
	try:
		options, files = getopt.getopt(l,"cpbhf:t", ['startframe=', 'nframes=', 'numframes=', 'jumpframes=','xmin=', 'xmax=', 'ymin=', 'ymax=', 'rotate=', 'AOS_file=', 'bin_file=', 'subtract_mean','AOS_dir=','bin_dir=','keyword='])
	except getopt.error:
		print("Options not recognized. Try -h for help")
		sys.exit()
	for o in options:
		if o=='-h':
			print usage
			sys.exit()
		switches[o[0].lstrip('-')]=o[1]
	return (switches, files)


def getParams():
	switches, files= parse_options(sys.argv[1:],default_options.copy())
	if switches.has_key('f'):
		os=open(switches['f']).read()
		s2, f2 = parse_options(os.split(),switches)
		f2=[f for f in f2 if f]
		switches.update(s2)
		files.extend(f2)
	for o in switches.keys():
		if option_dtypes.has_key(o):
			switches[o]=option_dtypes[o](switches[o])
	if 't' in switches.keys():
		testme(files, switches)
		sys.exit()
	return (files, switches)


if __name__=='__main__':
	fn, sw = getParams()
	if 'c' in sw.keys():
		splitstack(fn,sw)
	elif 'p' in sw.keys():
		process(fn, sw)
	elif 'b' in sw.keys():
		batch_process(fn,sw)
	else:
		print "Option not recognized. See usage."
		print usage
		sys.exit()
		

