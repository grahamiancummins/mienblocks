#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2008-12-16.

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

from numpy import *

def drawNet(cv):
	net = cv.document.getElements('Network')[0]
	cells = net.getElements('AbstractCell', depth=1)
	pn = cv.getPlotName(net)
	if pn:
		try:
			del(cv.graph.plots[pn])
			del(cv.graph.modelRefs[pn])
		except:
			pass
	cd = ones((len(cells), 4))*4.0
	for i, c in enumerate(cells):
		cd[i,:3]=array(cells[i].attrib('location'))
	pn = cv.graph.addSpherePlot(cd)
	net._guiinfo["plot name"]=pn
	cv.graph.modelRefs[pn]={'mien.nmpml':net, 'aux':''}
	cv.graph.OnDraw()
	return pn
	

	
def loadNetData(cv):
	net = cv.document.getElements('Network')[0]
	if "plot name" in net._guiinfo:
		pn = net._guiinfo["plot name"]
	else:
		pn = drawNet(cv)
	dat = net.getElements('Data')[0]
	cv.graph.modelRefs[pn]["TimeSeries"]=dat.getData()
	cv.graph.modelRefs[pn]["TimeSeriesStep"]=1.0/dat.attrib('SamplesPerSecond')
	cv.graph.showTimeSeries(0, True)		
		
	
	
	
