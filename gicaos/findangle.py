#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2008-06-27.

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
from mien.image.imagetools import *
from mien.image.stacks import fromTimeSeries
from mien.image.simple import pad
from mien.math.fit import regress
#from msc import makeball
from hairtrack import _makeline

def makeball(xc, yc, r, shape):
	rs=r**2
	def ballf(x,y):
		return (x-xc)**2+(y-yc)**2<=rs
	return fromfunction(ballf, shape[:2])


def _angle(point1, point2, point3):
	ls1=array(point1)-array(point2)
	ls2=array(point3)-array(point2)
	ls1=_norm(ls1)
	ls2=_norm(ls2)
	a=arccos(dot(ls1, ls2))
	a=180*a/pi
	return a

def _ptoline(x,y,m,b):
	v=[m, 1.0]
	uv=array([1.0, m])/(sqrt(1+m**2))
	d=uv*dot(uv, array((x,y-b)))
	v=d+array([0,b])
	#print x,y,m,b,v
	return v

def showProjection(doc, upath="/Data:DataFile"):
	nip='/Data:proj'
	ndat=doc.getInstance(upath).getData()
	fromTimeSeries(doc, upath, 2.0, width=-1, outputPath=nip)
	#pad(doc, nip, 10, 10, 50, 50)
	idat, h=getImageDataAndHeader(doc, nip)
	ndat-=array(h['SpatialAnchor'][:2])
	m, b = regress(ndat)
	line=255*_makeline(m, b, idat.shape)
	line=reshape(line, (line.shape[0], line.shape[1], 1, 1))
	df=colorOverlay(idat, line)
	frames=[]
	for i in range(idat.shape[3]):
		x, y = _ptoline(ndat[i,0], ndat[i,1], m, b)
		ball = 255*makeball(x, y, 1.0, idat.shape)
		ball=reshape(ball, (ball.shape[0], ball.shape[1], 1, 1))
		frames.append(concatenate([idat[:,:,:,i:i+1], line, ball], 2))
	df=concatenate(frames, 3)
	setImageData(df, nip, doc)


def writeParameterFile(doc, pointUL=(0,0), pointLR=(400,300), pointHair1=(200,300), pointHair2=(200,0), frameStart=0, nframes=-1, fname='batch_parameters.txt'):
	xmin = min(pointUL[0], pointLR[0])
	xmax = max(pointUL[0], pointLR[0])
	ymin = min(pointUL[1], pointLR[1])
	ymax = max(pointUL[1], pointLR[1])
	dy=abs(pointHair1[1]-pointHair2[1])
	dx=pointHair2[0]-pointHair1[0]
	if pointHair1[1]<pointHair2[1]:
		dx=-dx
	afv=arctan(float(dx)/dy)
	afv=180*afv/pi
	print pointHair1, pointHair2, dy, dx, afv
	ps="--xmin %i --ymin %i --xmax %i --ymax %i --startframe %i" % (xmin, ymin, xmax, ymax, frameStart)
	if nframes>0:
		ps+=" -nframes %i" % (nframes,)
	if abs(afv)>5:
		ps+=" --rotate %G" % afv
	ps+="\n"
	print ps
	open(fname, 'w').write(ps)
	
	
	
	