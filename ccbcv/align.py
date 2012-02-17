#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-05-07.

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

from mien.spatial.alignment import alignObject
import numpy as N
import os
import mien.parsers.fileIO as io
import mien.parsers.nmpml as nmp
import scipy.optimize as opt

def _getElems(doc):
	els = doc.getElements(["Cell", "Fiducial"])
	sel = []
	for el in els:
		if el.name().startswith("std_"):
			continue
		if el.attrib("noAlign"):
			continue
		sel.append(el)
	return sel

def _nearCenter(els):
	a = N.row_stack([e.getPoints()[:,:3] for e in els])
	m = (a.min(0) + a.max(0)) / 2.0
	dists = []
	for e in els:
		a = e.getPoints()[:,:3]
		mdist = ((a-m)**2).sum(1).min()
		dists.append(mdist)
	ei = N.array(dists).argmin()
	return els[ei]

def _setDisplayGroup(doc, els, gn):
	grp = doc.getElements('Group', gn)
	if grp:
		grp = grp[0]
	else:
		col=self.graph.getNewColor()
		grp = nmp.createElement("Group", {"Name":gn, 'color':(200,200,90)})
		doc.newElement(grp)
	for o in els:
		if "DisplayGroup" in o.attributes:
			del(o.attributes["DisplayGroup"])
		if "color" in o.attributes:
			del(o.attributes["color"])
		o.move(grp)
	
def loadStandardFiducials(doc):
	'''Add the CCB standard set of ganglion fiducials to the document. These contours will be named "std_*", and will, by default, not be operated on by other functions in this module'''
	fn = os.path.join(os.path.split(__file__)[0], 'std.nmpml')
	d2=io.read(fn)
	for el in d2.getElements(["Cell", "Fiducial"]):
		doc.newElement(el)

def deleteStandardFiducials(doc):
	'''Remove any elements named "std_*". This gets rid of the fiducials loaded by loadStandardFiducials'''
	els = doc.getElements(["Cell", "Fiducial"])
	for e in els:
		if e.name().startswith("std_"):
			e.sever()

def _anterior(el):
	pts = el.getPoints()
	myi = pts[:,1].argmax()
	return pts[myi,:3]

def scale(doc, scale_x=1.0, scale_y=1.0, scale_z=1.0):
	'''Scale the indicated dimensions by the provided ammounts. All Cell and fiducial elements in the document are scaled, unless their names begin with "std_", or they define the attribute "noAlign".'''
	spTrans={'Scale_x':scale_x, 'Scale_y':scale_y, 'Scale_z':scale_z}
	for obj in _getElems(doc):
		alignObject(obj, spTrans)

def scaleAll(doc, factor=-1.38):
	'''Scale all X Y and Z (but not D) dimensions by factor. All Cell and fiducial elements in the document are scaled, unless their names begin with "std", or they define the attribute "noAlign".'''
	spTrans={'Scale_x':factor, 'Scale_y':factor, 'Scale_z':factor}
	for obj in _getElems(doc):
		alignObject(obj, spTrans)

def _allPerms(n):
	allels = set(range(n))
	choices = [[i] for i in range(n)]
	for i in range(1, n):
		newchoices = []
		for l in choices:
			others = allels - set(l)
			for o in others:
				newchoices.append(l+[o])
		choices = newchoices
	return choices
	
	

def compile_ordered(doc, elems=[], newname="compiled", delete=False):
	'''Assemble the list of (line fiducial) elements in an order, such that the distances between the last ponit of element N and the first point in element N+1 are minimized. Collect those points in a single new object named newname. If delete is true, remove the old objects'''
	elems = [doc.getInstance(n) for n in elems]
	ords = _allPerms(len(elems))
	costs = N.zeros(len(ords))
	for i, p in enumerate(ords):
		seq = [elems[j] for j in p]
		cost=0
		for j in range(1, len(elems)):
			s1 = elems[j-1].getPoints()[-1,:3]
			t1 = elems[j].getPoints()[0,:3]
			cost+= ((t1 - s1)**2).sum()
		costs[i]=cost
	mord = ords[N.array(costs).argmin()]
	elems = [elems[j] for j in mord]
	nn = elems[0].clone()
	nn.setName(newname)
	pts = N.row_stack([e.getPoints() for e in elems])
	nn.setPoints(pts)
	doc.newElement(nn)
	if delete:
		for e in elems:
			e.sever()

def labelAllLines(doc):
	'''create a labeled point object containing the first point of each Cell and Fiducial in the document (other than the standard), labeled with the name of the object.'''
	els = _getElems(doc)
	ne=nmp.createElement("Fiducial", {"Style":"points", "Name":"objectlabels"})
	labs = [(i, els[i].name()) for i in range(len(els))]
	pts = N.ones((len(els), 4))
	for i in range(len(els)):
		pts[i,:3] = els[i].getPoints()[0,:3]
	ne.point_labels=dict(labs)
	ne.setPoints(pts)
	doc.newElement(ne)
	

def guessFiducialNames(doc, mode="loops", write=True):
	'''try to guess the ids of the various elements in a document. mode "loop" expects a file with ganglion cross sections, similar to Gwen's Long and Medium hair protocols, and identifies an afferent, xhair, varicosities, and transverse coronal and sagittal sections. If write is true, the new names are applied. In loop mode, the sagittal section is assumed to contain several lines, which are fused together.'''
	names = {}
	els = _getElems(doc)
	cells = [e for e in els if e.__tag__ == "Cell"]
	if len(cells)==1:
		names["Afferent"]=cells[0]
		fids = [e for e in els if e.__tag__ != "Cell" and e.attrib("Style")!="spheres"]
		names['xhair'] = _nearCenter(fids)
	elif len(cells)==2:
		y0 = cells[0].getPoints()[:,1].mean()
		y1 = cells[1].getPoints()[:,1].mean()
		if y1>y0:
			names["Afferent"]=cells[0]
			names['xhair'] = cells[1]
		else:
			names["xhair"]=cells[0]
			names['Afferent'] = cells[1]
	else:
		doc.report("too many cells to auto-classify")
		return {}
	varic = [e for e in els if e.attrib("Style")=="spheres"]
	names["varicosities"]=varic[0]
	if len(varic)>1:
		doc.report("Warning: more than one varicosity cloud. Picking one at random")
	fids = [e for e in els if e.attrib("Style")=="line" and not e in names.values()]
	fids = [f for f in fids if f.getPoints().shape[0]>5]
	fmin = N.zeros((len(fids), 3))
	fmax = N.zeros((len(fids), 3))
	fmean = N.zeros((len(fids), 3))
	fstd = N.zeros((len(fids), 3))
	for i, f in enumerate(fids):
		pt = f.getPoints()[:,:3]
		fmin[i,:]=pt.min(0)
		fmax[i,:]=pt.max(0)
		fmean[i,:]=pt.mean(0)
		fstd[i,:]=pt.std(0)
	frange = fmax - fmin
	frange = frange+.001*(frange==0)
	tcont=frange[:,1].argmax()
	names["transverse"] = fids[tcont]
	if mode=="loops":
		ccm = (frange[:,2]+frange[:,0])  /frange[:,1]
		ccont = ccm.argmax()
		names["coronal"] = fids[ccont]
		for e in names.values():
			if e in fids:
				fids.remove(e)
		names["sagital"] = fids
	for n in names:
		if type(names[n])==list:
			s = ",".join([e.upath() for e in names[n]])
		else:
			s=names[n].upath()
		print("%s -> %s" % (n, s))
	if write:
		for n in names:
			if type(names[n])==list:
				compile_ordered(doc, [e.upath() for e in names[n]], n, True)
			else:
				names[n].setName(n)
	return names
		

def xhairAlign(doc, elemXhair="guess"):
	'''Translate all elements so as to set the anterior-most point in the x-hair object to 0,0,0. elemXhair may be an object ID or "guess". The algorithm to guess the X-hair ID is to choose the contour that contains the point closest to the center of the bounding box of all countours in the data set'''
	#std_xhair = doc.getElements('Fiducial', 'std_xhair')[0]
	if elemXhair!="guess":
		new_xhair = doc.getInstance(elemXhair)
	else:
		els = _getElems(doc) #some xhairs now are Cells or Spheres, not lines!!!
		new_xhair = _nearCenter(els)
		doc.report("Guessing %s to be the xhair" % (new_xhair.upath(),))
	#topt = _anterior(std_xhair)
	topt = N.array([0.0, 0.0, 0.0])
	frompt = _anterior(new_xhair)
	pt=topt - frompt
	conv = 	{'Trans_x':pt[0],
			 'Trans_y':pt[1],
			 'Trans_z':pt[2]}
	for obj in 	_getElems(doc):
		alignObject(obj, conv)

def _nearestPts(els, pt):
	'''If els is a list of pointcontainers, pt is a 3 vector, return the Nx3 array of points such that the ith point is the point in els[i] that is nearest to pt (euclidean distance)'''
	pts =[]
	for e in els:
		ep=e.getPoints()[:,:3]
		d = ((ep-pt)**2).sum(1).argmin()
		pts.append(ep[d])
	return N.array(pts)

def simpleAverageContour(doc, delete=False):
	'''construct an average of all contours in the data set, using a very simple averaging scheme. If delete, destroy the existing contours'''
	els = doc.getElements("Fiducial", {"Style":"line"})
	ne = els[0].clone()
	ne.setName("average")
	_setDisplayGroup(doc, [ne], "averages")
	cue_pts = els[0].getPoints()
	out_pts = N.ones_like(cue_pts)
	for i in range(out_pts.shape[0]):
		pts = _nearestPts(els, cue_pts[i, :3])
		cent = pts.sum(0)/pts.shape[0]
		pts = _nearestPts(els, cent)
		out_pts[i,:3]=pts.sum(0)/pts.shape[0]
	ne.setPoints(out_pts)
	doc.newElement(ne)
	if delete:
		for e in els:
			e.sever()

def _presid(pars, dat, axis):
	nax = [i for i in range(3) if not i==axis]
	z = N.ones(dat.shape[0])*pars[2]
	for i in range(2):
		z+=dat[:,nax[i]]*pars[i]
	err = dat[:,axis]-z
	return err

def _pregress(a):
	aid = a.std(0).argmin()
	guess=N.ones(3)
	guess[aid]=0.0
	res = opt.leastsq(_presid, guess, (a,aid))
	if res[1]>4:
		raise StandardError("No Solution")
	return list(res[0])+[aid]
	

def _pproject(a, plane):
	nax = [i for i in range(3) if not i==plane[3]]
	out = a.copy()
	z = N.ones(a.shape[0])*plane[2]
	for i in range(2):
		z+=a[:,nax[i]]*plane[i]
	out[:,plane[3]]=z
	return out

def _norm(v):
	return N.sqrt( (v**2).sum() )

def _eucd(a, b):
	a = a-b
	return N.sqrt( (a**2).sum(1) )
	

def _planeNormal(a):
	a=a-a.mean(0)
	v1 = a[0]
	i=1
	vect = N.cross(a[i,:], v1)
	while _norm(vect)<.001:
		i+=1
		vect = N.cross(a[i,:], v1)
	if vect[abs(vect).argmax()]<0:
		vect*=-1
	vect = vect/_norm(vect)
	return vect

def _rotateAround(ax, ang, pts=None):
	'''rotate the 3D pts around the 3 vector ax, counterclockwise, by ang radians. If pts is None, return a rotation matrix rotmat, such that dot(pts, rotmat) implements the rotation. If pts is an array, apply the rotation and return the rotated points'''
	if ang % (2*N.pi) == 0.0:
		if pts==None:
			return N.identity(3)
		else:
			return pts.copy()
	ax=ax.astype(N.float32)/_norm(ax)
	c = N.cos(ang)
	s = N.sin(ang)
	x, y, z = ax
	rotmat =N.array([[x**2+(1-x**2)*c, x*y*(1-c)-z*s, x*z*(1-c)+y*s],
			 		[x*y*(1-c)+z*s, y**2+(1-y**2)*c, y*z*(1-c)-x*s],
		 	 		[x*z*(1-c)-y*s, y*z*(1-c)+x*s, z**2+(1-z**2)*c]]).transpose()
	if pts == None:
		return rotmat
	return N.dot(pts, rotmat)

def _rot2D(ang, pts):
	'''Return the 2D pts rotated counterclockwise by ang radians'''
	rotmat = N.array([[N.cos(ang), -N.sin(ang)],
					  [N.sin(ang),  N.cos(ang)]]).transpose()
	return N.dot(pts, rotmat)

def _setAsZ(ax, dat=None):
	'''calculate a rotation such that the axis ax will become the new Z axis. If dat is none, return (axis, angle) representing the rotation. If dat is an array, apply the transformation to it, and return the result'''
	zaxis=N.array([0.0,0.0,1.0])
	ax=ax/_norm(ax)
	theta=-N.arccos(N.dot(ax, zaxis))
	rot=N.cross(zaxis, ax)
	if dat == None:
		return (rot, theta)
	return _rotateAround(rot, theta, dat)

def _plane2xy(a):
	'''Return (a2d, axis, ang), where a2d is a 2D matrix equivalent to the best planar projection of a, and axis, ang specifies the rotation required to make the plane equivalent to the XY plane. '''
	ax = _planeNormal(a)
	ax, ang = _setAsZ(ax)
	pts = _rotateAround(ax, ang, a)
	return (pts[:,:2], ax, ang)

def _crossXax(pts):
	cross = []
	for i in range(1, pts.shape[0]):
		if pts[i,1] == 0.0:
			cross.append(pts[i, 0])
		elif pts[i, 0]<0 or pts[i-1, 0]<0 or pts[i,1]*pts[i-1, 1]>=0.0:
			pass
		else:
			rng = pts[i-1, 0]-pts[i,0]
			rat = pts[i,1]/(pts[i,1]-pts[i-1,1])
			cross.append(pts[i,0]+rng*rat)
	return cross
			

def _interpMiss(a, miss=-1):
	a=N.array(a).astype(N.float32)
	mid = N.nonzero(a==miss)[0]
	for i in mid:
		distl = 1
		distr = 1
		while (i+distr) % a.shape[0] in mid:
			distr+=1
		while i-distl in mid:
			distl+=1
		vall = a[	i-distl]
		valr= a[(i+distr) % a.shape[0]]
		rng = valr-vall
		rat = float(distl)/(distr+distl)
		a[i] = vall+rng*rat
	return a
		

def _elipse(alph, maa, mia, xoff, yoff, ang):
	#FIXME: not regularized because of offset
	alph-=ang
	r = N.sqrt((maa**2 * mia**2) / ((maa*N.sin(alph))**2 + (mia*N.cos(alph))**2))
	alph += ang
	pt = [r*N.cos(alph), r*N.sin(alph)]
	pt[0]+=xoff
	pt[1]+=yoff
	return pt	

def _sigmoid(x, top, bot, midpoint, slope):
	amp = top-bot
	y = amp/(1.0+N.exp( (-1*(x-midpoint))*slope))
	y+=bot
	return y

def _eggyweg(alph, maa, mia, xoff, yoff, ang, stretch, mid, slope):
	alph-=ang
	r = N.sqrt((maa**2 * mia**2) / ((maa*N.sin(alph))**2 + (mia*N.cos(alph))**2))
	pt = N.array([r*N.cos(alph), r*N.sin(alph)])
	skf = _sigmoid(pt[0], 1.0/stretch,stretch, mid, slope)
	pt[1]*=skf
	pt = _rot2D(ang, pt)
	pt+=N.array([xoff, yoff])
	return pt

def _angleScan(fn, args, arc):
	angles = N.arange(0, 2*N.pi, arc)
	pts = N.zeros((angles.shape[0], 2))
	for i in range(angles.shape[0]):
		pts[i,:]=fn(angles[i], *args)
	#pts= _regularize(pts, arc, 'max')
	return pts
	

def planeRegressAndProject(doc, elems=[], newname="planarProjection"):
	'''collect all the points defined by elems and calculate a planer regression. Then construct a new point fiducial named newname containing the projection of all the points onto the regression plane.
'''
	a = N.row_stack([doc.getInstance(e).getPoints()[:,:3] for e in elems])
	plane = _pregress(a)
	a=_pproject(a, plane)
	ne=nmp.createElement("Fiducial", {"Style":"points", "Name":newname})
	ne.setPoints(a)
	_setDisplayGroup(doc, [ne], "projections")
	doc.newElement(ne)

def _tobestplane(pts):
	plane = _pregress(pts)
	pip = _pproject(pts, plane)
	centroid = pip.mean(0)
	pip-=centroid
	pip, axis, angle = _plane2xy(pip)
	return (pip[:,:2], axis, angle, centroid)
	

def _regularize(pip, arc, mode):
	angles = N.arange(0, 2*N.pi, arc)
	crossings = []
	pip = N.row_stack([pip, pip[0]])
	for a in angles:
		rpip = _rot2D(-a, pip)
		cs = _crossXax(rpip)
		if len(cs) == 0:
			crossings.append(-1)
		elif len(cs)==1:
			crossings.append(cs[0])
		elif mode == "max":
			crossings.append(N.max(cs))
		elif mode == "min":
			crossings.append(N.min(cs))
		elif mode == "mean":
			crossings.append(N.mean(cs))
		elif mode == "skip":
			crossings.append(-1)
	crossings = _interpMiss(crossings, -1)
	pts = N.zeros((crossings.shape[0], 2))
	for i in range(pts.shape[0]):
		u = _rot2D(angles[i], [1,0])
		pts[i,:]=u*crossings[i]
	return pts

def _back23D(pts, axis, angle, centroid):
	pts = N.column_stack([pts, N.zeros(pts.shape[0])])
	pts = _rotateAround(axis, -angle, pts)
	pts += centroid
	return pts

def regularizeContour(doc, elem="/Fiducial:transverse", newname="regularized", arc=1.0, mode="max"):
	'''
SWITCHVALUES(mode)=["max", "min", "mean", "skip"]
	'''
	el = doc.getInstance(elem)
	pts =el.getPoints()[:,:3]
	arc = N.pi*arc/180.0
	pts, axis, angle, centroid = _tobestplane(pts)
	pts = _regularize(pts, arc, mode)
	pts = _back23D(pts, axis, angle, centroid)
	ne=nmp.createElement("Fiducial", {"Style":"points", "width":5, "Name":newname})
	_setDisplayGroup(doc, [ne], "projections")
	ne.setPoints(pts)
	els = doc.getElements("Fiducial", newname, depth=1)
	if els:
		els[0].sever()
	doc.newElement(ne)

def _eggResid(pars, dat):
	# maa, mia, xoff, yoff, ang, stretch, mid, slope
	pars = N.array(pars)
	ndat = dat - pars[2:4]
	ndat = _rot2D(-pars[4], ndat)	
	err = []
	for i in range(dat.shape[0]):
		pt = ndat[i,:]
		alph = N.arctan2(pt[1], pt[0])
		r = N.sqrt((pars[0]**2 * pars[1]**2) / ((pars[0]*N.sin(alph))**2 + (pars[1]*N.cos(alph))**2))
		ept = N.array([r*N.cos(alph), r*N.sin(alph)])
		skf = _sigmoid(ept[0],  1.0/pars[5],pars[5], pars[6], pars[7])
		ept[1]*=skf
		miss = _norm(pt) - _norm(ept)
		if miss < 0:
			miss = N.sqrt(-miss)
		else:
			err.append(miss)
	return N.array(err)

def _eggFit(a, guess):
	res = opt.leastsq(_eggResid, guess, (a,))
	if res[1]>4:
		raise StandardError("No Solution")
	return res[0]

def _elipseResid(pars, dat):
	pars = N.array(pars)
	err = []
	for i in range(dat.shape[0]):
		pt = dat[i,:]-pars[2:4]
		alph = N.arctan2(pt[1], pt[0])
		alph-=pars[4]
		r = N.sqrt((pars[0]**2 * pars[1]**2) / ((pars[0]*N.sin(alph))**2 + (pars[1]*N.cos(alph))**2))
		dr = N.sqrt( (pt**2).sum() )
		err.append(dr-r)
	return N.array(err)

def _elipseFit(a, guess):
	res = opt.leastsq(_elipseResid, guess, (a,))
	if res[1]>4:
		raise StandardError("No Solution")
	return res[0]
	

def getBestElipse(doc, elem="/Fiducial:std_av_sagital", newname="reg_coronal"):
	el = doc.getInstance(elem)
	arc=N.pi/180
	pts =el.getPoints()[:,:3]
	rpts, axis, angle, centroid = _tobestplane(pts)
	pts = rpts
	size = _eucd(pts[:,:2], N.array([0,0]))
	mai = size.argmax()
	ang = N.arctan2(pts[mai,1], pts[mai,0])
	guess = (size[mai], size.min(), 0, 0, ang)
	egg = _elipseFit(pts[:,:2], guess)
	bfe = _angleScan(_elipse, egg, arc)
	bfe = _back23D(bfe, axis, angle, centroid)
	ne=nmp.createElement("Fiducial", {"Style":"points", "width":10, "Name":newname})
	_setDisplayGroup(doc, [ne], "projections")
	ne.setPoints(bfe)
	els = doc.getElements("Fiducial", newname, depth=1)
	if els:
		els[0].sever()
	doc.newElement(ne)

def getBestEgg(doc, elem="/Fiducial:std_av_transverse", newname="reg_transverse"):
	el = doc.getInstance(elem)
	arc=N.pi/180
	pts =el.getPoints()[:,:3]
	pts, axis, angle, centroid = _tobestplane(pts)
	size = _eucd(pts[:,:2], N.array([0,0]))
	mai = size.argmax()
	ang = N.arctan2(pts[mai,1], pts[mai,0])
	#maa, mia, xoff, yoff, ang, stretch, mid, slope
	guess = (360, 240, 20, 127, N.pi/2, 1.6, 60.0, .006)
	#guess = (size[mai], size.min(), 0, 0, N.arctan2(pts[mai,1], pts[mai,0]), 1.6, 60.0, 0.006)
	print guess
	gpts = _angleScan(_eggyweg, guess, arc)
	try:
		egg = _eggFit(pts[:,:2], guess)
		print egg
		bfe = _angleScan(_eggyweg, egg, arc)
	except:
		print "No Solution"
		bfe = N.zeros((1,2))
	for i, out in enumerate([pts, gpts, bfe]):
		p= N.column_stack([out, N.zeros(out.shape[0])])
		ne=nmp.createElement("Fiducial", {"Style":"points", "width":10, "Name":str(i)})
		_setDisplayGroup(doc, [ne], "projections")
		ne.setPoints(p)
		els = doc.getElements("Fiducial", str(i), depth=1)
		if els:
			els[0].sever()
		doc.newElement(ne)

	# bfe = _back23D(bfe, axis, angle, centroid)
	# ne=nmp.createElement("Fiducial", {"Style":"points", "width":10, "Name":newname, "DisplayGroup":"projections"})
	# ne.setPoints(bfe)
	# els = doc.getElements("Fiducial", newname, depth=1)
	# if els:
	# 	els[0].sever()
	# doc.newElement(ne)
	

def drawEgg(doc, newname="elipse", arc=1.0, maa = 100, mia=50, xoff=0.0, yoff=0.0, ang = 45, stretch=2.0, mid=0.0, slope=.01):
	ang = ang*N.pi/180
	arc=arc*N.pi/180
	pts=_angleScan(_eggyweg, (maa, mia, xoff, yoff, ang, stretch, mid, slope), arc)
	pts = N.column_stack([pts, N.zeros(pts.shape[0])])
	ne=nmp.createElement("Fiducial", {"Style":"points", "width":5, "Name":newname})
	_setDisplayGroup(doc, [ne], "projections")
	ne.setPoints(pts)
	els = doc.getElements("Fiducial", newname, depth=1)
	if els:
		els[0].sever()
	doc.newElement(ne)

# def drawElipse(doc, newname="elipse", arc=1.0, maa = 100, mia=50, xoff=0.0, yoff=0.0, ang = 25):
# 	ang = ang*N.pi/180
# 	arc=arc*N.pi/180
# 	pts=_angleScan(_elipse, (maa, mia, xoff, yoff, ang), arc)
# 	pts = N.column_stack([pts, N.zeros(pts.shape[0])])
# 	ne=nmp.createElement("Fiducial", {"Style":"points", "width":5, "Name":newname, "DisplayGroup":"projections"})
# 	ne.setPoints(pts)
# 	els = doc.getElements("Fiducial", newname, depth=1)
# 	if els:
# 		els[0].sever()
# 	doc.newElement(ne)

