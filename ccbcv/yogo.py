#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-07-14.

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
from mien.wx.base import BaseGui
import wx, tempfile, json, os, wx
import mien.parsers.fileIO as io
from ccbcv.rest import PSDB, Resource
from mien.parsers.mzip import serialize, deserialize
from mien.parsers.nmpml import createElement
from numpy import mean, array

URLS = ['http://cercus.cns.montana.edu:8090']



class SearchGui(wx.Dialog):
	def __init__(self, xm, records, id=-1, **opts):
		self.xm=xm
		self.attribs = self.getAandV(records)
		self.records = self.getRecords(records)
		self.conditions=[]
		self.found=self.records.keys()
		wxopts = {'title':"DB Search"} 
		wxopts.update(opts)
		wx.Dialog.__init__(self, xm, id, **wxopts)
		self.sizer = wx.BoxSizer(wx.VERTICAL)
		
		box = wx.BoxSizer(wx.HORIZONTAL)
		self.newAtrB = wx.Button(self, -1, " Add Condition ")
		wx.EVT_BUTTON(self, self.newAtrB.GetId(), self.addCond)
		box.Add(self.newAtrB, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		self.applyB = wx.Button(self, -1, " Search ")
		wx.EVT_BUTTON(self, self.applyB.GetId(), self.runSearch)
		box.Add(self.applyB, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		self.downB = wx.Button(self, -1, " Download ")
		wx.EVT_BUTTON(self, self.downB.GetId(), self.getFound)
		box.Add(self.downB, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		self.dismissB = wx.Button(self, -1, " Dismiss ")
		wx.EVT_BUTTON(self, self.dismissB.GetId(), lambda x:self.Destroy())
		box.Add(self.dismissB, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		self.sizer.Add(box, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)

		self.info=wx.StaticText(self, -1, "         %i Entries Found      " % len(self.found))
		self.sizer.Add(self.info, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		self.SetSizer(self.sizer)
		self.SetAutoLayout(True)
		self.sizer.Fit(self)
		self.Show(True)


	def tonumber(self, v):
		if type(v) in [tuple, list]:
			try:
				return float(mean(array(v)))
			except:
				return None
		try:
			v = float(m[k])
		except:
			try:
				v = v.split("_")
				v1 = float(v[0])
				v2 = float(v[1])
				v = (v1+v2)/2.0
			except:
				return None
		return v
			
		
	def getAandV(self, r):
		a = {}
		for dic in r:
			m = dic['metadata']
			for k in m:
				if not k in a:
					a[k]=set([])
				v = self.tonumber(m[k])
				if v == None:
					v = m[k]
					if type(v)==list:
						v = tuple(v)
				a[k].add(v)
		for k in a:
			a[k] = list(a[k])
		return a
			
	def getRecords(self,r):
		a = {}
		for dic in r:
			id_ = dic['id']
			md = dic['metadata']
			for k in md:
				v = self.tonumber(k)
				if v!=None:
					md[k]=v
			a[id_]=md
		return a
			
	def match(self, cond):
		if len(cond) == 2:
			return [k for k in self.records if self.records[k].get(cond[0])==cond[1]]
		else:
			matches = []
			for k in self.records:
				try:
					v = float(self.records[k][cond[0]])
					b = eval("%G %s %s" % (v, cond[1], cond[2]))
					if b:
						matches.append(k)
				except:
					pass
			return matches
			
				
	def runSearch(self, event):
		conds =[]
		for c in self.conditions:
			cond = []
			if c[0]=='--':
				cond.append('--')
			else:
				cond.append(c[0].GetStringSelection())
			cond.append(c[1])
			cond.append(c[2].GetStringSelection())
			if len(c)>3:
				cond.append(c[3].GetValue())
			conds.append(cond)
		vals = set(self.match(conds[0][1:]))
		for c in conds[1:]:
			nv = set(self.match(c[1:]))
			if c[0]=='And':
				vals = vals.intersection(nv)
			else:
				vals = vals.union(nv)
		self.found = list(vals)
		self.info.SetLabel("    %i Entries found    " % len(self.found))

	def noop(self, event):
		pass
		
	def killBox(self, box, cond):
		self.conditions.remove(cond)
		box.DeleteWindows()
		self.sizer.Fit(self)

	def finish_cond(self, box, chooseatr, cond):
		atr = chooseatr.GetStringSelection()
		cond.append(atr)
		box.Add(wx.StaticText(self, -1, atr), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		vals = self.attribs[atr]
		if all([type(x) in [int, float] for x in vals]):
			mi = min(vals)
			ma = max(vals)
			box.Add(wx.StaticText(self, -1, "%G - %G" % (mi, ma)), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
			chooseop = wx.Choice(self, -1, choices=['<', '>', '==', "<=", ">=", "!="])
			box.Add(chooseop,  0, wx.ALIGN_CENTRE|wx.ALL, 5)
			cond.append(chooseop)
			val = wx.TextCtrl(self, -1, "%G" % ma)
			box.Add(val,1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
			cond.append(val)
		else:	
			chooseval = wx.Choice(self, -1, choices=map(str, vals))
			box.Add(chooseval,  0, wx.ALIGN_CENTRE|wx.ALL, 5)
			cond.append(chooseval)
		self.sizer.Fit(self)
		chooseatr.Destroy()
		self.sizer.Fit(self)
			

	def addCond(self,event):
		cond = []
		box = wx.BoxSizer(wx.HORIZONTAL)
		db = wx.Button(self, -1, " DEL ")
		wx.EVT_BUTTON(self, db.GetId(), lambda x: self.killBox(box, cond))
		box.Add(db, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		
		if len(self.conditions)>0:
			dowhat=	wx.Choice(self,-1, choices=["And", "Or"])
			cond.append(dowhat)
			box.Add(dowhat,  0, wx.ALIGN_CENTRE|wx.ALL, 5)
		else:
			cond.append('--')
		
		chooseatr = wx.Choice(self, -1, choices=self.attribs.keys())
		box.Add(chooseatr,  0, wx.ALIGN_CENTRE|wx.ALL, 5)
		wx.EVT_CHOICE(self, chooseatr.GetId(), lambda x: self.finish_cond(box, chooseatr, cond))		
		self.conditions.append(cond)
		self.sizer.Add(box, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		self.sizer.Fit(self)

	def getFound(self, event):
		if self.found:
			self.xm.downloadGroup(records=self.found)

class DBTool(BaseGui):
	def __init__(self, parent, **opts):
		BaseGui.__init__(self, parent, title="Database Tool", menus=["Connection", "Get", "Put"], pycommand=True)
		
		controls=[["Connection", "Choose Data Store", self.selectDB],
				  ["Get", "List All Entries", self.list],
				  ["Get", "Show Details", self.infoprint],
				  ["Get", "Search", self.do_search],
				  ["Get", "Download Single File", self.download],
				  ["Get", "Download Several Files", self.downloadGroup],
				  ["Put", "Upload Current File", self.upload],
				  ]		
		self.fillMenus(controls)
		self.mainSizer = wx.BoxSizer(wx.VERTICAL)
		self.main.SetSizer(self.mainSizer)
		self.main.SetAutoLayout(True)		
		self.SetAutoLayout(True)		
		self.mainSizer.Add(wx.StaticText(self.main, -1, 'Connected To:'), 1, wx.GROW|wx.ALL|wx.ALIGN_CENTRE, 5)
		self.dbid = wx.StaticText(self.main, -1, '')
		self.mainSizer.Add(self.dbid, 1, wx.GROW|wx.ALL|wx.ALIGN_CENTRE, 5)		
		self.dbreccount = wx.StaticText(self.main, -1, '0 Records')
		self.mainSizer.Add(self.dbreccount, 1, wx.GROW|wx.ALL|wx.ALIGN_CENTRE, 5)
		self.selectDB(None, URLS[0], "/CercalSystem/")
		self.doc = self.Parent.document
		self.SetSize(wx.Size(500,200))
		
		
	def getMetas(self):
		conflict = []
		metas = {}
		for e in self.doc.elements:
			m = dict([(k[5:], e.attrib(k)) for k in e.attributes if k.startswith("meta_")])
			for k in m:
				if k in conflict:
					continue
				elif not k in metas:
					metas[k] = m[k]
				elif metas[k]!=m[k]:
					del(metas[k])
					conflict.append(k)
		return metas	

	def classList(self, url):
		z=Resource(url)
		d=z.get('/Class/')
		cl = ['/'+a['id']+'/' for a in d if not a.get('core')]
		return cl
	
	def selectDB(self, event, url=None, clas='/CercalSystem/'):
		if not url:
			if len(URLS)==1:
				self.report("Only one datastore available. Using it")
				url = URLS[0]
			else:
				d = self.askParam([{"Name":"Select Database Site", "Type":"List", "Value":URLS}])
				if not d:
					return
				url =d[0]
		if not clas or type(clas)==int:
			cl = self.classList(url)
			if len(cl)==1:
				clas = cl[0]
			elif type(clas)==int:
				clas = cl[clas]
			else:
				d = self.askParam([{"Name":"Select Database Table", "Type":"List", "Value":cl}])
				if not d:
					return
				clas =d[0]
		self.rest = PSDB(url, clas)
		self.dbid.SetLabel('%s%s' % (url, clas))
		n = len(self.list(None))
		self.dbreccount.SetLabel("%i records" % n)


	def list(self, event):
		ids = self.rest.getIDList()
		if event==None:
			return ids
		self.report("\n".join(ids))
		
	def upload(self, event):
		groups = self.doc.getElements("Group")
		groups = [g for g in groups if g.attrib("DBrecord")]
		if any(groups):
			self.report('found existing records. Committing them to the DB')
			for g in groups:
				self.report(g.name())
				self.upload_group(g)
		else:
			self.report('no existing DB groups. Uploading whole file as new record')
			self.upload_doc()
			
	def upload_group(self, g):
		m =  dict([(k[5:], g.attrib(k)) for k in g.attributes if k.startswith("meta_")])
		name = g.name()
		self.do_upload(name, g, m)
	
	def upload_doc(self):
		m = self.getMetas()
		name = "%s_%s_%s" % (m['length'][0].upper(), str(m['class']), str(m['slide_number']))
		self.do_upload(name, self.doc, m)
	
	def do_upload(self, name, doc, meta):
		name = name.replace(".", "_")
		s = serialize(None, doc)
		self.rest.addOrUpdate(name, meta, s)
		self.report("sent")
		
	def infoprint(self, event):
		ids = self.list(None)
		d = self.askParam([{"Name":"Which Record?", "Type":"List", "Value":ids}])
		if not d:
			return
		print self.rest.getInfo(d[0])	
	
	def do_search(self, event):
		j = self.rest.get(self.rest.path)
		import ccbcv.yogo
		reload(ccbcv.yogo)
		s=ccbcv.yogo.SearchGui(self, j)
		
	def download(self, event=None, record=None, append=True, refresh=True):
		if not record:
			ids = self.list(None)
			d = self.askParam([{"Name":"Which Record?", "Type":"List", "Value":ids}])
			if not d:
				return
			record = d[0]
		df = self.rest.getFile(record)
		doc = deserialize(df)
		if not append:
			self.Parent.newDoc(doc)
		else:			
			m = self.rest.getInfo(record)['metadata']
			m = dict([('meta_'+k, m[k]) for k in m])
			m["Name"]=record
			m["DBrecord"]=self.rest.path
			m["DBurl"]=self.rest.url
			m["color"] = (255,255,255)
			group = createElement("Group", m)
			self.Parent.document.newElement(group)
			for e in doc.elements[:]:
				e.move(group)
			if refresh:
				self.Parent.update_all(element=self.Parent.document, action='rebuild')

	def downloadGroup(self, event=None, records=None):
		if not records:
			ids = self.list(None)
			d = self.askParam([{"Name":"Which Record?", "Type":"Select", "Value":ids}])
			if not d:
				return
			records = d[0]
		for r in records:
			self.download(None, r, True, False)
		self.Parent.update_all(element=self.Parent.document, action='rebuild')
		
			
		
		
