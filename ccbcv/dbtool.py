#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2008-11-03.

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
from mien import blocks
from ccbcv.rest import PSDB
import re, sys, os
import mien.parsers.fileIO as io
URL = 'http://cercus.cns.montana.edu:8090'
PATH = '/CercalSystem/'

D = PSDB(URL, PATH)
#iids = D.getIDList()
#
#for iid in iids:
#	print iid
#	md = {}
#	md['type']='anatomy'
#	md['file_type']='mien/cell'
#	md['anatomy_type']='cercal filiform afferent'
#	D.update(iid, md)
#

metas = {
	'type':'anatomy',
	'file_type':'mien/spatial',
	'anatomy_type':'cercal afferent map'
}
for fn in sys.argv[1:]:
	doc = io.read(fn)
	for e in doc.getElements(['Cell', 'Fiducial']):
		for md in metas:
			e.setAttrib(md, metas[md])
	print "set %s in %s" % (md, fn)
	io.write(doc, fn)	
