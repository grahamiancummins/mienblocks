#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-02-03.

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

import mien.nmpml.basic_tools as bt
import time, os
from reftools import readBib
from subprocess import Popen, PIPE


HD = os.environ['HOME']
WD = os.path.join(HD, 'msb')
GPGUSER = "gic"

def _gpg_enc(s, user=GPGUSER):
	cmd = "gpg -ear %s" % user
	p = Popen(cmd, shell=True, bufsize=10000000,
          stdin=PIPE, stdout=PIPE, close_fds=True)
	s2=p.communicate(s)
	return s2[0]
	
def _gpg_dec(s):
	cmd = "gpg -da"
	p = Popen(cmd, shell=True, bufsize=10000000,
          stdin=PIPE, stdout=PIPE, close_fds=True)
	s2=p.communicate(s)
	return s2[0]	

class SBEntry(bt.NmpmlObject):
	_allowedChildren = ['SBAttachment', 'SBReference', 'SBSecret']
	_requiredAttributes = ["Name"]
	_specialAttributes = ["Type", "Summary", "Deadline", "Priority", "Rating"]
	_hasCdata = True
	DONOTCONVERT = ["Type", "Summary", "Deadline", "Priority", "Rating"]

	def __str__(self):
		return self.str(False)

	def attrib(self, attr):
		return self.attributes.get(attr, "")
	
	def setAttrib(self, a, v):
		'''set attributes key a to v'''
		self.attributes[a]=v
		
	def str(self, verbose):
		if not verbose:
			return "%s (%s) %s" % (self.name(), self.attrib('Type'), self.attrib('Summary'))
		s = "%s:\n" % self.name()
		for a in self._specialAttributes:
			if a == 'Deadline':
				v = self.attrib(a)
				if v:
					v = float(v)
					v = time.strftime('%m/%d %H:%M', time.localtime(v))
					s = s + "Deadline: %s\n" % v
			else:	
				s=s+"%s: %s\n" % (a, self.attrib(a))
		els = self.getElements()
		for e in els:
				s+= str(e)
		dat = self.cdata.strip()
		if dat:
			s = s+"-----\n"+dat+"\n"
		s = s+"-----\n"
		return s


class SBAttachment(bt.NmpmlObject):
	_allowedChildren = []
	_requiredAttributes = ["Name"]
	_specialAttributes= ["Path"]
	_hasCdata = False

	def __str__(self):
		return "Attachment: %s (%s)\n" % (self.attrib("Path"), self.attributes.get("SourceFile", "?"))

	def sever(self):
		print "severing attachment"
		if os.path.exists(self.path()):
			print "unlinking file"
			os.unlink(self.path())
		bt.NmpmlObject.sever(self)
		
	def path(self):
		return os.path.join(WD, self.attrib("Path"))	
		
	def bind(self, fname):
		bname = self.container.name()
		afiles = [os.path.splitext(fn)[0] for fn in os.listdir(WD) if fn.startswith(bname)]
		i = 1
		aname = "%s_%i" % (bname, i)
		while aname in afiles:
			i+=1
			aname = "%s_%i" % (bname, i)
		aname = aname + os.path.splitext(fname)[-1]
		self.setAttrib('Path', aname)
		self.setAttrib("SourceFile", fname)
		open(self.path(), 'wb').write(open(fname, 'rb').read())


class SBReference(bt.NmpmlObject):
	_allowedChildren = []
	_requiredAttributes = ["Name"]
	_hasCdata = False
	
	def attrib(self, attr):
		a=self.attributes.get(attr, "Unknown")
		if type(a) in [str, unicode]:
			a=a.strip()
		return a
	
	def __str__(self):
		return self.format()
	
	def setAttrib(self, a, v):
		'''set attributes key a to v'''
		self.attributes[a]=v
	
	
	def castAttributes(self):
		pass
			
	def format(self, style=None):
		if style=='all':
			d=self.refs[id]
			s="%s:\n" % (self.name())
			for k in self.attributes:
				if k == "Name":
					continue
				s+="%s :: %s\n" % (k, self.attrib(k))
			return s		
		else:
			a = self.attrib('author')
			if type(a) in [tuple, list]:
				a = ",".join(a)
			return "%s; %s; %s\n" % (a, self.attrib('title'), str(self.attrib('year')))
	
	def loadBib(self, bfn, rname = "*"):
		refs = readBib(bfn)
		if rname == "*":
			rname = refs.keys()[0]
		r = refs[rname]
		self.setName(rname)
		for k in r:
			self.setAttrib(k, r[k].strip("{}"))
		
	
class SBSecret(bt.NmpmlObject):
	_allowedChildren = []
	_requiredAttributes = ["Name"]
	_hasCdata = True

	def __str__(self):
		return "Encrypted Data\n"
		
	def decrypt(self):
		s = _gpg_dec(self.cdata)
		return s
		
	def encrypt(self, s):
		self.cdata = _gpg_enc(s)
		print "set encrypted cdata"
	
		
XML={'SBEntry':SBEntry,
	'SBAttachment':SBAttachment,
	'SBReference':SBReference,
	'SBSecret':SBSecret,
	"default class":bt.NmpmlObject
	}

def create(tag, name=None):
	'''Return an NmpmlObject subclass of type "tag" with the specified attributes and cdata set.'''
	attr = {}
	if name:
		attr['Name']=name
	node={'tag':tag, 'attributes':attr, 'elements':[], 'cdata':""}
	cl=	XML.get(tag, XML['default class'])
	return cl(node)
	

