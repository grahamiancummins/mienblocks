#!/usr/bin/env python
# encoding: utf-8
#Created by Graham Cummins on 2007-09-24.

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


import mien.parsers.fileIO as io
from sys import argv
import gicmext.sysChar as sc
from numpy import *
from mien.nmpml.data import newData
	
	
def spikeDistance(e1d, e2d, cost=.002):
	if cost==0:
		d=abs(e1d.shape[0]-e2d.shape[0])
		print '0'
	elif cost>=2:
		d=union1d(e1d, e2d).shape[0]
		print '1'
	elif not (e1d.shape[0] and e2d.shape[0]):
		print 'nul'
		d=max(e1d.shape[0], e2d.shape[0])
	elif abs(e1d.shape[0]-e2d.shape[0])>3*e1d.shape[0]:
		print 'bogus'
		d=2*abs(e1d.shape[0]-e2d.shape[0])
	else:
		print 'ok'
		d=sc.victorDistance(e1d, e2d, cost)
	return d
		

def getAllDist(est, real, cost=0.1):
	cost=cost*1000.0/real.fs()
	dat1=est.getData()
	dat2=real.getData()
	id1=unique1d(dat1[:,1])
	id2=unique1d(dat2[:,1])
	dist=zeros((id1.shape[0], id2.shape[0]), float32)
	for i in range(id1.shape[0]):
		ii=id1[i]
		for j in range(id2.shape[0]):
			ji=id2[j]
			ei=take(dat1[:,0], nonzero(dat1[:,1]==ii)[0])
			ej=take(dat2[:,0], nonzero(dat2[:,1]==ji)[0])
			dist[i,j]=spikeDistance(ei, ej, cost)
	return (dist, id1, id2)

def makeEquiv(d, id1, id2):
	z=zeros((id1.shape[0],3), float32)
	for i in range(z.shape[0]):
		j=argmin(d[i,:])
		z[i,0]=id1[i]
		z[i,1]=id2[j]
		z[i,2]=d[i,j]
	return z


def spikeDistanceTest(st, rt):
	m, id1, id2=getAllDist(st, rt)
	print m
	d=makeEquiv(m, id1, id2)
	print d
	de=newData(zeros(0), {'SampleType':'group'})
	for i in range(d.shape[0]):
		rst=rt.getData()
		print rst.shape
		rst=take(rst[:,0], nonzero(rst[:,1]==d[i,1])[0], 0)
		est=st.getData()
		est=take(est[:,0], nonzero(est[:,1]==d[i,0])[0], 0)
		cst=zeros((rst.shape[0]+est.shape[0],2))
		cst[:rst.shape[0],0]=rst
		cst[rst.shape[0]:,0]=est
		cst[rst.shape[0]:,1]=1
		cde=de.createSubData("/unit%i" % (int(d[i,1]),), cst, {'SampleType':'labeledevents', 'SamplesPerSecond':rt.fs()})
	io.write(de, "check_results.mdat", format=".mdat", newdoc=True)



def getSortedTimes(d):
	dat=d.getData()
	ind=argsort(dat[:,0])
	return dat[ind,:]



def overlapReport(lt, loc, counts):
	print "-----"
	print "YUCK!! Here are the detailed counts:"
	getq=0
	while getq<lt:
		new=(-1, 0)
		for k in loc.keys():
			if loc[k]>new[1]:
				new=(k, loc[k])
		getq+=new[1]
		del(loc[new[0]])
		print "   %i: %i spikes (%.2f percent)" % (new[0], new[1], 100.0*new[1]/lt)
	print counts
	print "-----"

def missReport(ru, d):
	rd=d['rd']
	sd=d['sd']
	allr=rd[nonzero(rd[:,1]==ru)[0],0]
	alls=sd[nonzero(sd[:,1]==d['ssun'])[0],0]
	print 
	miss=[]
	hit=[]
	li=-1
	for j in range(allr.shape[0]):
		et=allr[j]
		i=li+1
		while i<alls.shape[0] and alls[i]<et-d['tol']:
			li=i
			i+=1
		if i>=alls.shape[0] or alls[i]>et+d['tol']:
			miss.append(allr[j])
		else:
			hit.append(allr[j])
			li+=1
	#print len(miss), len(hit), allr.shape[0], float(len(miss))/allr.shape[0],float(len(hit))/allr.shape[0]
	mper=100*float(len(miss))/allr.shape[0]
	miss=array(miss)
	supers={}
	li=-1
	for j in miss:
		i=li+1
		ids=[]
		while i<rd.shape[0] and rd[i,0]<j+d['tol']:
			while rd[i,0]<j-d['tol']:
				li=i
				i+=1
			id=rd[i,1]
			if id!=ru:
				ids.append(id)
			i+=1
		#z=tuple(unique1d(rd[nonzero((rd[:,0]-j)<d['tol'])][:,1])) 
		# orders of magnitude slower than the while loops!
		ids=tuple(unique1d(ids))
		supers[ids]=supers.get(ids,0)+1
	print "-----"
	print "%i misses (%.2f percent of spikes)" % (miss.shape[0], mper)
	print supers
	print "-----"
	
def subsetReport(counts, totals, stuff):
	lt=0
	aex=[]
	nsp=0
	for c in counts.keys():
		aex.extend(list(c))
		lt+=counts[c]
		if len(c)>1:
			nsp+=counts[c]
	uexp=unique1d(aex)
	loc={}
	ids=(-1, 0)
	print "%i total spikes" % lt
	#print (stuff['sd'][:,1]==stuff['ssun']).sum()
	for q in uexp:
		loc[q]=0
		for c in counts.keys():
			if q in c:
				loc[q]+=counts[c]
		if loc[q]>ids[1]:
			ids=(q, loc[q])
	ppf=100*float(ids[1])/lt
	prm = 100.0*ids[1]/totals[ids[0]]
	print "Best single unit match is %i, explaining %.2f percent of spikes" % (ids[0], ppf)
	print "Template detects %.2f percent of spikes in real unit %i" % (100.0*ids[1]/totals[ids[0]], ids[0])
	print "    %.4f percent of detected events are possible superpositions" % (100.0*nsp/ids[1])
	print "    These include spikes from units: %s" % (str(uexp),)
	if prm<99:
		missReport(ids[0], stuff)
	if ppf<99:
		overlapReport(lt, loc, counts)
	print "TYPE 1 ERROR: %.4f, TYPE 2 ERROR: %.4f" % (100-ppf, 100-prm)
		
	
	

def subsetTest(st,rt, tol=.0005):
	tol=tol*rt.fs()
	sd=getSortedTimes(st)
	rd=getSortedTimes(rt)
	asoc=[]
	sa={}
	lj=-1
	for i in range(sd.shape[0]):
		#print i
		sid=sd[i,1]
		if not sa.get(sid):
			sa[sid]={}
		j=lj+1
		spikes=[]
		while j<rd.shape[0] and sd[i,0]>rd[j,0]-tol:
			#print j
			if sd[i,0]>rd[j,0]+tol:
				lj=j
				j+=1
			else:
				asoc.append([i,j])
				spikes.append(j)
				j+=1
		if not spikes:
			spikes=(-1,)
		else:
			spikes=tuple(unique1d([rd[h,1] for h in spikes]))
		ns=sa[sid].get(spikes, 0)
		sa[sid][spikes]=ns+1
	totals=bincount(rd[:,1].astype(int32))
	asoc=array(asoc)
	stuff={'asoc':asoc,'sd':sd, 'rd':rd,'tol':tol}
	for k in sa.keys():
		counts=sa[k]
		print "\n\n==SpikeSorter Unit %i==" % k
		stuff['ssun']=k
		subsetReport(counts, totals, stuff)
	
if __name__=='__main__':
	try:
		rtf=argv[1]
		stf=argv[2]
	except:
		print "usage: test_results.py fileWithActualTimes fileWithSortedTimes"
	rt=io.read(rtf).getElements('Data', depth=1)[0]
	st=io.read(stf).getElements('Data', depth=1)[0]
	rt.data[:,0]+=.0015*rt.fs()
	#spikeDistanceTest(st, rt)
	subsetTest(st, rt)

		
		
	
	