#!/usr/bin/env python
# encoding: utf-8
#Created by Graham   Cummins on 2007-05-10.

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
import sys, os


def getHomeDir():
	h=os.environ.get('HOME')
	if not h:
		print "Warning: HOME environment variable not defined. \nThis is a BAD THING. You should define it. \nFor now, Mien will use the current directory"
		h=os.getcwd()
		os.environ['HOME']=h
	return h
	
EDIR=os.environ.get('MIEN_EXTENSION_DIR')
if not EDIR:
	EDIR=os.path.join(getHomeDir(), 'mienblocks')
if not os.path.isdir(EDIR):
	print "no extension directory"
	sys.exit()

BINDIR=os.path.join(EDIR, 'mb_binary')
if not EDIR in sys.path:
	sys.path.append(EDIR)
from mb_binary.loader import getPlatform
PLAT=getPlatform()
PLATDIR=os.path.join(BINDIR, PLAT)
if not os.path.exists(PLATDIR):
	os.mkdir(PLATDIR)
if not os.path.exists(os.path.join(PLATDIR, '__init__.py')):
	open(os.path.join(PLATDIR, '__init__.py'), 'w').write(' ')

if 'win' in PLAT:
	LIBEXT='.pyd'
else:
	LIBEXT='.so'

bd=[]	
for f in os.listdir(EDIR):
	fn=os.path.join(EDIR, f)
	if os.path.isdir(fn) and os.path.exists(os.path.join(fn, '__init__.py')):
		bsf=os.path.join(fn, 'bin', 'setup.py')
		if os.path.exists(bsf):
			bd.append(bsf)

for sfn in bd:
	print "building %s"	% sfn
	builddir=os.path.split(sfn)[0]
	instdir=os.path.split(builddir)[0]
	cdir=os.getcwd()
	os.chdir(builddir)
	libs=[fn for fn in os.listdir(instdir) if fn.endswith(LIBEXT)]
	for fn in libs:
		os.unlink(os.path.join(instdir, fn))
	cmd="python setup.py install --install-lib=%s" % instdir
	print cmd
	os.system(cmd)
	libs=[fn for fn in os.listdir(instdir) if fn.endswith(LIBEXT)]
	for fn in libs:
		open(os.path.join(PLATDIR, fn), 'w').write(open(os.path.join(instdir, fn)).read())
	print "done"
	print 
	print
	os.chdir(cdir)

	
