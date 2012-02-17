#!/usr/bin/env python
# encoding: utf-8
#Created by Graham Cummins on 2007-09-19.

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

import os
import mien.parsers.fileIO as io
from sorter import *
from mien.nmpml.data import newData

#This would be good as an option, but it looks like batch is currently set to take multiple data files for all sys.argv[>1].  A unix for loop would do the same thing, can I steal sysargv[3] to become an allow template modification' boolean?
from sep.dsp import shiftTemplates as sT

def takewindows(dat, evts, lead, length):
	print dat.shape, evts.shape, lead, length
	window=arange(length)-lead
	window=resize(window, (evts.shape[0], window.shape[0]))
	window=window+reshape(evts, (-1, 1))
	dat=take(dat, ravel(window.astype(Int32)), 0)
	dat=transpose(reshape(ravel(transpose(dat)), (-1, length)))
	return dat
	
def calc_mean(data, pars=(), template=None):
	return data.mean(1)
							
def no_error(data, pars=(), template=None):
	return None							
							
DISC_FUNCTIONS={"Mean":calc_mean}
import discriminants
DISC_FUNCTIONS.update(discriminants.DISC_FUNCTIONS)

TOSAVE=0
LASTSHIFT=[]

def detect(dat, temp, bn):
	print "detecting: %s" % (temp.name(),)
	try:

		disc=temp.attributes['Discriminant']
		th1, th2=temp.attributes['Thresholds']
		dp=parseParams(temp.attrib('DiscriminantParameters'))
		print "%s(%s) with thresholds: %.4f/%.4f" % (disc, str(dp), th1, th2)
	except:
		print "No discriminant/threshold information. Skipping template"
		return
	try:
		df=DISC_FUNCTIONS[disc]
	except:
		print "No function found for discriminant %s. Skipping template" % (disc,)
		return
	st=temp.getSubData('/shift')
	if st:
		shifts=st.getData()[:,0]
		blockShift(dat, shifts, False)
		print "Applied shift template %s" % (str(shifts),)
	else:
		print "No shifts for this template"
	if 'Mean/OptMin+threshold' in disc:#cause I'm not fixing the mess, just patching a way to get my thing to work
		try:
			mn=temp.attributes['RightSpikeValue']
		except:
			print('proper spike value not saved, all hell may break loose')
			mn=None
		disc=df(dat.getData(), dp, temp, mn)
	else:
		disc=df(dat.getData(), dp, temp)
	if disc==None:
		print "error in calculating discriminant. Skipping template"
		return
	evts=schmitTrigger(disc, th1, th2)
	
	
	#if sys.argv[3]: would go here
	#global LASTSHIFT
	#if not evts.any() and len(LASTSHIFT)>1:
	#	blockShift(dat, LASTSHIFT, True)
	#	evts=schmitTrigger(disc, th1, th2)

	#newshifts=sT(dat,evts,shifts)
	#runthrough=0
	evtsnew=evts
	#while (shifts-newshifts).sum()>dat.shape()[1] and runthrough<10:
		#print('strt')
		#print(set(evts)-set(evtsnew))
		#print(set(evtsnew)-set(evts))
	#	disc=df(dat.getData(), dp, temp)
	#	evtsnew=schmitTrigger(disc, th1, th2)
	#	dictemp=temp.getHierarchy()
	#	temp.createSubData('/shift',newshifts,dictemp['/shift'].header(),True)
	#	newshifts = sT(dat,evtsnew,newshifts)
	#	global TOSAVE
	#	TOSAVE=1
	#	runthrough+=1
	
	#LASTSHIFT=newshifts-shifts

	print "detected %i events" % evtsnew.shape[0]
	if evtsnew.shape[0]:
		saveWaves(evtsnew, bn, temp, dat)
		print(temp.attrib('subtracted')>0)
		if temp.attrib('subtracted')>0:
			td=temp.getSubData('template')
			print(td.getData().shape)
			subtractTemplate(dat, evtsnew, td)
			print "subtracted template waveforms"
		lab=temp.name()[10:]
		writeSpikeData(dat, evtsnew, "/spikes", append=True, lab=lab)
	print "done with %s\n\n" % (temp.name(),)
	return evtsnew

def saveWaves(spi, bn, t, dat):
	fn=bn+"_%s.mdat" % (t.name(),)
	tem=t.getElements("Data", "template", depth=1)[0]
	lead=tem.attrib('Lead')
	length=tem.getData().shape[0]
	
	#ignore spikes too close to the ends of the data file
	spi=spi[where(spi>lead)]
	spi=spi[where(spi<(dat.shape()[0]-(length-lead)))]
	if spi.shape[0]<1:
		return 

	waves=takewindows(dat.getData(), spi, lead, length)
	head={'SampleType':'ensemble',
	      'Lead':lead,
		'Reps':spi.shape[0],
		'SamplesPerSecond':dat.fs()
		}
	waves=newData(waves, head)
	h=waves.createSubData('/hidden')
	h.newElement(t.clone(False))
	h.newElement(tem.clone(False))
	io.write(waves, fn, newdoc=True, format=".mdat")


def batchSort(tf, df):
	if type(tf)==str:
		tf=io.read(tf)
	bn=os.path.split(df)[-1]	
	bn, ext=os.path.splitext(bn)
	bn=bn+"-"+ext[1:]
	sfn=bn+"_sorted_spikes.mdat"
	dfstr=df
	df=io.read(df)
	print(tf.getElements("Data", "spikesorter_setup", depth=2))
	setup=tf.getElements("Data", "spikesorter_setup", depth=2)[0]
	temps=tf.getElements("Data", depth=2)
	temps=[t for t in temps if t.name().startswith("spikesort_")]
	temps.sort(sortByOrder)
	dat = df.getElements("Data", depth=1)[0]
	writeShifts(dat, zeros(dat.shape()[1]))
	precondition(dat, setup)
	writeShifts(dat, zeros(dat.data.shape[1]))
	for t in temps:
		spi=detect(dat, t, bn)
	
	if TOSAVE:
		#newfname=sys.argv[1]
		#newfname, jnk=os.path.splitext(newfname)
		dfstr = os.path.basename(dfstr)
		dfstr, jnk=os.path.splitext(dfstr)
		newfname = 'spikes' + dfstr + '.mdat'
		print(newfname)
		io.write(tf,newfname,newdoc=False)

	spikes=dat.getSubData('/spikes')
	io.write(spikes, sfn, newdoc=True, format=".mdat")
	

if __name__=='__main__':
	import sys
	if len(sys.argv)<3:
		print "usage: python batch.py template dataFile"
	else:
		tf=io.read(sys.argv[1])
		for df in sys.argv[2:]:
			print "sorting %s" % df
			batchSort(tf, df)
