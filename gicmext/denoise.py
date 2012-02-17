#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-01-16.

# Copyright (C) 2009 Graham I Cummins
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
from mien.math.sigtools import hanning
from numpy.fft import rfft

def _fft(signal, fs):
	'''Returned frequency spacing is always 1 Hz, length is int(fs/2)+1. Returned phases are for COS _NOT_ SIN. '''
	ft = rfft(signal - signal.mean(), fs)
	amp = abs(ft)
	amp*=2.0/fs
	# amp = ft*conjugate(ft)
	# amp=sqrt(amp.real)
	phase = arctan2(ft.imag, ft.real)
	return column_stack([amp, phase])

def _dice(lod, w):
	wins = []
	os = 0
	ns = lod[0].shape[0]
	while os < ns:
		if ns - os < w*.1:
			print("Warning: discarding very short window at tail end of data") 
			break
		chunk = []
		for a in lod:
			chunk.append(a[os:os+w])
		wins.append(chunk)
		os+=w
	return wins	

def fourierSpectrum(ds, select=(None, None, None), newpath="/ft"):
	'''calculate the fourier spectrum of the selection and store it at newpath. 	
	 '''
	dat = getSelection(ds, select)
	head = getSelectionHeader(ds, select)
	fs = head['SamplesPerSecond']
	ft = zeros((int(fs/2.0)+1, 2*dat.shape[1]), dat.dtype)
	for i in range(dat.shape[1]):
		c = dat[:,i]
		ft[:,2*i:2*i+2] = _fft(c, fs)
		#ft[:,2*i] = 10 * ft[:,2*i]/ft[:,2*i].max()
	ds.createSubData(newpath, ft, {"SampleType":"timeseries", "SamplesPerSecond":1.0}, True)
                    

def _refinePhase(t, c, amp, freq):
	phases = arange(0, 2*pi, .1)
	resids = zeros_like(phases)
	for i in range(phases.shape[0]):
		s = amp*cos(2*pi*freq*t + phases[i])
		r = c - s
		resids[i] = (r**2).sum()
	phase = phases[argmin(resids)]
	return phase
	
def _sineDetect(c, fs, freq, freqRange, refinePhase):
	'''return a sine wave on the same domain as the signal c'''
	ft = _fft(c, fs)
	freq = int(round(freq))
	if freqRange == 0:
		amp, phase = ft[freq]
	else:
		sf = 0
		if freqRange > 0:
			sf = freq - freqRange
			ft = ft[freq-freqRange:freq+freqRange+1, :]
		freq = argmax(ft[:,0])
		amp, phase = ft[freq,:]
		freq+=sf
	print("Component used is %i Hz with amp = %.3f, phase = %.3f" % (freq, amp, phase))
	t = arange(c.shape[0])/float(fs)
	if refinePhase:
		phase = _refinePhase(t, c, amp, freq)
		print('reselected phase as %.2f' % phase)
	s = amp*cos(2*pi*freq*t + phase)
	return s

def _sineBlock(c, fs, freq, freqRange, refinePhase, blockwidth):
	'''return a sine wave on the same domain as the signal c'''
	ft = _fft(c, fs)
	freq = int(round(freq))
	if freqRange != 0:
		if freqRange > 0:
			sf = freq - freqRange
			freq = argmax(ft[freq-freqRange:freq+freqRange+1, 0])+sf
		else:
			freq = argmax(ft[:,0])
	t = arange(c.shape[0])/float(fs)
	sig = zeros_like(t)
	for f in range(freq-blockwidth, freq+blockwidth):
		amp, phase = ft[f]
		if refinePhase:
			phase = _refinePhase(t, c, amp, f)
		s = amp*cos(2*pi*f*t + phase)
		sig = sig+s
	return sig


def killSineComponent(ds, select=(None, None, None), freq = 100, freqRange = -1, refinePhase=True, window=0, killwindow=0, newpath='test'):
	'''Detect and remove a single frequency component. Freq specifies the location to search for a component to remove. FreqRange specifies how far around the specified freq to search. Thus, if freqRange is 0, a component at exactly freq will be removed, but if freqRange is 10, the strongest component in the range freq-10 to freq+10 will be used. If freqRange is negative, then it is considered to be infinite, and the strongest single frequency component in the signal is used (and freq is ignored). If refinePhase is False, the phase of the component is read from the fourier spectrum. This can be somewhat noisy, however. If refinePhase is True, a local optimization (of the dot product of the sine component and the signal) is used to improve the precision of the phase estimate. If window is non-zero, component detection is performed separately for sequential windows of length "window" (in seconds). Note that this may produce discontinuities in the residual (clicks) at the window boundaries which will need to be smoothed out with a subsequent function.

Multiple channels specified in "select" will be handled sequentially and independently.

If "newpath" is a non-empty string, the result of subtracting the identified components from the selected signal is stored in a new element at that path. Otherwise, the subtraction is applied to the selected data in place. 	
	
SWITCHVALUES(refinePhase)=[True, False]	
	'''
	dat = getSelection(ds, select)
	out = zeros_like(dat)
	head = getSelectionHeader(ds, select)
	fs = head['SamplesPerSecond']
	if not window:
		wins = [[dat, out]]
	else:
		window = int(round(window*fs))
		wins = _dice([dat, out], window)
	for w in wins:
		dat, out = w	
		for i in range(dat.shape[1]):
			c = dat[:,i] 
			c = c - c.mean()
			if killwindow:
				s = _sineBlock(c, fs, freq, freqRange, refinePhase, killwindow)
			else:
				s = _sineDetect(c, fs, freq, freqRange, refinePhase)
			out[:,i] = c - s 
	if not window:
		out = wins[0][1]
	else:
		out = row_stack([w[1] for w in wins])
	if newpath:
		ds.createSubData(newpath, out, head, True)
	else:
		setSelection(ds, out, select)


