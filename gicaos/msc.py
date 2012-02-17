#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2008-06-25.

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
from gicmapseek.mapseek import MapSeeker, Transform

def makeball(xc, yc, r, shape):
	rs=r**2
	def ballf(x,y):
		return (x-xc)**2+(y-yc)**2<=rs 
	return fromfunction(ballf, shape[:2])


class ImageTransform(Transform):
	def match(self, image, target):
		return dot(image.flat, target.flat)
		
	def apply(self, inp, g, target=None, inv=1):
		out=zeros_like(inp)
		if target!=None:
			q=zeros(len(self))
		for i in nonzero1d(g):
			o=self.ithtransform(inp, i, inv)
			if target!=None:
				q[i]=self.match(o, target)
			o*=g[i]
			out+=o	
		out/=out.sum()
		if target==None:
			return out
		else:
			return (out,q)	


class HShift(ImageTransform):
	def __init__(self, maxlength):
		self.tvec=arange(-maxlength, maxlength+1)		
	
	def ithtransform(self, inp, i, inv):
		tv=inv*self.tvec[i]
		if tv==0:
			return inp  # do we need copy??
		out=zeros_like(inp)
		if tv>0:
			out[tv:,:]=inp[:-tv,:]
		else:
			out[:tv,:]=inp[-tv:,:]
		return out		

	def get(self, i):
		return "%i pixel horizontal shift" % (self.tvec[i],)	
	
class VShift(ImageTransform):
	def __init__(self, maxlength):
		self.tvec=arange(-maxlength, maxlength+1)	
	
	def ithtransform(self, inp, i, inv):
		tv=inv*self.tvec[i]
		if tv==0:
			return inp  # do we need copy??
		out=zeros_like(inp)
		if tv>0:
			out[:,tv:]=inp[:,:-tv]
		else:
			out[:,:tv]=inp[:,-tv:]
		return out		

	def get(self, i):
		return "%i pixel vertical shift" % (self.tvec[i],)	

def _scale(i, s):
	w=i.shape[0]*s
	h=i.shape[1]*s
	ws=uniformSampleIndex(i.shape[0], w)
	hs=uniformSampleIndex(i.shape[1], h)	
	i=i[ws,:]
	i=i[:,hs]
	return i
	
def _center(i, s):
	hos=i.shape[0]-s[0]
	hos=int(round(hos/2.0))
	vos=i.shape[1]-s[1]
	vos=int(round(vos/2.0))
	if min(hos, vos)>=0:
		return i[hos:hos+s[0], vos:vos+s[1]]
	if hos>=0:
		i=i[hos:hos+s[0], :]
	else:
		hos=-hos
		ht=s[0]-i.shape[0]-hos
		sp=zeros((hos, i.shape[1]), i.dtype)
		ep=zeros((ht, i.shape[1]), i.dtype)
		i=vstack([sp, i, ep])
	if vos>=0:
		return i[:,vos:vos+s[1]]
	else:
		vos=-vos
		vt=s[1]-i.shape[1]-vos
		sp=zeros((i.shape[0], vos), i.dtype)
		ep=zeros((i.shape[0], vt), i.dtype)
		return hstack([sp, i, ep])

class BinImScale(ImageTransform):
	def __init__(self, maxscale=10):
		self.tvec=arange(1, maxscale+1).astype(float32)
		
	def ithtransform(self, inp, i, inv):
		tv=self.tvec[i]
		if tv==1:
			return inp  # do we need copy??
		if inv<0:
			tv=1.0/tv
		s=inp.shape
		inp=_scale(inp, tv)
		inp=_center(inp, s)		
		#print tv, inp.shape, inp.sum()
		return inp	

	def get(self, i):
		return "%.1f scale" % (self.tvec[i],)			
	pass

def getFinalImage(msc):
	s=[argmax(msc.layers[li]['gain']) for li in range(1, len(msc.layers))]
	im=msc.layers[0]['for']
	for li, ti in enumerate(s):
		tran=msc.getTrans(li+1)
		print tran.get(ti)
		im=tran.ithtransform(im, ti, 1)
	return im

def run_msc(target):
	print target.shape
	source=makeball(target.shape[0]/2, target.shape[1]/2, 2, target.shape)
	trans=[]
	#trans.append(BinImScale(1))
	trans.append(HShift(target.shape[0]/2))
	trans.append(VShift(target.shape[1]/2))
	ms=MapSeeker(trans, {'maxiter':200, 'kappa':0.2, 'rule':'kappa', 'checkdomain':False, 'silent':2})
	print source.shape, target.shape
	ms.run(source.astype(float32),target.astype(float32))
	return ms

	
