#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2008-06-05.

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

from numpy import *

try:
	import pyni
except:
	import mb_binary.loader
	pyni=mb_binary.loader.load('pyni')
	
	
	
if __name__=='__main__':
	m=[0, 0]
	fs=10000.0
	r=arange(0,10*pi, 500/fs)
	s1=sin(r)
	s2=sin(r+pi/2)
	dat=column_stack([s1,s2])
	dat+=2.0
	dev='Dev0'
	cids=[dev+'/ao0',dev+'/ao1']
	try:
		pyni.reset(dev)
	except:
		pyni.reset(dev)
	print dat.shape
	j=pyni.aoutput(m,fs, ','.join(cids), dat)
	print m

	
