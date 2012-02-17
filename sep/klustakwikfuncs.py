#! usr/bin/env python
'''
Takes a data set and makes templates out of it
'''
#INCLUDE SOMETHING WHERE A 'BLANK' ON A GIVEN CHANNEL, AND CHANNELS FURTHER DOWN THE LINE, DOESN'T AFFECT THE SPIKE ID
import os
from numpy import *
import helperfuncs as oth

def distances_from_clusters(clusts,waves):
	#takes waves and their assigned clusters and returns a n(samples) * m(classes) arry of distance between each wave and the class means.
	clasnum = len(unique(clusts))
	means = zeros((classnum))

def read_KlustaKwik_results(nm,number):
	#reads in a name.clu.number file and returns a vector of classes
	name = os.getcwd() + os.path.sep + nm + '.clu.' + str(number)
	name = oth.check_fname(name)
	if not os.path.exists(name):
		raise NameError ('.clu file does not found at appropriate location %s' % (name))
	clufile = open(name,'r')
	try:
		nclusts = clufile.readline()
		outvect = clufile.readline()
	except:
		raise NameError ('.clu file not written properly.')
	if len(outvect)<1:
		raise NameError ('clu file not complete - read_KlustaKwick_reslults')
	nclusts = int(nclusts)
	outvect = [int(outvect.replace('\n',''))]
	for line in clufile:
		outvect.append(int(line.replace('\n','')))
	clufile.close()
	os.remove(name)
	return outvect	

def run_KlustaKwik(samples,nm,number=1):
	#Takes a python sample array and turns runs KlustKwik on it, returning the groups
	import random
	name = os.getcwd() + os.path.sep + nm + '.fet.' + str(number)
	fetf = open(name,'w')
	[samples] = oth.check_inputs([samples],['array'],callingtag=[['samples'],'run_KlustaKwik'])
	if len(shape(samples))<2:
		samples = reshape(samples,(len(samples),1))
	ht,ln = samples.shape
	fetf.write(str(ln) + '\n')
	for n in range(ht):
		for m in range(ln-1):
			fetf.write(str(samples[n,m])+'\t')
		fetf.write(str(samples[n,ln-1]) + '\n')	
	fetf.close()
	#GET A GENERAL WAY TO ASK FOR KLUSTAKWIK LOCATION?
	if os.path.exists('/KlustaKwik'):
		pth = ''
	elif os.path.exists(os.path.expanduser('~') + '/KlustaKwik'):
		pth = os.path.expanduser('~')
	else:
		raise NameError ('could not find KlustaKwik.  Make sure instal is in home directory')
	call = pth + '/KlustaKwik/KlustaKwik ' + nm + ' ' + str(number) + ' -RandomSeed ' + str(random.randint(0,100)) + ' -UseFeatures ' + '1 ' * ln # REMOVED : -Min Clusters 2 -MaxClusters 20
	print call
	os.system(call)
	output = read_KlustaKwik_results(nm,number)
	os.remove(name)
	return output





def run_test(fname):
	#from a file produced by maketemplatestemp.py, run a series of tests to see how well KlustaKwik does in coming up with the same groups
	import pickle
	from os.path import splitext
	file = open(fname,'r')
	dictary = pickle.load(file)
	spknumber = dictary['spikenums']
	handanswers= zeros((sum(spknumber),1))
	for m in range(len(spknumber)):
		handanswers[sum(spknumber[:m]):sum(spknumber[:m])+spknumber[m]] = m+1
	#timegroups = run_KlustaKwik(transpose(dictary['timelags']),splitext(fname)[0], number=0)
	channames = [nam for nam in dictary.keys() if not nam.find('channel')]
	channames.append('timelags')
	pcor = {}
	for i in range(max(handanswers)):	
		pcor['unit' + str(i)] = zeros((len(channames),1))
	groups = zeros((dictary[channames[0]].shape[1],len(channames)))
	for m in range(len(channames)):
		groups[:,m]	= run_KlustaKwik(transpose(dictary[channames[m]]), splitext(fname)[0], number=m)
		for i in range(max(handanswers)):
			locgrp = groups[[n for n in range(len(handanswers)) if handanswers[n]==i+1],m]
			pcor['unit' + str(i)][m] = sum(locgrp == median(locgrp)) / float(len(locgrp))
	#get the overall euclidian distnce in the full space.
	return changroups, timegroups
	#make a test based on the current templates
	#what is the signal to noise ratio of the various templates
	#which spikes are 'correctly' sorted using KlustaKwik
	#how many channels are needed for a succesful sorting at a given sig/noise ratio
	#what is the maximal separation between the templates?
