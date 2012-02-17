#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2008-02-04.

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

import pullsdts.sdts as sd
from numpy import array, transpose, where
import mien.nmpml.data as mdat
import re

def getDem(idfn):
	c=sd.sdtsClass(None, idfn)
	c.getSelf(['IDEN'])
	c.type=sd.sdtsQuery(c,'DAST','IDEN')
	c.initKeyInfo()
	info=sd.sdtsDEMreport(c)
	c.getSpecial('CEL0')
	ed=c.keyInfo.elevDict
	info={}
	info['elevationFill']=ed['fill']
	info['elevationVoid']=ed['void']
	info['elevationRange']=[ed['zMin'], ed['zMax']]
	cd=c.keyInfo.cornerDict
	info['utmRange']=[cd['xMin'], cd['xMax'], cd['yMin'], cd['yMax']]
	info['utmZone']=c.keyInfo.utmZone
	info['elevationUnits']=c.keyInfo.unitZ
	ddf=c.ddf[c.ddfDict['CEL0']][1]
	a=transpose(array(ddf.data))
	return (c.keyInfo.name, a,info)

def read(f, **kwargs):
	fn=f.name
	f.close()
	name, data, header=getDem(fn)
	
	node={'tag':"Nmpml", 'attributes':{'Name':'0'}, 'elements':[], 'cdata':''}
	document = mdat.basic_tools.NmpmlObject(node)
	
	name=re.sub("\W+", "_", name)
	node={'tag':"Data", 'attributes':{'Name':name}, 'elements':[], 'cdata':''}
	dc=mdat.Data(node)
	if kwargs.get('literal'):
		header['SampleType']='sfield'
	else:
		header['SampleType']='timeseries'
		header['SamplesPerSecond']=1.0
		tm=where(data==header['elevationVoid'],data.max(), data)
		if header['elevationVoid']!=header['elevationFill']:
			data=where(data==header['elevationFill'],data.max(), data)
		mini=data.min()
		data=where(data==header['elevationVoid'], mini, data)
		if header['elevationVoid']!=header['elevationFill']:
			data=where(data==header['elevationFill'],mini, data)
		header['elevationVoid']=mini
		header['elevationFill']=mini
		header['conertedForDataViewer']=1		
	document.newElement(dc)
	dc.datinit(data, header)
	return document
	


ftype={'notes':'Reads SDTS transfer files, but only if the opened file is the ident.ddf of an expanded ddf directory containing DEM information. Requires pullsdts module. Also only works for local files, due to limitations in my use of the pullsdts API',
		'read':read,
		'data type':'Numerical data',
		'elements':['Data'],
		'extensions':['.ddf']}	
	
	
	
	
	