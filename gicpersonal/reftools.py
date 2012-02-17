#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-02-05.

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

import re, StringIO, cPickle, getopt, os, codecs

delim=re.compile("@")


def newref(d=None, attrs=None):
	if not d:
		d={}
	if not attrs:
		attrs={}
	r={'tag':'Reference', 'attributes':attrs, 'cdata':"", 'elements':[]}
	for key in d.keys():
		if key=='Status':	
			continue
		s=d[key]
		r['elements'].append({'tag':key, 'attributes':{}, 'cdata':s, 'elements':[]})
	stat={'tag':'Status', 'attributes':{'Read':'-1', 'Priority':'-1', 'Utility':'-1'}, 'cdata':"", 'elements':[]}	
	if d.get('Status'):
		stat['attributes']=d['Status']
	r['elements'].append(stat)
	if not 'Comment' in d.keys():
		r['elements'].append({'tag':"Comment", 'attributes':{}, 'cdata':"None", 'elements':[]})
	return r	

def uniquename(name, used):
	bn=name	
	ii=97
	while name in used:
		name=bn+chr(ii)
		ii+=1
		if ii>122:
			ii=97
			bn=bn+'a'	
	return name

class Bibfile:
	def __init__(self):
		self.refs={}

	def parse(self, f):
		if type(f) in [str, unicode]:
			f = open(f)
		token=[]
		read=False
		c=f.read(1)
		while c:
			if read:
				if c=="{":
					self.processEntry(self.until_close(f), ''.join(token).strip()) 
					token=[]
					read=False
				else:
					token.append(c)
			elif c=="@":
				read=True
			c=f.read(1)

	def until_close(self, f):
		buf=[]
		depth=1
		esc=False
		while depth:
			c=f.read(1)
			if not c:
				raise StandardError("Unpaired delimiter in file")
			if c!="\r":	
				buf.append(c)	
			if esc:
				esc=False
			elif c=="\\":
				esc=True	
			elif c=="{":
				depth+=1
			elif c=="}":
				depth-=1	
		return ''.join(buf)
	
	def until(self, c, f):
		buf=[]
		esc=False
		nc=f.read(1)	
		while not nc==c:
			buf.append(nc)
			nc=f.read(1)	
			if not nc:
				return None
		return ''.join(buf)
			
	def nextprop(self, f):
		pn=self.until('=', f)
		if not pn:
			return (None, None)
		pn=pn.strip()
		pn=pn.lstrip(',')
		pn=pn.lstrip()
		check=self.until('{', f)
		if check==None:
			return (None, None)
		val=self.until_close(f)
		return (pn, val[:-1].strip())
	
	def autoname(self, r):
		n=''
		if r.has_key('author'):
			n=r['author'].split(',')[0]
			n=re.sub("\w\.", "", n)
			n=re.sub("[^\w_-]", "_", n)
		else:
			n="unknown"
		if r.has_key('year'):
			n+=r['year']
		return n	
	
	def processEntry(self, s, reftype):
		if reftype=='detect':
			bb=s.find("{")
			reftype=s[:bb].rstrip("@")
			s=s[bb+1:]
		f=StringIO.StringIO(s)
		ref={'class':reftype}
		name=self.until(',', f)
		if name==None:
			return
		name=name.strip()
		while True:
			k, v=self.nextprop(f)
			if k==None:
				break
			ref[k]=v
		if not name:
			name=self.autoname(ref)
		name=uniquename(name, self.refIDs())	
		self.refs[name]=ref
		return name
		
	def refIDs(self):
		k=self.refs.keys()
		k.sort()
		return k
		
	def tobibtex(self, rn):
		l=[]
		ref=self.refs[rn]
		l.append("@%s{%s," % (ref['class'], rn))
		rk=ref.keys()
		rk.sort()
		for prop in rk:
			if 	prop in ['class', 'Status', 'Comment']:
				continue
			l.append("  %s = {%s}," % (prop, ref[prop]))
		l[-1]=l[-1][:-1]
		l.append('}')
		return "\n".join(l)
			
		
	def write(self, fname=None, mode='xml'):
		if not fname:
			fname=self.filename
			mode=self.filemode
		if os.path.isfile(fname):
			print 'backing up %s ' % fname
			open(fname+'.bak', 'w').write(open(fname).read())
		print 'writing %s ' % fname
		f=open(fname, 'w')
		if mode=='tex':
			for rn in self.refIDs():
				f.write('\n')
				f.write(self.tobibtex(rn))
				f.write('\n')
		elif mode=='cache':
			cPickle.dump(self.refs, f)	
		elif mode=='xml':
			refs={'tag':'References', 'attributes':{}, 'cdata':"", 'elements':[]}
			for k in self.refs.keys():
				r=newref(self.refs[k], {'id':k})
				refs['elements'].append(r)
			xml2dict.write(f, refs)
		f.close()
				
		
	def match(self, l, pr):
		nm=0
		mk=['author', 'keywords', 'title', 'year', 'abstract']
		md={}
		for k in mk:
			md[k]=self.refs[pr].get(k, '').lower()
		for s in l:
			for k in mk:
				if s in md[k]:
					if k=='abstract':
						nm+=.5
					else:
						nm+=1
		return nm
	
	def anymatch(self, l, pr):
		mk=['author', 'keywords', 'title', 'year', 'abstract']
		md={}
		for k in mk:
			md[k]=self.refs[pr].get(k, '').lower()
		for s in l:
			for k in mk:
				if s in md[k]:
					return True
		return False
					
		
	def find(self, st=None):
		sl=[s.lower() for s in st.split()]
		mmv=0
		mid=None
		for id in self.refIDs():
			mv=self.match(sl, id)
			if mv>mmv:
				mid=id
				mmv=mv
		return mid
		
	def findall(self, st, fast=False, cutoff=.5):
		sl=[s.lower() for s in st.split()]
		if fast:
			return [rid for rid in self.refIDs() if self.anymatch(sl, rid)]
		matches={}	
		for id in self.refIDs():
			mv=self.match(sl, id)
			if mv:
				matches[id]=mv
		if not matches:
			return []		
		mmv=max(matches.values())
		if cutoff:
			for id in matches.keys():
				if matches[id]<cutoff*mmv:
					del(matches[id])
		ml=matches.keys()
		ml.sort(lambda x,y:cmp(matches[y], matches[x]))
		return ml
			

	def format(self, id, style=None):
		if style=='all':
			d=self.refs[id]
			s=""
			for k in d.keys():
				s+="%s :: %s\n\n" % (k, d[k])
			return s		
		else:
			try:
				return "%s; %s; %s" % (self.refs[id]['author'].strip(), self.refs[id]['title'].strip(), self.refs[id]['year'].strip())
			except:
				return "%s (ref incomplete)" % id
				
def readBib(fn):
	b = Bibfile()
	b.parse(fn)
	return b.refs

# ftype={'notes':'Converts from SBReference tags to BibTeX',
# 		'read':readBib,
# 		'write':writeBib,
# 		'data type':'References',
# 		'elements':['SBReference'],
# 		'extensions':['.bib']}
