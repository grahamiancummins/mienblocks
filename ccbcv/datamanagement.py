#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-07-14.

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

from mien.parsers.nmpml import createElement
import mien.spatial.cvextend as cve

def displayGroupsToElements(cv):
	doc = cv.document
	groups = {}
	for e in doc.elements:
		dg = cve.getDisplayGroup(e)
		if not dg in groups:
			groups[dg]=[]
		groups[dg].append(e)
	for dg in groups:
		g = groups[dg]
		m = dict([(k, e.attrib(k)) for k in g[0].attributes if k.startswith("meta_")])
		m["Name"]=dg
		group = createElement("Group", m)
		doc.newElement(group)
		for e in g:
			e.move(group)
		cv.update_all(element=doc, action='rebuild')
	

def groupByMeta(cv):
	doc = cv.document
	grouped = []
	groups = []
	for e in doc.elements:
		if e in grouped:
			continue	
		m = dict([(k, e.attrib(k)) for k in e.attributes if k.startswith("meta_")])
		els = doc.getElements(attribs = m, depth=1)
		if set(els).intersection(grouped):
			print('warning: some elements fit multiple groups')
			els = set(els) - set(grouped)
		groups.append(els)
		grouped.extend(els)
	for g in groups:
		m = dict([(k, e.attrib(k)) for k in g[0].attributes if k.startswith("meta_")])
		dg = [cve.getDisplayGroup(e) for e in g]
		if all([gn == dg[0] for gn in dg[1:]]):
			name = dg[0]
		else:
			name=""
			for k in sorted(m):
				name = name+"%s%s" % (k[5:], str(m[k]))
		m["Name"]=name
		group = createElement("Group", m)
		doc.newElement(group)
		for e in g:
			e.move(group)
		cv.update_all(element=doc, action='rebuild')
		
	
	
