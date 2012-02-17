#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-07-16.

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

from mien.interface.cellview3D import CellViewer
import wx, os, sys, tempfile
from mien.parsers.mzip import deserialize
sys.path.append("/home/gic/mienblocks")
from ccbcv.rest import PSDB

URL = 'http://cercus.cns.montana.edu:8090'
PATH = '/CercalCellAfferent/'
CERCDB = PSDB(URL, PATH)
os.environ['DISPLAY'] = 'localhost:1.0'
record = sys.argv[1]
wxapp = wx.PySimpleApp()
x = CellViewer()
x.Show(True)
df = CERCDB.getFile(record)
doc = deserialize(df)
x.newDoc(doc)
fid, fname=tempfile.mkstemp('.png')
x.graph.screenShot(fname)
CERCDB.putFile(record, open(fname,'rb').read(), "snapshot", 'image/png')
os.unlink(fname)
