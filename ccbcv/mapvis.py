#!/usr/bin/env python
# encoding: utf-8
#Created by gic on 2007-03-02.

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
from mien.datafiles.dataset import *
import ccbcv.dircolors

def showSynapseLatency(cv):
	cell = cv.getCell()
	syn = cell.getElements("Synapse")
	synloc, syninf=_getSynTemplate(syn, 6)
	pn = cv.graph.addSpherePlot(synloc)
	cell._guiinfo["synapse plot name"]=pn
	cv.graph.modelRefs[pn]={'mien.nmpml':cell, 'aux':'synapses'}
	colorrange = [2,12]
	cv.graph.set_color(pn , syninf[:,3], 'hot', colorrange)
	cv.graph.OnDraw()
	#self.graph.addCscale(syninf[:,1], 'hot', colorrange)

def invertMap(cv):
	els = cv.getVisible()
	metas = ['meta_cercus', 'meta_directional_tuning']
	for e in els:
		if not all([m in e.getInheritedAttributes() for m in metas]):
			print('metadata not defined for %s. Skipping' % e.upath())
			continue
		if e.__tag__=='SpatialField':
			z = e.attrib('Origin')
			ed = e.attrib('Edge')
			ds = e.getElements("Data", depth=1)[0]
			dat = ds.getData()
			red = z[0]+ed*dat.shape[0]
			e.setAttrib("Origin", (-red, z[1], z[2]))
			dat = dat[ arange(dat.shape[0]-1,-1,-1), ...]
			
			ds.datinit(dat)
		else:	
			pts = e.getPoints()
			pts[:,0]*=-1
			e.setPoints(pts)
		if e.attrib("meta_cercus", True)=='left':
			e.setAttrib("meta_cercus", 'right', True)				
		else:
			e.setAttrib("meta_cercus", 'left', True)
		d = e.attrib('meta_directional_tuning', True)
		d = d % 360
		d = 360-d
		e.setAttrib('meta_directional_tuning', d, True)
		ang = d *pi/180
		c = ccbcv.dircolors._getAngleColor(ang)
		pycol=ccbcv.dircolors.convertColor(c, 'py')
		e.setAttrib('color', pycol, True)
	cv.addAll()
	
def loadDensityFile(cv):
	fn=cv.askForFile()
	if not fn:
		return
	l=file(fn).readlines()
	l=array([map(float, line.split()) for line in l[2:]])
	#ind=l[:,:3].astype(int32)
	l=l[:,3]
	# xs=ind[:,0].max()+1
	# ys=ind[:,1].max()+1
	# zs=ind[:,1].max()+1
	tv=l.max()
	l=where(l<tv*.00001, 0, l)
	l=l/l.max()
	print tv
	l=reshape(l, (100,100,100))
	# dm=zeros((xs,ys,zs), float32)
	# for i in range(l.shape[0]):
	# 	dm[ind[i,:]]=l[i]
	print "submit"
	cv.graph.addDensPlot(l, edge=4.2, anchor=array((-161.89,-298.07,-131.32))	)
	print "done"
	cv.graph.OnDraw()
		
def zStepAnimation(cv):
	d = cv.askParam([{'Name':"# of steps", "Value":100}, 
					{"Name":"Step Size", "Value":10.0},
					{"Name":"Directory", "Value":"Z_animation"}])
	if not d:
		return
	
	ns=d[0]
	dir = d[2]
	inc = d[1]
	if os.path.isdir(dir):
		os.system("rm -rf %s" % dir)
	os.mkdir(dir)
	for i in range(ns):
		fname=os.path.join(dir, "frame%05i.bmp" % i)
		cv.graph.screenShot(fname=fname)
		print fname		
		vp = cv.graph.viewpoint - inc*cv.graph.forward
		cv.graph.viewpoint=vp
		cv.graph.OnDraw()
	cv.report("Saved Images")
	




