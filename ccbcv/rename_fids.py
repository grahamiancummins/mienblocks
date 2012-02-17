#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-05-11.

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

import sys, os
import mien.parsers.fileIO as io
import ccbcv.align as al
import mien.parsers.nmpml as nmp
import re

aname = re.compile("([SML])\.(\d+)\.10\.(\d+)")

if sys.argv[1]=='rn':
	for n in sys.argv[2:]:
		if "_renamed" in n:
			continue
		if "_fubar" in n:
			continue
		print(n)
		nn, ext = os.path.splitext(n)
		nn = nn+"_renamed"+ext
		doc = io.read(n)
		try:
			al.guessFiducialNames(doc)
			io.write(doc, nn)
		except:
			print("failed")
			raise
elif sys.argv[1]=="col":
	ndoc = nmp.blankDocument()
	for n in sys.argv[2:]:
		doc = io.read(n)
		els = []
		for e in doc.elements:
			if e.name() in ["xhair", "transverse", "sagital", "coronal"]:
				ne = e.clone()
				snum = aname.match(n)
				nn = ne.name()+"_"+"_".join(snum.groups())
				ne.setName(nn)
				ndoc.newElement(ne)
	io.write(ndoc, "combined_fiducials.nmpml")
elif sys.argv[1]=="sep":
	cf = io.read(sys.argv[2])
	for n in ["xhair", "transverse", "sagital", "coronal"]:
		els = [e for e in cf.elements if e.name().startswith(n)]
		ndoc = nmp.blankDocument()
		for e in els:
			ndoc.newElement(e)
		nn = n+"_fiducials.nmpml"
		io.write(ndoc, nn)

	