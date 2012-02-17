#!/usr/bin/env python
# encoding: utf-8
#Created by Graham Cummins on 2007-07-02.

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

from mien.wx.graphs.glcolor import *


def showSectionDepth(cv):
	d=cv.askParam([{"Name":"Max Depth (0 for Auto)",
					 "Value":0}])
	if not d:
		return
	md=d[0]
	c=cv.getCell()
	name=cv.getPlotName(c)
	try:
		secind = cv.graph.modelRefs[name]['sections']
	except:
		cv.report("Can't highlight sections in plot %s because it has no section index" % name)
		return
	bds=array([c.branchDepth(s[0]) for s in secind])
	if md:
		r=(0, md)
	else:
		r=(0, bds.max())
	col=colorscale(bds, 'hot', r)
	cv.graph.plots[name]['colorlist'] = col
	cv.graph.recalc(name)
	if cv.graph.plots.has_key('ColorScale'):
		del(cv.graph.plots['ColorScale'])
	cv.graph.addColorScale(min=r[0], max=r[1], name="ColorScale")
	cv.graph.OnDraw()


def setAllDiametersToConstant(cv):
	elems = [f for f in cv.getVisible() if f.__tag__=='Fiducial' and f.attrib('Style')=='spheres']
	if not elems:
		return
	d = cv.askParam([{"Name":"D", "Value":0.2}])
	if not d:
		return
	for e in elems:
		pts = e.getPoints()
		if pts.shape[1]>4:
			pts[:,3]=1
			pts[:,3]*=d[0]
		else:
			fill = ones(pts.shape[0])*d[0]
			pts = column_stack([pts[:,:3], fill, pts[:,3]])
		e.setPoints(pts)
	cv.addAll()
	cv.graph.OnDraw()
	
def restoreDiameters(cv):
	elems = [f for f in cv.getVisible() if f.__tag__=='Fiducial' and f.attrib('Style')=='spheres']
	change = 0
	for e in elems:
		pts = e.getPoints()
		if pts.shape[1]<4:
			continue
		pts = pts[:,[0,1,2,4]]
		e.setPoints(pts)
		change = 1
	if change:
		cv.addAll()
		cv.graph.OnDraw()
	