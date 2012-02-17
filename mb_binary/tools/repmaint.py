#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2008-05-13.

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

import os, re, sys


RDIR='/var/www/repository'
URL='http://mien.msu.montana.edu/svn/mienblocks'
EDIR='/opt/src/work/'

# RDIR='/home/gic/testrepo'
# EDIR='/home/gic/wcopy'


BDIR=os.path.join(EDIR, 'mienblocks')
DEBDIR=os.path.join(EDIR, 'deb')
sviv=re.compile("Last Changed Rev:\s*(\d+)")

DEB_CONTROL='''
Package: python-mien-BLOCKNAME
Version: 0.0.VERSION
Section: python
Priority: optional
Maintainer: Graham Cummins <gic@cns.montana.edu>
Depends: python-mien (>> 0.0.500) DEPS
Description: Provides an extension block for the MIEN project.
	DESC
Installed-Size: SIZE
Architecture: ARCH
'''
PKGNAME=re.compile("\w+_(\d+)_([^.]+)\.tgz$")

PLATFORMS=['macosx', 'win32', 'linux-i686', 'linux-ia64', 'linux-x86_64']
DEB_PORTS={'linux-i686':'i386', 'linux-ia64':'ia64', 'linux-x86_64':'amd64'}


def movefile(foo, bar):
	open(bar, 'w').write(open(foo).read())
	os.unlink(foo)

def insureDir(d):
	d=d.rstrip('/')
	dirs=[]
	while not os.path.exists(d):
		d, t = os.path.split(d)
		dirs.append(t)
	while dirs:
		d=os.path.join(d, dirs.pop())
		os.mkdir(d)

def getVersion(url):
	vs=os.popen('svn info %s' % url).read()
	m=sviv.search(vs)
	return int(m.group(1))
	
def tarrevnum(fn):	
	m=PKGNAME.match(fn)
	if not m:
		return -1
	v, a = m.groups()
	v=int(v)
	return v	
	
def revsort(a, b):
	return cmp(tarrevnum(a), tarrevnum(b))

def isStable(url):
	vs=os.popen('svn log -r HEAD %s' % url).read()
	for x in vs.split('\n'):
		if x.strip().lower().startswith('stable release:'):
			return True
	return False
		
def getBlocks(force=False):
	blockdirs=[]
	blocks=[]
	for bd in re.split("\s", os.popen('svn list %s' % URL).read()):
		if bd.endswith('/') and not bd.startswith('mb_binary'):
			cont=os.popen('svn list %s' % (URL+"/%s" % bd)).read()
			if "__init__.py" in cont:
				blockdirs.append(bd.rstrip('/'))
	insureDir(BDIR)
	mbb=os.path.join(BDIR, 'mb_binary')
	if not os.path.isdir(mbb):
		os.system('svn co %s %s' % (URL+"/mb_binary", mbb))
	else:
		os.system('svn up %s' % mbb)	
	for bn in blockdirs:
		vf=os.path.join(BDIR, bn, 'VERSION')
		try:
			ov=int(open(vf).read())
		except:
			ov=-1
		nv=getVersion(URL+"/%s" % bn)
		if nv>ov or force:
			blocks.append((bn, nv))
			os.system('svn export --force %s/%s %s/%s > /dev/null' % (URL, bn, BDIR, bn))
			open(vf, 'w').write("%i\n" % nv)
	return blocks

def trimdir(d, mn):
	plats=['all']+PLATFORMS
	for p in plats:	
		fi=[f for f in os.listdir(d) if f.endswith('%s.tgz' % p)]
		if len(fi)<=mn:
			continue
		fi.sort(revsort)
		print fi
		while(len(fi)>mn):
			f=fi.pop(0)
			os.unlink(os.path.join(d, f))


def deb_dep_string(deps):
	ds=''
	for d in deps:
		if not d[3]:
			continue
		ds+=', %s' % d[3]
		if d[4]:
			ds+="(>=%s)" % d[4]
	return ds 

def deb_build(bn, plat, v, deps, desc):
	insureDir(DEBDIR)
	curdir=os.getcwd()
	os.chdir(DEBDIR)
	sdir=os.path.join(BDIR, bn)
	pn="python-mien-%s" % bn
	if os.path.isdir(pn):
		os.system('rm -rf %s' % pn)
	os.mkdir(pn)
	os.mkdir('%s/DEBIAN' % pn)
	cs=DEB_CONTROL.replace('VERSION', str(v))
	size=os.popen('du -s %s' % sdir).read()
	size=size.split()[0]
	cs=cs.replace('SIZE', str(size))
	cs=cs.replace('ARCH', plat)
	cs=cs.replace('BLOCKNAME', bn)
	cs=cs.replace('DESC', desc)
	cs=cs.replace('DEPS', deb_dep_string(deps))
	open('%s/DEBIAN/control' % pn, 'w').write(cs)
	insureDir("./%s/usr/lib/python2.6/dist-packages/mienblocks" % pn)
	os.system('cp -r %s %s/usr/lib/python2.6/dist-packages/mienblocks/' % (sdir, pn) )
	debn='%s_0.0.%i_%s.deb' % (bn, v, plat)
	os.system('dpkg -b %s %s' % (pn, debn))
	os.system('rm -rf %s' % pn)
	os.chdir(curdir)
	return debn

def rebuild_apt_repo():
	dtd=os.path.join(RDIR, 'ubuntu')
	curdir=os.getcwd()
	os.chdir(dtd)
	for arch in DEB_PORTS.values():
		ad=os.path.join(RDIR, 'ubuntu', 'dists', 'jaunty', 'main', 'binary-%s' % arch)
		insureDir(ad)
		pfn=os.path.join(ad, 'Packages.gz')
		if os.path.exists(pfn):
			os.unlink(pfn)
		print "generating package index %s" % pfn
		os.system('dpkg-scanpackages -a %s pool /dev/null | gzip -9c > %s' % (arch, pfn))
	os.chdir(curdir)	

def apt_update(bn, plat, v, deps, desc):
	pn=deb_build(bn, plat, v, deps, desc)
	dtd=os.path.join(RDIR, 'ubuntu', 'pool')
	insureDir(dtd)
	for f in os.listdir(dtd):
		if f.startswith('python-mien-%s' % bn) and f.endswith("%s.deb" % plat):
			os.unlink(os.path.join(dtd, f))
	try:
		movefile(os.path.join(DEBDIR, pn), os.path.join(dtd, pn))
	except:
		print("##################### package build failed %s" % pn) 
	
	
def get_deps(bn):
	curdir=os.getcwd()
	bin=[]
	deps=[]
	desc="no description"
	try:
		os.chdir(BDIR)
		exec('import %s.__init__ as mod' % bn)
		if "BINARIES" in dir(mod):
			bin=mod.BINARIES
		if "DEPENDENCIES" in dir(mod):
			deps=mod.DEPENDENCIES
		if "DESCRIPTION" in dir(mod):
			desc=mod.DESCRIPTION
	except:
		print "couldn't get dependancies for %s" % bn
	os.chdir(curdir)
	return (bin, deps, desc)
	
def getBinary(mn, plat):
	mbb=os.path.join(BDIR, 'mb_binary', plat)
	mfn=os.path.join(mbb, mn+".so")
	if os.path.exists(mfn):
		return mfn
	mfn=os.path.join(mbb, mn+".pyd")
	if os.path.exists(mfn):
		return mfn
	return None

def set_binary(bn, bin, plat):
	bdn=os.path.join(BDIR, bn)
	for fn in os.listdir(bdn):
		if os.path.splitext(fn)[-1] in ['.so', '.pyd', '.egg-info']:
			os.unlink(os.path.join(bdn, fn))
	for be in bin:		
		bfn=getBinary(be, plat)
		if not bfn:
			raise StandardError("No binary found")
		tbfn=os.path.join(bdn, os.path.split(bfn)[-1])
		open(tbfn, 'w').write(open(bfn).read())		
	
def package(bn, v, stab=None):
	if stab=='d':
		stable=False
	elif stab=='s':
		stable=True
	else:
		stable = isStable(URL)
	if stable:
		dn='stable'
	else:
		dn='dev'		
	print "packaging block %s revision %i (%s)" % (bn, v, dn)
	td=os.path.join(RDIR, dn, bn)
	insureDir(td)
	bin, deps, desc= get_deps(bn)
	open(os.path.join(td, 'DEPENDANCIES'), 'w').write(repr(deps))
	open(os.path.join(td, 'DESCRIPTION'), 'w').write(repr(desc))
	if not bin:
		fn="mien_%s_%s_all.tgz" % (bn, v)
		fn=os.path.join(td, fn)
		cmd='tar -C %s -czf %s %s' % (BDIR, fn, bn)
		#print cmd
		os.system(cmd)
		if stable:
			apt_update(bn, 'all', v, deps, desc)
	else:
		for plat in PLATFORMS:
			try:
				set_binary(bn, bin, plat)
			except:
				print "can't get binaries for module %s platform %s" % (bn, plat)
				continue
			fn="mien_%s_%s_%s.tgz" % (bn, v, plat)
			fn=os.path.join(td, fn)
			cmd='tar -C %s -czf %s %s' % (BDIR, fn, bn)
			os.system(cmd)
			if stable and DEB_PORTS.has_key(plat):	
				apt_update(bn, DEB_PORTS[plat], v, deps, desc)	
	if stable:
		rebuild_apt_repo()
		trimdir(td, 4)	
	else:
		trimdir(td, 1)	
	

if __name__=='__main__':
	force=False
	stab=None
	if "stable" in sys.argv:
		stab='s'
	elif "dev" in sys.argv:
		stab='d'
	if "force" in sys.argv:
		force=True
	sys.path.insert(0, '.')
	b=getBlocks(force)
	if b:
		for bd in b:
			package(bd[0], bd[1], stab)
	else:
		print "No blocks are changed"
