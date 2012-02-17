#!/usr/bin/env python
# encoding: utf-8
#Created by gic on 2007-04-10.

# Copyright (C) 2007 Graham I Cummins
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

def read(f, **kwargs):
	d=f.read()
	d=eval(d)
	attr=nmpml.nameFromFile(f)	
	abst=nmpml.createElement('AbstractModel', attr)
	disable=[]
	for i, l in enumerate(d):
		fn, args, dis = l[:3]
		if dis:
			disable.append(l)
		mb=nmpml.createElement('MienBlock', {'Function':fn})
		abst.newElement(mb)
		mb.setArguments(args)
	if disable:
		abst.setAttrib('disable', disable)	
	return nmpml.wrapInDocument([abst])
	
def write(fileobj, doc, **kwargs):
	abst=doc.getElements('AbstractModel')[0]
	disable=abst.attrib('disable') or []
	fl=[]
	for i, e in enumerate(abst.elements):
		if not e.__tag__=='MienBlock':
			continue	
		dis=i in disable
		args=e.getArguments()
		fn=e.attrib('Function')
		fl.append([fn, args, dis])
	print fl	
	fileobj.write(repr(fl))	

ftype={'notes':'Stores only the functions and parameters for a simple Abstract model (Abstract models are simple if they contain only MienBlock elements)',
		'read':read,
		'write':write,
		'data type':'Abstract models',
		'elements':['AbstractModel'],
		'extensions':['.dsp']}
		
		
def _kwargstodict(**kw):
	return kw		
		
		
def qread(f, **kwargs):
	d=f.readlines()
	attr=nmpml.nameFromFile(f)	
	abst=nmpml.createElement('AbstractModel', attr)
	for l in d:
		l = l.strip()
		if not l or l.startswith("#"):
			continue
		i = l.index("(")
		fn = l[:i]
		argstring = l[i+1:-1]
		args = eval("_kwargstodict(%s)" % argstring)	
		mb=nmpml.createElement('MienBlock', {'Function':fn})
		abst.newElement(mb)
		mb.setArguments(args)
	return nmpml.wrapInDocument([abst])
	
def qwrite(fileobj, doc, **kwargs):
	abst=doc.getElements('AbstractModel')[0]
	disable=abst.attrib('disable') or []
	for i, e in enumerate(abst.elements):
		if not e.__tag__=='MienBlock':
			continue	
		args=e.getArguments()
		fn=e.attrib('Function')
		if i in disable:
			fn = "#"+fn
		argstring=""
		for a in args:
			argstring = argstring+"%s=%s," % (a, repr(args[a]))
		argstring=argstring.rstrip(",")
		fileobj.write("%s(%s)\n" % (fn, argstring))
		

qtype={'notes':'Stores only the functions and parameters for a simple Abstract, using a short syntax. Useful for editing DSP batch jobs by hand.',
		'read':qread,
		'write':qwrite,
		'data type':'Abstract models',
		'elements':['AbstractModel'],
		'extensions':['.qsp']}		