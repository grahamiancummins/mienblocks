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

import sys, struct, getopt, os, re
from numpy import *
import mien.parsers.fileIO as io

NIKON_PixPerDiv=107.25
AOS_PixPerDiv=187.5

def retrieveData(fn, header=False):
	'''This function opens a file and returns the data members and sampling rate.'''
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

def stitch(l):
	newdat=zeros()
	for f in l:
		dat, fs = 

def getVel():
	pass
		
def scanFT():
	pass
	
def constructXfer(vidTS, mfTS, sw):
	lv=stitch(vidTS)
	lm=stitch(mfTS)
	
	
def file_match(fn, sw):
	a=[], b=[]
	p=re.compile("\.((mien)|(mdat))")
	for f in fn:
		if p.search(f):
			beg=re.split(p,os.path.split(f)[1])[0]
			q=re.compile(beg+"\.(bin)")
			for g in fn:
				if q.search(g):
					a.append(f)
					b.append(g)
					break
		else:
			print "skipping file %s" % f		
	try:
		constructXfer(a,b, sw)
	except:
		print "error while processing %s" % f
		import traceback
		e= sys.exc_info()
		apply(traceback.print_exception, e)



'''Usage: 

python videoToXfer.py [options] list_of_angle_traces.mdat list_of_microflown_files.bin

Takes time traces made by longMovieToAngle.py and stitches them together. ASSUMES THAT THE TIME 
Does the same for microflown data. Calculates transfer functions: gain = angle / air vel, rad/(m/s)
and phase = angle - air vel, radians.

OPTIONS:
-h 	  -- prints usage
--out_file fname  -- saves transfer function as fname, default is XferFunc.mat
'''

option_dtypes={
}


default_options={
	'out_file':"XferFunc.mat"
}

def parse_options(l,switches):
	try:
		options, files = getopt.getopt(l,"h", ['out_file='])
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
	for o in switches.keys():
		if option_dtypes.has_key(o):
			switches[o]=option_dtypes[o](switches[o])
	return (files, switches)


if __name__=='__main__':
	file_match(fn, sw):


