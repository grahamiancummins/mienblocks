#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-05-20.

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

from mien.image.imagetools import *

def invert(doc, image, outputPath="CALC"):
	a, h = getImageDataAndHeader(doc, image)
	am = a.max()
	a = float(am) - a.astype(float32)
	a = (255*a/am).astype(uint8)
	if not outputPath:
		outputPath=image
	setImageData(a, outputPath, doc, h)
	
def subtractStackMean(doc, image, outputPath="CALC"):
	a, h = getImageDataAndHeader(doc, image)
	a = a.astype(float32)
	a-=a.mean(3)[:,:,:,newaxis]
	#a=a.astype(uint8)
	if not outputPath:
		outputPath=image
	setImageData(a, outputPath, doc, h)
	
def inverseThreshold(doc, image, thresh=128, outputPath="CALC"):
	a, h = getImageDataAndHeader(doc, image)
	a = (a<thresh).astype(uint8)*255
	if not outputPath:
		outputPath=image
	setImageData(a, outputPath, doc, h)
	
def addStack(doc, image, outputPath="CALC"):
	a, h = getImageDataAndHeader(doc, image)
	out = zeros((a.shape[0], a.shape[1], a.shape[2], 1), float32)
	for i in range(a.shape[3]):
		out+=a[...,i:i+1]
	out = out/a.shape[3]
	out = out.astype(uint8)
	if not outputPath:
		outputPath=image
	setImageData(out, outputPath, doc, h)	