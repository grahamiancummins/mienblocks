#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2008-01-24.

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

import sys, os, mien, pydoc

MIENHOME=d=os.path.split(mien.__file__)[0]
BLOCKTYPES=['DSP','SPATIAL','DV','CV','ME', 'PARSERS', 'NMPML', 'MECM']

def tryLoad(mn):
	try:
		exec "import %s as mod" % mn
	except:
		print "error loading module %s" % mn
		mod=None
	return mod

def getHomeDir():
	h=os.environ.get('HOME')
	if not h:
		print "Warning: HOME environment variable not defined. \nThis is a BAD THING. You should define it. \nFor now, Mien will use the current directory"
		h=os.getcwd()
		os.environ['HOME']=h
	return h

def getmods():	
	EDIR=os.environ.get('MIEN_EXTENSION_DIR')
	if not EDIR:
		EDIR=os.path.join(getHomeDir(), 'mienblocks')
	if not os.path.isdir(EDIR):
		print "no extension directory"
		return {}
	if not EDIR in sys.path:
		sys.path.append(EDIR)	
	mods={}
	for f in os.listdir(EDIR):
		fn=os.path.join(EDIR, f)
		ifn=os.path.join(fn, '__init__.py')
		if os.path.isdir(fn) and os.path.exists(ifn):
			mod=tryLoad(f)
			md={}
			if mod:
				for modtype in BLOCKTYPES:
					if modtype in dir(mod):
						md[modtype]=repr(getattr(mod,modtype))
			mods[f]=md
	return mods

def modified(mod):
	mmt=os.stat(mod.__file__)[8]
	dfn=os.path.join(os.getcwd(), mod.__name__)+'.html'
	if not os.path.isfile(dfn):
		return True
	dmt=os.stat(dfn)[8]
	if dmt<mmt:
		return True
	return False	

def killnbs(mod):
	dfn=os.path.join(os.getcwd(), mod.__name__)+'.html'
	s = open(dfn).read()
	s = s.replace("&nbsp;", " ")
	open(dfn, 'w').write(s)

def writedoc(mn):
	#print mn
	try:
		exec("import %s as mod" % mn)
	except:
		print "WARNING: can't import %s" % mn
		raise
		return 
	if modified(mod):
		pydoc.writedoc(mod)
		killnbs(mod)
	else:
		print "%s not modified" % mn
	if not '__init__' in mod.__file__:
		return
	#is a package - need to get subpackages
	d=os.path.split(mod.__file__)[0]
	dd=os.listdir(d)
	for fn in dd:
		fpn=os.path.join(d, fn)
		wd=False
		if fn.startswith("_"):
			pass
		elif os.path.isfile(fpn) and fn.endswith('.py'):
			#found a module
			if not fn in ['test.py', 'testme.py', 'setup.py']:
				wd=True
		elif os.path.isdir(fpn):
			if '__init__.py' in os.listdir(fpn):
				if not fn=='tools':
					wd=True
		if wd:		
			nmn=os.path.splitext(fn)[0]
			nmn='.'.join([mn, nmn])
			writedoc(nmn)


def writeindex(mods):
	f=file('mienblocks_index.html', 'w')
	f.write('''<!doctype html PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
<html><head><title>Python: mienblocks index</title>
</head><body bgcolor="#f0f0f8">''')
	for mn in mods.keys():
		s="<h3><a href='%s.html'>Block Package: %s</a></h3>\n" % (mn,mn)
		f.write(s)
		for k in mods[mn].keys():
			s="provides %s blocks: <pre>%s</pre><br>\n" % (k, mods[mn][k]) 
			f.write(s)
		f.write("<br>\n")
	f.write("</body>")
	f.close()
	
if __name__=='__main__':
	if len(sys.argv)>1:
		cdir=os.getcwd()
		os.chdir(sys.argv[1])
	else:
		cdir=None
	m=getmods()	
	writeindex(m)
	for mod in m.keys():		
		writedoc(mod)
	if cdir:
		os.chdir(cdir)
