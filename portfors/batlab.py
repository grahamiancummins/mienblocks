#!/usr/bin/env python
# encoding: utf-8

#Created by gic on Thu Oct 14 15:02:16 CDT 2010

# Copyright (C) 2010 Graham I Cummins
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
from mien.datafiles.dataset import *
import mien.parsers.nmpml as nmp

def loadRawTrace(gui, elems):
	ds = elems[0]
	rtfn = ds.attrib('RawTraceFilename', True)
	os = ds.attrib('raw_data_offset')
	sh = ds.attrib('raw_data_shape')
	fs = ds.attrib('raw_data_samplerate')
	rds = multiply.reduce(sh) * 2
	f = open(rtfn)
	f.seek(os)
	a = fromstring(f.read(rds), int16)
	f.close()
	a = reshape(a, (sh[1], sh[0])).transpose()
	nd = gui.makeElem('Data', {'Name':'RawResponseTrace',
						'SampleType':'timeseries',
						'StartTime':0.0,
						'SamplesPerSecond':fs}, 
						ds)
	nd.datinit(a)

loadRaw = (loadRawTrace, "Data")

def _stackLE(lods):
	d1 = newData(zeros((0,2)), {'SampleType':'labeledevents',
		'SamplesPerSecond':lods[0].fs(), 'nsweeps':0,
		'StartTime':lods[0].start(),
		'Name':'combinedEvents', 'Labels':[]})
	for ds in lods:
		labs = ["%sSweep%i" % (ds.name(), i) for i in range(ds.attrib('nsweeps'))]	
		ndat = ds.data.copy()
		ndat[:,1]+=d1.attrib('nsweeps')
		d1.setAttrib('nsweeps', d1.attrib('nsweeps') + ds.attrib('nsweeps'))
		d1.data = row_stack([d1.data, ndat])
		d1.attributes['Labels'].extend(labs)
	return d1

def sortByStimulus(doc):
	stim = doc.getElements('Data', {'SampleType':'timeseries'})
	stim = [s for s in stim if s.name().startswith('Call')]
	traces = doc.getElements('Data', {'SampleType':'labeledevents'})
	traces = [s for s in traces if s.name().startswith('Trace')]
	ndoc = nmp.blankDocument()
	for s in stim:
		withdrug = []
		without = []
		for t in traces:
			if t.getTypeRef('Data') and t.getTypeRef('Data')[0].target() == s:
				nt = t.clone()
				if nt.noData():
					nt.datinit(zeros((0,2)))
				nt.setAttrib('Name', '%s%s%s' % (t.container.container.name(), t.container.name(), t.name()))
				resample(nt, s.fs())
				nt.setAttrib('StartTime', s.start() - t.attrib('stim0_delay')/1000.0)
				if t.attrib('Drug'):
					withdrug.append(nt)
				else:
					without.append(nt)
		ns = s.clone()
		if withdrug:
			withdrug = _stackLE(withdrug)
			withdrug.setAttrib('Name', 'BIC')
			ns.newElement(withdrug)
		if without:
			without = _stackLE(without)
			without.setAttrib('Name', 'NoBIC')
			ns.newElement(without)
		ndoc.newElement(ns)
	return ndoc



cmds = {'stim':sortByStimulus}

if __name__=='__main__':
	import mien.parsers.fileIO as io
	import sys, os
	fn = sys.argv[1]
	cmd = sys.argv[2]
	doc = io.read(fn)
	ndoc=cmds[cmd](doc)
	fn, ext = os.path.splitext(fn)
	nfn = fn+"_%s" % cmd + ext
	io.write(ndoc, nfn)

