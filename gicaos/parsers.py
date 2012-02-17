#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2007-12-11.

# Copyright (C) 2007 Graham I Cummins
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

import numpy as N
import struct, re
import mien.parsers.nmpml
import time

def selectVideoData(nframes, dims, gui):
	lod=[{'Name':'Starting Frame', 'Value':0},
		{'Name':"Number of frames", 'Value':nframes},
		{'Name':'Frame Step (>1 skips frames)', 'Value':1},
		{'Name':'X min', 'Value':0},
		{'Name':'Y Min', 'Value':0},
		{'Name':'X Max', 'Value':dims[0]},
		{'Name':'Y Max', 'Value':dims[1]}
		]
	from mien.interface.cli import askParametersCLI
	pars= askParametersCLI(lod, gui)
	return pars
			
def binread(f, fmt):
	fmt="<"+fmt
	s=f.read(struct.calcsize(fmt))
	s=struct.unpack(fmt, s)
	if len(s)==1:
		return s[0]
	return s


# typedef struct { 
#  BITMAPINFOHEADER  bi;           //bitmap info header 
#  BOOL              bwMode;       //if true then monochrom camera else color 
#  int               SizeX;        //size of pixel in a line 
#  int               SizeY;        //size of line 
#  double            TScale;       //time scale (1/TScale = Fps) 
#  int               Shutter;      //shutter value 
#  float             PreTrigTime;  //pre trigger time 
#  int               PreTrigPages; //pre trigger pages 
#  char              Date[64];     //the date when the sequence was stored 
#  char              Time[64];     //the time when the sequence was stored 
#  char              Comment[256]; //comment 
#  int   Bitmode;      //5, 8 or 10 bit mode 
# } RAWHEADERV1;

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
	

def read_raw(f, **kwargs):
	h=read_raw_header(f)
	select =kwargs.get('select')
	f.seek(0, 2)
	flen=f.tell()
	flen=flen-1024
	bpp=h['bits_per_pixel']/8
	sof=bpp*h['dims'][1]*h['dims'][0]
	if not h['BandW']:
		sof*=3
	nframes=flen/sof
	if select:
		if type(select)==dict:
			defaults = {'startframe':0, 'framestep':1, 'xmin':0, 'ymin':0,
				'nframes':nframes, 'xmax':h['dims'][0], 'ymax':h['dims'][1]}
			defaults.update(select)
			select = [defaults[k] for k in ['startframe', 'nframes', 'framestep', 'xmin', 'ymin', 'xmax', 'ymax']]
		else:
			gui=kwargs.get('gui')
			select=selectVideoData(int(nframes),h['dims'], gui)
			if select is None:
				return 	mien.parsers.nmpml.blankDocument()
	f.seek(1024)
	if h['bits_per_pixel']>8:
		print "WARNING: int16 image"
		dtype=N.uint16
	else:
		dtype=N.uint8
	if h['BandW']:
		cdim=1
	else:
		print "WARNING: color image"
		cdim=3	
	#a=N.transpose(N.reshape(a[:300*400], (300, 400)))	
	art=time.time()
	if not select:
		a=N.fromfile(f, dtype)
		a=N.reshape(a, (-1, cdim, h['dims'][1],h['dims'][0]))
		a=N.transpose(a)
	else:
		startframe, nftr, framestep, xmin, ymin, xmax, ymax = select
		if startframe:
			f.seek(1024+sof*startframe)
		btr = sof*min(nftr,nframes-startframe)
		a=N.fromfile(f, dtype, btr)
		a=N.reshape(a, (-1, cdim, h['dims'][1],h['dims'][0]))
		a=N.transpose(a)
		a=a[xmin:xmax, ymin:ymax, :, 0:a.shape[3]:framestep]
	print("Read in %.4f sec" % (time.time()-art,))
	h["StackSpacing"]=h['timescale']
	if select:
		h['OriginalNumberofFrames'] = nframes
		h['OriginalDims'] = h['dims']
		h['FrameOffset'] = startframe
		h['FrameStep'] = framestep
		h['NumberofFrames'] = min(nftr,nframes-startframe)
		h['XDims'] = (xmin,xmax)
		h['YDims'] = (ymin,ymax)
	else:
		h['NumberofFrames'] = nframes
	for hk in ['bits_per_pixel', 'dims', 'BandW', 'timescale']:
		del(h[hk])
	de=mien.parsers.nmpml.createElement('Data', {'Url':kwargs['unparsed_url']})
	h['SampleType']='image'
	de.datinit(a, h)
	n = mien.parsers.nmpml.blankDocument()
	if select:
		n.fileinformation['select_done']=True
	n.newElement(de)
	return n
	
	
def _map2byte(a):
	minval=a.min()
	maxval=a.max()
	if minval==maxval:
		a=ones(a.shape)*128
	else:	
		a=a-minval
		a=255*a.astype('d')/(maxval-minval)
		a=N.where(a>255, 255, a)
		a=N.where(a<0, 1.0, a)
	a=a.astype(N.uint8)
	return a	
	
def _write_raw(data, h, fobj):
	#FIXME: this is not AOS compliant!!! Only batch.py can read it!!!
	#j1, width, height, j2, timescale=struct.unpack('<44siiid', f.read(64))
	
	fobj.write(" "*40)  
	if data.shape[2]>1:
		print "writing color"
		fobj.write(struct.pack('<i', 0))
	else:
		print "writing BW"
		fobj.write(struct.pack('<i', 1))
	fobj.write(struct.pack('<ii', data.shape[0], data.shape[1]))
	fobj.write(4*" ")
	fobj.write(struct.pack('<d', 1.0/h['StackSpacing']))
	fobj.write(struct.pack('<i', h.get('shutter', 0)))
	pt=h.get('pretrig', (0.0, 0))
	fobj.write(struct.pack('<fi', pt[0], pt[1] ))
	fobj.write(struct.pack('64s', h.get('date', ' ')))
	fobj.write(struct.pack('64s', h.get('time', ' ')))
	fobj.write(struct.pack('256s', h.get('comment', ' ')))
	fobj.write(struct.pack('<i', 8))
	fobj.write(' '*560)
	t=time.time()
	if data.dtype!=N.uint8:
		data=_map2byte(data)
	data=N.ravel(N.transpose(data))
	fobj.write(data.tostring())
	
def write_raw(fobj, doc, **kwargs):
	dats=doc.getElements('Data', {'SampleType':'image'})
	dats=[d for d in dats if len(d.shape())==4]
	if not dats:
		print('No image stacks')
		return
	lens=[d.shape()[3] for d in dats]
	li=N.argmax(lens)
	data=dats[li].getData()
	header=dats[li].header()
	_write_raw(data, header, fobj)
	

raw_d={'notes':'Reads RAW output from an AOS high speed video camera',
		'read':read_raw,
		'write':write_raw,
		'data type':'Numerical data',
		'elements':['Data'],
		'extensions':['.raw']}

