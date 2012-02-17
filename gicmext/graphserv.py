#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2008-07-14.

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


from SocketServer import TCPServer,StreamRequestHandler,BaseServer
import socket, struct, cPickle, threading
from mien.nmpml.data import newData
from mien.math.array import array, reshape, fromstring

HOSTNAME = socket.gethostname()
ADDR=socket.gethostbyname(HOSTNAME)
PORT=8898

class QueueHandler(StreamRequestHandler):
	def handle(self):
		hl=struct.unpack("<l", self.rfile.read(4))[0]
		h=cPickle.loads(self.rfile.read(hl))
		a=fromstring(self.rfile.read(), "<f4")
		a=reshape(a, h['ashape'])
		del(h['ashape'])
		self.server.plot(a,h)
		self.wfile.write("ok")

class GraphServer(TCPServer):
	def __init__(self, dv, port):
		self.dv=dv
		self.port=port
		self.addr = ADDR
		self.abort=False
		BaseServer.__init__(self, (self.addr, self.port), QueueHandler)

	def start(self):	
		self.socket = socket.socket(self.address_family,
                                    self.socket_type)
		self.server_bind()
		self.server_activate()
		self.serveThread=threading.Thread(target=self.serve_forever)
		self.serveThread.setDaemon(True)
		self.serveThread.start()


	def serve_forever(self):
		print "starting server on %s:%i" % (self.addr, self.port)
		while not self.abort:
			self.handle_request()
		print "server done"	

	def plot(self, a, h):	
		if not self.dv.data or self.dv.data.__tag__!="Data":
			dat=newData(None, {'SampleType':'group'})
			self.dv.document.newElement(dat)
			self.dv.report('Auto-generating Data element')
			self.dv.data=dat
			self.dv.onNewData()
		self.dv.data.datinit(a, h)
		self.dv.update_all(object=self.dv.data)
		

def launchGraphServer(dv):
	d=dv.askParam([{'Name':'Port', 'Value':PORT }])
	if not d:
		return
	g=GraphServer(dv, d[0])
	g.start()
	dv.report('Started graph server on port %i' % d[0])
	
def graph(d, h, addr=ADDR, port=PORT):	
	soc=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	soc.connect((ADDR, PORT))
	h['ashape']=d.shape
	h=cPickle.dumps(h)
	h=struct.pack('<l', len(h))+h
	soc.send(h+d.astype("<f4").tostring())
	soc.shutdown(1)
	v=[]
	m=0
	while m<3:
		r=soc.recv(100)
		if len(r)==0:
			m+=1
		v.append(r)
	soc.close()	
	v=''.join(v)
	return v

def graphts(dat, fs=1.0):
	graph(dat, {"SampleType":'timeseries', 'SamplesPerSecond':fs})
