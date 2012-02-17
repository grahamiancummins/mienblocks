#!/usr/bin/env python
# encoding: utf-8
#Created by gic on 2007-04-13.

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
import numpy as N

def addSyn(gui, l):
	d = gui.askParam([{"Name":"When",
							"Value":.01},
							
					{"Name":"Which",
							"Value":-1}])
	obj = l[0]
	obj.addEvents(N.array([d[0]]), d[1])
	
def sequence(gui, l):
	d = gui.askParam([{"Name":"Delay",
							"Value":.001},
							{"Name":"Start",
							"Value":.002}])
	obj = l[0]
	syn = obj.synapses()
	evts = N.zeros((len(syn), 2))
	st = d[1]
	for i, e in enumerate(sorted(syn)):
		evts[i,0]=st
		evts[i,1]=e
		st+=d[0]
	obj.findDataElement()
	fs = obj.data.fs()
	evts[:,0]*=fs
	evts = evts.astype('i4')
	print evts
	obj.data.datinit(evts, {'SampleType':'labeledevents', 'SamplesPerSecond':fs})

def dirProj(gui, l):
	obj = l[0]
	d = gui.askParam([{"Name":"Stimulus File",
							"Value":"",
							"Browser":FileBrowse},
						   {"Name":"Direction",
							"Value":0.0},
						   {"Name":"Sampling Rate (Hz)",
							"Value":20000.0},
						   {"Name":"Target Type",
							"Type":"List",
							"Value":["Base64", "scl", "pydat"]},
						   ])
	if not d:
		return
	stim = read_datafile(d[0])[0]
	stim= get_directional_projection(stim, d[1])
	stim = reshape(stim, (-1,1))
	atr = {"Type":d[3],
		   'SamplesPerSecond':str(d[2])}
	if d[3]!="Base64":
		fn = d[0]
		fn = os.path.splitext(fn)[0]
		fn += "." + d[3]
		atr["Url"] = fn
	d = gui.makeElem("Data", atr, obj)
	d.addValues(stim, 1)


def _getSynMetas(se):
	d = {}
	syn_d = se.synapses()
	#syns2 = [n.target() for n in se.getElements("ElementReference")]
	for m,sid in enumerate(syn_d):
		syn = syn_d[sid][0]
		d[sid] = (syn.attrib('meta_cercus'), syn.attrib('meta_class') == 0, syn.attrib('meta_directional_tuning'), syn.attrib('meta_length') =='long') #just long and not-long classes, just distal and not-distal classes
	return d	

def _get_sep_params(gui,els):
	sei = els[0]
	d = gui.askParam([{"Name":"prox left time",
				   "Value":.001},
				  {"Name":"prox left dir",
					"Value":45.0}, 
				  {"Name":"dist left time",
				   "Value":.001},
				  {"Name":"dist left dir",
					"Value":45.0},
				  {"Name":"prox right time",
				   "Value":.001},
				  {"Name":"prox right dir",
					"Value":45.0},
				  {"Name":"dist right time",
				   "Value":.001},
				  {"Name":"dist right dir",
					"Value":45.0},	
					])
	return d, sei

def sequence_sep(gui, els):
	d, sei = _get_sep_params(gui,els)
	if not d:
		return
	syns = _getSynMetas(sei)
	evts = []
	deg2rad = N.pi/180
	for sid in syns:
		sv = syns[sid]
		index = (sv[0]=='right')*4 + (sv[1]*2)
		stimdir= d[index+1]
		strength = N.cos(deg2rad*(stimdir - sv[2]))
		if N.random.rand()<strength:
			evts.append( (d[index], sid) )
	evts = N.array(evts)
	sei.findDataElement()
	fs = sei.data.fs()
	evts[:,0]*=fs
	for m in range(evts.shape[0]):
				evts[m,0] += round(N.random.poisson(lam=.5/1e3*fs,size=1))#this assumes a poisson distribution of spiketimes about .1ms after the stimulus.
				evts[m,0] += N.random.uniform(low=0,high=2/1e3*fs)#moving along 2mm of the cercus
	evts = evts.astype('i4')
	print evts
	sei.data.datinit(evts, {'SampleType':'labeledevents', 'SamplesPerSecond':fs, 'StartTime':0.0})

def _assign_affernets(syns):
	'''
	Takes a set of syns and defines the afferents these syapses belong to.  Output is a list of lists with each element of the form: 
	[array(mask the afferent comes from, afferent number within that mask),(cercus coming from, boolian for is distal hair,prefered angle in body coordinates,boolian for is long hair),
		[indeces in syns of synapses assigned to this afferent],[failure rate of each synapse]] 
	'''
	import otherfuncs as oth
	#get all unique groups
	allvals = N.array(syns.values())
	ustyle = oth.unique_rows(allvals)[0]
	#divide up randomly so each aff has ~5 syns
	affcodes = []
	for m in range(len(ustyle)):
		ugrp = [n for n in range(allvals.shape[0]) if (allvals[n,:]==ustyle[m]).all()]
		synperaff = .7 #this is approximate and from the X hairs on to MGI as in Chiba, Shepherd and Murphey, but I don't see it there.
		numaffs = N.ceil(len(ugrp)/synperaff)#the total number of afferents for this class
		for n in range(len(ugrp)):
			p = N.floor(N.random.uniform(low=0, high=numaffs, size=1))[0]#randomly assing each synapse to an afferent
			affcodes.append(([m,int(p)],ugrp[n])) #tuples of ([class, afferent],synapseid)
	#turn into list of afferent, afferent direction, synapses for afferent
	uaffcodes = N.array([n[0] for n in affcodes])
	uaffcodes = oth.unique_rows(uaffcodes)[0]
	affrnts=[]
	for af in uaffcodes:
		sids = [affcodes[n][1] for n in range(len(affcodes)) if (affcodes[n][0]==af).all()]		
		grpinfo = syns[sids[0]] #arbitrarily choosing the first synapse to get the metadata
		failurerate = list(N.random.gamma(4.115,scale=.334, size=len(sids)))#HAVE UNKNOWNS TO FILL IN HERE From Davis and Murphey 93 via work on 1-26-11
		affrnts.append([af,grpinfo,sids,failurerate])
	return affrnts
	
def model_seps(gui, quin, fromscript=0, scripdict=[], curfolder='.'):		
		''' 
		Really doing the work of setting up the afferent events
		'''
		import otherfuncs as oth
		#from mexscriptsettings import *
		N.random.seed()

		#get all of the settings for the experiment from the current model to be run	
		if len(scripdict)<1:
			from runmodel import set_globals
			scripdict=set_globals()
		HARDREFRACT = scripdict['HARDREFRACT']
		BASEAFFERNTRATE = scripdict['BASEAFFERNTRATE']
		FRINCREASE = scripdict['FRINCREASE']
		STIMDURATION = scripdict['STIMDURATION']
		HAIRBLOCKSIZE = scripdict['HAIRBLOCKSIZE']
		REPS = scripdict['REPS']
		LEADIN = scripdict['LEADIN']
		EXPTLEN = scripdict['EXPTLEN']
		WEIGHTS = N.array(oth.reorder_list(list(scripdict['weights']),[0,3,1,2])) #transform into local ordering
	
		#fiugre out where the sypses are (scripts send a reference to synapses instead of a gui ref)
		if fromscript:
			synapses = gui
			d = quin
		else:
			d, synapses = _get_sep_params(gui, quin)
		if not d:
				return
	
		#setting relevant names	
		syns = _getSynMetas(synapses)
		synapses.findDataElement()
		fs = synapses.getParent("Group").getElements("Recording")[0].attributes["SamplesPerSecond"]#step up and back down the hierarchy to find experiment's time attribute
		simlen = synapses.getParent("Group").getElements("Experiment")[0].attributes['time']#step up and back down the hierarchy to find experiment's time attribute
		fs = float(fs)
		rnlen = float(simlen)/1e3*fs
		deg2rad = N.pi/180

		#in case there is less time avialable than there are repeats
		while rnlen<(((LEADIN + EXPTLEN*(REPS-1))/1e3 + STIMDURATION)*fs):
			REPS -= 1 

		# stick synapses on afferents	
		if fromscript and oth.scan_dir('.gicmextsettings.p', curfolder):#loading which afferents are which from a file AT SOME POINT THIS SHOULD BECOME MORE GENERAL
			import pickle
			#print curfolder + '/.gicmextsettings.p'
			#holder = oth.load_pickle(curfolder + '/.gicmextsettings.p')
			fl = open(curfolder + '/.gicmextsettings.p','r')
			holder = pickle.load(fl)
			affrnts = holder['affrnts']
			bratelist = holder['bratelist']
			fl.close()
			imported = 1
		else:
			imported = 0
			affrnts = _assign_affernets(syns)
			bratelist = []#[N.max((N.random.uniform(low=BASEAFFERNTRATE[0], high=BASEAFFERNTRATE[1], size=1)[0],0.)) for sid in affrnts]

		evts = [[0,rnlen+1]]
		countr = 0
		#set the firing for each synapse
		allprobs = dict()
		for sid in affrnts:
				if imported:
					brate = bratelist[countr]
				else:
					brate = N.max((N.random.uniform(low=BASEAFFERNTRATE[0], high=BASEAFFERNTRATE[1], size=1)[0],0.))
					bratelist.append(brate)
				countr += 1
				bsrt = N.tile(brate,(1,rnlen)) 
				#decode the prefered direction
				sv = sid[1]
				index = (sv[0]=='right')*4 + (sv[1]*2)
				stimdir= d[index+1]
				strength = N.cos(deg2rad*(stimdir - sv[2]))
				#get the stim induced rate
				strength = strength * WEIGHTS[index/2]
				incrs = strength * (FRINCREASE - brate)
				stimrt = N.max((brate + incrs,0))
				for m in range(REPS):
						#set the time during which the stim is on
						stimon = round((LEADIN + EXPTLEN*m + d[index]*1e3)*fs/1e3)
						stimoff = min(round(stimon + STIMDURATION*fs), rnlen-1)
						if sid[1][3]:
							stimform = (stimrt-brate)*N.sin(N.arange(0.,STIMDURATION*fs)/(STIMDURATION*fs)*N.pi)+brate #As per Landolfa and Miller 95, a long hair fires as the velocity (stimulus waveform) and...
						else:
							stimform = (stimrt-brate)*N.cos(N.arange(0.,STIMDURATION*fs)/(STIMDURATION*fs)*N.pi)+brate #short hairs fire as the deritave of the stimulus wave form.  Would need a constant multiplier, but then divide by length of hair...
						#print bsrt[0,stimon:stimoff].shape, stimon, stimoff, stimform[0:stimoff-stimon].shape,fs, STIMDURATION
						bsrt[0,stimon:stimoff] = stimform[0:stimoff-stimon] 
				#run the poisson process
				Pspk = bsrt / fs #from spikes/sec to spikes/data sample
				randnums = N.random.uniform(low=0, high=1, size=(1,Pspk.shape[1]))
				spktimes = N.where(Pspk[0,:] >= randnums[0,:])[0]
				#subtract spikes in the refract period
				outrefract = N.where(N.diff(spktimes) > HARDREFRACT*fs)[0] + 1 
				outrefract = N.concatenate((N.array([0]),outrefract))#add back the first spike
				if len(spktimes):
						spktimes = spktimes[outrefract]
				#find the location of the hair
				posdlay = round(N.random.uniform(low=-.5*HAIRBLOCKSIZE,high=.5*HAIRBLOCKSIZE,size=1)) #this assumes we're moving a block of hairs aproximately hairbloacksize*2 mm long
				spktimes += posdlay
				spktimes = spktimes[spktimes>0]
				spktimes = spktimes[spktimes<rnlen]
				#write the spikes
				for spk in spktimes:
					for m in range(len(sid[2])):
						#add in the probability of realease given firing
						nvesicles = N.random.poisson(sid[3][m],size=1)
						[evts.append((spk, sid[2][m])) for q in range(nvesicles)]
				allprobs[str(sid)] = Pspk		
		#save the afferent identities for a model run
		if fromscript and not imported:
			import pickle
			fl = open(curfolder + '/.gicmextsettings.p','w')
			holder = {'affrnts':affrnts,'bratelist':bratelist}
			#oth.save_pickle(holder, curfolder + '/.gicmextsettings.p')
			pickle.dump(holder, fl)
			fl.close()

		#package up for export
		evts = N.array(evts)
		evts = evts.astype('int32') #for the format needed elsewhere
		synapses.data.datinit(evts, {'SampleType':'labeledevents', 'SamplesPerSecond':fs, 'StartTime':0.0})
		return evts

MDL_S = (model_seps, "SynapticEvents")	
ESEQ_SEP=(sequence_sep, "SynapticEvents")	
DP=(dirProj, 'IClamp')	
AS=(addSyn, "SynapticEvents")
SS=(sequence, "SynapticEvents")
