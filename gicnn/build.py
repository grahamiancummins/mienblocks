#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2008-12-15.

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

from numpy import array, sqrt
from nmpml import mknet
import os

IFT='''
begintemplate TREF
public pp, x, y, z, position, is_art
objref pp
proc init() {
  pp = new CTYPE()
}
func is_art() { return 1 }
proc position(){x=$1  y=$2  z=$3}
endtemplate TREF

'''


NETSPEC='''
//Network specification interface

objref cells, nclist, netcon
{cells = new List()  nclist = new List()}

func cell_append() {cells.append($o1)  $o1.position($2,$3,$4)
	return cells.count - 1
}

func nc_append() {//srcindex, tarcelindex, wt, delay
netcon = new NetCon(cells.object($1).pp, cells.object($2).pp)
netcon.weight = $3   netcon.delay = $4
nclist.append(netcon)
return nclist.count - 1
}

'''

MODINIT='''
celsius=20
dt=0.1
finitialize()
batch_save()

'''


# EXNET='''
#   /* IntFire10 */  cell_append(new IntFire1_IntFire1(),	37,	 22, 0)
#   /* defnetstim1 */  cell_append(new defnetstim_NetStim(),	-52,	 21, 0)
#   /* IntFire12 */  cell_append(new IntFire1_IntFire1(),	55,	 -35, 0)
#   /* defnetstim1 -> IntFire10    */  nc_append(1, 0, -1,  2,1)
#   /* IntFire10 -> IntFire12    */  nc_append(0, 2, -1,  0,1)
# '''

# batch_save(&ten3[1239].v(0.856))
# 
# batch_run(50, 0.100000, "output.bat")

class Cell(object):
	def __init__(self, modtype, pars):
		self.mt = modtype
		self.pars = pars
		self.position=(0,0,0)
		self.tref = None
		
	def setPosition(self, l):
		self.position=l
		
	def same(self, c):
		if self.mt == c.mt and self.pars == c.pars:
			self.tref = c.tref
			return True
		return False
		
	def template(self, n):
		self.tref = "c%i_%s" % (n, self.pars)
		s=IFT.replace('TREF', self.tref)
		s=s.replace('CTYPE', self.pars)
		return s

class Network(object):
	def __init__(self):
		self.cells = []
		self.connections = []
		self.recordings = []
		self.cell_recordings = []
		self.events = []
		self.terminate = []
		self.timeout = -1
		self.output=None
		self.fs = 2000.0
		
	def addCell(self, c):
		self.cells.append(c)
		return len(self.cells)-1
	
	def addConnection(self, i, j, wt, d):
		self.connections.append((i,j, wt, d))
		return len(self.connections)-1		

	def record(self, i):
		self.recordings.append(i)
		
	def recordCell(self, i, s):
		self.cell_recordings.append((i, s))
		
	def terminateOn(self, i):
		self.terminate.append(i)
		
	def eventIn(self, i, t):
		self.events.append((i, t))
		
	def crossingtime(self):	
		d = array([c[3] for c in self.connections])
		d = min(d.max(), 2*d.mean())
		nc = sqrt(len(self.cells))
		return d*nc
		
	def write_hoc(self, f):
		if type(f)==str:
			f=open(f, 'w')
		n = 0
		for i in range(len(self.cells)):
			ci = self.cells[i]
			if not any([ci.same(cj) for cj in self.cells[:i]]):
				f.write(ci.template(n))
				n+=1
		f.write(NETSPEC)
		for c in self.cells:
			f.write("cell_append(new %s(), " % c.tref)
			f.write("%.2f, %.2f, %.2f)\n" % c.position)
		for c in self.connections:
			f.write("nc_append(%i, %i, %.2f, %.2f)\n" % c)
		f.write(MODINIT)
		for e in self.events:
			f.write("nclist.object(%i).event(%.2f)\n" % e)
		for c in self.cell_recordings:
			f.write('batch_save(&cells.object(%i).pp.%s)\n' % c)
		t = self.crossingtime()
		sp = 1.0/(self.fs/1000.0)
		f.write('\nbatch_run(%.2f, %.2f, "output.bat")\n' % (t, sp))
			
			
	def buildMienNet(self):
		net=mknet()
		net.addCells(self.cells)
		net.addConnections(self.connections)
		if self.output!=None:
			net.setCellData(self.output, self.fs)
		return net	
		
	def run(self):
		self.write_hoc('net.hoc')
		#os.system("neuron net.hoc")
		self.output = array([[float(x) for x in s.split()] for s in open("output.bat", 'rb').readlines()[2:]])
		return self.buildMienNet()

