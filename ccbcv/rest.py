	#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-07-15.

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

#from restclient import Resource
import json, urllib2, base64

class PutRequest(urllib2.Request):
	def get_method(self):
		return "PUT"
	

class DeleteRequest(urllib2.Request):
	def get_method(self):
		return "DELETE"

class Resource(object):
	def __init__(self, url):
		self.url = url
		self._auth = None
		self.opener = urllib2.build_opener(urllib2.HTTPHandler)
		
	def build_request(self, verb, path,  headers, payload=None):
		url = self.url + path
		if verb == 'put':
			req = PutRequest(url)
		elif verb == 'delete':
			req = DeleteRequest(url)
		else:
			req = urllib2.Request(url)
		if payload:
			req.add_data(payload)
			cl =  len(payload)
			req.add_header("Content-Length", cl)
		for k in headers:
			req.add_header(k, headers[k])
		return req

	def auth(self, uid, password=''):
		if uid == None:
			self._auth = None
		else:
			self._auth = base64.encodestring(uid+":"+password).rstrip("\n")

	def send_request(self, verb, path, headers=None, payload=None, isjson=True):
		if headers == None:
			headers = {}
		if self._auth:
			headers['Authorization'] = "Basic " + self._auth
		if isjson:
			headers['Content-Type'] ='application/json'
			if payload:
				payload = json.dumps(payload)
			else:
				headers['Accept'] = 'application/json'
		req = self.build_request(verb, path, headers, payload)
		s = self.opener.open(req).read()
		if isjson and verb == "get":
			s = json.loads(s)
		return s

	def get(self, path, isjson = True):
		return self.send_request('get', path, isjson=isjson)

	def post(self, path, payload, headers=None, isjson=True):
		return self.send_request("post", path, headers, payload, isjson) 

	def put(self, path, payload, headers=None, isjson=True):
		return self.send_request("put", path, headers, payload, isjson) 

	def delete(self, path):
		return self.send_request("delete", path, isjson=False) 

		
#be careful with the "/" on path and urlname. "//" and trailing "/" are not ignored 

class PSDB(Resource):
	def __init__(self, url, path):
		Resource.__init__(self, url)
		self.path = path
	
	def report(self, s):
		print(s)

	def getIDList(self):
		l = self.get(self.path)
		return [x['id'] for x in l]
		
	def getInfo(self, iid):
		d=self.get(self.path+iid)
		return d

	def new(self, iid, meta, data, check=True):
		if check and iid in self.getIDList():
			raise IOError('Entry %s already exists. Please use Update')
		pl = {'metadata':meta, 'id':iid}
		self.post(self.path, pl)
		if data:
			self.put(self.path+iid+".datafile", data, {'Content-Type':'application/octet-stream'}, False)

	def update(self, iid, meta):
		rec = self.getInfo(iid)
		rec['metadata'].update(meta)
		self.put(self.path+iid, rec)


	def addOrUpdate(self, iid, meta, data):
		if iid in self.getIDList():
			self.update(iid, meta)
			self.putFile(iid, data)
		else:
			self.new(iid, meta, data, False)

	def putFile(self, iid, data, fpath='datafile', ctype='application/octet-stream'):
		self.put(self.path+iid+"." + fpath, data, {'Content-Type':ctype}, False)

	def delete(self, iid):
		Resource.delete(self, self.path+iid)

	def getFile(self, iid, fpath='datafile'):
		return self.get(self.path+iid+"." + fpath, False)
	


if __name__=='__main__':
	URL = 'http://cercus.cns.montana.edu:8090'
	PATH = '/CercalCellAfferent/'
	test = PSDB(URL, PATH)
	#print test.getIDList()
	test.delete('testme')
	#test.new('testme', {"foo":"bar", "baz":"qux"}, 'randomdatastring')
	#test.update('testme', {"foo":"barth", "baz":"quuux"})
	#test.putFile('testme', 'ff')
	#print test.getInfo('testme')	
	#print test.getFile('testme')
