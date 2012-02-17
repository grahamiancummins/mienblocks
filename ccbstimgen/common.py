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

from mien.dsp.generators import *
from mien.math.array import rotate
from mien.math.sigtools import bandpass
from mien.parsers.matfile import readmatfile
from mien.parsers.fileIO import write
from numpy import random
import os


def _cfilt(dat, filt, off):
	dl=dat.shape[0]
	filt = reverseArray(filt)
	dat=convolve(dat, filt, 'full')
	off=int(round(filt.shape[0]/2.0))+off
	dat=dat[off:off+dl]
	return dat

def _halfCos(d, n):
	dat=zeros((n,2), 'f')
	dat[:,0]=sin(pi*arange(n)/float(n))
	dat=rotate(dat, d)
	return dat
	

def halfCosineCircle(ds, timeStart=0.0, numberOfDirections=4, directionOffset=45.0, pulseLengthMS=40.0, pauseMS=20.0, order='increasing'):
	'''Creates a sequence of half cosine impulses from several directions equally spaced around a circle. This signal is added to the first two channels of the primary data series (this must be a timeseries with at least two channels), such that the sequence begins at time timeStart (specified in seconds). The stimulus consists of numberOfDirections impulses such that the smallest angle is directionOffset, and the largest angle is <=360 degrees. Angles are in degrees, 0 is at the animal's head, and angles increase clockwise. Each half cosine has a duriation in milliseconds of pulseLengthMS, followed by a pause in milliseconds of pauseMS. The pluses may be provided in increasing (clockwise), decreasing (counterclockwise) or random order.

SWITCHVALUES(order)=['increasing', 'decreasing', 'random']
'''
	numberOfDirections=int(numberOfDirections)
	fs=ds.fs()
	spw=int(round(fs*pulseLengthMS/1000.0))
	spp=int(round(fs*pauseMS/1000.0))
	spd=spw+spp
	l=numberOfDirections*(spd)
	xcoordStart=int(round(timeStart*fs))
	sel = (None, [0,1], (xcoordStart, xcoordStart+l))
	dat=zeros((l, 2), ds.dtype())
	dirs=arange(directionOffset, 360+directionOffset, 360.0/numberOfDirections)
	if order=='decreasing':
		dirs.reverse()
	elif order=='random':
		random.shuffle(dirs)
	print dirs	
	for i, d in enumerate(dirs):
		w=_halfCos(d, spw)
		dat[i*spd:i*spd+spw,:]=w.astype(ds.dtype())
	setSelection(ds, dat, sel)	

def chirp(ds, timeStart=0.0, timeStop=10.0, freqStart=5, freqStop=11):
	'''Generate a linear frequency ramp from freqStart to  freqStop'''
	dat = ds.getData(copy=True)
	fs = ds.fs()
	indStart = int(round(timeStart*fs))
	indStop = int(round(timeStop*fs))
	nind = indStop-indStart
	modulate = float(freqStop)/freqStart
	dt =freqStart*ones(nind)/float(fs)
	mod = linspace(1, modulate, nind)
	dt*=mod
	t = cumsum(dt)
	s = sin(2*pi*t)
	dat[indStart:indStop,0]=s
	ds.datinit(dat)
	
	
def sequentialChirps(ds, timeStart=0.0, timeStop=100.0, freqStart=5, freqStop=50, nsteps = 6, percentRamp=.1):
	''' '''
	dat = ds.getData(copy=True)
	fs = ds.fs()
	indStart = int(round(timeStart*fs))
	indStop = int(round(timeStop*fs))
	nind = indStop-indStart
	
	tt = timeStop-timeStart 
	
	lenoftone = tt/(nsteps + (nsteps-1)*percentRamp)
	lenofchirp = lenoftone*percentRamp
	lenoftone = int(round(lenoftone*fs))
	lenofchirp = int(round(lenofchirp*fs))
	ind = 0
	mod = ones(nind)
	freq = linspace(freqStart, freqStop, nsteps)
	for i in range(freq.shape[0]):
		mod[ind:ind+lenoftone]=freq[i]
		ind+=lenoftone
		if i<freq.shape[0]-1:
			chirp = linspace(freq[i], freq[i+1], lenofchirp)
			mod[ind:ind+lenofchirp]=chirp
			ind+=lenofchirp
	dt=mod/float(fs)
	t = cumsum(dt)
	s = sin(2*pi*t)
	dat[indStart:indStop,0]=s
	ds.datinit(dat)	
	
def singleChannelNoise(ds, timeStart=0.0, segmentLength=10.0, pad=0.5, reps=10, bandMin=5, bandMax=400, fnameRigFilter='', seed=0):
	'''Construct a single chanel band limited white noise stimulus. bandMin and bandMax specify the frequency of the band pass. segmentLength specifies the length of a noise segment in seconds. pad specifies an amount of silence surrounding the noise segment (pad occurs both before and after the noise). Reps specifies a number of times to repeat the pad,segment pair (thus, the total stimulus will be (segmentLength+2*pad)*reps seconds long). If specified, fnameRigFilter is a file name specifying a mat file containing a rig-specific velocity to voltage filter, which should be applied to the stimulus (after band passing). Seed, if specified and True (e.g. not 0), seeds the random number generator'''
	sl=int(round(segmentLength*ds.fs()))
	pad=int(round(pad*ds.fs()))
	l=reps*(sl+2*pad)
	xstart=int(round(timeStart*ds.fs()))
	sel = (None, [0], (xstart, xstart+l))
	if seed:
		random.seed(seed)
	dat=concatenate([zeros(pad), random.randn(sl), zeros(pad)])
	dat=bandpass(dat, bandMin, bandMax, ds.fs())
	fnameRigFilter=fnameRigFilter.strip()
	if fnameRigFilter:
		h=readmatfile(fnameRigFilter)
		h=h['h']
		ff=h['vel2volt0']
		opt=h['vel2volt_offsetpts_0'][0][0]
		hfs=h['sampfreq'][0][0]
		if hfs!=ds.fs():
			ff=array_resample(ff, hfs, ds.fs())
			opt=int(round(ds.fs()/hfs))
		dat=_cfilt(dat, ff, opt)
	dat=resize(dat, reps*dat.shape[0])
	sd=dat[pad:-pad].std()
	dat*=1.0/sd
	dat=reshape(dat, (-1, 1))	
	setSelection(ds, dat, sel)	
	fn='gwn%ito%iHz%ireps%isec_' % (bandMin, bandMax, reps, segmentLength)
	if fnameRigFilter:
		fn+="filtered"
	else:
		fn+="raw"
	ds.setAttrib('fname', fn)
	
	
def stimwrite(ds, nchans=1, fname='fromds'):
	'''write a stimulus with nchans to file fname. If fname is fromds, use the attribute "fname" of ds (which must have been previously set). fname should not include a file type extension'''
	if fname=='fromds':
		fname=ds.attrib('fname')
	if nchans>1:
		ext='.dcl'
	else:
		ext='.scl'
	fname=fname+ext	
	write(ds, fname, newdoc=True, format=ext)
		


def _gettuple(s, ctt=float):
	l=s.split(',')
	return tuple(map(ctt, l))
	
def _getoffset(s, sld, od):
	s=s.strip().lower()
	segdur=sld['rep']*(sld['dur']+2*sld['pad'][0])
	anch=0
	if s.startswith('end') or s.startswith('last') or s.startswith('next'):
		if s.startswith('end'):
			if od.values():
				anch = max(od.values())
		elif s.startswith('last'):
			anch=od.get('last', 0.0)
		else:
			for c in sld['chan']:
				anch=max(anch, od[c])
		if "+" in s:
			s=s.split('+')[-1]
		else:
			s=''
	if s:
		anch+=float(s)
	for c in sld['chan']:
		if not od.has_key(c):
			od[c]=0
		od[c]=max(od[c], anch+segdur)
	od['last']=anch
	return anch

def _parsetxtline(l, offsets):
	#offset; waveform type; duration; padding; repeats; frequency; channels; amplitude
	l=l.strip()
	if not l or l.startswith('#'):
		return None
	try:	
		sl=l.split(';')
		sld={}
		sld['wave']=sl[1].strip().lower()
		sld['dur']=float(sl[2])
		sld['rep']=int(sl[4])
		sld['pad']=_gettuple(sl[3])
		sld['freq']=_gettuple(sl[5])
		sld['chan']=_gettuple(sl[6], int)
		sld['amp']=_gettuple(sl[7])
		sld['off']=_getoffset(sl[0], sld, offsets)
	except:
		print("WARNING: can't parse line %s" % l)
		raise
		return None
	return sld
	

def _smooth(dat, pad, n):
	ramp=arange(n)/float(n)
	dat[:n]*=ramp
	dat[-n:]*=ramp[arange(ramp.shape[0]-1,-1,-1)]
	return dat

NO_CHAN_AMP=['pulse']

def _chanDistrib(dat, sd):
	dat=transpose(resize(dat, (len(sd['chan']), dat.shape[0])))
	if not sd['wave'] in NO_CHAN_AMP:		
		if len(sd['amp'])==1:
			dat*=sd['amp'][0]
		elif len(sd['amp'])==dat.shape[1]:
			dat*=sd['amp']
	return dat



def _genWN(sl, sd):
	if len(sd['freq'])>2:
		random.seed(sd['freq'][2])
	dat=concatenate([zeros(200), random.randn(sl), zeros(200)])
	dat=bandpass(dat, sd['freq'][0], sd['freq'][1], sd['fs'])	
	return dat[200:-200]
	

def _genSin(sl, sd):
	x=arange(sl)/float(sd['fs'])
	w=sd['freq'][0]*(2*pi)
	p=0.0
	if len(sd['freq'])>1:
		p=sd['freq'][1]*pi/180.0
	dat=sin(w*x+p)
	return dat

def _genPulse(sl, sd):
	on=int(round(sd['freq'][0]*sd['fs']))
	off=int(round(sd['freq'][1]*sd['fs']))
	pd=on+off
	ind=mod(arange(sl), pd)
	dat=where(ind<=on, sd['amp'][0], sd['amp'][1])
	return dat

def _genRamp(sl, sd):
	on=int(round(sd['freq'][0]*sd['fs']))
	off=int(round(sd['freq'][1]*sd['fs']))
	up=arange(on)/float(on)
	down=arange(off)/float(off)
	down=down[arange(down.shape[0]-1,-1,-1)]
	ramp=concatenate([up, down])
	n=int(ceil(float(sl)/ramp.shape[0]))
	if n>1:
		ramp=resize(ramp.shape[0]*n)
	ramp=ramp[:sl]
	return ramp
	
def _genSSW(sl,sd):
	# build frequency array
	sf = sd['freq']
	tl=len(sf)
	ml=mod(tl,3)
	if ml:
		print("Wrong number of arguments in frequency. Omitting %d arguments." % ml)
	freq=array([])
	for i in arange(floor(tl/3)):
		ind=int(i*3)
		f=arange(sf[ind],sf[ind+1],sf[ind+2])
		freq=hstack([freq,f])
	#find the number of samples in the sine wave segments and in the FM ramps
	nf=len(freq)
	nsampintone = int(round(float(sl)/((11.0/10)*nf - 0.1))) 
	nsampinchirp = int(round(nsampintone/10.0))
	#build the modulated time vector to produce a FM sine wave
	modulate=zeros(sl)
	ind = 0
	for i in range(len(freq)):
		modulate[ind:ind+nsampintone]=freq[i]
		ind+=nsampintone
		if i<len(freq)-1:
			chirp = linspace(freq[i], freq[i+1], nsampinchirp)
			modulate[ind:ind+nsampinchirp]=chirp
			ind+=nsampinchirp
	dt=modulate/float(sd['fs'])
	t = cumsum(dt)
	return sin(2*pi*t)	

def _genDc(sl, sd):
	return ones(sl, float32)

STIM_GEN={
	'wn':_genWN,
	'sin':_genSin,
	'pulse':_genPulse,
	'ramp':_genRamp,
	'dc':_genDc,
	'ssw':_genSSW
}

def _genWave(sd):
	sl=int(round(sd['dur']*sd['fs']))
	pad=int(round(sd['pad'][0]*sd['fs']))
	dat=STIM_GEN[sd['wave']](sl, sd)
	if len(sd['pad'])>1:
		dat=_smooth(dat, int(round(sd['pad'][1]*sd['fs'])))
	dat=concatenate([zeros(pad), dat, zeros(pad)])
	if sd['rep']>1:
		dat=resize(dat, dat.shape[0]*sd['rep'])	
	dat=_chanDistrib(dat, sd)
	return dat
			


	
def simpleStimFromFile(ds, fname='BreeProt1.txt', samplingRate=10000, fnameOutput='BreeProt1.scl'):
	'''Generate a stimulus based on instructions in a text file. fname is the text file specifying the stimulus. If fnameOutput is specified, write the stimulus to that file name (using the ncl format by default, but you can override this by specifying an extension to fnamOutput). The stimulus is sampled at samplingRate.
	
The text file is formatted as follows:
	
Each line in the file specifies a stimulus segment. These will be added together to generate the final stimulus. Comment lines begining with "#" and blank lines are ignored. All other lines must contain the following fields, separated by ";" characters: 

offset; waveform type; duration; padding; repeats; frequency; channels; amplitude

Some fields may be subdivided using "," characters. For example "channels" could be ";0;" or ";0,1,2;"

All numbers specifying time coordinates (such as offsets, padding lengths or periods) are always considered to be in seconds (not sample points or milliseconds!), so the number of samples associated to a value of N is round(N*samplingRate).

The meaning and values of the fields are:

offset:
This may be 1) a number, 2) the string "next", 3) the string "end" 4) the string "last" 5) "next", "last" or "end" followed by "+" followed by a number.

The value specifies where to start the stimulus segment. If it is a number it is treated as an offset from the start of the file in seconds. If it is "next" it is treated as the end of the last stimulus segment that was specified on any of the channels used by this segment. If it is "last" it is the same offset as the start of the last specified segment. If it is "end" it is the smallest index such that all previously specified segments (on any channel) are completed. "next+#", "last+#" and "end+#" determine "next", "last" or "end" as described, and add an additional offset in seconds.

If multiple segments are specified such that they apply signal to the same channels at the same offsets, these signals are added together in the final stimulus.

waveform type:
This is a string specifying what sort of signal to send. The waveform type affects how many parameters are expected in the in some other  fields, and how they are interpreted, as described below. Some waveform types ignore some field. When a waveform type ignores a field, it may be empty (";;"), or zero (";0;"), with the same result. 

Currently supported waveform types are:

"wn": Band limited white noise. "frequency" should be a list of two numbers, specifying the lower and upper band limits in Hz. 	Amplitude is the standard deviation. Optionally, there may be a third number, which will act as a random seed (this can be used to insure that two noise samples in different segments are the same as each other)

"sin": Sine wave. Frequency may be a single number (the actual frequency in Hz), or 2 (the frequency in Hz, and the phase in degrees). "amplitude" is one number; max absolute value of the wave. 

"pulse": A square wave pulse chain. Frequency is two numbers; the time spent in the on position, and the time spent in the off position. The wave turns "on" immediately when the segment starts. "amplitude" is two numbers; the value when the pulse is on, and the value when it is off.

"ramp": An asymmetric triangle wave (strictly positive). Frequency is two numbers: the rise time and the return time. Amplitude is the peak value.

"dc": A dc offset. Frequency is ignored. Amplitude is one number; the value of the signal. A "dc" stimulus with an amplitude of 0 sends silence, and can be used as a spacer.

"ssw": Sequential sine waves separated by linear FM ramps. Frequency is a list with a length that is a multiple of three. Each set of three numbers is a starting frequency, a stopping frequency, and a frequency increment. Example: 5,10,1,10,50,5 means generate a sine wave every 1 Hz starting at 5 Hz and stopping at 9 Hz, then every 5 Hz starting at 10 Hz and stopping at 45 Hz. Duration must be calculated by the user: dur = (total of frequencies)*(dur of sine wave) + (total of frequencies -1 )*(dur of sine wave)/10. The duration of the ramp is always assumed to be 1/10-th the length of a sine wave segment. Amplitude is the peak value of (all) the sine waves.

duration:
This is a single number, which is the duration of the signal in seconds. Note that this is NOT the same as the duration of the whole segment, unless repeats is 1 and padding is 0. 

padding:
A duration, in seconds, to send silence before and after each repeat of the waveform. Padding may also be two numbers. In this case the second number is used as the length (in seconds) of a  boxcar smoothing filter at the beginning and end of the waveform. Use this to avoid clicks. The smoothing occurs after the padding, so the first nonzero sample will be at the start of the signal, but the first full-amplitude sample will be "smoothing" seconds later.

repeats:
An integer, specifying the number of times to send the waveform. The padding is also repeated. Thus, the full duration of a segment is repeats*(duration+2*padding)

frequency:
a number or list of numbers specifying frequency information for the waveform. Different waveforms use this value differently, as described above. 

channels:
an integer, or list of integers, specifying the channel or channels to put the signal on. If the signal is on several channels it is exactly the same signal (in particular noise is frozen noise).

amplitude:
A number or list of numbers specifying the amplitude of the signal. How this is interpreted depends on waveform type (see above). In general, there will either be one amplitude, or one amplitude per channel. "pulse" waveforms require two exactly two amplitudes, and do not support differential amplitudes per channel (use several segments instead). 
'''
	offsets={}
	sdl=[]
	for l in open(fname).readlines():
		sl=_parsetxtline(l, offsets)
		if sl:
			sdl.append(sl)
	if offsets.has_key('last'):
		del(offsets['last'])
	chan=max(offsets.keys())
	dur=max(offsets.values())
	nsamp=int(round(dur*samplingRate))
	dat=zeros((nsamp, chan+1), float32)
	for stim in sdl:
		if not STIM_GEN.has_key(stim['wave']):
			print("Unknown wave type %s" % stim['wave'])
			continue
		stim['fs']=samplingRate	
		sw=_genWave(stim)
		off=int(round(stim['off']*stim['fs']))
		#print "adding %s with shape %s at %i" % (stim['wave'], str(sw.shape), off)
		dat[off:off+sw.shape[0],stim['chan']]+=sw
	ds.datinit(dat, {"SampleType":'timeseries', 'SamplesPerSecond':samplingRate})
	if fnameOutput:
		if not os.path.splitext(fnameOutput)[-1]:
			fnameOutput+='.ncl'
		ext=os.path.splitext(fnameOutput)[-1]	
		write(ds, fnameOutput, newdoc=True, format=ext)
		print("Wrote stimulus to %s" % fnameOutput)