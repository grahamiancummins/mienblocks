#!/usr/bin/env python -2
# encoding: utf-8

#Created by gic on DATE.

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

from mien.datafiles.dataset import getSelection, getSelectionHeader 
import numpy as np

def spectrogram(ds, select=(None, None, None), newpath='/sgw', winwidth=.01, tstep = .0001, fstart=10000, fstop=120000, fstep=500, wintype='no'):
	'''
	Contstruct a timeseries dataset that is a corse spectogram of the data D
	specified by ds and select (which should also be a time series, containing
	only one channel). The result will have length tsteps and width fsteps.The
	nth channel contains the frequency specified by the nth element of
	range(fstart, fstop, fstep).
	
	The value of the specrogram at each sample point is the magnitude of the
	real fourier transform of a region of length "winwidth" times a 
	windowing function. The nth point is based on a window centered tstep*n
	into the domain.
	
	Winwidth and tstep are specified in seconds, not sample points.

	wintype determines the shape of the windowing function. Currently supported
	values are "no" (a flat "window") and "triangle"

	SWITCHVALUES(wintype)=['no', 'triangle']

	'''
	dat = getSelection(ds, select)
	h = getSelectionHeader(ds, select)
	fs = h['SamplesPerSecond']
	nfs = 1.0/tstep
	winwidth =int(round(winwidth*fs/2.0))
	window = None
	if wintype=="triangle":
		window = np.linspace(0, 1, winwidth)
		window = np.concatenate([window, window[::-1]])
	nft = winwidth + 1 
	ind = np.arange(fstart, fstop, fstep)
	ind = nft * ind / (fs/2.0)
	ind = ind.astype(np.int32)[::-1]
	tstep = int(round(tstep*fs))	
	xind = np.arange(winwidth, dat.shape[0]-winwidth, tstep).astype(np.int32)
	ft = np.zeros((xind.shape[0], ind.shape[0]))
	for i in range(xind.shape[0]):
		d = dat[xind[i]-winwidth:xind[i]+winwidth,0]
		#warning, very strange behavior of rfft for 2d arrays,
		#even if shape is Nx1 or 1xN.
		if window!=None:
			d = d * window
		d = np.fft.rfft(d)
		ft[i,:] = abs(d[ind])	
	ds.createSubData(newpath, ft, {'SampleType':'timeseries', 'SamplesPerSecond':nfs, 'imageYrange':(fstart, fstop-fstart)}, True)




