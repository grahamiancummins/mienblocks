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

import re
from mien.wx.graphs.graphGL import *
from numpy import *
from mien.math.array import vnorm, rotateAround
from ccbcv.align import _setDisplayGroup

DIRECTIONS={
 1: 205.0,
 2: 240.0,
 3: 292.0,
 4: 321.4,
 5: 31.7,
 6: 213.0,
 7: 28.7,
 8: 159.0,
 9: 113.6,
 10: 299.1,
 11: 23.6,
 12: 207.9,
 13: 45.0
}

def _linterp(pt1, pt2, ptt):
	p3= pt1+ (pt2-pt1)*ptt
	return p3

def _getAngleColor(a):
	# rcent = pi/4
	# gcent = 5*pi/4
	# bcent = 7*pi/4
	rcent = 0 + pi/6
	gcent = 2*pi/3 +pi/6
	bcent = 4*pi/3 +pi/6
	if a <= rcent or a >= bcent:
		rr = (2*pi - bcent)
		ptr = ((a+rr) % (2*pi))/(rcent+rr)
		col = _linterp( array((0.0, 0.0, 1.0)), array((1.0, 0.0, 0.0)), ptr)
	elif a<= gcent:
		a = a - rcent
		gcent = gcent - rcent
		ptg = a/gcent
		col = _linterp( array((1.0, 0.0, 0.0)), array((0.0, 1.0, 0.0)), ptg)
	else:
		a = a - gcent
		bcent = bcent - gcent
		ptb = a/bcent
		col = _linterp( array((0.0, 1.0, 0.0)), array((0.0, 0.0, 1.0)), ptb)
	col = vnorm(vnorm(col)**.6)
	#col = col/col.max()
	return tuple(col)

def _getDisplayGroup(el):
	dg = el.attrib("DisplayGroup", True)
	if dg:
		return dg
	els = el.xpath(True)
	els.reverse()
	for e in els:
		if e.__tag__ == "Group":
			return e.name()
	return None


def _getLenColor(a):
	rcent = 0 
	gcent = .5
	bcent = 1.0
	if a <= gcent:
		ptr = a/gcent
		col = _linterp( array((1.0, 0.0, 0.0)), array((0.0, 1.0, 0.0)), ptr)
	elif a > gcent:
		ptg = (a-gcent)/bcent
		col = _linterp( array((0.0, 1.0, 0.0)), array((0.0, 0.0, 1.0)), ptg)
	col = vnorm(vnorm(col)**.6)
	return tuple(col)
	

CFUNCS={
	'angle':( _getAngleColor, 2*pi),
	'linrgb':(_getLenColor, 1.0)
}

CSCALES = colorscales.keys() + CFUNCS.keys()

def _colorFromNumber(a, scale="hot",  r=None):
	if r!=None:
		a = (a - r[0])/(r[1]-r[0])
	if scale in colorscales:
		a = int(a*255)
		c = colorscale(array([1]), scale, 'absolute')[0]
	else:
		a = a*CFUNCS[scale][1]
		c =CFUNCS[scale][0](a)
	return c


def _get_source_file(o, chop=False):
	while 1:
		try:
			f=o.fileinformation['filename']
		except:
			f=""
		if f:
			if chop:
				f=os.path.split(f)[-1]
				f=os.path.splitext(f)[0]
			return f
		elif not o.container:
			return ""
		else:
			o=o.container


def _getClass(el, cv=None):
	n=_getDisplayGroup(el)
	t=re.compile("([LMS])[._-](\d+)")
	if not n:
		n=_get_source_file(el, chop=True)
		if not n:
			cv.report("element %s has no info" % n)
			return
		doc = el.xpath(True)[0]
		_setDisplayGroup(doc, [el], n)
	m=t.match(str(n))
	if not m:
		cv.report("element name %s can't be classified" % n)
		return
	l=m.groups()[0].lower()
	el.setAttrib('meta_length', {'l':'long', 'm':'medium', 's':'short'}[l], True)
	el.setAttrib('meta_class', int(m.groups()[1]), True)
	vals = [x.lower() for x in n.split(".")]
	if vals[-1] =='r' or vals[-2]=='r':
		el.setAttrib('meta_cercus', 'right', True)
	else:
		el.setAttrib('meta_cercus', 'left', True)
		

def setMetaTagsFromFileName(cv):
	for el in cv.getVisible():
		_getClass(el, cv)
		try:
			cv.report("set %s to %s %i %s" % (el.name(), el.attrib('meta_length', True), el.attrib('meta_class', True), el.attrib('meta_cercus', True)))
		except:
			pass

def SetDirectionalTuningFromMetaTags(cv):
	for el in cv.getVisible():
		aclass = el.attrib('meta_class', True)
		if not aclass:
			_getClass(el, cv)
			aclass = el.attrib('meta_class', True)
			if not aclass:
				continue
		cerc = el.attrib('meta_cercus', True).lower()[0]
		d = DIRECTIONS[aclass]
		if cerc == 'r':
			d = 360 - d
		el.setAttrib('meta_directional_tuning', d, True)
		cv.report('setting metadata in element %s' % el.name())

def ColorByDirection(cv):
	for el in cv.getVisible():
		dt =  el.attrib('meta_directional_tuning', True) 
		if dt==None:
			c = (1.0, 1.0, 1.0)
		else:
			ang =dt % 360
			ang = ang *pi/180
			c = _getAngleColor(ang)
		pycol=convertColor(c, 'py')
		el.setAttrib('color', pycol)
		pn=cv.getPlotName(el)
		cv.graph.plots[pn]['color']=c
		cv.graph.recalc(pn)
	cv.graph.OnDraw()

def ColorSynapsesByDirection(cv):
	cell = cv.getCell()
	spn= cell._guiinfo.get('synapse plot name')
	if not spn:
		print "no spn"
		print cell._guiinfo
		from mien.spatial.cvvis import showSynapses
		showSynapses(cv, cell)	
		spn = cell._guiinfo.get('synapse plot name')
	syn = cv.graph.modelRefs[spn]['synapses']
	sattr = zeros(len(syn), float32)
	cl = []
	for i, s in enumerate(syn):
		try:
			a = float(s.attrib('meta_directional_tuning', True))
			ang =a % 360
			ang = ang *pi/180
			c = _getAngleColor(ang)
			cl.append(c)
		except:
			pass
	cv.graph.plots[spn]['colorlist'] = cl	
	cv.graph.recalc(spn)
	cv.graph.OnDraw()		

def ColorPointsByLabel(cv):
	els = cv.getVisible()
	for e in els:
		if e.__tag__ == 'Fiducial' and e.attrib('Style') == 'spheres' and e.point_labels:
			cl = []
			for i in range(e.points.shape[0]):
				try:
					v = float(e.point_labels[i])
				except:
					v = 0.0
				cl.append(v)
			cl = colorscale(array(cl))
			pn = cv.getPlotName(e)
			cv.graph.plots[pn]['colorlist'] = cl
			cv.graph.recalc(pn)
	cv.graph.OnDraw()
			
	

def ColorSynapsesByDistality(cv):
	cell = cv.getCell()
	spn= cell._guiinfo.get('synapse plot name')
	if not spn:
		print "no spn"
		print cell._guiinfo
		from mien.spatial.cvvis import showSynapses
		showSynapses(cv, cell)	
		spn = cell._guiinfo.get('synapse plot name')
	syn = cv.graph.modelRefs[spn]['synapses']
	sattr = zeros(len(syn), float32)
	cl = []
	for i, s in enumerate(syn):
		if s.attrib('meta_class')==0:
			c = (1,1,1)
		else:
			
			a = float(s.attrib('meta_directional_tuning', True))
			ang =a % 360
			ang = ang *pi/180
			c = _getAngleColor(ang)
		cl.append(c)
	cv.graph.plots[spn]['colorlist'] = cl	
	cv.graph.recalc(spn)
	cv.graph.OnDraw()		

def ColorSynapsesByDistalityInverse(cv):
	cell = cv.getCell()
	spn= cell._guiinfo.get('synapse plot name')
	if not spn:
		print "no spn"
		print cell._guiinfo
		from mien.spatial.cvvis import showSynapses
		showSynapses(cv, cell)	
		spn = cell._guiinfo.get('synapse plot name')
	syn = cv.graph.modelRefs[spn]['synapses']
	sattr = zeros(len(syn), float32)
	cl = []
	for i, s in enumerate(syn):
		if s.attrib('meta_class')!=0:
			c = (1,1,1)
		else:
			
			a = float(s.attrib('meta_directional_tuning', True))
			ang =a % 360
			ang = ang *pi/180
			c = _getAngleColor(ang)
		cl.append(c)
	cv.graph.plots[spn]['colorlist'] = cl	
	cv.graph.recalc(spn)
	cv.graph.OnDraw()		

def randomColorsPerGroup(cv):
	els = cv.getVisible()
	cv.graph.clearAll()
	used=[]
	dgcols = {}
	for el in els:
		dg = _getDisplayGroup(el) or el.upath()
		if not dg in dgcols:
			col=cv.graph.getNewColor(used)
			used.append(col)
			pycol=convertColor(col, 'py')
			dgcols[dg]=pycol
		el.setAttrib('color', dgcols[dg])
	cv.addAll()

def randomColorsPerObject(cv):
	used=[]
	els = cv.getVisible()
	cv.graph.clearAll()
	for el in els:
		col=cv.graph.getNewColor(used)
		used.append(col)
		pycol=convertColor(col, 'py')
		el.setAttrib('color', pycol)
	cv.addAll()


def _castVals(v):
	v.sort()
	vd = {}
	for sv in v:
		if sv == None or sv == False:
		 	fv = None
		elif type(sv) in [int, float]:
			fv=sv
		elif type(sv) == tuple:
			try:
				fv = mean(sv)
			except:
				fv = v.index(sv)
		else:
			try:		
				fv = float(sv)
			except:
				try:
					fv = mean(map(float, fv.split("_")))
				except:
					fv = v.index(sv)
		vd[sv] = fv
	return vd

def colorByLengthAndDistal(cv):
	for e in cv.getVisible():
		if e.attrib('meta_cercal_distance', True)!=10:
			c = (1,1,1)
		else:
			l = e.attrib('meta_length', True)
			if l == 'long':
				c = (1,0,0)
			elif l == 'medium':
				c = (0,1,0)
			else:
				c = (0,0,1)
		pycol=convertColor(c, 'py')
		e.setAttrib('color', pycol)
		pn=cv.getPlotName(e)
		cv.graph.plots[pn]['color']=c
		cv.graph.recalc(pn)
	cv.graph.OnDraw()


def colorByMeta(cv):
	tags=set([])
	for e in cv.getVisible():
		for k in e.getInheritedAttributes():
			if k.startswith("meta_"):
				tags.add(k)
	d = [{"Name":"Which Tag",
			"Type":"List",
			"Value":list(tags)},
		{"Name":"Color Scale",
		"Type":"List",
		"Value":CSCALES},
		{"Name":"Min Value",
		"Value":0.0},
		{"Name":"Max Value",
		"Value":100.0},
		{"Name":"Make Untagged Elements White?",
		"Type":"List",
		"Value":["Yes", "No"]}]
	l = cv.askParam(d)
	if not l:
		return
	vals = list(set([e.attrib(l[0], True) for e in cv.getVisible()]))
	vals = _castVals(vals)
	for e in cv.getVisible():
		v = e.attrib(l[0], True)
		v = vals[v]
		if v == None:
			if l[4]=="No":
				continue
			else:
				c = (1.0,1.0,1.0)
		else:
			c = _colorFromNumber(v, l[1], (l[2], l[3]))
		print v, l[1], l[2], l[3], c
		pycol=convertColor(c, 'py')
		e.setAttrib('color', pycol)
		pn=cv.getPlotName(e)
		cv.graph.plots[pn]['color']=c
		cv.graph.recalc(pn)
	cv.graph.OnDraw()
	

def _setShiny(cv):
	plots = cv.graph.plots
	l=cv.askParam([{"Name":"Which Plot",
					"Type":"List",
					"Value":plots.keys()},
					{"Name":"Value",
					"Value":50.0}
				])	
	if not l:
		return
	plots[l[0]]['Shininess']=l[1]
	cv.graph.recalc(l[0])
	cv.graph.OnDraw()

def lunimanceByMeta(cv):
	tags=set([])
	for e in cv.getVisible():
		for k in e.getInheritedAttributes():
			if k.startswith("meta_"):
				tags.add(k)
	d = [{"Name":"Which Tag",
			"Type":"List",
			"Value":list(tags)},
		{"Name":"Min Value",
		"Value":0.0},
		{"Name":"Max Value",
		"Value":100.0}]
	l = cv.askParam(d)
	if not l:
		return
	vals = [e.attrib(l[0], True) for e in cv.getVisible()]
	vals = _castVals(vals)
	for e in cv.getVisible():
		v = e.attrib(l[0], True)
		v = vals[v]
		v = (v - l[1])/(l[2]-l[1])
		c = e.attrib('color', True) or (255, 255, 255)
		c=convertColor(c, 'gl')
		c2 = 3*vnorm(array(c))
		if not any(isnan(c2)):
			c = c2
		else:
			c = array(c)
		c = tuple(c*v)
		pycol=convertColor(c, 'py')
		e.setAttrib('color', pycol)
		pn=cv.getPlotName(e)
		cv.graph.plots[pn]['color']=c
		cv.graph.recalc(pn)
	cv.graph.OnDraw()


def showColorWheel(cv):
	if "colorwheel" in cv.graph.plots:
		del(cv.graph.plots['colorwheel'])
	fp = cv.graph.frontPlane()
	cent = fp[0]+.9*fp[1]+.9*fp[2]
	cent = cent + .1*cv.graph.forward
	rad = cv.graph.up*.05*min(vnorm(fp[1], False), vnorm(fp[2], False))
	# cent = fp[0]+.5*fp[1]+.5*fp[2] +.1*cv.graph.forward
	# rad = cv.graph.up*.5*vnorm(fp[1], False)
	sang = 0
	aw = pi/48
	dl=glGenLists(1)
	glNewList(dl, GL_COMPILE)
	glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
	while(sang < 2*pi):
		nrad = rotateAround(rad, cv.graph.forward, aw)
		col = _getAngleColor(sang+aw/2)
		sang+=aw
		glBegin(GL_POLYGON)
		materialColor(col)
		glVertex3fv(cent+.5*rad)
		glVertex3fv(cent+rad)
		glVertex3fv(cent+nrad)
		glVertex3fv(cent+.5*nrad)
		glEnd()
		rad=nrad
	# cent = cent -.1*cv.graph.forward
	# for ang in [30, 45, 115, 150]:
	# 	a1 = ang*pi/180
	# 	rad = cv.graph.up*.05*min(vnorm(fp[1], False), vnorm(fp[2], False))
	# 	rad1 = rotateAround(rad, cv.graph.forward, a1)
	# 	a2 = 2*pi - a1
	# 	rad2 = rotateAround(rad, cv.graph.forward, a2)
	# 	materialColor((.1, .1, .1))
	# 	glLineWidth(2.0)
	# 	glBegin(GL_LINES)
	# 	glVertex3fv(cent)
	# 	glVertex3fv(cent+rad1)
	# 	glVertex3fv(cent)
	# 	glVertex3fv(cent+rad2)
	# 	glEnd()
	glEndList()
	cv.graph.addCustomDisplayList(dl, name="colorwheel")
	cv.graph.OnDraw()
		
							
							
