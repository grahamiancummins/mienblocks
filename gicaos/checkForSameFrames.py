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

usage='''usage: checkForSameFrames.py [options] fname.raw

This script checks AOS camera output for duplicate frames, and 
prints a message which is either "OK" or "BAD: Frames # - # are the same"

"options" may include the following:

-t int   -- Specify the number of sequential equivalent frames to check before 
	rejecting the file. Default is 15
-p float   -- Specify a power threshold used to discriminate equivalent frames. 
	default is 0 (frames must be identical). If specified, then the RMS power of the 
	difference between two frames must be greater than this for the frames to count 
	as different. 
'''
options={
	't':15,
	'p':0.0
}

try:
	opts, files = getopt.getopt(sys.argv[1:], "t:p:")
	fnamein = files[0]
	for o in opts:
		oname = o[0].lstrip('-')
		otype = type(options[oname])
		options[oname]=otype(o[1] )
except:
	
	print usage
	sys.exit()


from numpy import *
import struct
			
def binread(f, fmt):
	fmt="<"+fmt
	s=f.read(struct.calcsize(fmt))
	s=struct.unpack(fmt, s)
	if len(s)==1:
		return s[0]
	return s



def read_raw_header(f):
	f.read(40)   # BITMAPINFOHEADER. Don't know what to do with this
	h={}
	#print repr(f.read(4))
	h['BandW']=binread(f, 'i')
	h['dims']=binread(f, 'ii')
	f.read(4)
	h['timescale']=binread(f, 'd')
	h['shutter']=binread(f, 'i')
	h['pretrig']=binread(f, 'fi')
	h['date']=binread(f, '64s').strip('\x00').strip()
	h['time']=binread(f, '64s').strip('\x00').strip()
	h['comment']=binread(f, '256s').strip('\x00').strip()
	h['bits_per_pixel']=binread(f, 'i')
	return h


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
		
def readFrameN(f, h, n):
	loc = 1024+ n*h['sof']
	f.seek(loc)
	frame=fromfile(f, uint8, h['sof'])
	frame = transpose(reshape(frame, (h['dims'][1],h['dims'][0])))
	return frame
	
def sameFrame(f0, f1, p):
	if not p:
		return alltrue(f0==f1)
	else:
		resid = (f1-f0)**2
		resid = sqrt(resid.sum())
		return resid < p
print fnamein
f = open(fnamein, 'rb')
h = read_raw_header(f)
sof, nframes = frameInfo(f, h)
h['sof']=sof
h['nframes']=nframes

frame0 = readFrameN(f, h, 0)
nsame = 0
for ind in range(1, h['nframes']):
	frame1 = readFrameN(f, h, ind)
	if sameFrame(frame0, frame1, options['p']):
		nsame+=1
		if nsame >= options['t']:
			print "BAD: Frames %i - %i are equivalent" % (ind-nsame, ind)
			sys.exit()
	else:
		nsame = 0
	frame0 = frame1

print "OK"

