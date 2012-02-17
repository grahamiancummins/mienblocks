#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2007-12-11.

# Copyright (C) 2007 Graham I Cummins
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

import mien.nmpml.basic_tools as nmbt
from mien.nmpml.data import newData

def createElement(cl, tag, attrs):
	node={'tag':tag, 'attributes':attrs, 'elements':[], 'cdata':''}
	return cl(node)

class Network(nmbt.NmpmlObject):
	'''Container class that implements a neural network made of Cell or AbstractCell elements. Contents may be equivalently represented as Cell or AbstractCell tags, or ElementReference elements pointing to these elements. 
	'''
	_allowedChildren = ['Comments', 'Connection','ElementReference', 'Cell', 'AbstractCell', 'Data']
	_requiredAttributes = ['Name']

	
	def addCells(self, cells):
		for c in self.getElements('AbstractCell', depth=1):
			c.sever()
		for ci, cs in enumerate(cells):
			loc = cs.position
	 		c = createElement(AbstractCell, 'AbstractCell', {'Name':ci, 'location':loc})
			self.elements.append(c)
		
	def addConnections(self, cons):
		for c in self.getElements('Connection', depth=1):
			c.sever()
		for cs in cons:
	 		c = createElement(Connection, 'Connection', {'Name':"%i_%i" % (cs[0], cs[1]), 'source':cs[0], 'target':cs[1], 'weight':cs[2], 'delay':cs[3]})
			self.elements.append(c)

		
	def setCellData(self, a, fs):
		d=self.getElements('Data')
		if d:
			d = d[0]
			d.datinit(a, {'SampleType':'timeseries', 'SamplesPerSecond':fs})
		else:
			d = newData(a, {'Name':'activation_data', 'SampleType':'timeseries', 'SamplesPerSecond':fs})
			self.newElement(d)


class Connection(nmbt.NmpmlObject):
	_allowedChildren = ['Comments', 'ElementReference']
	_requiredAttributes = ['Name', 'source', 'target', 'weight', 'delay']
	_specialAttributes = []

class AbstractCell(nmbt.NmpmlObject):
	'''Class to implement a mathematically abstract cell '''
	_allowedChildren = ['Comments', 'ElementReference', 'Connection', 'AbstractModel', 'Data']	
	_requiredAttributes = ['Name', 'location']
	

def mknet():
	n = createElement(Network, 'Network', {'Name':'network'})
	return n

