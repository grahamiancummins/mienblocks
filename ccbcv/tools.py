#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2008-11-03.

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
import re, os
import mien.parsers.fileIO as io
from mien.spatial.alignment import alignObject

aff_file_name = re.compile('([lms])\.(\d+)\.(\d+)\.(\d+).*')

length_abbrv = {'l':'long', 'm':'medium', 's':'short'}

def getAff(fname):
	m = aff_file_name.match(fname.lower())
	if not m:
		print "no match"
		return None
	length, aclass, instar, slide = m.groups()
	print length, aclass, instar, slide
	if instar!="10":
		print "instar !=10"
		return None
	doc = io.read(fname)
	for e in doc.getElements(depth=1):
		if not e.__tag__ in ['Cell', 'Fiducial']:
			e.sever()
		e.setAttrib('meta_length', length_abbrv[length])
		e.setAttrib('meta_class', aclass)
		e.setAttrib('meta_instar', 10)
		e.setAttrib('meta_slide_number', slide)
		e.setAttrib('meta_cercus', 'left')
	return doc
			
def convert_aff(fname, scale=1.0):
	doc = getAff(fname)
	if not doc:
		return
	if scale!=1.0:
		sd={ 'Scale_x':scale, 'Scale_y':scale, 'Scale_z':scale}
		for e in doc.getElements(depth=1):
			alignObject(e, sd)
	fname = os.path.splitext(fname)[0]+'.nmpml'
	io.write(doc, fname, format='nmpml')

def make_map(dir):
	doc = io.read(os.path.join(dir, 'standard_outline.123.nmpml'))
	invert = { 'Scale_x':-1.0}
	for fn in os.listdir(dir):
		if not fn[0] in ['L', 'M', 'S']:
			continue
		if not fn.endswith('nmpml'):
			continue
		d2=io.read(os.path.join(dir, fn))
		varic = d2.getElements('Fiducial', {"Style":'spheres'})[0]
		for s in ["color", "Color", "Direction"]:
			if s in varic.attributes:
				del(varic.attributes[s])		
		right_varic = varic.clone()
		right_varic.setAttrib('meta_cercus', 'right')
		right_varic.setName(varic.name()+"_right")
		alignObject(right_varic, invert) 
		doc.newElement(varic)
		doc.newElement(right_varic)
	io.write(doc, 'full_map.nmpml', format='nmpml')
	
	
if __name__ == '__main__':
	# import sys
	# for fn in sys.argv[1:]:
	# 	print "converting %s" % fn
	# 	convert_aff(fn, 1.344)
	
	#make_map(os.getcwd())
	