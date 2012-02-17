#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-06-16.

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

import sys, os, getopt

usage='''usage: longMovieToAngle.py [options] L fname.raw

L is the same fulcrum distance and filter width used by batch.py. fname.raw is an AOS file. Output is a timeseries file fname.mdat containing the angle as a function of time for the hair in the movie fname.raw. Program is set up to find dark hair on bright background. Auto-rotate has not been corrected and will likely fail under this set-up.  Do not use it!! 

"options" may include the following:

-w int   -- filter width in pixels (default is 5). As in batch.py
-n int   -- range of frames to use in guessing the rotation angle and the mean. default is 100.
-m int (0 or 1) -- should we subtract the mean? (default 1)
-s int	 -- number of frames to skip between active frames when constructing the angle-and-mean-guessing set. default 1
-t float -- between 0 and 1. The thresholding value used during auto-rotation. Pixels brighter than t*max(image) are considered part of the hair.
-a float -- rotational correction angle. Any value >180 indicates to guess this (default is no rotation)
'''
options={
	'w':5,
	'n':100,
	's':1,
	't':.8,
	'a':0.0,
	'm':1
}

NIKON_PixPerDiv=107.25
AOS_PixPerDiv=187.5

try:
	opts, files = getopt.getopt(sys.argv[1:], "a:w:n:t:s:m:")
	L=float(files[0])
	fnamein = files[1]
	for o in opts:
		oname = o[0].lstrip('-')
		otype = type(options[oname])
		options[oname]=otype(o[1] )
except:
	raise
	print usage
	sys.exit()


import mien.parsers.fileIO as io
import gicaos.parsers as parse
import mien.nmpml.data as mdat
import mien.parsers.nmpml as nmpml
from numpy import *
from numpy.random import permutation
from mien.math.array import rotate, roundtoint



def imrotate(dat, ang, indexes=None):
	ang=ang % 360
	if ang==0:
		return (dat, None)
	if not indexes:
		ind=transpose(array(nonzero(ones(dat.shape[:2]))))
		s=(dat.shape[0]/2, dat.shape[1]/2)
		rind=ind.astype(float32)-s
		rind=rotate(rind, ang)
		rind=roundtoint(rind)+s
		gi=nonzero(logical_and(all(rind>=(0,0), 1), all(rind<dat.shape[:2],1)))
		ind=ind[gi]
		rind=rind[gi]
		indexes = (ind, rind)
	else:
		ind, rind = indexes
	out=ones_like(dat)*dat.mean()
	out[ind[:,0], ind[:,1], :, :]=dat[rind[:,0], rind[:,1], :, :]
	dat = out
	return (dat, indexes)

def frameInfo(f, h):
	f.seek(0, 2)
	flen=f.tell()
	flen=flen-1024
	bpp=h['bits_per_pixel']/8
	sof=bpp*h['dims'][1]*h['dims'][0]
	if not h['BandW']:
		sof*=3
	nframes=flen/sof
	return (sof, nframes)
		

def guessAngle(dat, thresh):
	sdat = dat>=thresh*dat.max()
	angs = arange(-30, 31)
	fit = []
	indexes = []
	for ang in angs:
		z, ind = imrotate(sdat, ang)
		z = z.sum(1).sum(1).sum(1)
		fit.append(z.max())
		indexes.append(ind)
	a = angs[argmax(fit)]
	ind = indexes[argmax(fit)]
	return (a, ind)
	
def readFrameN(f, h, n):
	loc = 1024+ n*h['sof']
	f.seek(loc)
	frame=fromfile(f, uint8, h['sof'])
	frame = transpose(reshape(frame, (h['dims'][1],h['dims'][0])))
	return frame
	
def readFrames(f, h, a):
	frames = zeros((h['dims'][0], h['dims'][1], 1, len(a)))
	for i, fnum in enumerate(a):
		frames[...,i]=readFrameN(f, h, fnum)[:,:,newaxis]
	return frames
	

print fnamein
fnameout = os.path.splitext(os.path.split(fnamein)[-1])[0]+"_ts.mdat"
dirs = fnamein.split('/')
if len(dirs)>2:
	ddir = dirs[-3]
	if not os.path.isdir(ddir):
		os.mkdir(ddir)
	hdir = '/'.join(dirs[-3:-1])
	if not os.path.isdir(hdir):
		os.mkdir(hdir)
	fnameout = os.path.join(hdir, fnameout)
print fnameout
of = open(fnameout, 'w')
of.close()
f = open(fnamein, 'rb')
h = parse.read_raw_header(f)
sof, nframes = frameInfo(f, h)
h['sof']=sof
h['nframes']=nframes
start = int(max(0, nframes/2 -  options['n']/2))
stop = int(min(nframes-1, nframes/2 +  options['n']/2))
a = arange(start, stop, options['s'])
dat = readFrames(f, h, a)
mean = dat.mean(3)[...,0]
if options['a'] <= 180:
	ang = options['a']
	crap, index = imrotate(dat, ang)
else:
	ang, index = guessAngle(dat, options['t'])
print "guessing angle to be %i" % ang
print "processing %i frames ..." % nframes
out = []
#nframes = min(600, nframes)
for i in range(nframes):
	frame = readFrameN(f, h, i) 
	if options['m']:
		frame = frame - mean
	frame, junk = imrotate(frame, ang, index)
	x = frame.sum(1)
	if options['w']>1:
		x=convolve(ones(options['w']), x, mode='same')
	out.append(argmin(x))
	if not i%500:
		print i
out = array(out, float32)
if L:	
	L=L*AOS_PixPerDiv/NIKON_PixPerDiv	
	out-=out.mean()
	out = out/L

dat = mdat.newData(out, {'SampleType':'timeseries', 'SamplesPerSecond':1.0/h['timescale']})
doc = nmpml.blankDocument()
doc.newElement(dat)
io.write(doc, fnameout)

