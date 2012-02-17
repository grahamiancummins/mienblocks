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

import inspect, os, tempfile, time, socket
import sbnmpml as nmp
from mien.xml.xmlhandler import readXML, writeXML



''' 
Features to provide:

Interactive prompt
Edit py string with vi
nmpml classes: entry, attachment, reference, link, secret

'''
SERVER = 'matrim.cns.montana.edu'
HD = nmp.HD
WD = nmp.WD
DB = os.path.join(WD, 'msb.xml')
doc = None
e = [None]
hit = set([])

if not os.path.exists(WD):
	os.mkdir(WD)
if not os.path.exists(DB):
	doc = nmp.create('ScrapBookDB')
	#save()
else:
	doc = readXML(DB, nmp.XML)


def save():
	'''Save the database'''
	open(DB+".bak", "wb").write(open(DB).read())
	open(os.path.join(WD, '.CHANGED'), 'w').write(str(time.time()))
	writeXML(DB, doc, {}, True, True)		

def _chooseList(l):
	print('select option:')
	for i, li in enumerate(l):
		print "%i: %s" % (i, li)
	print "%i: Cancel" % (len(l),)
	r = raw_input("> ")
	try:
		r = int(r)
	except:
		r = -1

	if r>=0 and  r<len(l):
		return l[r]
	elif r==len(l):
		return None
	print "Please select an integer item from the list (including Cancel)"
	return _chooseList(l)

def allEntries():
	return doc.getElements('SBEntry', depth=1)

def allTypes():
	e = allEntries()
	e = [x.attrib('Type') for x in e]
	e = set(e)
	if '' in e:
		e.remove('')
	return list(e)

def _strInput(lab, s):
	print "%s. Current value: %s ..." % (lab, s[:40])
	v = raw_input("Enter value, k to keep, e to edit > ")
	v = v.strip()
	if v == 'k':
		return s
	if v == 'e':
		return vi(s)
	print type(v)
		
	return v

def editEntry(ent):
	done = False
	options = ['Show', 'Set Summary', 'Set Type', 'Set Priority', 'Set Rating', 'Set Deadline', 'Edit Data', 'Remove Sub-Element', 'Add Ref', 'Attach', 'Add Secret', 'Commit']
	while not done:
		act = _chooseList(options)
		if act ==None:
			return None
		elif act == 'Commit':
			return ent
		elif act == 'Show':
			print(ent.str(True))
		elif act == 'Set Summary':
			s = _strInput('summary', ent.attrib('Summary'))
			ent.setAttrib('Summary', s)
		elif act == 'Set Type':
			print "Type is currently %s" % (ent.attrib('Type'),)
			t = allTypes()
			t.append('New Type')
			t = _chooseList(t)
			if t == None:
				continue
			if t == 'New Type':
				t = raw_input('Type > ')
			ent.setAttrib('Type', t)
		elif act in ['Set Priority', 'Set Rating']:
			atr = act.split()[-1]
			print 'Current value is %s' % (ent.attrib(atr),)
			pri = [str(i) for i in range(1, 11)]
			pri = _chooseList(pri)
			if pri == None:
				continue
			ent.setAttrib(atr, pri)
		elif act == 'Set Deadline':
			print "Use '+N' to set N days from now, MM/DD to set a calendar day, and MM/DD:hh:mm (24 hour) to set a full date and time"
			d = raw_input("> ").strip()
			try:
				if d.startswith('+'):
					t = time.time()
					t = t + 24*60*60*int(d.lstrip("+"))
				else:
					t = list(time.localtime())
					if ":" in d:
						d, h, m = d.split(':')
						t[3]=int(h)
						t[4]=int(m)
					m, d = d.split('/')
					if t[1]>m:
						t[0]=t[0]+1
					t[1]=int(m)
					t[2]=int(d)
					t  = time.mktime(t)
				ent.setAttrib('Deadline', str(t))
			except:
				print "Failed to convert to a time. Ignored"
		elif act == 'Edit Data':
			s = _strInput('data', ent.cdata)
			ent.cdata = s			
		elif act.startswith('Remove'):
			els = [str(el) for el in ent.elements]
			print "delete sub-element"
			sel = _chooseList(els)
			if sel == None:
				continue
			el = ent.elements[els.index(sel)]
			el.sever()
		elif act == "Attach":
			s = _strInput('file name', os.path.expanduser("~/Desktop/"))
			a = nmp.create('SBAttachment', 'a')
			ent.newElement(a)
			a.bind(s)
			print "Attached %s as %s" % (s, a.attrib('Path'))
		elif act == "Add Ref":
			el = nmp.create("SBReference", 'r')
			s = _strInput('bib file name', os.path.expanduser("~/Desktop/scholar.bib"))
			el.loadBib(s)
			ent.newElement(el)
		elif act == "Add Secret":
			el = nmp.create("SBSecret", 'c')
			s = _strInput('content', "username:, password: ")
			el.encrypt(s)
			ent.newElement(el)




def _syscall(cmd, s, placeholder = None):
	fid, fname=tempfile.mkstemp('.txt')
	fobj=os.fdopen(fid, 'w')
	fobj.write(s)
	fobj.close()
	if placeholder:
		cmd=cmd.replace(placeholder, fname)
	else:
		cmd=cmd+" "+fname		
	os.system(cmd)
	s=open(fname).read()
	os.unlink(fname)
	return s

def vi(s=''):
	'''edit string s in vim, return the result.'''
	return _syscall('vim', s)

def _getel(el, sub = None):
	ei = None
	if el == None:
		if e[0]==None:
			print "No selected element"
		else:
			ei = e[0]
	elif type(el) in [str, unicode]:			
		el = doc.getElements('SBEntry', el, depth=1)
		if not el:
			print "No entries match name"
		else:
			ei = el[0]
	if ei and sub:
		ei = ei.getElements(sub)
		if not ei:
			print "selected element has no sub-elements of required type"
			ei=None
		else:
			ei = ei[0]
	return ei
	
def _sresults(l, clear = True):
	if clear:
		hit.clear()
	for el in l:
		hit.add(el)
	if len(hit)>20:
		print "%i hits" % (len(hit),)
	else:
		hits()		
		
		
### UI 		
	
def new():
	'''create a new element and edit it'''
	ent = nmp.create('SBEntry', 'e')
	doc.newElement(ent)
	ed = editEntry(ent)
	if not ed:
		print('Cancelled new')
		ent.sever()
	else:
		save()

def clear():
	'''clear the hit list'''
	hit.clear()

def browse(start=0, stop=-1):
	'''select as hits all entries between the indexes start and stop'''
	els = allEntries()
	if stop<0:
		stop = len(els)
	els = els[start:stop]
	for i in els:
		hit.add(i)
	hits()	

def hits():
	'''show hits'''
	if not hit:
		print "No hits"
		return
	for i in hit:
		print str(i)

def show(el=None):
	'''print data about el'''
	el = _getel(el)
	if el:
		print el.str(True)

def showsec(el=None):
	'''showsec(elementname). Decrypt and print secret data ossociated to elementname (or e[0])'''
	el = _getel(el, "SBSecret")
	if el:
		s=el.decrypt()
		print
		print s

def search(ss, where='sdt', restrict=True):
	'''where may be s (Summary), d (data), t (Type) or any combination, if ss is a string. Defaults to all.'''	
	if hit and restrict:
		els = list(hit)
	else:
		els = allEntries()
	matches = []
	for el in els:
		if 's' in where and ss in el.attrib('Summary'):
			matches.append(el)
			continue
		if 'd' in where and ss in el.cdata:
			matches.append(el)
			continue
		if 't' in where and ss in el.attrib('Type'):
			matches.append(el)
			continue
	_sresults(matches)



def psearch(i, where='p', restrict = True):
	'''Where may be p (Priority) or r (rating). Default is p. searches for cases where Priority is defined, and >=i'''
	if hit and restrict:
		els = list(hit)
	else:
		els = allEntries()
	matches = []
	for el in els:
		if where == 'p':
			p = el.attrib('Priority')
		else:
			p = el.attrib('Rating')
		if not p:
			continue
		if int(p)>=i:
			matches.append(el)
	_sresults(matches)	

def soon(days = 1, restrict = True):
	'''Finds cases with deadlines less than "days" from now'''
	if hit and restrict:
		els = list(hit)
	else:
		els = allEntries()
	matches = []
	secs = days*60*60*24
	for el in els:
		d = el.attrib('Deadline')
		if d:
			d = float(d)
			if d - time.time() < secs:
				matches.append(el)
	_sresults(matches)



def sel():
	'''select an element from the hits list to place in location e[0] '''
	if not hit:
		print "No hits"
		e[0]=None
		return
	hitlist = list(hit)
	hitnames = [str(h) for h in hitlist]
	h = _chooseList(hitnames)
	if h == None:
		e[0]=None
		return
	i = hitnames.index(h)
	e[0] = hitlist[i]
	show()

def delete(el=None):
	'''destroy the named element'''
	el = _getel(el)
	if el:
		if el in hit:
			hit.remove(el)
		if e[0] == el:
			e[0]=None
		el.sever()
		save()

def edit(el = None):	
	el = _getel(el)
	if el:
		el=editEntry(el)
		if el:
			save()

def sync():
	''' synchronize with the server '''
	if socket.gethostname() ==  SERVER:
		print "You ARE the server!"
		return
		
	if not os.path.exists(os.path.join(WD, '.CHANGED')):
	 	down = True
	elif not os.path.exists(os.path.join(WD, '.SYNCED')):
		down = True
	else:
		st = float( open (os.path.join(WD, '.SYNCED')).read() )
		ct = float( open (os.path.join(WD, '.CHANGED')).read() )
		down = st > ct
	if down:
		print "downloading"
		cmd = "rsync -av --delete --exclude=.* %s:msb/ ~/msb/" % (SERVER,)
		os.system(cmd)
		open (os.path.join(WD, '.SYNCED'), 'w').write(str(time.time())) 
	else:
		print "uploading"
		cmd = "rsync -av --delete --exclude=.* ~/msb/ %s:msb/ " % (SERVER,)
		os.system(cmd)

def h():
	print "UI Functions: save, showsec, new, clear, browse, hits,  show, search, psearch, soon, sel, delete, edit, sync"

if __name__ == '__main__':
	ns = globals()
	ns.update(locals())
	from IPython.Shell import IPShellEmbed
	ipshell = IPShellEmbed(argv=[])
	ipshell(local_ns=ns)
