#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-07-22.

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


#Steps to create a snapshot:
#For all of the below, you will need mien and mienblocks directories in your pythonpath. 
#You will have to set the mien directory in the PYTHONPATH environment variable. You can then 
#set the blocks directory automatically, using:

import mien.blocks


# You will also need a very recent update of mien for some of this stuff to work

#1) Get a data file. To do this you need a database URL, class path, and id


#these my be set as constants, downloaded from some url, or whatever.
URL = 'http://cercus.cns.montana.edu:8090'
PATH = '/CercalCellAfferent/'

#construct a Rest resource

from ccbcv.rest import PSDB
JSONH = {'Content-type': 'application/json', 'Accept':'application/json'}
CERCDB = PSDB(URL, PATH)

# you can request a list of database records:

idlist = PSDB.getIDList()

# see ccbcv.scripts or ccbcv.yogo for examples of polling, searching, etc from the DB

#select some record

record = idlist[0]

#obviously, there are more useful ways to do this. This is just an example

# now download the record to a local document:

df = CERCBD.getFile(record)

#right now this file is a string. You want a MIEN document, so we need to decode it

from mien.parsers.mzip import deserialize
doc = deserialize(df)

#doc is now a MIEN document instance, containing several anatomical data objects

#2) Create a CellViewer, and load the data

#First, set the display
import os
os.environ['DISPLAY'] = 'localhost:1.0'
#This is required to set the display if you are logged into phobos (or another linux box) via ssh
#Unless Ryan simplified this part of the setup
#Somewhere else in the system, you will need to issue "xinit -- /usr/bin/X 1:" in order to start this 
#display so you can bind to it. 
#If you are locally logged in on console, you don't need this

#Now make a CV
import wx
from mien.interface.cellview3D import CellViewer
wxapp = wx.PySimpleApp()
x = CellViewer()
x.Show(True) # On Mac or Windows, you don't need to do this "Show" step, but on recent Linux, you do.

#Attach the document you downloaded to the CV

x.newDoc(doc)

#3) Set the camera viewpoint

# A) you can load a saved viewpoint from a file:

fn = "/path/to/viewpoint.nmpml"  # you had to make this file separately,
# use CV->Extensions->Viewpoints->Save Display Specification from an interactive CV session.
from mien.spatial.viewpoints import readDisplaySpec
readDisplaySpec(x, fn)

# B) Alternatively, you can set the display manually, using python constants stored in your script.
#

#set the background color
x.graph.clearcolor = [0,0,0]
#This is a GL color, so it is float values between 0 and 1, not ints 0-255. [1.0, 1.0, 1.0] is white.

#set the quadric resolution. This is the number of facets used to draw a sphere or cylinder	
x.graph.slices = 12

#set the viewpoint. This is the 3D location of the camera
from numpy import array
x.graph.viewpoint=array((159, 175, 527) )

#set the camera orientation
x.graph.forward = array((0, 0, -1.0))
x.graph.up = array((0, 1.0, 0))

#set the width of the view volume
x.graph.extent = 558.5

#set the depth of the view volume
x.graph.depthoffield = 1117.6

#redraw the scene

x.graph.OnDraw()

# If you like, you can also set a display filter 
x.displayfilter = ["Cells", "Spheres"]
# this particular one will show only the varicosities, and the axons. 
#You can include in the list any elements in:
# "Cells", "Spheres", "Fields","Named Points", "Lines", "Images"
# If you set this to "[]" you will show all elements
#Once you set it, you need to do:
x.addAll()
#to make it take effect


#3) Set the colors of things:

#You probably want to start out with this:

from ccbcv.dircolors import SetDirectionalTuningFromMetaTags 
SetDirectionalTuningFromMetaTags(x)
# This colors everything according to a directional color coding scheme

# You can also set a given element any color you want, although this is a bit cumbersome
# To do it you need an object reference for the object you want. There are too many ways to do this
# to show them all. Here is a simple one. If you need others, ask me.

obj = x.document.getElements("Fiducial", {"Style":"spheres"})[0]
# this gets the first sphere fiducial element in the document
# now get the name of the plot of this object
plotname = x.getPlotName(obj)
#now set the color
x.graph.plots[plotname]['color'] = (1, 1 , 1)
#now recompute the plot
x.graph.reclac(pn)
# and, if you need to, redraw it
x.graph.OnDraw()

# 4) Lets replace the fiducial lines in this file with the standard ones

fids = x.document.getElements("Fiducial", {"Style":"line"})
for f in fids:
	f.sever()
x.addAll()

from ccbcv.align import loadStandardFiducials
loadStandardFiducials(x.document)
x.addAll()

#Note that calls to addAll may be slow and expensive. You don't have to do them all the time. Only before you draw. I'm repeating them here in case you leave out some steps.


#5) We also want to remove the standard fiducials for the sagital and coronal contours
fids = [ f for f in x.document.getElements("Fiducial", {"Style":"line"}) if not "transverse" in f.name()]
for f in fids:
	f.sever()
x.addAll()


#6) Now take a picture 
fid, fname=tempfile.mkstemp('.png')
x.graph.screenShot(fname)

#7) upload the picture to the DB
CERCDB.putFile(record, open(fname,'rb').read(), "snapshot", 'image/png')
f = open(fname, 'rb')

#'snapshot' will end up being the name of the attribute that holds this 
#file in the database. To download the file using some other system, 
#you would need to send a "GET" to
#http://cercus.cns.montana.edu:8090/CercalCellAfferent/<record>.snapshot

os.unlink(fname)
	



# No doubt you will need some other manipulations, but this should get you started



