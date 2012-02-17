#!/usr/bin/env python

## Copyright (C) 2005-2006 Graham I Cummins
## This program is free software; you can redistribute it and/or modify it under 
## the terms of the GNU General Public License as published by the Free Software 
## Foundation; either version 2 of the License, or (at your option) any later version.
## 
## This program is distributed in the hope that it will be useful, but WITHOUT ANY 
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
## PARTICULAR PURPOSE. See the GNU General Public License for more details.
## 
## You should have received a copy of the GNU General Public License along with 
## this program; if not, write to the Free Software Foundation, Inc., 59 Temple 
## Place, Suite 330, Boston, MA 02111-1307 USA
## 

'''This block defines functions that calulate new timeseries by applying some function to a number of existing timeseries channels.'''

from mien.datafiles.dataset import *

def power(ds, select=(None, None, None), newpath='/power'):
	'''Calculate the cumulative power of the selection (sqrt(s**2)) and stores the reluting single channel in dpath'''
	dat=getSelection(ds, select)
	h=getSelectionHeader(ds, select)
	h['Labels']=['power']
	dat=sqrt((dat**2).sum(1))
	ds.createSubData(newpath, data=dat, head=h, delete=True)
