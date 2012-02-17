#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-07-06.

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


import bree, os, time
import mien.parsers.fileIO as io
from numpy import *

semaphore = os.path.expanduser("~/.matlabServiceSemaphore.txt")
datafile = os.path.expanduser("~/.matlabServiceData.mat")

moddir = os.path.split(bree.__file__)[0]
mfiledir = os.path.join(moddir, 'matlab')
mfile = 'tffrompars'

class MatlabService(object):
	def __init__(self, doc):
		doc._matlabservice = self
		self.doc = doc
		self.data = datafile
		self.semaphore = semaphore
		if not os.path.isfile(semaphore):
			self.launch()

	
	def launch(self):
		open(self.semaphore, 'w').write("0\n")
		os.system('matlab -nosplash -nojvm -r "path(\'%s\', path);matlablistener(\'%s\', \'%s\', \'%s\', \'%s\')" &' % (mfiledir, self.data, self.semaphore, mfile, mfiledir))

	
	def __del__(self):
		self.quit()
		
	def quit(self):
		try:
			open(self.semaphore, 'w').write("-1\n")
		except:
			pass
		try:
			self.doc._matlabservice = None
		except:
			pass
		
	def eval(self, ds):
		ds = ds.clone()
		ds.setName('data')
		io.write(ds, self.data, format='.mat', newdoc=1)
		open(self.semaphore, 'w').write("1\n")
		sv = 1
		while sv == 1:
			time.sleep(.5)
			try:
				sv = int(open(self.semaphore, 'r').read())
			except:
				pass
		doc = io.read(self.data)
		ds=doc.getElements('Data')[0]
		if not ds.data.shape[1]==3:
			print ds.attributes
			ef = ones(ds.data.shape[0])*1.9
			ds.data = column_stack([ds.data[:,0], ef, ef])
		return ds


def mservicecall(ds):
	doc = ds.xpath(True)[0]
	try:
		ms = doc._matlabservice
		if not ms:
			raise StandardError("no service")
	except:
		ms = MatlabService(doc)
	return ms.eval(ds)


def mserviceclose(ds):
	doc = ds.xpath(True)[0]
	try:
		ms = doc._matlabservice
		ms.quit()
	except:
		if os.path.isfile(semaphore):
			open(semaphore, 'w').write('-1\n')

	



