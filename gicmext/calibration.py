#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-06-03.

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

'''
Calibration module for microflown and wind boxes in the Miller lab

This is an extension block for the MIEN software suite. It will not operate as independent software, but a copy is maintained in the calibration disk archive so that the code can be referred to in efforts to test or reproduce the calibration results. 

PHASE_CONVENTION:

All code in this model assumes that a sinusoidal component with parameters Amp, Freq, Phase, is represented as Amp*cos(Freq*2*pi*time + Phase).

The use of the + sign is for compatibility with the convention used in Fourier transform libraries.

The result is that, if the peak of an output signal occurs N radians after the peak of an input signal, this phase lag is represented as outputphase-inputphase = -N.

TIME_REVERSAL_CONVENTION:
Filters (objects which might match a waveform in the signal) are applied by convolving the signal with the time reverse of the filter. 

Impulse responses (the response of a system to a delta function input) are applied by strait convolution with the input, without a time reversal. 

This module chooses to construct impulse response functions, and to apply them with NO time reversal. This saves a step in constructing the function with inverse fourier transform. 

The previous matlab implementation also seems to have used impulse response functions. As tested in Matlab v2007b, calling Matlab's "filter" with (filter, 1, data), with filter a timeseries vector, as done by Zane Aldworth's "quickcalibfilt.m", is equivalent to calling conv(data, filter), and subsequently removing 1/2 the filter length from the beginning and end of the signal. There is no time reversal involved, consequently the vector "filter" is treated as an impulse response. 

This module is therefore using the same conventions as the previous implementation. 

ONE_POINT_OFFSET:
It seems that numpy irfft generates a filter which is 1 point to long. After moving the negative-frequency values of the ift to the left side of the signal, the 0 sample of the filter needs to be removed to compensate for this. 

FILTER_RESAMPLE:

Resampling filters is tricky business. It absolutely can't be done by interpolation. This causes a frequency-dependent change in the gain. Upsampling a filter by a factor of N using interpolation causes an N fold increase in the gain for very low frequency, but no change in the gain for very high frequency, so there is no single scale factor that corrects for this. The viable options are "comb resampling" (eg. uniformly filling zeros between the numerical samples of the filter, until it reaches the desired sampling rate), or taking the ft, zero padding the right side of the ft, and taking the inverse ft. Both methods are implemented in this module.
'''


from mien.datafiles.dataset import *
from mien.math.sigtools import bandpass, bode, windowedFFT, ampPhaseToComplex, array_resample
from numpy.random import randn
from numpy.fft import rfft, irfft, ifft
import os
import mien.parsers.fileIO as io




def _applyFilterWithTR(dat, filt):
	ds=dat.shape[0]
	fs=len(filt)
	filt = filt[arange(filt.shape[0]-1, -1, -1)]
	dat=concatenate([zeros(fs, dat.dtype),  dat, zeros(fs, dat.dtype)])
	dat=convolve(dat, filt, 'same')
	dat=dat[fs:fs+ds]
	return dat


def _applyfilter(dat, filt):
	ds=dat.shape[0]
	fs=len(filt)
	dat=concatenate([zeros(fs, dat.dtype),  dat, zeros(fs, dat.dtype)])
	dat=convolve(dat, filt, 'same')
	dat=dat[fs:fs+ds]
	return dat


def _makeCos(fs, freq, phase, nc):
	phase = phase*pi/180
	samppercycle = fs/freq
	nsamp=nc*samppercycle
	dt = 1.0/fs
	t = arange(nsamp)*dt
	sig = cos(2*pi*freq*t+phase)
	return sig


def makeCosWave(ds, freq=50, phase=90, ncycles=100, fs = 10000, newpath="/"):
	dat = _makeCos(fs, freq, phase, ncycles)
	head = {'SampleType':'timeseries', "SamplesPerSecond":fs}
	ds.createSubData(newpath, dat, head, True)


def _trigger(cd, lt, ht):
	evts=[]
	hit=nonzero(cd>ht)[0]
	fci=nonzero(hit[1:]-hit[:-1]!=1)[0]+1
	fcross=hit[fci]
	for j in range(1, fcross.shape[0]):
		if any(cd[fcross[j-1]:fcross[j]]<lt):
			evts.append(fcross[j])
	return array(evts)


def _cosineModel(dat, fs, freq2=None):
	dat-=dat.mean()
	cross = _trigger(dat, .7*dat.min(), .7*dat.max())
	mc=(cross[1:]-cross[:-1]).mean()
	per=mc/float(fs)
	freq=1.0/per
	mc=int(mc)
	if freq2:
		if abs(freq-float(freq2))>0.05:
			print('Difference in given versus calculated frequency. Given =  %.2G, calculated = %.2G. Using given frequency.' % (float(freq2), freq))
			freq=float(freq2)
		mc=int(round(fs/freq))
	
	x=arange(dat.shape[0]).astype(float32)/fs
	sm=cos(2*pi*freq*x[:-mc])
	dos=array([dot(sm, dat[i:i+sm.shape[0]]) for i in range(mc)])
	phase=-2*pi*float(argmax(dos))/mc
	sm=cos(2*pi*freq*x+phase)
	nz=nonzero(logical_and(abs(sm)>.05*sm.max(), abs(dat)>.05*dat.max()))
	r=dat[nz]/sm[nz]
	amp=abs(r).mean()
	#print "estimate y=%.2G*sin(2*pi*%.2G*x %+.2G)" % (amp, freq, phase)
	return (amp, freq, phase*180/pi)


def analyzeFilterSin(ds, dpathFilt="/", minFreq=5, maxFreq=500):
	'''Apply a range of cosine waves to the single channel time domain filter at dpathFilt. Construct a table of gain and phase (a Bode plot) for the filter from these experiments, and save it in the dpath "filterResponseSin"'''
	filt = ds.getSubData(dpathFilt)
	fs = filt.fs()
	filt = filt.data[:,0]
	freqs = arange(minFreq, maxFreq, 1.0)
	tf = zeros((freqs.shape[0], 3))
	tf[:,0]=freqs
	for i, freq in enumerate(freqs):
		cw = _makeCos(fs, freq, 0, 100)
		fcw =  _applyfilter(cw, filt)
		try:
			a, f, p = _cosineModel(cw, fs, freq2=freq)
			a2, f2, p2 = _cosineModel(fcw, fs, freq2=freq)
		except:
			print "can't get cosine models at %.3g. Skipping" % freq
			continue
		gain = a2/a
		phase = p2-p
		tf[i,1]= gain
		tf[i,2] = phase*pi/180.0
		print tf[i,:]
	head = {"SampleType":"timeseries", "SamplesPerSecond":1.0, "StartTime":minFreq}
	ds.createSubData('filterResponseSine', data=tf[:,1:], head=head, delete=True)


def _bode(idat, odat, fs):
	ift = rfft(idat, fs)
	oft =  rfft(odat, fs)
	trans = (ift * conjugate(oft)) / (ift * conjugate(ift) ) 
	freq = arange(trans.shape[0]).astype(Float64)*fs/(2*trans.shape[0])
	amp=abs(trans)
	phase=arctan2(trans.imag, trans.real)
	return (freq, amp, phase)


def sinScanToTF(ds, fname="breeMFdata.mdat", newpath="/", start=.5, accSens = 0.0999, stride=5.5, dur=3.0, nscans=62):
	doc = io.read(fname)
	dat = doc.getElements("Data")[0]
	fs = dat.fs()
	dat = dat.getData()
	calib=[]
	offset = int(round(start*fs))
	dur = int(round(dur*fs))
	stride = int(round(stride*fs))
	lfreq = 0
	for i in range(nscans):
		accel = dat[offset:offset+dur, 1]
		mf = dat[offset:offset+dur, 0]
		offset+=stride
		accel -= accel.mean()
		mf-=mf.mean()
		accel/=accSens
		#print max(accel), max(mf)
		aa, af, ap = _cosineModel(accel, fs)
		va, vf, vp = _cosineModel(mf, fs)
		#print aa, va
		if abs(af - vf)/min(af, vf) > .1*min(af, vf):
			print "Warning: %s: estimated different frequncies for input (%.4g) and output (%.4g). Skipping this data point" % (ffn, af, vf)
			continue
		freq = (af+vf)/2.0
		if freq < lfreq:
			print "Warning: frequency isn't increasing at %i (last:%.4g, this %.4g). Skipping point" % (offset, lfreq, freq)
			continue
		lfreq=freq
		#print offset
		print aa, af, ap
		print va, vf, vp
   		ap-=90
		aa=aa/(2*pi*af)
		while ap<vp:
			ap+=360
		while ap>vp:
			ap-=360
		gain = aa/va
		phase = (ap-vp) 
		phase= (phase*pi/180)
		phase = phase % (2*pi)
		if phase>pi:
			phase-=2*pi
		calib.append([freq, gain, phase])
	calib = array(calib)
	ind = calib[:,0].argsort()
	calib = calib[ind, :]
	for i in range(calib.shape[0]):
		print calib[i]
	gain = uniformsample(calib[:,[0,1]], 1.0, True)
	phase = uniformsample(calib[:,[0,2]], 1.0, True)
	head = {"SampleType":"timeseries", "SamplesPerSecond":1.0, "StartTime":calib[0, 0]}
	ds.createSubData(newpath, column_stack([gain, phase]), head=head, delete=True)	


def datDirToTF(ds, newpath="/", dir="mf04dat"):
	files = os.listdir(dir)
	calib = []
	for f in files:
		if not os.path.splitext(f)[-1][1:].isdigit():
			print "ignoring %s" % f
			continue
		ffn = os.path.join(dir, f)
		try:
			doc = io.read(ffn)
			dat = doc.getElements("Data")[0]
		except:
			print "read failure %s" % ffn
			continue
		fs = dat.fs()
		dat = dat.getData()
		accel = dat[:,1] - dat[:,1].mean()
		accel*=10.01
		vel = dat[:,2] - dat[:,2].mean()
		aa, af, ap = _cosineModel(accel, fs)
		va, vf, vp = _cosineModel(vel, fs)
		if abs(af - vf)/min(af, vf) > .1*min(af, vf):
			print "Warning: %s: estimated different frequncies for input (%.4g) and output (%.4g). Skipping this data point" % (ffn, af, vf)
			continue
		freq = (af+vf)/2.0
		print ffn
		print aa, af, ap
		print va, vf, vp
   		ap-=90
		aa=aa/(2*pi*af)
		while ap<vp:
			ap+=360
		while ap>vp:
			ap-=360
		gain = aa/va
		phase = (ap-vp) 
		print gain, phase
		phase= (phase*pi/180)
		phase = phase % (2*pi)
		if phase>pi:
			phase-=2*pi
		calib.append([freq, gain, phase])
	calib = array(calib)
	ind = calib[:,0].argsort()
	calib = calib[ind, :]
	gain = uniformsample(calib[:,[0,1]], 1.0, True)
	phase = uniformsample(calib[:,[0,2]], 1.0, True)
	head = {"SampleType":"timeseries", "SamplesPerSecond":1.0, "StartTime":calib[0, 0]}
	d = ds.getSubData(newpath)
	if d:
		d.datinit(column_stack([gain, phase]), head)
	else:
		ds.createSubData(newpath, column_stack([gain, phase]), head=head)
	pass


def _quickFFT(sig, fs):
	oft =  rfft(sig, fs)
	freq = arange(oft.shape[0])*fs/(2*oft.shape[0])
	amp=abs(oft)
	amp*=2.0/fs
	phase=arctan2(oft.imag, oft.real)
	return (freq, amp, phase)



def mfTransferFuncFromWN(ds, dpath="/", chanAccel=1, chanMF=0, accSens = 0.0999, newpath="/xfer", useWindowedFFT=True):
	'''Calculate a transfer function from MicroFlown voltage responses to velocity in m/s. The input data in dpath chanAccel should be the output of an accelerometer that is absolutely calibrated by "accSens" in V/(m/s^2).  dpath chanMF contains the microflown output voltage. This function implicitly integrates the accelerometer output to get a velocity estimate (in frequency space). The resulting transfer function is stored in newpath as two channels: gain, and phase
SWITCHVALUES(useWindowedFFT)=[True, False]
'''
	if useWindowedFFT:
		getFFT = windowedFFT
	else:
		getFFT = _quickFFT
	d = ds.getSubData(dpath)
	fs = d.fs()
	acc = d.data[:,chanAccel]
	#really, we want m/s**2, not volts
	acc=acc/accSens
	afreq, aamp, aphase = getFFT(acc, fs)
	afreq[0]=1
	#but wait, we want velocity in m/s
	aphase -= pi/2
	aamp/=(2*pi*afreq)
	mf =  d.data[:, chanMF]
	vfreq, vamp, vphase = getFFT(mf, fs)
	if any(vamp==0):
		vamp += .00000001*(vamp==0)
	gain = aamp/vamp
	phase = aphase - vphase
	phase = phase % (2*pi)
	phase = where(phase>pi, phase-2*pi, phase)
	phase = where(phase<-pi, phase+2*pi, phase) 
	gain = uniformsample(column_stack([vfreq, gain]), 1.0, True)
	gain[0]=0
	phase = uniformsample(column_stack([vfreq, phase]), 1.0, True)
	head = {"SampleType":"timeseries", "SamplesPerSecond":1.0, "StartTime":vfreq.min()}
	ds.createSubData(newpath, data=column_stack([gain, phase]), head=head, delete=True)	


def genericTransferFuncFromWN(ds, dpath="/", chanFrom=0, chanTo=1, newpath="/xfer", useWindowedFFT=True, zfill=1):
	'''Calculate a generic transfer function between two timeseries in dpath chanFrom and chanTo, No special assumptions are made about the types of these data. The resulting transfer function is stored in newpath as two channels: gain, and phase.
	The transfer function is sampled at 1 sample = 1 Hz in frequency space.
	The first zfill samples of the transfer function (gain and phase) are set to zero. To get the raw transfer function, set zfill=0.
SWITCHVALUES(useWindowedFFT)=[True, False]
'''
	if useWindowedFFT:
		getFFT = windowedFFT
	else:
		getFFT = _quickFFT
	d = ds.getSubData(dpath)
	fs = d.fs()
	din = d.data[:,chanFrom]
	dout = d.data[:,chanTo]
	ifreq, iamp, iphase = getFFT(din, fs)
	ofreq, oamp, ophase = getFFT(dout, fs)
	if any(iamp==0):
		small = .000001*abs(iamp[vamp!=0]).min()
		iamp += small*(vamp==0)
	gain = oamp/iamp
	phase = ophase - iphase
	phase = phase % (2*pi)
	phase = where(phase>pi, phase-2*pi, phase)
	phase = where(phase<-pi, phase+2*pi, phase) 
	gain = uniformsample(column_stack([ofreq, gain]), 1.0, True)
	phase = uniformsample(column_stack([ofreq, phase]), 1.0, True)
	if zfill:
		gain[:zfill]=0.0
		phase[:zfill]=0.0
	head = {"SampleType":"timeseries", "SamplesPerSecond":1.0, "StartTime":ofreq.min()}
	ds.createSubData(newpath, data=column_stack([gain, phase]), head=head, delete=True)	


#FIXME: these functions both suck 
#def causalRegressiveModel(ds, dpath='/', chanFrom=0, chanTo=1, npts=100, newpath="/arx"):
# 	'''Generate a causal (left-side coefficients only) regressive model of the mapping from dpath chanFrom to dpath chanTo, and store it in newpath'''
# 	dat = ds.getSubData(dpath)
# 	idat = dat.data[:,chanFrom]
# 	odat = dat.data[:,chanTo]
# 	model = []
# 	for i in range(npts-1, odat.shape[0]):
# 		seg = idat[i-npts+1:i+1]
# 		mseg = odat[i]/(seg*npts)
# 		model.append(mseg)
# 	model = array(model)	
# 	model=transpose(model)
# 	#model = model[arange(model.shape[0]-1,-1,-1)]
# 	head = {"SampleType":"ensemble", "Reps":model.shape[1], "SamplesPerSecond":dat.fs()}
# 	ds.createSubData(newpath, data=model, head=head, delete=True)	
# 
# 
# # def applyCausalRegressive(ds, dpathData='/', chan=0, dpathAR="/arx", newpath="arx_out"):
# 	dat = ds.getSubData(dpathData)
# 	idat=dat.getData()[:,chan]
# 	arx = ds.getSubData(dpathAR).getData()
# 	out = zeros_like(idat)
# 	am = arx.mean(1)
# 	for i in range(arx.shape[0]-1, idat.shape[0]):
# 		#out[i] = (arx[:,i-arx.shape[0]+1] * idat[i-arx.shape[0]+1:i+1]).sum()
# 		out[i] = (am * idat[i-arx.shape[0]+1:i+1]).sum()
# 	ds.createSubData(newpath, data=out, head=dat.header(), delete=True)	

	
def analyzeFilterWN(ds, dpathFilt="/", useWindowedFFT=True, newpath='filterResponseWN'):
	'''Apply a range of cosine waves to the single channel time domain filter at dpathFilt. "
SWITCHVALUES(useWindowedFFT)=[True, False]
	'''
	if useWindowedFFT:
		getFFT = windowedFFT
	else:
		getFFT = _quickFFT
	filt = ds.getSubData(dpathFilt)
	fs = filt.fs()
	filt = filt.data[:,0]
	noise = randn(fs*40)
	fnoise =  _applyfilter(noise, filt)
	head = {"SampleType":"timeseries", "SamplesPerSecond":fs}
	#ds.createSubData('filteredNoise', data=column_stack([noise, fnoise]), head=head, delete=True)
	ifreq, iamp, iphase = getFFT(noise, fs)
	ofreq, oamp, ophase = getFFT(fnoise, fs)
	if any(iamp==0):
		iamp += .00000001*(iamp==0)
	gain = oamp/iamp
	phase = ophase - iphase
	phase = phase % (2*pi)
	phase = where(phase>pi, phase-2*pi, phase)
	phase = where(phase<-pi, phase+2*pi, phase) 
	gain = uniformsample(column_stack([ofreq, gain]), 1.0, True)
	phase = uniformsample(column_stack([ofreq, phase]), 1.0, True)
	freq = uniformsample(column_stack([ofreq, ofreq]), 1.0, True)
	tf = column_stack([freq, gain, phase])
	head = {"SampleType":"timeseries", "SamplesPerSecond":1.0, "StartTime":freq.min()}
	ds.createSubData(newpath, data=tf[:,1:], head=head, delete=True)


def _filterResample(dat, fromfs, tofs):
	if  fromfs == tofs:
		return dat
	n = int(dat.shape[0]/2.0)
	dat = concatenate([dat[n:], dat[:n]])
	nift = int(round(dat.shape[0]*tofs/fromfs))
	c = rfft(dat, dat.shape[0])
	ts = irfft(c, nift)
	n = int(ts.shape[0]/2.0)
	ts = concatenate([ts[n:], ts[:n]])
	#phase correction by one sample point here. Why is that?
	#it seems that irfft doesn't use an odd number of Fourier points, and so the center of the 
	#spectrum gets shifted by one? Overtly specifying an odd number of transform points doesn't solve 
	#the problem though. using nyquist*2+1 
	ts=ts[1:]
	return ts


def _filterResampleTD(dat, fromfs, tofs):
	#only works if len(dat) == fromfs
	if  fromfs == tofs:
		return dat
	newsize = int(round(dat.shape[0]*float(tofs)/fromfs))
	newdat = zeros(newsize, dat.dtype)
	ind = linspace(0, newsize-1, dat.shape[0])
	ind = round(ind).astype(int32)
	newdat[ind]=dat
	return newdat
	


def applyFilterToSignal(ds, dpathSig='/', dpathFilt="/filter", channel=0, newpath='filtered'):
	sig = ds.getSubData(dpathSig)
	filt = ds.getSubData(dpathFilt)
	filt = _filterResample(filt.data[:,0], filt.fs(), sig.fs())
	sigdat = sig.data[:, channel]
	sigdat = _applyfilter(sigdat, filt)
	head = {"SampleType":"timeseries", "SamplesPerSecond":sig.fs(), "StartTime":sig.start()}
	ds.createSubData(newpath, data=sigdat, head=head, delete=True)
	


def filterSin(ds, dpathFilt="/", freq=50, phase=0, cosFS=None):
	'''Apply a the single channel time domain filter at dpathFilt. save in "filteredSine"'''
	filt = ds.getSubData(dpathFilt)
	fs = filt.fs()
	head = {"SampleType":"timeseries", "SamplesPerSecond":fs}
	filt = filt.data[:,0]
	cw = _makeCos(fs, freq, phase, 100)
	fcw =  _applyfilter(cw, filt)
	dat = column_stack([cw, fcw])
	ds.createSubData('filteredSine', data=dat, head=head, delete=True)
	a, f, p = _cosineModel(cw, fs, freq2=freq)
	a2, f2, p2 = _cosineModel(fcw, fs, freq2=freq)
	gain = a2/a
	phase = p2-p
	print a, f, p
	print a2, f2, p2
	print gain, phase	


def compressFilter(ds, dpath='/', newpath='/reduced', targetfs=10000, targetlength=4000, smoothingpoints=-1):
	filt = ds.getSubData(dpath)
	ffs = filt.fs()
	fdat = filt.getData(copy=True)[:,0]
	head = filt.header()
	if targetfs:
		fdat = _filterResample(fdat, ffs, targetfs)
		head["SamplesPerSecond"]=targetfs
	if targetlength and fdat.shape[0]>targetlength:
		rn = floor((fdat.shape[0]-targetlength)/2)
		fdat = fdat[rn:-rn]
	fdat-=fdat.mean()
	if smoothingpoints:
		if smoothingpoints=='all' or smoothingpoints<0:
			swin = (cos(linspace(-pi, pi, fdat.shape[0])) + 1)/2.0
			fdat*=swin
		else:
			swin = (cos(linspace(0, pi, smoothingpoints)) + 1)/2.0
			fdat[-smoothingpoints:]*=swin
			swin = swin[arange(swin.shape[0]-1, -1, -1)]
			fdat[:smoothingpoints]*=swin
		fdat-=fdat.mean()
	ds.createSubData(newpath, data=fdat, head=head, delete=True)
	

	
def getFilterSpectrum(ds, dpathFilt="/", newpath="/spec"):
	dat = ds.getSubData(dpathFilt)
	fs = dat.fs()
	dat = dat.data[:,0]
	n = int(dat.shape[0]/2.0)
	dat = concatenate([dat[n:], dat[:n]])
	f, amp, phase = _quickFFT(dat, fs)
	amp*=fs/2.0
	head = {"SampleType":"timeseries", "SamplesPerSecond":1.0}
	ds.createSubData(newpath, column_stack([amp, phase]), head=head, delete=True)


def getFilteredNoiseSpectrum(ds, dpathFilt='/', newpath="nspec"):
	dat = ds.getSubData(dpathFilt)
	fs = dat.fs()
	dat = dat.data[:,0]
	noise = randn(fs*20)
	fnoise =  _applyfilter(noise, dat)
	f, amp, phase = _quickFFT(fnoise, fs)
	f1, amp1, phase1 = _quickFFT(noise, fs)
	amp = amp/amp1
	phase = phase-phase1
	head = {"SampleType":"timeseries", "SamplesPerSecond":1.0}
	ds.createSubData(newpath, column_stack([amp, phase]), head=head, delete=True)


def filterFromXFer(ds, dpathXFer='/', newpath='/filter', nyquist=5000):
	d = ds.getSubData(dpathXFer)
	fs, start = d.fs(), d.start()
	gain = d.data[:,0]
	phase = d.data[:,1]
	if not nyquist:
		nyquist = start + gain.shape[0]/fs
	if start:
		npad = int(round(start*fs))
		gain = concatenate([zeros(npad), gain])
		phase = concatenate([zeros(npad), phase])
	else:
		gain[0]=0
		phase[0]=0
	c = gain*exp(1j*phase)
	ts = irfft(c, nyquist*2)
	n = int(ts.shape[0]/2.0)
	ts = concatenate([ts[n:], ts[:n]])
	#phase correction by one sample point here. Why is that?
	#it seems that irfft doesn't use an odd number of Fourier points, and so the center of the 
	#spectrum gets shifted by one? Overtly specifying an odd number of transform points doesn't solve 
	#the problem though. using nyquist*2+1 
	ts=ts[1:]
	head = {"SampleType":"timeseries", "SamplesPerSecond":nyquist*2}
	ds.createSubData(newpath, data=ts, head=head, delete=True)
	analyzeFilterWN(ds, dpathFilt=newpath, useWindowedFFT=True)

