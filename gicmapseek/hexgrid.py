#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2008-08-28.

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

from mien.datafiles.dataset import *

C30=0.86602540378443871


__doc__='''
hexgrids are stored as MIEN Data instances  with 'SampleType':'hexgrid'
They rely on the following attributes:

SampleType: str 'hexgrid'
width: Int. The number of intersection points in a horizontal row of the mesh (the edges are chosen so that this is the same for each row)
edge: Float. The physical size of each grid edge. Usually this is in units of pixels in the original rectangular representation.
blanks: Float. Mask value to assign to unspecified points or edges. Usually -1


Each point in the hex grid corresponds to one row in the data array. These are stored such that the entire first horizontal row of points are coded left to right, followed by the second row, etc. Thus, the 3rd point in the 4th row of a grid with a width of 20 is stored on line 62 (y*w+x, where both x and y count starting with 0).

Each row contains 1, 3, or 6 columns of intensity values. In the one column case, the first column is a value associated to the grid point itself. In the 3 and 6 column cases, values are associated to the edges leading away from the point. These are indexed clockwise, starting with a move directly to the right (index+=1). For an initial index of i on a grid of width w the index reached by each edge is: 

c= divmod(i, w)[0]%2
i+1, i+w+c, i+w+c-1, i-1, i-w-c, i-w-c+1

Edges that travel off the specified grid (for example to an index smaller than 0, or on the edges of the grid, where i-1 or i+1 would in fact change rows) are assigned the value specified by the attribute 'blanks'.

Note that if there are six specified edges, then every edge that is specified at all is specified twice, once going from node A to node B, and again going from node b to node a. This is generally done when the edges have different weights in the different directions, corresponding to the case of a directed graph, and is often called a Directed grid. The 3 edge case is called an Non-directed grid, and the 1 value case is called a Point grid. Functions dealing with these different cases have the suffixes P, D, and ND, for example toHexP, toHexND, toHexD.

'''

INVERSES=[3, 4, 5, 0, 1, 2]

def hexItoXY(i, w, e, asint=True):
	r, x = divmod(i, w)
	c=r%2
	yc=r*e*C30
	xc=x*e+c*.5*e
	if asint:
		yc=int(round(yc))
		xc=int(round(xc))
	return (xc, yc)


def interpPts(pt1, pt2, npts):
	x=linspace(pt1[0], pt2[0], npts)
	y=linspace(pt1[1], pt2[1], npts)
	i=column_stack([x,y])
	i=around(i).astype(int32)
	return i

def calc3Edges(a, i, w, e, blanks):
	r, x = divmod(i, w)
	c=r%2
	edges=ones(3)*blanks
	cxc, cyc=hexItoXY(i, w, e)
	ioe=int(round(e))
	npts=ioe*2
	if x+1<w:
		ia=interpPts((cxc, cyc), (cxc+ioe, cyc), npts)
		edges[0]=a[ia[:,0], ia[:,1]].sum()
	nyc=cyc+int(round(e*C30))
	xshift=int(round(e/2.0))	
	if not nyc < a.shape[1]:
		return edges
	if x+c<w:
		ia=interpPts((cxc, cyc), (cxc+xshift, nyc), npts)
		edges[1]=a[ia[:,0], ia[:,1]].sum()
	if x+c-1>=0:
		ia=interpPts((cxc, cyc), (cxc-xshift, nyc), npts)
		edges[2]=a[ia[:,0], ia[:,1]].sum()
	return edges
	
def hexMap(l, w, block=None):
	'''Return an lx6 array containing the edge mapping for a hexgrid of l total elements with width w. Index (i, j) in the map contains the index of the row reprsenting the node reached by following the jth edge away from node i. Edges are indexed counter-clockwise, with edge 0 going towards the right. Edges that lead to nodes not included in the map have index -1 (the "blanks" attribute isn't used by hexMap, since non-blank values are always non-negative. If the argument "block" is specified, it should be a boolean array of lx6. In this case all indexes corresponding to True values of the array are left equal to -1 in the map, even if they lead to valid nodes.'''	
	z = ones((l,6))*-1
	for i in range(l):
		for j in range(6):
			if block!=None and block[i, j]:
				continue
			i2 = followEdge(i, j, w)
			if i2>=0 and i2<l:
				z[i,j]=i2
	return z.astype(int32)
	
def hexLocations(l, w, e=1.0):
	'''Returns an lx7x2 array of coordinates for a hexgrid with the specified l (number of total points) w (width) and e (edge length). For a return array X, X[i,j,0] is the x coordinate of the center of the jth edge leading away from point i, and X[i,j, 1] is the y coordinate for that edge. The 7th column along the second dimension contains coordinates for the points themselves, rather than edges, so X[i,6,0] is the x coordinate of grid point i. Coordinates of non-defined edges are set to (-1, -1).'''
	pointlocs = transpose(array(hexItoXY(arange(l),w,e,False)))
	hmap =  hexMap(l,w)
	locs = ones((l, 7, 2))*-1
	locs[:,6,:]=pointlocs
	for j in range(6):
		ok = hmap[:,j] > -1
		source = pointlocs[ok, :]
		target = pointlocs[hmap[:,j],:]
		target = target[ok, :]
		center = (source + target) / 2.0
		locs[ok,j,:] = center
	return locs	
			
	
	
def calcP(a, i, w, e, blanks):
	x, y = hexItoXY(i, w, e)
	return [a[x,y]]
	
def calcGradND(a, i, w, e, blanks):
	return calcGrad(a, i, w, e, blanks, True)

def calcGrad(a, i, w, e, blanks, ND=False):
	if ND:
		ndirs=3
	else:
		ndirs=6
	edges=ones(ndirs)*blanks
	npts=int(round(e*2))
	for j in range(ndirs):
		t=followEdge(i,j,w)
		if t==-1:
			continue
		tp=hexItoXY(t,w,e)
		if tp[1]>=a.shape[1]:
			continue
		sp=hexItoXY(i,w,e)
		ia=interpPts(sp, tp, npts)
		ia=a[ia[:,0], ia[:,1]]
		ia=ia[1:]-ia[:-1]
		if ND:
			ia=abs(ia)
		edges[j]=ia.sum()
	return edges
	
def toHex(dat, w, blanks, nm, getedge):
	if not type(dat)==Data:
		a=dat
		dat=newData(None, {})
	else:
		a=dat.getData()
	edge=(a.shape[0]-1.0)/(w+.5)
	h=int(floor(a.shape[1]/(edge*C30)))
	ni=w*h
	g=zeros((ni, nm))
	for i in range(ni):
		g[i,:]=getedge(a, i, w, edge, blanks)
	dat.datinit(g, {'SampleType':'hexgrid', 'width':w, 'blanks':blanks, 'edge':edge})	
	return dat

def toHexP(dat, w, blanks=-1):
	return toHex(dat, w, blanks, 1, calcP)
	
def toHexND(dat, w, blanks=-1):
	'''Convert the Data instance dat to an undirected hexgrid using the specified parameters. dat may also be an array'''
	return toHex(dat, w, blanks, 3, calc3Edges)

def toHexGradND(dat, w, blanks=-1):
	return toHex(dat, w, blanks, 3, calcGradND)

def toHexGrad(dat, w, blanks=-1):
	return toHex(dat, w, blanks, 6, calcGrad)

def followEdge(i, j, w):
	'''returns the index of the point on the other end of the jth edge from point i in a grid of width w. Return -1 if that isn't a point in the map.'''
	r, x = divmod(i, w)
	c=r%2
	if j==0:
		if x+1>=w:
			return -1
		return i+1
	elif j==1:
		if x+c>=w:
			return -1
		return i+w+c
	elif j==2:
		if x+c-1<0:
			return -1
		return i+w+c-1
	elif j==3:
		if x<1:
			return -1
		return i-1
	elif r<1:
		return -1
	elif j==4:
		if x+c-1<0:
			return -1
		return i-w+c-1
	elif j==5:
		if x+c>=w:
			return -1
		return i-w+c


def getAdjacentPoints(i, w):
	c= divmod(i, w)[0]%2
	e=[i+1, i+w+c, i+w+c-1, i-1, i-w+c-1, i-w+c]
	return e
	
def xyToHexI(pt, w, e):
	'''Return the index associated to a point (x, y)'''
	r = int(round(pt[1]/(C30*e)))
	if r<0:
		return None
	c=r%2
	x=pt[0]-c*.5*e
	x=int(round(x/e))
	if x>w or x<0:
		return None
	if x==w:
		x=w-1
	i=r*w+x
	return i
	
def nd2d(a, w, blanks):
	'''converts a non-directed grid (3 column) to a directed grid (6 column)'''
	out=zeros((a.shape[0], 6))
	out[:,:3]=a
	for i in range(out.shape[0]):
		for j in range(3,6):
			t=getEdgeCostAndTarget(a, i, j, w)
			if t:
				out[i,j]=t[1]
			else:
				out[i,j]=blanks
	return out
	
def getEdgeCostAndTarget(a, i, j, w):
	t=followEdge(i,j,w)
	if t==-1:
		return None
	if j<a.shape[1]:
		return (t, a[i,j])
	else:
		return (t, a[t, j-3])
		
	
def  lineCoordsFromHex(a, w, e, b=None):
	pts=[]
	for i in range(a.shape[0]):
		for j in range(a.shape[1]):
			if b and a[i, j]==b:
				continue
			i2=followEdge(i, j, w)
			if i2!=-1:
				p1=hexItoXY(i, w, e, False)
				p2=hexItoXY(i2, w, e, False)
				pts.append([p1[0], p1[1], p2[0], p2[1], a[i,j] ])
	return array(pts)

def  halfLinesFromHex(a, w, e, b=None):
	pts=[]
	for i in range(a.shape[0]):
		for j in range(a.shape[1]):
			if b and a[i, j]==b:
				continue
			i2=followEdge(i, j, w)
			if i2!=-1:
				p1=hexItoXY(i, w, e, False)
				p2=hexItoXY(i2, w, e, False)
				p2=[ float(p1[0]+p2[0])/2.0, float(p1[1]+p2[1])/2.0 ]
				pts.append([p1[0], p1[1], p2[0], p2[1], a[i,j] ])
	return array(pts)
	
					
def pathSeparation(p1, p2, w):
	'''return the number of edge traversals required to reach p2 from p1'''
	r1, x1 = divmod(p1, w)
	r2, x2 = divmod(p2, w)
	x1+=.5*(r1%2)
	x2=x2+.5*(r2%2)
	dr=abs(r1-r2)
	dx=abs(x1-x2)
	d=dr+max(0, round(dx-dr/2.0))
	return d
	
def findConnectingEdge(p1, p2, w):
	'''return the index (0-5) of the edge that should be followed from p1 to reach p2. If p1 is not adjacent to p2, return -1'''
	for j in range(6):
		if followEdge(p1, j, w)==p2:
			return j
	return -1
	
				
				