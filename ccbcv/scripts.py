#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-01-15.

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
import sys, os, re 
import mien.parsers.fileIO as io
import ccbcv.dircolors as dc
import mien.nmpml.data as md
from numpy import row_stack, pi, array, reshape
from ccbcv.rest import PSDB
from mien.parsers.nmpml import createElement, blankDocument
from mien.parsers.mzip import serialize, deserialize

URL = 'http://cercus.cns.montana.edu:8090'

def pts2data(arg):
	'''pts2data  fname [fname2 [...]] - extract points from sphere fiducials to a text data file

This function will load the contents of all the named files (provided they are readable by MIEN), 
select all the Fiducial elements that have Style == spheres, extract the point data from these
elements, concatenate the data into a single data element, and print that data to standard output
in text data file format. You can use shell redirection (e.g. "pts2data fname > data.txt") to 
write the points to a file.
'''
	doc = io.readall(arg)
	fid = doc.getElements('Fiducial', {'Style':'spheres'})
	pts = [f.getPoints() for f in fid]
	pts = row_stack(pts)
	d = md.newData(pts, {'SampleType':'generic'})
	f = io.match_extension('txt')[0]
	io.write(d, sys.stdout, format=f, newdoc=True)


cmds = {"pts2data":pts2data}


fnp=re.compile("([LMS])[_.](\d+)[_.]\d+[_.](\d+)")

def meta_from_name(fn):
	m = fnp.match(fn)
	atr = {}
	atr['meta_length'] = {'l':'long', 'm':'medium', 's':'short'}[m.groups()[0].lower()]
	atr['meta_class']= int(m.groups()[1])
	atr['meta_cercus']='left'
	atr['meta_cercal_distance']=10.0
	atr['meta_instar']=10
	atr['meta_slide_number']=int(m.groups()[2])
	atr['meta_directional_tuning'] = dc.DIRECTIONS[atr['meta_class']]
	return atr

def setMetasFromNames_(lfn):
	'''construct metadata tags based on structured file names'''
	for fn in lfn:
		doc = io.read(fn)
		atr = meta_from_name(fn)
		for e in doc.getElements():
			for a in atr:
				e.setAttrib(a, atr[a])
			for a in ['meta_cercal_length']:
				if a in e.attributes:
					del(e.attributes[a])
			ang = e.attrib('meta_directional_tuning') % 360
			ang = ang *dc.pi/180
			c = dc._getAngleColor(ang)
			pycol=dc.convertColor(c, 'py')
			e.setAttrib('color', pycol)
		io.write(doc, fn)

cmds['fname2meta']= setMetasFromNames_

def convertMetas(lfn):
	'''set some values for the metadata tags cercal_distance, class, cercus, and directional_tuning. Use these to set color. Sets cercal_distance to 10 (proximal). Uses the dircolors module to infer class and thus direction and color. This module assumes the data are stored in a file name of origin, using "." as the field separator.'''
	for fn in lfn:
		print fn
		doc = io.read(fn)
		els = doc.getElements(["Cell", "Fiducial", "SpatialField"], depth=1)
		for e in els:
			e.setAttrib('meta_cercal_distance', 10)	
			aclass = e.attrib('meta_class')
			if aclass == None:
				try:
					dc._getclass(e)
					aclass = e.attrib('meta_class')
				except:
					print "failed to get class for %s" % fn
					continue
			cerc = e.attrib('meta_cercus').lower()[0]
			try:
				d = dc.DIRECTIONS[aclass]
			except:
				print "no directional tuning for  %s" % (str(aclass),)
				continue
			if cerc == 'r':
				d = 360 - d
			e.setAttrib('meta_directional_tuning', d)
			d = d % 360
			ang = d * pi/180
			c = dc._getAngleColor(ang)
			pycol=dc.convertColor(c, 'py')
			if "Color" in e.attributes:
				del(e.attributes['Color'])
			e.setAttrib('color', pycol)	
		io.write(doc, fn)

cmds['setmeta']=convertMetas

def defaultMetas(lfn):
	''' sets length:long, class:0, cercus:left, instar:10, slide_number:-1, directional_tuning:0, cercal_distance:10. If any of these attributes already have values, this function will not overwrite them. It is mainly useful to prevent functions that crash if these basic metas are undefined from crashing. If you want to change the defaults, you may pass arguments that are of the form name:value, as well as file names. For example meta_cercus:right fn1 fn2  will operate on files fn1 and fn2, but will set cercus:right as well as the other defaults listed above.'''
	defaults = {
		'meta_length':'long',
		'meta_class':0,
		'meta_cercus':'left',
		'meta_instar':10,
		'meta_slide_number':-1,
		'meta_directional_tuning':0,
		'meta_cercal_distance':10
	}

	files = []
	for s in lfn:
		if ":" in s:
			n, v = s.split(":")
			defaults[n]=v
		else:
			files.append(s)
	for fn in files:
		doc = io.read(fn)
		for e in doc.getElements(["Cell", "Fiducial", "SpatialField"]):
			for a in defaults:
				if not a in e.attributes:
					e.setAttrib(a, defaults[a])
				elif a == 'meta_directional_tuning':
					e.setAttrib('meta_directional_tuning', e.	attrib('meta_directional_tuning') % 360)
		io.write(doc, fn)


cmds['setdefaults']=defaultMetas

def distribMetas(lfn):
	'''Cause all elements in each file to have the same meta tags that are on any elements in that files'''
	for fn in lfn:
		print fn
		doc = io.read(fn)
		els = doc.getElements(["Cell", "Fiducial", "SpatialField"], depth=1)
		attribs = {}
		for e in els:
			for k in e.attributes:
				if k.startswith("meta_"):
					if k in attribs:
						if attribs[k]!=e.attributes[k]:
							print("Warning: multiply defined meta attribute %s. Will not write this one" % k)
							del(attribs[k])
					else:
						attribs[k]=e.attributes[k]
		for e in els:
			for k in attribs:
				e.setAttrib(k, attribs[k])
		io.write(doc, fn)


cmds['distribute']=distribMetas

def scale134(lfn):
	'''scale the elements in the listed files by a factor of 1.34 in x y and z (but not d)'''
	from mien.spatial.alignment import alignObject
	for n in lfn:
		doc = io.read(n)
		nn, ext = os.path.splitext(n)
		nn = nn+"_scaledup"+ext
		factor = 1.34
		scale = {'Scale_x':factor, 'Scale_y':factor, 'Scale_z':factor}
		els = doc.getElements(["Cell", "Fiducial", "SpatialField"])
		for e in els:
			alignObject(e, scale)
		io.write(doc, nn)
	
cmds['scale134']=scale134

def renameFids(lfn):
	'''First argument should be a command "rn", "col" or "sep". These functions were used in creation of the standard fiducials. 
	rn calls "guessFiducialNames (from ccbcv align) to attempt to name the fiducial lines in a file as sagital, coronal, and transverse, rather than the arbitrary names they may have. col collects the fiducials in the list of arguments into a single "combined fiducials" file. sep opperates on a file generated by col (the argument list must have exactly one file name after the command sep), and splits this into files containing xhair, transverse, sagital, and coronal lines.
	'''
	import ccbcv.align as al
	import mien.parsers.nmpml as nmp
	if lfn[1]=='rn':
		for n in lfn[2:]:
			if "_renamed" in n:
				continue
			if "_fubar" in n:
				continue
			print(n)
			nn, ext = os.path.splitext(n)
			nn = nn+"_renamed"+ext
			doc = io.read(n)
			try:
				al.guessFiducialNames(doc)
				io.write(doc, nn)
			except:
				print("failed")
				raise
	elif lfn[1]=="col":
		ndoc = nmp.blankDocument()
		for n in lfn[2:]:
			doc = io.read(n)
			els = []
			for e in doc.elements:
				if e.name() in ["xhair", "transverse", "sagital", "coronal"]:
					ne = e.clone()
					snum = aname.match(n)
					nn = ne.name()+"_"+"_".join(snum.groups())
					ne.setName(nn)
					ndoc.newElement(ne)
		io.write(ndoc, "combined_fiducials.nmpml")
	elif lfn[1]=="sep":
		cf = io.read(lfn[2])
		for n in ["xhair", "transverse", "sagital", "coronal"]:
			els = [e for e in cf.elements if e.name().startswith(n)]
			ndoc = nmp.blankDocument()
			for e in els:
				ndoc.newElement(e)
			nn = n+"_fiducials.nmpml"
			io.write(ndoc, nn)
		

cmds['renamefid']=renameFids

def db_getmetas(fn, stripm = True):
	if type(fn) in [str, unicode]:
		doc = io.read(fn)	
	else:
		doc = fn
	conflict = []
	metas = {}
	for e in doc.elements:
		if stripm:
			m = dict([(k[5:], e.attrib(k)) for k in e.attributes if k.startswith("meta_")])
		else:
			m = dict([(k, e.attrib(k)) for k in e.attributes if k.startswith("meta_")])
		for k in m:
			if k in conflict:
				continue
			elif not k in metas:
				metas[k] = m[k]
			elif metas[k]!=m[k]:
				del(metas[k])
				conflict.append(k)
	return metas	


def makeDBGroup(lfn):
	'''For each file in the list, make a database group containing the metadata for these objects. Also, remove these metadata from the objects contained within the group. Attempt's to guess a database ID ane assign it as the name of the group as well'''

	PATH = '/CercalSystem/'
	for fn in lfn:
		doc = io.read(fn)
		m = db_getmetas(doc, False)
		if 'meta_dbid' in m:
			name = m['meta_dbid']
			del(m['meta_dbid'])
		else:
			try:
				name = "%s_%s_%s" % (m['meta_length'][0].upper(), str(m['meta_class']), str(m['meta_slide_number']))
			except:
				name = "DBGroup"
		print "setting group %s in %s" % (name, fn)
		m["Name"]=name
		m["DBrecord"]=PATH
		m["DBurl"]=URL
		group = createElement("Group", m)
		els = doc.elements[:]
		doc.newElement(group)
		for e in els: 
			e.move(group)
		del(m['Name'])
		for e in group.getElements():
			for k in m:
				if k in e.attributes:
					del(e.attributes[k])
			for k in ["Color", "DisplayGroup"]:
				if k in e.attributes:
					del(e.attributes[k])
		io.write(doc, fn)

cmds['dbgroups']=makeDBGroup

def setAttrs(lfn):
	'''Takes a list of "name:value" pairs and a list of filenames, and assigns all the attributes in the name:value pairs to all the toplevel elements in the files. Any input not containing a ":" is assumed to be a file name'''
	attrs = {}
	files = []
	for e in lfn:
		if ":" in e:
			n,v = e.split(":")
			attrs[n]=v
		else:
			files.append(e)
	for fn in files:
		doc = io.read(fn)
		for e in doc.elements:
			for n in attrs:
				e.setAttrib(n, attrs[n])
		io.write(doc, fn)

cmds['setattrs']=setAttrs

def _consolidateTags(grp):
	tags = {}
	for e in grp.elements:
		for k in ["Color", "DisplayGroup"]:
			if k in e.attributes:
				del(e.attributes[k])
		for k in e.attributes:
			if k.startswith("meta_"):
				if not k in tags:
					tags[k] = set([])
				if type(e.attrib(k)) == list:
					tags[k].add(tuple(e.attrib(k)))
				else:
					tags[k].add(e.attrib(k))
	for k in sorted(tags):
		if len(tags[k]) == 1:
			grp.setAttrib(k, tags[k].pop())
	for e in grp.elements:
		for k in grp.attributes:
			if k.startswith("meta_") and k in e.attributes:
				del(e.attributes[k])		

def _makeSubGroup(grp, attr):
	if attr in grp.attributes:
		return
	avs = {}	
	for e in grp.elements:
		if e.__tag__ == "Group":
			_makeSubGroup(e, attr)
		else:
			av = e.attrib(attr)
			if av!=None:
				if not av in avs:
					avs[av] = []
				avs[av].append(e)
	if len(avs) < 2:
		return
	for av in avs:
		if len(avs[av])>1:
			gn = "%s_%s" % (attr, av)
			m = {'Name':gn, attr:av}
			ngrp = createElement("Group", m)
			grp.newElement(ngrp)
			for e in avs[av]: 
				e.move(ngrp)
			_consolidateTags(ngrp)

def makeSubgroups(lfn):
	'''Takes the name of an attribute as the first argument, followed by a list of files. For all group element in the files, if at least two, and less than all, of the children  of that group have the same value for the named attribute, a subgroup is created to contain them.'''
	attr = lfn[0]
	for fn in lfn[1:]:
		doc = io.read(fn)
		for e in doc.elements:
			if e.__tag__=="Group":
				_makeSubGroup(e, attr)
	io.write(doc, fn)

cmds['subgroup']=makeSubgroups


def dbscript(lfn):
	'''The first argument should be a command. Allowed commands are:
	add, set, del, list, info, pull, metas, file

	add takes a list of file names to add to the db. 
	set takes a DB id, meta tag, and value, and sets the indicated 
		tag on the indicated object to the value
	del deletes the listed DB ids. The first ID may be "all" to 
		clear the db.
	list takes no arguments and prints a list of ids of the db entries
	info takes a list of ids and prints detailed info about each
	pull takes a db id and a file name, and downloads the datafile
		associated to the id into the named file. 
	metas list all the defined metadata tags in the db
	file  takes a db id, an attribute name (e.g. image) and a file name
		downloads the named file attribute into the named file
	'''
	cmd = lfn[0]
	PATH = '/CercalSystem/'
	CERCDB = PSDB(URL, PATH)
	CERCDB.auth('gic', 'graham')
	if cmd == 'del':
		lfn = lfn[1:]
		if lfn and lfn[0] == 'all':
			lfn =  CERCDB.getIDList()
		for name in lfn:
			CERCDB.delete(name)
			print "deleted entry %s" % name
	elif cmd == 'add':
		for fn in lfn[1:]:
			doc = io.read(fn)
			groups = doc.getElements("Group", depth = 1)
			groups = [g for g in groups if g.attrib('DBrecord')]
			if groups:
				for grp in groups:
					print("Commiting db group %s from %s" % (grp.name(), fn))
					m =  dict([(k[5:], grp.attrib(k)) for k in grp.attributes if k.startswith("meta_")])
					name = grp.name()
					name = name.replace(".", "_")
					s = serialize(None, grp)
					if grp.attrib("DBurl") == URL and grp.attrib("DBrecord") == PATH:
						db = CERCDB
					else:
						db = PSDB(grp.attrib("DBurl"),grp.attrib("DBrecord") )
					db.addOrUpdate(name, m, s)
			else:
				m = db_getmetas(doc)
				if 'dbid' in m:
					name = m['dbid']
					del(m['dbid'])
				else:
					name = "%s_%s_%s" % (m['length'][0].upper(), str(m['class']), str(m['slide_number']))
				print "commiting %s as %s" % (fn, name)
				s = serialize(None, doc)
				CERCDB.addOrUpdate(name, m, s)
	elif cmd == 'set':
		iid = lfn[1]
		tag = lfn[2]
		val = lfn[3]
		nmd = {tag:val}
		CERCDB.update(iid, nmd)
	elif cmd == 'list':
		for iid in CERCDB.getIDList():
			print(iid)
	elif cmd == 'info':
		l = CERCDB.get(CERCDB.path)
		lidd = dict([(e['id'], e) for e in l])
		for id_ in lfn[1:]:
			e = lidd.get(id_, 'No such entry')
			print(e)
	elif cmd == 'pull':
		record = lfn[1]
		fname = lfn[2]
		df = CERCDB.getFile(record)
		doc = deserialize(df) 
		doc = io.write(doc, fname, format='guess')
	elif cmd == 'metas':
		l = CERCDB.get(CERCDB.path)
		metas = set([])
		for e in l:
			md = e['metadata']
			for k in md:
				metas.add(k)
		for k in metas:
			print(k)
	elif cmd == 'file':
		record = lfn[1]
		fpath = lfn[2]
		fname = lfn[3]
		df = CERCDB.getFile(record, fpath)
		open(fname, 'wb').write(df)
		

cmds['db']=dbscript

def checkstate(lfn):
	'''for all the listed files, verify presence of a cell, varicosities, at least 3 fiducial lines, and the meta tags:
	meta_cercus
	meta_class
	meta_cercal_distance
	meta_length
	meta_slide_number
	meta_cercal_distance
	meta_instar
	meta_directional_tuning
	'''
	need_metas = [
		'meta_cercus',
		'meta_class',
		'meta_cercal_distance',
		'meta_length',
		'meta_slide_number',
		'meta_cercal_distance',
		'meta_instar',
		'meta_directional_tuning',
	]
	for fn in lfn:
		doc = io.read(fn)
		md = {}
		count = {'cell':0, 'sphere':0, 'line':0}
		els = doc.getElements(["Cell", "Fiducial"])
		for e in els:
			if e.__tag__ == 'Cell':
				count['cell']+=1
			elif e.attrib("Style") == 'spheres':
				count['sphere']+=1
			else:
				count['line']+=1
			for atr in e.attributes:
				if atr.startswith("meta_"):
					md[atr]=e.attrib(atr)
		if count['cell']<1:
			print "%s missing cell" % fn
		if count['sphere']<1:
			print "%s missing varricosities" % fn
		if count['line']<3:
			print "%s has only %i line fiducials" % (fn, count['line'])
		for mt in need_metas:
			if not mt in md:
				print "%s is missing meta tag %s" % (fn, mt)
		sn = md.get('meta_slide_number')
		if sn in [-1, '-1']:
			print "%s has bogus slide number" % fn



cmds['checkstate']=checkstate

def setmeta(lfn):
	'''the first argument should be a metadata tag (without the leading meta_), and the second should be a value. Sets this tag to this value in all the listed files. If the value is DEL, removes the tag.'''
	md = 'meta_' + lfn[0]
	mv = lfn[1]
	for fn in lfn[2:]:
		doc = io.read(fn)
		for e in doc.getElements(['Cell', 'Fiducial']):
			e.setAttrib(md, mv)
		print "set %s in %s" % (md, fn)
		io.write(doc, fn)

cmds['set1meta']=setmeta

def setSlideNumber(lfn):
	'''Sets the slide number from file name, using names of the forms:
	date_n..., l.c.i.n..., l_c_i_n...'''
	fmt1 = re.compile('([LMS])[_.](\d+)[_.](\d+)[_.](\d+)')
	fmt2 = re.compile('[\d_]+')
	for fn in lfn:
		sn = None
		m = fmt1.match(fn)
		if m:
			sn = m.groups()[3]
		else:
			m = fmt2.match(fn)
		 	if m:
				sn = m.group()
		if sn:
			print fn, sn
			doc = io.read(fn)
			for e in doc.getElements():
				e.setAttrib('meta_slide_number', sn)
			io.write(doc, fn)

cmds['setslide']=setSlideNumber

def _gmm2dat(atr, weights, means, covs):
	atr.update({'SampleType':'Group', 'Name':'gmm'})
	dat1 = createElement('Data', atr)
	dw = createElement('Data', {'SampleType':'generic', 'Name':'weights'})
	dw.datinit(weights)
	dat1.newElement(dw)
	dm = createElement('Data', {'SampleType':'generic', 'Name':'means'})
	dm.datinit(means)
	dat1.newElement(dm)
	dc = createElement('Data', {'SampleType':'generic', 'Name':'covs'})
	dc.datinit(covs)
	dat1.newElement(dc)
	return dat1

	

def gmms2data(lfn):
	for fn in lfn:
		doc = io.read(fn)
		doc2 = blankDocument()
		gmms = doc.getElements('MienBlock', {'Function':'ccbcv.gmm.gmm'})
		for g in gmms:
			atr = g.getInheritedAttributes()
			pars = g.getArguments()
			weights = array(pars['weights'])
			means = reshape(array(pars['means']), (weights.shape[0], -1))
			covs = reshape(array(pars['covs']), (means.shape[0], means.shape[1], means.shape[1]))
			doc2.newElement(_gmm2dat(atr, weights, means, covs))
		io.write(doc2, fn+".mat")


cmds['gmm2data']=gmms2data

def help(arg):
	'''help cmd  - print usage information for "cmd"
cmd may be any command know to the script module. Use "help" with no argument to list commands'''
	if not arg:
		usage()
	else:
		k=arg[0]
		if not k in cmds:
			print("Unknown command. Use 'help' with no argument to list commands")
			return
		print(cmds[k].__doc__)

cmds['help']=help

def usage():
	s = "Usage: scripts.py cmd [args]\npossible values for 'cmd' are:\n\n" 
	for k in cmds:
		hs = cmds[k].__doc__.split("\n")[0]
		s = s + "%s  - %s\n\n" % (k, hs)
	s = s + "\nUse 'help cmd' for detailed help on a particular command\n"
	print(s)

		
if __name__ == '__main__':
	if len(sys.argv)<2:
		usage()
		sys.exit()
	if not sys.argv[1] in cmds:
		usage()
		sys.exit()
	cmds[sys.argv[1]](sys.argv[2:])


