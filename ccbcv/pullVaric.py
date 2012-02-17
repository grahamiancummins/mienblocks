#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-07-15.

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


import mien.parsers.fileIO as io
import mien.parsers.nmpml as nmpml
from ccbcv.rest import PSDB
from mien.parsers.mzip import deserialize

URL = 'http://cercus.cns.montana.edu:8090'
PATH = '/CercalSystem/'
CERCDB = PSDB(URL, PATH)

def getVaric(iid):
	df = CERCDB.getFile(iid)
	doc = deserialize(df)
	var = doc.getElements('Fiducial', {"Style":"spheres"})
	return var

records =  CERCDB.get(PATH)
doc = nmpml.blankDocument()
for rec in records:
	if 'afferent' in rec['metadata']['anatomy_type']:
		iid = rec['id']
		print iid
		els = getVaric(iid)
		if not els:
			print("warning, no varicosities in record %s. Skipping record" % iid)
			continue
		elif len(els)>1:
			print("warning, duplicate varicosities in record %s. Using first element" % (iid,))
		el = els[0]
		el.sever()
		el.setName("v"+iid)
		metas = CERCDB.getInfo(iid)['metadata']
		for k in metas:
			el.setAttrib('meta_'+k, metas[k])
		doc.newElement(el)
io.write(doc, 'varric.mat', format='.mat')

