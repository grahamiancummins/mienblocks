#!/usr/bin/env python
# encoding: utf-8

#Created by gic on Fri Sep 24 11:25:00 CDT 2010

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

from mien.parsers.nmpml import createElement
import mien.parsers.nmpml as nmp
import ccbcv.gmm
import numpy

def data2points(gui, els):
	dat = els[0]
	labs = dat.getLabels()
	a = gui.askParam([{'Name':'X', 'Value':labs, "Type":"List"},
					{'Name':'Y', 'Value':labs, "Type":"List"},
					{'Name':'Z', 'Value':labs, "Type":"List"},
					{'Name':'D', 'Value':["Constant"] + labs, "Type":"List"},
					{'Name':'Labels', 'Value':["No Labels"] + labs, "Type":"List"}])
	if not a:
		return 
	dat = dat.getData()
	pts = numpy.ones((dat.shape[0], 4))
	pts[:,0] = dat[:, labs.index(a[0])]
	pts[:,1] = dat[:, labs.index(a[1])]
	pts[:,2] = dat[:, labs.index(a[2])]
	if a[3] != "Constant":
		pts[:,3] = dat[:, labs.index(a[3])]
	p= gui.makeElem('Fiducial', {"Style":"spheres"}, gui.document)
	p.setPoints(pts)
	if a[4]!="No Labels":
		p.point_labels = dict( zip( range(dat.shape[0]), map(str, dat[:,labs.index(a[4])])))

def scalePoints(gui, els):
	cols = ["X", "Y", "Z", "D", "Labels"]
	a = gui.askParam([{"Name":"Which", "Value":cols, "Type":"List"},
						{"Name":"Factor", "Value":-1.0}
					])
	if not a:
		return
	ind = cols.index(a[0])
	f = a[1]
	if ind == [4]:
		for k in els[0].point_labels.keys():
			try:
				els[0].point_labels[k] = str(float(els[0].point_labels[k])*f)
			except:
				pass
	else:
		pts = els[0].getPoints()
		pts[:,ind] = pts[:,ind]*f
		els[0].setPoints(pts)

def showGMMPars(gui, els):
	weights, means, covs  = ccbcv.gmm._gmmFromAM(els[0].container)
	print "There are %i components" % (len(weights),)
	a = gui.askParam([{'Name':'Which Component', 'Value':0}])
	if not a:
		return
	m = means[a[0],:]
	c = covs[a[0], ...]
	print m
	print c

	
def doTestGMM(gui, els):
	am = els[0]
	import portfors.density as den
	bb =den._getGMMBB(am)
	a = gui.askParam([{'Name':'Data Dimension', 'Value':len(bb[0])}])
	if not a:
		return
	pts = numpy.column_stack([numpy.linspace(bb[0][i], bb[1][i], 10) for i in range(a[0])])
	ds = createElement("Data", {"Name":'points', "SampleType":"generic"})
	ds.datinit(pts)
	am.run(ds)
	sfs = ds.getSubData('gmmout').getData()
	print "run successful"
	for i in range(10):
		if len(sfs.shape) == 1 or sfs.shape[1] == 1:
			print "%s -> %.2g" % (','.join(map(str, pts[i])), sfs[i])
		else:
			print "%s -> %s" % (','.join(map(str, pts[i])), ','.join(map(str, sfs[i])))

d2p = (data2points,"Data")
scale = (scalePoints,"Fiducial")
showGMM = (showGMMPars, "MienBlock")
testGMM = (doTestGMM, "AbstractModel")
