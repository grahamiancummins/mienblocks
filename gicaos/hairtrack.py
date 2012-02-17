#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2008-06-24.

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
from mien.image.stacks import fromTimeSeries, frameCompare
from mien.image.simple import pad
from mien.image.metrics import measureAngle
from mien.math.fit import regress
import scipy.signal
from numpy.random import permutation
#import sparsemsc
#reload(sparsemsc)
#import msc
#reload(msc)


def setTimeseriesData(doc, image, dat, path, labels=None):
	dat=array(dat)
	if not path:
		path=image
	path=path+"_timeseries"
	if not ":" in path:
		path="/Data:"+path
	i=doc.getInstance(image)
	ss=i.attrib('StackSpacing')
	if not ss:
		print("Warning: no stack spacing specified. Timeseries generated at 1.0 Hz")
	fs=1.0/ss
	h={'SampleType':'timeseries', 'SamplesPerSecond':fs}
	if labels:
		h['Labels']=labels
	e=forceGetPath(doc, path)
	e.datinit(dat, h)
	return e.upath()


def _makeline(s,o, shape):
	def linef(x,y):
		return abs(y-(s*x+o))<=1
	return fromfunction(linef, shape[:2])

def lineImage(doc, s=1.0, o=5.0):
	dat=_makeline(s,o, (300,200))
	dat*=255
	setImageData(dat, 'line', doc)

def findLine(doc, image, outputPath='line'):
	'''finds the best fit line in the indicated frame'''
	dat=getImageData(doc, image)
	if not isBinary(dat):
		print("Warning: dat is not binary. Using an automatic threshold")
		me, ma, st= dat.mean(), dat.max(), dat.std()
		thresh=min(ma-st, me+st)
		dat=dat>=thresh
	frames=range(dat.shape[3])
	get=[]
	lines=[]
	for frame in frames:
		df=dat[:,:,0,frame]
		ind=transpose(array(nonzero(df))).astype(float32)
		m, b = regress(ind)
		lines.append((m,b))
		line=_makeline(m, b, df.shape)
		df=colorOverlay(df, line)
		get.append(df)
	df=concatenate(get, 3)
	setImageData(df, outputPath or image, doc)
	setTimeseriesData(doc, image, lines, outputPath, ['Slope', 'Intercept'])
	

def findPoint(doc, image, outputPath='point'):
	dat=getImageData(doc, image)
	if not isBinary(dat):
		print("Warning: dat is not binary. Using an automatic threshold")
		me, ma, st= dat.mean(), dat.max(), dat.std()
		thresh=min(ma-st, me+st)
		dat=dat>=thresh
	frames=range(dat.shape[3])
	get=[]
	points=[]
	for frame in frames:
		df=dat[:,:,0,frame]
		ind=transpose(array(nonzero(df))).astype(float32)
		m, b = regress(ind)
		x=ind[:,0].mean()
		y=m*x+b
		points.append((x,y))
		pt=zeros_like(df)
		pt[x,y]=1.0
		df=colorOverlay(df, pt)
		get.append(df)
	df=concatenate(get, 3)
	setImageData(df, outputPath, doc)
	setTimeseriesData(doc, image, points, outputPath, ['X', 'Y'])
	

def rot90CW(doc, image, outputPath=''):
	dat, h=getImageDataAndHeader(doc, image)
	dat=transpose(dat, [1,0,2,3])
	dat=dat[arange(dat.shape[0]-1,-1,-1),:,:,:]
	setImageData(dat, outputPath or image, doc, h)


def sparseBallMSC(doc, image, outputPath=''):
	dat, h=getImageDataAndHeader(doc, image)
	fs=[]
	for frame in range(dat.shape[3]):
		print('matching frame %i' % frame)
		df=dat[:,:,0,frame].copy()
		ms=sparsemsc.run_msc(df)
		im=sparsemsc.getFinalImage(ms)
		im=colorOverlay(im, df)
		fs.append(im)
	dat=concatenate(fs, 3)
	setImageData(im, outputPath or image, doc, h)

def remFrameMean(doc, image, outputPath='nomean'):
	dat, h=getImageDataAndHeader(doc, image, float32)
	dat=dat-dat.mean(3)[:,:,:,newaxis]
	for i in range(dat.shape[3]):
		fmv=dat[:,:,:,i].min()
		fev=dat[:,:,:,i].mean()
		fxv=dat[:,:,:,i].max()
		dat[:,:,:,i]=255*maximum((dat[:,:,:,i]-fev), 0)/(fxv-fev)
		#print "frame %i. min: %.3f mean %.3f, max %.3f" % (i, dat[:,:,:,i].min(), dat[:,:,:,i].mean(), dat[:,:,:,i].max())
	setImageData(dat, outputPath or image, doc, h)
	

def timeDeriv(doc, image, outputPath='ddt'):
	dat, h=getImageDataAndHeader(doc, image, float32)
	td=zeros_like(dat)
	for i in range(1, dat.shape[3]):
		td[:,:,:,i-1]=dat[:,:,:,i]-dat[:,:,:,i-1]
	setImageData(td[:,:,:,:-1], outputPath or image, doc, h)
	

def ballMSC(doc, image, outputPath=''):
	dat, h=getImageDataAndHeader(doc, image)
	fs=[]
	for frame in range(dat.shape[3]):
		print('matching frame %i' % frame)
		df=dat[:,:,0,frame].copy()
		ms=msc.run_msc(df)
		im=msc.getFinalImage(ms)
		im=colorOverlay(im, df)
		fs.append(im)
	dat=concatenate(fs, 3)
	setImageData(dat, outputPath or image, doc, h)


# def rectMSC(doc, image, width=5, height=30):
# 	dat, h=getImageDataAndHeader(doc, image)
# 	fs=[]
# 	for frame in range(dat.shape[3]):
# 		print('matching frame %i' % frame)
# 		df=dat[:,:,0,frame].copy()
# 		ms=msc.run_msc(df)
# 		im=msc.getFinalImage(ms)
# 		im=colorOverlay(im, df)
# 		fs.append(im)
# 	dat=concatenate(fs, 3)
# 	setImageData(dat, outputPath or image, doc, h)


def _getFrameMax(db, dat):
	get=[]
	points=[]
	for frame in range(dat.shape[3]):
		df=db[:,:,0,frame]
		x, y = divmod(argmax(df), df.shape[1])
		points.append((x,y))
		pt=zeros_like(df)
		pt[x,y]=1.0
		df=colorOverlay(dat[:,:,0,frame], pt)
		get.append(df)
	df=concatenate(get, 3)
	return (array(points), df)


def frameOverlay(doc, imageA, imageB, outputPath=''):
	dat1, h = getImageDataAndHeader(doc, imageA)
	dat2, h = getImageDataAndHeader(doc, imageB)
	dat3=zeros_like(dat1)
	xv=dat1.max()
	mv=dat1.min()
	iv=xv+.1*(xv-mv)
	for i in range(dat1.shape[3]):
		mask=dat2[:,:,:,i]!=0
		dat3[:,:,:,i]=where(mask, iv, dat1[:,:,:,i])
	setImageData(dat3, outputPath or imageA, doc)

def _vizPt(doc, datpath, vispath, sshape, overlay=None):
	if not vispath:
		return
	image=vispath
	if not ":" in image:
		image="/Data:" + image
	fromTimeSeries(doc, datpath, ptsize=4.0, outputPath=image)
	vd, h = getImageDataAndHeader(doc, image)
	hpad=sshape[0]-vd.shape[0]
	vpad=sshape[1]-vd.shape[1]
	pad(doc, image, left=0, right=hpad, top=0, bottom=vpad)
	if overlay:
		frameOverlay(doc, overlay, image, image)


def findVcolMax(doc, image, width=5, outputPath='blurmaxdata', outputPathVis='blurmaxvis'):
	'''Find the brightest column '''
	dat, h = getImageDataAndHeader(doc, image, float32)
	pts=[]
	for i in range(dat.shape[3]):
		x=dat[:,:,0,i].sum(1)
		if width>1:
			x=convolve(ones(width), x, mode='same')
		x=argmax(x)
		y=int(dat.shape[1]/2)
		pts.append((x, y))
	datpath=setTimeseriesData(doc, image, array(pts), outputPath, labels=['X', "Y"])
	_vizPt(doc, datpath, outputPathVis, dat.shape, image)

def testTSOnImage(doc, image, upathTS='/Data:element2'):
	dat, h = getImageDataAndHeader(doc, image, float32)
	ts = doc.getInstance(upathTS).data
	y = int(dat.shape[1]/2) * ones_like(ts)
	ts = column_stack([ts, y])
	datpath=setTimeseriesData(doc, image, ts, 'bogo', labels=['X', "Y"])
	_vizPt(doc, datpath, 'vis', dat.shape, image)
	

# def findYLevel(doc, image,  outputPath='top'):
# 	dat, h = getImageDataAndHeader(doc, image, float32)
# 	ccs=convolve(array([1,1,1,1,1]), dat[:,0,0,:].sum(1)).max()
# 	mv=ccs
# 	mi=0
# 	print mv
# 	for i in range(1,dat.shape[1]):
# 		x=convolve(array([1,1,1,1,1]), dat[:,i,0,:].sum(1)).max()
# 		ccs+=x
# 		print i, x, ccs, ccs/float(i+1)
# 		x=ccs/float(i+1)
# 		if x>mv:
# 			print "max"
# 			mv=x
# 			mi=i
# 	dat=dat[:,:mi+1,:,:]
# 	setImageData(dat, outputPath or image, doc, h)

def angleFromVertical(doc, point1, point2):
	'''Measures the angle between the horizontal and the line segment defined by two points, in degrees counterclockwise. This is such that fastRotate on the negative of the returned angle will render the line segment horizontal in the resulting image'''
	point3=(point2[0], point2[1]+5)
	measureAngle(doc, point3, point2, point1)

def _makegauss(c, sd, shape):
	def gaussf(x,y):
		return (1/(2*pi*sd**2))*exp( -1*( (x-c[0])**2+(y-c[1])**2)  / (2*sd**2) )
	return fromfunction(gaussf, shape[:2])


def autoRotate(doc, image, nframes=2, thresh = .8, outputPath='rot'):
	dat, h = getImageDataAndHeader(doc, image, float32)
	sdat = permutation(arange(dat.shape[3]))[:nframes]
	sdat = dat[...,sdat]
	sdat = sdat>=thresh*sdat.max()
	angs = arange(-30, 31)
	fit = []
	for ang in angs:
		z = _imrotate(sdat, ang)
		z = z.sum(1).sum(1).sum(1)
		fit.append(z.max())
	a = angs[argmax(fit)]
	dat = _imrotate(dat, a)
	setImageData(dat, outputPath or image, doc, h)

# def tRot(doc, image, ang=20, outputPath='rot'):
# 	dat, h = getImageDataAndHeader(doc, image, float32)
# 	dat = _imrotate(dat, ang)
# 	v = dat.sum(1).sum(1).sum(1)
# 	print v.shape
# 	print v.max(), v.mean()
# 	setImageData(dat, outputPath or image, doc, h)
	

def _imrotate(dat, ang):
	ang=ang % 360
	if ang==0:
		dat=dat.copy()
	elif ang==90:
		dat=transpose(dat, [1,0,2,3])
	elif ang==180:
		dat=dat[arange(dat.shape[0]-1,-1,-1),:,:,:]
		dat=dat[:,arange(dat.shape[1]-1,-1,-1),:,:]
	elif ang==270:
		dat=transpose(dat, [1,0,2,3])
		dat=dat[arange(dat.shape[0]-1,-1,-1),:,:,:]
	else:
		ind=transpose(array(nonzero(ones(dat.shape[:2]))))
		s=(dat.shape[0]/2, dat.shape[1]/2)
		rind=ind.astype(float32)-s
		rind=rotate(rind, ang)
		rind=roundtoint(rind)+s
		gi=nonzero(logical_and(all(rind>=(0,0), 1), all(rind<dat.shape[:2],1)))
		ind=ind[gi]
		rind=rind[gi]
		out=ones_like(dat)*dat.mean()
		out[ind[:,0], ind[:,1], :, :]=dat[rind[:,0], rind[:,1], :, :]
		dat = out
	return dat

def _doBlur(dat, filt):
	m=dat.max()
	mi=dat.min()
	for i in range(dat.shape[2]):
		for j in range(dat.shape[3]):
			dc=scipy.signal.convolve2d(dat[:,:,i,j], filt, mode='same')
			dat[:,:,i,j]=dc
	dat-=dat.min()
	dat/=dat.max()
	dat*=(m-mi)
	dat+=mi
	return dat

	

def _blurMax(im, filt, mode=None):
	db=scipy.signal.convolve2d(im, filt, mode='same')
	if mode=='abs':
		db=abs(db)
	x, y = divmod(argmax(db), db.shape[1])
	return (x, y)

def findDiskMax(doc, image, diskRadius=2.0, outputPath='blurmaxdata', outputPathVis='blurmaxvis'):
	'''Find the max point in a disk blurred image '''
	dat, h = getImageDataAndHeader(doc, image, float32)
	filt=msc.makeball( diskRadius, diskRadius, diskRadius, (2*diskRadius+1, 2*diskRadius+1))
	pts=[]
	for i in range(dat.shape[3]):
		pts.append(_blurMax(dat[:,:,0,i], filt))
	datpath=setTimeseriesData(doc, image, array(pts), outputPath, labels=['X', "Y"])
	_vizPt(doc, datpath, outputPathVis, dat.shape)

def findDiskMaxWithXYCost(doc, image, diskRadius=2.0, thresh=.8, ypen=-.2, xpen=0.0, outputPath='blurmaxdata', outputPathVis='blurmaxvis'):
	'''Find the max point in a disk blurred image '''
	dat, h = getImageDataAndHeader(doc, image, float32)
	filt=msc.makeball( diskRadius, diskRadius, diskRadius, (2*diskRadius+1, 2*diskRadius+1))
	pts=[]
	for i in range(dat.shape[3]):
		db=scipy.signal.convolve2d(dat[:,:,0,i], filt, mode='same')
		if thresh:
			db=where(db>db.max()*thresh, db, 0)
		if xpen:
			p=1.0 - xpen*arange(db.shape[0])/float(db.shape[0])
			db=db*p[:,newaxis]
		if ypen:
			p=1.0 - ypen*arange(db.shape[1])/float(db.shape[1])
			db=db*p[newaxis,:]
		x, y = divmod(argmax(db), db.shape[1])
		pts.append((x, y))
	datpath=setTimeseriesData(doc, image, array(pts), outputPath, labels=['X', "Y"])
	_vizPt(doc, datpath, outputPathVis, dat.shape)

def findDiskMaxWithMovementCost(doc, image, diskRadius=2.0, thresh=.8, mvtSD=10.0, outputPath='blurmaxdata', outputPathVis='blurmaxvis'):
	'''Find the max point in a disk blurred image '''
	dat, h = getImageDataAndHeader(doc, image, float32)
	filt=msc.makeball( diskRadius, diskRadius, diskRadius, (2*diskRadius+1, 2*diskRadius+1))
	pts=[]
	for i in range(dat.shape[3]):
		db=scipy.signal.convolve2d(dat[:,:,0,i], filt, mode='same')
		if thresh:
			db=where(db>db.max()*thresh, db, 0)
		if mvtSD and i>0:
			p=_makegauss(pts[i-1], mvtSD, db.shape)
			db*=p
		x, y = divmod(argmax(db), db.shape[1])
		pts.append((x, y))
	datpath=setTimeseriesData(doc, image, array(pts), outputPath, labels=['X', "Y"])
	_vizPt(doc, datpath, outputPathVis, dat.shape, image)

def findRectMax(doc, image, width=2, height=2, outputPath='blurmaxdata', outputPathVis='blurmaxvis'):
	'''Find the max point in a rectangle blurred image '''
	dat, h = getImageDataAndHeader(doc, image, float32)
	filt=ones((width, height), float32)
	pts=[]
	for i in range(dat.shape[3]):
		pts.append(_blurMax(dat[:,:,0,i], filt))
	datpath=setTimeseriesData(doc, image, array(pts), outputPath, labels=['X', "Y"])
	_vizPt(doc, datpath, outputPathVis, dat.shape)
	

def findEdgeMax(doc, image, width=2, height=2, outputPath='blurmaxdata', outputPathVis='blurmaxvis'):
	'''Find the max point in a rectangle blurred image '''
	dat, h = getImageDataAndHeader(doc, image, float32)
	filt=ones((width, height), float32)
	filt=column_stack([filt, -filt])
	pts=[]
	for i in range(dat.shape[3]):
		pts.append(_blurMax(dat[:,:,0,i], filt, mode='abs'))
	datpath=setTimeseriesData(doc, image, array(pts), outputPath, labels=['X', "Y"])
	_vizPt(doc, datpath, outputPathVis, dat.shape)


		
		