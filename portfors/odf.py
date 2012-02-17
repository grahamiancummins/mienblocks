#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2010-10-11.

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


import zipfile, StringIO, mien.xml.xmlhandler
import numpy


class MiniXML(object):
	def __init__(self, node, container=None):
		self.up = None
		self.els = []
		if node.get('cdata'):
			self.data = ''.join(node['cdata'])
		else:
			self.data = ''
		self.tag = node['tag']
		self.attr = node['attributes']
		
	def setElements(self, els):
		'''Set the list self.elements, and the link e.container'''
		self.els=els
		for e in self.els:
			e.up = self	
		
	def __str__(self):
		if len(self.data) > 20:
			dt = self.data[:17] + "..."
		else:
			dt = self.data
		s = "<%s " % self.tag  + " ".join(["%s=%s" % (k, self.attr[k]) for k in self.attr.keys()]) + ">" + dt + " (%i subnodes)" % len(self.els)
		return s
		
	def __getitem__(self, k):
		if self.attr.has_key(k):
			return self.attr(k)
		elif type(k) == int and k < len(self.els):
			return self.els[k]
		else:
			return None
		
	def get(self):
		pass
		
	def search(self, tags=[], attribs={}, depth=-1, heads=False):
		'''returns all children recursively to a depth "depth". If depth
is negative, recurses all the way to the leaf level. If it is 1,
only immeadiate children are returned. If arguments are specified, the
list is filtered to contain only children with __tag__ in tags,  and
self.attrib(key)==value for every key in attribs. if "tags" is a string,
it is converted to [tags]. If attribs is a string, it is converted to
{"Name":attribs}. If "heads" is true, the search does not descend below a 
match (e.g. no children of a matching element will be returned.'''
		if type(tags)==type(" ") or type(tags)==type(u" "):
			tags = [tags]
		matches = []
		hit = True
		if tags and not self.tag in tags:
			hit = False
		for k in attribs:
			if not self[k] == attribs[k]:
				hit = False
		if hit:
			matches.append(self)
			if heads:
				return matches
		if depth == 0:
			return matches
		for e in self.els:
			matches.extend(e.search(tags, attribs, depth-1, heads))
		return matches
	
	def scan(self, depth=-1, subcall = False):
		z = [self.tag]
		if depth != 0:
			for e in self.els:
				z.extend(["  " + s for s in e.scan(depth-1, True)])
		if subcall:
			return z
		else:
			return "\n".join(z)
	
	
	@property
	def root(self):
		if not self.up:
			return self
		else:
			return self.up.root
	
	def eltags(self):
		for e in self.els:
			print e.tag

						
def readXMLZip(zipname, content_name_list=['content.xml']):
	f=zipfile.ZipFile(zipname, 'r')
	objs = []
	for cf in content_name_list:	
		xml=f.read(cf)
		xml=StringIO.StringIO(xml)
		doc=mien.xml.xmlhandler.readXML(xml, {'default class':MiniXML})
		xml.close()
		objs.append(doc)
	return objs


def tableCellContents(c):
	if c.els:
		return c[0].data

def table2array(el):
	rows = el.search('table:table-row')
	ncols = numpy.array([len(g.search('table:table-cell', depth=1)) for g in rows]).max()
	if not rows or not ncols:
		return numpy.array((0,0), 'object')
	tab = numpy.zeros((len(rows), ncols), 'object')
	for i, r in enumerate(rows):
		for j, c in enumerate(r.search('table:table-cell', depth=1)):
			tab[i,j] = tableCellContents(c)
	return tab
	

def readODS(fname):
	d = readXMLZip(fname)
	s = d[0].search('office:spreadsheet')[0]
	sheets = []
	for el in s.els:
		sheets.append(table2array(el))
	return sheets
	
	
	

