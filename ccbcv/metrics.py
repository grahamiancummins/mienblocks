#!/usr/bin/env python
# encoding: utf-8
#Created by Graham Cummins on 2007-06-26.

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

def printSimpleMetrics(doc, elems=[]):
	'''Calculate and print some simple metrics. Elems needs to include some "Cell" elemnts, since these metrics are only defined for cells.''' 
	for on in elems:
		obj=doc.getInstance(on)
		print "** Metrics for object %s **" % (obj.name())
		if not obj.__tag__=='Cell':
			print "  No metrics. This element is type %s. Metrics can only be calculated for Cell elements" % (obj.__tag__,)
			continue
		secs=obj._sections.values()
		print "  %i sections" % (len(secs),)
		nbp=0
		for k in obj._children.keys():
			if len(obj._children[k])>1:
				nbp+=1
		print "  %i branch points" % nbp	
		met=zeros((len(secs), 3))
		for i in range(met.shape[0]):
			s=secs[i]
			inf=s.morphInfo()
			met[i,0]=inf['length']
			met[i,1]=s.getPoints()[:,3].mean()	
			met[i,2]=inf['area']
		print "  total path length: %.3f" % (met[:,0].sum())		
		print "  average diameter: %.3f" % (obj.getPoints(True)[:,3].mean())		
		print "  total surface area: %.3f" % (met[:,2].sum())
		

def branchOrderStatistics(doc, elems=[]):
	'''Calculate and print the histogram of branch orders for a cell object '''			
	for on in elems:
		obj=doc.getInstance(on)
		print "** Metrics for object %s **" % (obj.name())
		if not obj.__tag__=='Cell':
			print "  No metrics. This element is type %s. Metrics can only be calculated for Cell elements" % (obj.__tag__,)
			continue
		bdd={}
		for s in obj.branch():
			bd=obj.branchDepth(s)
			bdd[bd]=bdd.get(bd,0)+1
		kl=bdd.keys()
		kl.sort()
		for bd in kl:
			print "%i sections with branch order %i" % (bdd[bd], bd)
	