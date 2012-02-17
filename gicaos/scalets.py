#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-07-05.

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
usage = '''scalets.py pix fnames
convert all data in the data elements in the listed files from pixels to degrees, assuming that:
the data are the locations of a light spot on a moving cercal hair, measured in AOS camera pixels
pix is the distance from cercus to light spot on the associated hair in Nikon 4x pixels
angles of motion are small
 '''


NIKON_PixPerDiv=107.25
AOS_PixPerDiv=187.5



try:
	factor = float(sys.argv[1])
except:
	print usage
	sys.exit()


L=factor*AOS_PixPerDiv/NIKON_PixPerDiv	
L = 1.0/L
	
for fn in sys.argv[2:]:
	print fn
	doc = io.read(fn)
	try:
		dat = doc.getElements("Data", depth=1)[0]
	except:
		print "no data in %s" % fn
		continue
	dat.data-=dat.data.mean()
	dat.data*=L
	io.write(doc, fn)