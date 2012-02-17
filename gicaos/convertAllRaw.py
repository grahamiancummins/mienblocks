#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-07-04.

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
import mien.parsers.fileIO as io
import gicaos.parsers as parse
import mien.nmpml.data as mdat
import mien.parsers.nmpml as nmpml
from numpy import *
from mien.math.array import rotate, roundtoint

usage='''usage: convertAllRaw.py sourcedir destdir

'''

options={
	'w':5,
	'n':150,
	's':1,
	't':.8,
	'a':400.0
}


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



def getInfo(f):
	h = parse.read_raw_header(f)
	sof, nframes = frameInfo(f, h)
	h['sof']=sof
	h['nframes']=nframes
	return h

def chunkOFrames(fn, frames = None):
	f = open(fn, 'rb')
	h = getInfo(f)
	nframes=h['nframes']
	if frames == None:
		if nframes<=options['n']+2:
			raise StandardError("Not enough frames")
		else:
			start = int(max(0, nframes/2 -  options['n']/2))
			stop = int(min(nframes-1, nframes/2 +  options['n']/2))
			a = arange(start, stop, options['s'])
	else:
		a = frames 
	dat = readFrames(f, h, a)
	return dat

	
		
def getAngle(fn):
	dat = chunkOFrames(fn)
	ang, index = guessAngle(dat, options['t'])
	return (ang, index)

	
def procFile(fn, rot, nfn):
	f = open(fn, 'rb')
	h = getInfo(f)
	nframes=h['nframes']
	print "converting %s (%i frames)" % (fn, nframes)
	if nframes<1000:
		frames = arange(nframes)
	else:
		frames = None
	dat = chunkOFrames(fn, frames)
	me = dat.mean(3)[...,0]
	out = []
	for i in range(nframes):
		frame = readFrameN(f, h, i) - me
		if rot!=None:
			frame, junk = imrotate(frame, 1, rot)
		x = frame.sum(1)
		if options['w']>1:
			x=convolve(ones(options['w']), x, mode='same')
		out.append(argmax(x))
		if not i%500:
			print "... frame %i" % i
	out = array(out, float32)
	dat = mdat.newData(out, {'SampleType':'timeseries', 'SamplesPerSecond':1.0/h['timescale']})
	doc = nmpml.blankDocument()
	doc.newElement(dat)
	io.write(doc, nfn)	
	

		


def recSearch(dn, files, ext=".raw"):
	for n in os.listdir(dn):
		fn = os.path.join(dn, n)
		if os.path.isdir(fn):
			recSearch(fn, files, ext)
		elif os.path.isfile(fn) and fn.endswith(ext):
			if not dn in files:
				files[dn]=[]
			files[dn].append(n)
			
			


def recmkdir(dn):
	dp = dn.split('/')
	path = ''
	while dp:
		path = os.path.join(path, dp[0])
		if not os.path.isdir(path):
			os.mkdir(path)
		dp = dp[1:]
			
if __name__ == '__main__':
	sdn = sys.argv[1]
	ddn = sys.argv[2]
	f = {}
	recSearch(sdn, f)
	for sdir in f.keys():
		print("processing %s" % sdir)
		tdir = sdir.replace(sdn, ddn)
		if not os.path.isdir(tdir):
			recmkdir(tdir)
		files = f[sdir]
		i = 0
		ang = None
		while ang ==None:
			try:
				fn = os.path.join(sdir, files[i])
				ang, rot = getAngle(fn)
			except StandardError:
				print "%s is too short to estimate angle" % fn
				i+=1
		print "guessed angle as %i (used %s)" % (ang, fn)
		for fn in files:
			fin = os.path.join(sdir, fn)
			fout = os.path.splitext(fn)[0]+"_ts.mdat"
			fout = os.path.join(tdir, fout)
			procFile(fin, rot, fout)
		
		
	

