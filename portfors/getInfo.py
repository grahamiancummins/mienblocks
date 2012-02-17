#!/usr/bin/env python

import os, re
import odf
import numpy as np
import parsePST 
import mien.parsers.nmpml as nmp

basedir =  'project/christine'
dsheet_path = 'DataSheet.ods'
basedir = os.path.join(os.environ['HOME'],basedir)
dsheet_path = os.path.join(basedir, dsheet_path)
callsdir = os.path.join(basedir, 'CBA calls Adults')
pathprefix = "Mouse "

cellIdLab = 'Cell ID'
mouseNoLab = 'Mouse #'
testLab = 'Test #'
conditionLab = 'Bic + Strych'

def asType(l, t):
	ol = []
	for i in l:
		try:
			ol.append(t(i))
		except ValueError:
			pass
	return np.array(ol)

def getDsheet(dsheet=None):
	if not dsheet:
		dsheet = dsheet_path
	tab = odf.readODS(dsheet)[0]
	lab = dict([(str(tab[0,i]), i) for i in range(tab.shape[1]) if tab[0,i]])
	cids = np.unique(tab[1:,lab[cellIdLab]])
	#cells = [{}]*(asType(cids, int).max()+1)
	cells = []
	for cid in cids:
		if cid in [None, 'Not complete']:
			continue
		cells.append({})
		rows = np.nonzero(tab[:,0] == cid)[0]
		#cidi = int(cid)
		cidi = -1
		for col in lab:
			if np.alltrue(tab[rows, lab[col]] == tab[rows[0], lab[col]]):
				cells[cidi][col] = str(tab[rows[0], lab[col]])
			else:
				cells[cidi][col] = list(tab[rows, lab[col]])
	return cells

def numOrRan(s):
	m = re.search("(\d+)-?(\d+)?", s)
	start, stop = m.groups()
	if not stop:
		return [int(start)]
	else:
		return range(int(start), int(stop)+1)




def addTraces(dat, traces, hasDrug):
	doc = dat.xpath(True)[0] 
	for i,tr in enumerate(traces):
		attrs = {
			'Name':'Trace%i' % i,
			'StartTime':0.0, 
			'SamplesPerSecond':1e6,  # batlab records spike times in microseconds 
			'SampleType':'labeledevents',
			'nsweeps':tr['nsweeps'],
			'raw_data_offset':tr['raw_data_offset'],
			'raw_data_shape':[tr['nsamples'], tr['nsweeps']],
			'raw_data_samplerate':tr['samplerate_resp'],
			'Drug':hasDrug,
			'stimuli_active':map(bool, tr['stimulus'])
		}
		trdat = nmp.createElement('Data', attrs)
		dat.newElement(trdat)
		if tr['spikes']:
			spdat = []
			for sweep in range(len(tr['spikes'])):
				for spike in range(len(tr['spikes'][sweep])):
					spdat.append([tr['spikes'][sweep][spike], sweep])
			if not spdat:
				spdat = np.zeros((0,2))
			trdat.datinit(np.array(spdat))
		sfiles = []
		for ch, s in enumerate(tr['stimulus']):
			for k in s:
				trdat.setAttrib('stim%i_%s' % (ch, k), s[k])
				if k == 'file':
					ename = "/Data:Call%s" % (s[k][:s[k].index('.')],)
					sfiles.append((ename, s[k]))
					er = nmp.createElement("ElementReference", {'Name':'Stim%i' % ch, 'Data':ch, 'Target':ename})
					trdat.newElement(er)
		for (upath, fname) in sfiles:
			if not doc.getInstance(upath, True):
				stimdat = nmp.forceGetPath(doc, upath)
				stimdat.setAttrib('SampleType','timeseries')
				stimdat.setAttrib('SamplesPerSecond',tr['samplerate_stim'])
				fname = os.path.join(callsdir, fname)
				sd = np.fromstring(open(fname).read(), np.int16)
				stimdat.datinit(sd)
				
			
	

def getTests(dsheet=None):
	cells = getDsheet(dsheet)
	files = {}
	for c in cells:
		etrack = c[ mouseNoLab]
		mouse = numOrRan(etrack)[0]
		dfpath = os.path.join(basedir, pathprefix+str(mouse), pathprefix +etrack)
		pstpath = os.path.join(dfpath, pathprefix + etrack + '.pst')
		if os.path.isfile(pstpath):
			print "found data for cell %s" % c[cellIdLab]
			if not pstpath in files:
				files[pstpath] = []
			files[pstpath].append(c)
		else:
			print "No data for %s, %s" % (c[cellIdLab], pstpath)
	doc = nmp.blankDocument()		
	for fn in files:
		pstmeta, tests = parsePST.parse(fn)
		pstmeta[1] = 'Date: ' +  pstmeta[1]
		for c in files[fn]:
			dat = nmp.addPath(doc, "/Data:Cell%s" % c[cellIdLab])
			dat.setAttrib('SampleType', "group")
			for k in c:
				safek = k.replace('#','Num').replace(' ', '_').replace('+', 'and').replace('?', '')
				dat.setAttrib(safek, c[k])
			dat.setAttrib('ExperimentMetaData', pstmeta)
			dat.setAttrib('RawTraceFilename', fn[:-4] + '.raw')
			for i, t in enumerate(c[testLab]):
				tids = numOrRan(t)
				for tid in tids:
					test = tests[tid-1]
					drug = bool(c[conditionLab][i]=='yes')
					tdat = nmp.createElement('Data', {'Name':'Test%i' % tid,'SampleType':'group', 'Drug':drug})
					for k in test:
						if not k == 'traces':
							tdat.setAttrib(k, test[k])
					dat.newElement(tdat)
					addTraces(tdat, test['traces'], drug)
	return doc

if __name__=='__main__':
	import sys
	ofile = sys.argv[1]
	if len(sys.argv)>2:
		dsheet = sys.argv[2]
	else:
		dsheet = None
	doc = getTests(dsheet)
	import mien.parsers.fileIO as io
	io.write(doc, ofile)
