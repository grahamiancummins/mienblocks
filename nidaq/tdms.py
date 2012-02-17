#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2008-07-03.

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

import struct

def read_length_n_str(f):
	l=struct.unpack("I", f.read(4))[0]
	return f.read(l)

def read_ni_type(f, dt):
	pass
	
def read_property(f):
	name = read_length_n_str(f)
	dt= struct.unpack("<I", f.read(4))[0]
	print name, dt
	if dt==32:
		v=read_length_n_str(f)
	elif dt==68:
		v=struct.unpack("<Qq", f.read(16))
	else:
		raise StandardError('Unknown Type %i' % dt)
	return (name, v)
	

def parse_header(f):
	h={}
	nno=struct.unpack("I", f.read(4))[0]
	for i in range(nno):
		name=read_length_n_str(f)
		di=struct.unpack("I", f.read(4))[0]
		if di==0:
			di=None
		elif di==4294967295L:
			di='same'
		else:
			di=read_length_n_str(f)
			# data type (enum), number of channels, number of values, [total size]
			if len(di)==20:
				di =struct.unpack("<IIQ", di)
			else:
				di=struct.unpack("<IIQQ", di)
		np=struct.unpack('<I', f.read(4))[0]
		props={}
		for j in range(np):
			pn, pv = read_property(f)
			props[pn]=pv
		h[name]=(i, di, props)
	return h		
		
		
	
def parse_data(f, do, no,  h):
	f.seek(do)
	return len(s)

def parse_segment(f, offset, header=None):
	if not header:
		header={}
	f.seek(offset)
	if not f.read(4)=='TDSm':
		raise IOError("This offset is not a TDMS segment")
	toc, v, sl, hl = struct.unpack("IIQQ", f.read(24))
	nextoffset=f.tell()+sl
	datoffset=f.tell()+hl
	has_header=toc & 2
	has_new_objects = toc & 4
	if has_header or has_new_objects:
		header.update(parse_header(f))
	has_data = toc & 8
	if has_data:
		data=parse_data(f, datoffset, nextoffset, header)
	else:
		data=None
	return (header, data, nextoffset)
	
def test(fn):
	f=open(fn)
	f.seek(0,2)
	tfl=f.tell()
	no=0
	h={}
	while no+4 < tfl:
		print "reading segment at %i" % no
		h, d, no = parse_segment(f, no)
		print h, d, no

def first(fn):
	parse_segment(open(fn), 0)
	
	