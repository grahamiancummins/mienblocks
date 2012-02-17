#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2010-12-04.

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
from numpy import fromstring, int16, reshape
import mien.parsers.nmpml as nmp

def read(f, **kw):
	a = reshape(fromstring(f.read(), int16), (-1, 1))
	d = nmp.blankDocument()
	dat = nmp.addPath(d, '/Data:call')
	dat.datinit(a, {'SampleType':'timeseries', 'SamplesPerSecond':40000.0})
	return d
	


p={'notes':'read only support',
		'read':read,
		'data type':'Numerical data',
		'elements':['Data'],
		'extensions':['.call1']}