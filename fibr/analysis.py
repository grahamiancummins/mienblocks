#!/usr/bin/env python
# encoding: utf-8
#Created by Graham Cummins on 2007-08-24.

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

from numpy import *
import mien.optimizers.arraystore as ast
from controls import SIZEOFSTATE


pnames=['sHt', 'sSpd', 'eReach', 'eSide', 'eExtend', 'eLead', 'eTime', 'ePower', 'eQlag', 'eQsym', 'eSlag', 'eSsym', 'rReach', 'rSide', 'rExtend', 'rLead', 'rTime', 'rPower', 'rQlag', 'rQsym', 'rSlag', 'rSsym']

def getReturnSteps(fn):
	a=ast.ArrayStore(fn)
	a=a.toarray()
	ind=nonzero(a[:,0]>0)
	a=a[ind[0],1:]
	return a
	
def load(fn):
	z=ast.ArrayStore(fn)
	return z.toarray()	
	
def writeSteps(fn, a):
	z=ast.empty(fn, a.shape[1])
	z=ast.ArrayStore(fn, 'w')
	z.setarray(a)
	z.close()


def writeStepFile(a, fn):
	f=file(fn, 'w')
	for i in range(len(pnames)):
		f.write("%s %.3f\n" % (pnames[i], a[i+SIZEOFSTATE+1]))
	f.close()
	
if __name__=='__main__':
	import sys
	a=getReturnSteps(sys.argv[1])
	print a.shape
	writeSteps(sys.argv[2], a)
	z=ast.ArrayStore(sys.argv[2])
	#print z.toarray().shape

	
	
