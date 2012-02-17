
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

def makeGroup(gui, els):
	m = {'Name':"GroupFromSelection"}
	ngrp = createElement("Group", m)
	gui.document.newElement(ngrp)
	for e in els:
		m = e.getInheritedAttributes()
		for k in m:
			e.setAttrib(k, m[k])
		e.move(ngrp)
	consolidateTags(gui,[ngrp])
	gui.update_all(object=gui.document, event="rebuild")


def delGroup(gui, els):
	for grp in els:
		a = grp.attributes
		nc = grp.container
		for e in grp.elements:
			for k in a:
				if k.startswith('meta_'):
					if not k in e.attributes:
						e.setAttrib(k, a[k])
			e.move(nc)
		grp.sever()
	gui.update_all(object=nc, event="rebuild")

def consolidateTags(gui, grp):
	grp = grp[0]
	tags = {}
	for e in grp.elements:
		for k in ["Color",  "DisplayGroup"]:
			if k in e.attributes:
				del(e.attributes[k])
		for k in e.attributes:
			if k.startswith("meta_"):
				if not k in tags:
					tags[k] = set([])
				if type(e.attrib(k)) == list:
					tags[k].add(tuple(e.attrib(k)))
				else:
					tags[k].add(e.attrib(k))
	for k in sorted(tags):
		if len(tags[k]) == 1:
			grp.setAttrib(k, tags[k].pop())
	for e in grp.elements:
		for k in grp.attributes:
			if k.startswith("meta_") and k in e.attributes:
				del(e.attributes[k])		

def subGroup(gui, els, attr=None):
	grp = els[0]
	if not attr:
		d = gui.askParam([{"Name":"Attribute",
						   "Type":str}])
		if not d:
			return
		attr = d[0]
	avs = {}	
	for e in grp.elements:
		if e.__tag__ == "Group":
			subGroup(gui, [e], attr)
		else:
			av = e.attrib(attr)
			if av!=None:
				if not av in avs:
					avs[av] = []
				avs[av].append(e)
	if len(avs) < 2:
		return
	for av in avs:
		if len(avs[av])>1:
			gn = "%s_%s" % (attr, av)
			m = {'Name':gn, attr:av}
			ngrp = createElement("Group", m)
			grp.newElement(ngrp)
			for e in avs[av]: 
				e.move(ngrp)
			consolidateTags(gui, [ngrp])
	gui.update_all(object=grp, event="rebuild")

def flatten(gui, l):
	delGroup(gui, l[0].elements[:])	

def isSingle(l):
	if len(l)==1:
		return True
	return False	

def areGroups(l):
	if not l:
		return False
	for e in l:
		if e!="Group":
			return False
	return True

CreG = (makeGroup, lambda x:True)
ConsG = (consolidateTags, "Group")
DelG = (delGroup, areGroups)
FlatG = (flatten, ["Group", "Nmpml"])
SubG = (subGroup, isSingle)
