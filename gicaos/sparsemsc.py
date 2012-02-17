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
from gicmapseek.refinements import LocalizingVectorField

class AShift(Transform):
	def __init__(self, maxlength, axis, spacesize):
		self.space=LocalizingVectorField(spacesize)
		self.axis=axis
		self.bias=None
		self.tvec=arange(-maxlength, maxlength+1)		
	
	def ithtransform(self, inp, i, inv):
		tv=inv*self.tvec[i]
		if tv==0:
			return inp.clone()  # do we need copy??
		out=zeros_like(inp)		
		ind,v=inp.get(copy=True)
		ind[:,self.axis]+=tv
		return inp.new((ind,v))	
		
	def get(self, i):
		return "%i pixel horizontal shift" % (self.tvec[i],)	



def getFinalImage(msc):
	s=[argmax(msc.layers[li]['gain']) for li in range(1, len(msc.layers))]
	im=msc.layers[0]['for']
	for li, ti in enumerate(s):
		tran=msc.getTrans(li+1)
		print tran.get(ti)
		im=tran.ithtransform(im, ti, 1)
	im=im.full()
	return im 

def run_msc(target):
	lv=LocalizingVectorField(target.shape)
	source=lv.local(array([target.shape[0]/2, target.shape[1]/2]), 2)
	trans=[]
	#trans.append(BinImScale(1))
	trans.append(AShift(target.shape[0]/2, 0, target.shape))
	trans.append(AShift(target.shape[1]/2, 1, target.shape))
	ms=MapSeeker(trans, {'maxiter':200, 'kappa':0.2, 'rule':'kappa', 'silent':2})
	target=lv.fromFull(target)
	o=target.full()
	ms.run(source,target)
	return ms

	