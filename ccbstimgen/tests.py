#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2008-05-21.

# Copyright (C) 2008 Graham I Cummins
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

def _peakFind(dat, frac):
	dm = dat.mean()
	dmax = dat.max()
	thresh = dm+ (dmax-dm)*frac
	evts = []
	hit=(dat>thresh)
	shifthit = shift(hit, 1)
	cross=nonzero1d(hit!=shifthit)
	if len(cross)==0:
		return array([])
	if dat[0]>thresh:
		cross = cross[1:]
	if dat[-1]>thresh:
		cross = cross[:-1]	
	cross = reshape(cross, (-1, 2))
	for j in range(cross.shape[0]):
		k = argmax(dat[cross[j, 0]:cross[j,1]])
		evts.append(cross[j,0]+k)
	return array(evts)

def estimatePeakSpacing(ds, select=(None, None, None), inverse=False, fraction=.5):
	'''Detect all the peaks between the mean of the selected data and the threshold mean+(max-mean)*fraction. measure the time lags between these peaks, and report the mean and standard deviation of the distribution of peaks. If "inverse" is True, do the same operation for -1*data. If multiple channels are specified by select, each is tested independently.

SWITCHVALUES(inverse)=[False, True]		
	'''
	dat =getSelection(ds, select)
	fs = float(getSelectionHeader(ds, select)['SamplesPerSecond'])
	for i in range(dat.shape[1]):
		d = dat[:,i]
		if inverse:
			d = d*-1
		peaks = _peakFind(d, fraction)
		lags = peaks[1:]-peaks[:-1]
		lags = lags/fs
		lm=lags.mean()
		print "channel %i: mean lag %.5G, std %.5G, (freq %.4G)" % (i, lm, lags.std(), 1.0/lm)
	
	
	