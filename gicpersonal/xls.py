#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2008-02-14.

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
import mien.parsers.nmpml as nmpml
import pyExcelerator as pe
import mien.nmpml.data as mdat


def makeDat(n, d,h):
	node={'tag':"Data", 'attributes':{'Name':n}, 'elements':[], 'cdata':''}
	dc=mdat.Data(node)
	dc.datinit(d, h)
	return dc
	

def xl2data(o):
	n=o[0]
	d=o[1]
	if not d:
		return None
	z=mdat.array(d.keys())
	w=z[:,1].max()+1
	l=z[:,0].max()+1
	lab=None
	start=0
	lines=[]
	for i in range(l):
		b=[]
		for j in range(w):
			if not d.has_key((i,j)):
				break
			b.append(d[(i,j)])
		else:
			try:
				line=map(float, b)
				lines.append(line)
			except:
				if not lab:
					lab=b
	if not lines:
		return None	
	h={}
	if lab:
		h['Labels']=lab
	h['SampleType']='timeseries'
	h['SamplesPerSecond']=1.0
	d=mdat.array(lines)
	return makeDat(n, d, h)

def read(f, **kwargs):
	objs=pe.parse_xls(f.name)
	data=[]
	for o in objs:
		dat=xl2data(o)
		if dat:
			data.append(dat)
	node={'tag':"Nmpml", 'attributes':{'Name':'0'}, 'elements':[], 'cdata':''}
	document = mdat.basic_tools.NmpmlObject(node)
	for d in data:
		document.newElement(d)
	return document

ftype={'notes':'read only support, and only converts data sheets',
		'read':read,
		'data type':'Numerical data',
		'elements':['Data'],
		'extensions':['.xls']}
