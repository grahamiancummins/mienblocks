#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2007-12-17.

# Copyright (C) 2007 Graham I Cummins
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

from gicspikesort.spikes import *

#def schmitTrigger(ds, thresh1, thresh2, select=(None, [0], None), newpath='/spikes', above=True, labs=None):

#sdf(self.dat, sel, pars, path)

def schmidt(data, select, params, path):
	abv=1
	if len(params)==3:
		abv=params[2]
		params=params[:2]
	dc=getSelection(data, select)
	mv=dc.max()
	ev=dc.mean()
	d=mv-ev
	thresh1=ev+d*min(params)
	thresh2=ev+d*max(params)
	schmitTrigger(data, thresh1, thresh2, select, path, abv, "Trigger Spikes")


DETECTORS={'schmidt':schmidt}