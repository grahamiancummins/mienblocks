
#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-06-03.

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
from mien.datafiles.dataset import *

SVGH = '''<?xml version="1.0" encoding="iso-8859-1"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1 Tiny//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11-tiny.dtd">
<svg version="1.1" baseProfile="tiny" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
	 x="0px" y="0px" width="WIDTHpx" height="HEIGHTpx" viewBox="0 0 WIDTH HEIGHT" xml:space="preserve">
'''


def _writeSVG(dat, fname, aspect):
	dat = dat.max() - dat
	dat = dat - dat.min()
	w = dat.shape[0]+1
	dat = dat * w * aspect / dat.max()
	of = open(fname, 'w')
	s = SVGH.replace('HEIGHT', "%g" % (w*aspect,))
	s = s.replace('WIDTH', "%g" % w)
	of.write(s)
	for c in range(dat.shape[1]):
		of.write('<g>\n  <polyline fill="none" stroke="#2E3192" stroke-width="3" stroke-linejoin="round" points="')
		for i in range(dat.shape[0]):
			of.write("%g,%g " % (i, dat[i,c]))
		of.write('" />\n</g>\n\n')
	of.write('</svg>\n')
	of.close()


def saveSnippetAsSVG(ds, xcoord, lead=.024, lag=.001, aspect=.5, fname='dvsvg.svg'):
	'''select a chunck of data around the indicated xcoord and save it to an svg file'''
	dat = ds.getData()
	xind = int(xcoord*ds.fs())
	sind = xind - int(lead*ds.fs())
	eind = xind + int(lag*ds.fs())
	dat = dat[sind:eind,:]
	_writeSVG(dat, fname, aspect)
	
def regionToSVG(ds, select=(None, None, None), aspect=.5, fname='dvsvg.svg'):
	'''select a chunck of data between the xcoords and save it to an svg file'''
	dat = getSelection(ds, select)
	_writeSVG(dat, fname, aspect)

