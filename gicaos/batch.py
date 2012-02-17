#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2008-06-26.

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
import sys, struct, getopt, os
from numpy import *
try:
	import mien.parsers.fileIO as io
except:
	print("No mien io support. Don't use mdat files")

NIKON_PixPerDiv=107.25
AOS_PixPerDiv=187.5


## --------------- Array Algorithms -------------------

def regress(dat):
	n=float(dat.shape[0])
	x=dat[:,0]
	y=dat[:,1]
	sumxx=(x**2).sum()
	sumyy=(y**2).sum()
	sumxy=(x*y).sum()
	Sxx = sumxx-x.sum()**2/n
	Sxy = sumxy-y.sum()*x.sum()/n
	m =Sxy/Sxx;
	b = (y.sum()-m*x.sum())/n
	return (m, b)


def interpolate(a, d):
	z=take(a, d.astype(int32))
	z=z.astype(d.dtype.char)
	rems=d%1
	for i in nonzero(rems)[0]:
		ind=int(d[i])
		last=a[ind]
		if ind+1 >=len(a):
			next=a[-1]+(a[-1]-a[-2])
		else:
			next=a[ind+1]
		percent=rems[i]
		z[i]=percent*(next-last)+last
	return z
	
def resample(a, from_samp, to_samp, interp=True):
	from_samp=1.0/from_samp
	to_samp=1.0/to_samp
	samp_r = to_samp/from_samp
	domain=arange(0, len(a), samp_r)
	if samp_r % 1 and 1/samp_r % 1 and interp:
		return interpolate(a, domain)
	else:
		return a[domain.astype(int32)]

def numfilter(dat, filt):
	ds=dat.shape[0]
	fs=len(filt)
	dat=concatenate([zeros(fs, dat.dtype),  dat, zeros(fs, dat.dtype)])
	dat=convolve(dat, filt, 'same')
	dat=concatenate([dat[fs-1:fs+ds-1]])
	return dat


def filterResample(dat, fromfs, tofs):
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

def trigger(cd, lt, ht):
	evts=[]
	hit=nonzero(cd>ht)[0]
	fci=nonzero(hit[1:]-hit[:-1]!=1)[0]+1
	fcross=hit[fci]
	for j in range(1, fcross.shape[0]):
		if any(cd[fcross[j-1]:fcross[j]]<lt):
			evts.append(fcross[j])
	return array(evts)
	
def bestSineModel(dat, fs, freq2=None):
	dat-=dat.mean()
	cross = trigger(dat, .7*dat.max(), 0)
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
	sm=sin(2*pi*freq*x[:-mc])
	dos=array([dot(sm, dat[i:i+sm.shape[0]]) for i in range(mc)])
	phase=-2*pi*float(argmax(dos))/mc
	sm=sin(2*pi*freq*x+phase)
	nz=nonzero(logical_and(abs(sm)>.05*sm.max(), abs(dat)>.05*dat.max()))
	r=dat[nz]/sm[nz]
	amp=abs(r).mean()
	#print "estimate y=%.2G*sin(2*pi*%.2G*x %+.2G)" % (amp, freq, phase)
	return (amp, freq, phase)

def rotate(a, dir):
	'''Nx2 array, float => Nx2 array
convert a 2 col array to another representing the same stimulus rotated
dir degrees clockwise. 0-180 should be in the 0 column and  L-R in the 1
column.'''
	dir=pi*dir/180
	newy=a[:, 0]*cos(dir) - a[:, 1]*sin(dir)
	newx=a[:, 0]*sin(dir) + a[:,1]*cos(dir)
	return transpose(array([newy, newx]))

def imrotate(i, t):
	ind=transpose(array(nonzero(ones(i.shape[:2]))))	
	s=(i.shape[0]/2, i.shape[1]/2)
	rind=ind.astype(float32)-s
	rind=rotate(rind, t)+s
	rind=around(rind).astype(int32)
	gi=nonzero(logical_and(all(rind>=(0,0), 1), all(rind<i.shape[:2],1)))
	ind=ind[gi]
	rind=rind[gi]
	out=ones_like(i)*i.dtype.type(i.mean())
	out[ind[:,0], ind[:,1], :]=i[rind[:,0], rind[:,1], :]
	return out

def uniformsample(a, dt):
	'''(N,Q) |Q>=2 array, float => (M,Q-1) array
convert an array of x/y pairs to a 1D array that uniformly samples the represented function with interval dt. Uses linear interpolation. If there are more than 2 columns, all are sampled using the first column as x'''
	a = take(a, argsort(a[:,0]), 0)
	xa = arange(a[0,0], a[-1,0]+.5*dt,dt)
	ya= zeros((len(xa),a.shape[1]-1)).astype(a.dtype)
	ins=a[:,0].searchsorted(xa)
	ins=where(ins<a.shape[0], ins, a.shape[0]-1)
	hit=a[ins,0]==xa
	hi=nonzero(hit)[0]
	ya[hi,:]=a[ins[hi], 1:]
	m=nonzero(logical_not(hit))[0]
	mi=ins[m]
	ub=a[mi,0]
	lb=a[mi-1,0]
	v=xa[m]
	p=(v-lb)/(ub-lb)
	p=reshape(p, (-1,1))
	ub=a[mi,1:]
	lb=a[mi-1,1:]
	ya[m,:]=lb+(ub-lb)*p
	return ya

def smooth(a, n):
	a=convolve(ones(n), a, mode='same')/float(n)
	return a

## --------------- File IO -------------------

def read_mien(f):
	doc=io.read(f)
	dat=doc.getElements('Data')[0]
	h=dat.header()
	d=dat.getData()
	fs = 1.0/h['StackSpacing']
	d=d[:,:,0,:]
	return (d, fs)

def read_raw(f, sw):
	f=open(f, 'rb')
	j1, width, height, j2, timescale=struct.unpack('<44siiid', f.read(64))
	f.seek(0, 2)
	flen=f.tell()-1024
	sof=width*height
	nframes=flen/sof
	f.seek(1024)
	print('loading image stack: %ix%i, %i frames  ...' % (width, height, nframes))
	if sw.get('startframe'):
		f.seek(1024+sw['startframe']*sof)
	btr=-1
	if sw['nframes']>0 and sw['nframes']+sw.get('startframe', 0) < nframes:
		btr = sw['nframes']*sof
	a=fromfile(f, uint8, btr)	
	a=transpose(reshape(a, (-1, height, width)))
	if sw.get('xmin'):
		a=a[sw['xmin']:,:]
	if sw.get('ymin'):
		a=a[:, sw['ymin']:,:]
	if sw.get('xmax', -1)!=-1:
		r=sw['xmax']-sw.get('xmin', 0)
		a=a[:r, :,:]
	if sw.get('ymax', -1)!=-1:
		r=sw['ymax']-sw.get('ymin', 0)
		a=a[:, :r,:]
	return (a, 1.0/timescale)

def read_ncl(f):
	f=open(f, 'rb')
	nchans, fs = struct.unpack("<ff", f.read(8))
	a=reshape(fromstring(f.read(), "<f4"), (-1, nchans))
	return (a, fs)
	
def read_streamer(f):
	'''Buggy, don\'t use. '''
	f=open(f, 'rb')
	hdrlen, chans, j0, samp= struct.unpack("<iB3sI", f.read(12))
	order=struct.unpack("B"*64, f.read(64))
	ranges=array(struct.unpack("<"+"f"*chans, f.read(4*chans)))
	f.seek(hdrlen)
	a=reshape(fromstring(f.read(), "<i2"), (-1, chans))
	print a[:,2].min(), a[:,2].max()
	a=a.astype(float32)* (ranges/2**11)
	return (a, samp)
	

def write_txt(fn, fs, lab, pts):
	f=open(fn, 'w')
	if fs:
		f.write('Sampling Rate (Hz): %G\n%s\n' % (fs, lab))
	else:
		f.write(lab+"\n")
	f.write("\n".join(map(lambda x:" ".join(map(lambda y:"%G" % y, x)), pts)))
	f.close()
	print('wrote to %s' % fn)
	
def write_ncl(fn, d, fs):
	f=open(fn, 'wb')
	d=d.astype("<f4")
	f.write(struct.pack("<ff", d.shape[1], fs))
	f.write(d.tostring())	
			

## --------------- Processing Macros -------------------

def getAofT(fn,  sw):
	if fn.endswith('raw'):
		dat, fs = read_raw(fn, sw)
	else:
		doc=io.read(fn)
		d=doc.getElements('Data')[0]
		h=d.header()
		dat=d.getData()
		fs = 1.0/h['StackSpacing']
		dat=dat[:,:,0,:]
	print('processing image stack: %ix%i, %i frames ...' % (dat.shape[0], dat.shape[1], dat.shape[2]))
	if sw.get('rotate'):
		dat=imrotate(dat, sw['rotate'])
	pts=[]
	if sw.has_key('subtract_mean'):
		dat=dat.astype(float32)-dat.mean(2)[:,:,newaxis]
		for i in range(dat.shape[2]):
			dat[:,:,i]-=dat[:,:,i].min()
			dat[:,:,i]/=dat[:,:,i].max()
	for i in range(dat.shape[2]):
		x=dat[:,:,i].sum(1)
		if sw['w']>1:
			x=convolve(ones(sw['w']), x, mode='same')
		x=argmax(x)
		pts.append(x)
	pts=array(pts).astype(float32 )
	L=sw['l']*AOS_PixPerDiv/NIKON_PixPerDiv	
	pts-=pts.mean()
	#small angle aprox
	saa=pts/L
	doc.sever()	
	return (saa, fs)

def calc_cw_transferfunc(dat, fs, freq=None):
	va, vf, vp = bestSineModel(dat[:,1], fs, freq)
	print "modeling velocity data: %.3G*sin(2*pi*%.2G*x %+.2G)" % (va, vf, vp)
	aa, af, ap = bestSineModel(dat[:,0], fs, freq)
	print "modeling angle data: %.3G*sin(2*pi*%.2G*x %+.2G)" % (aa, af, ap)
	if abs(float(vf)/af - 1) >.05:
		af= (vf+af)/2.0
		print "warning: velocity and angle don't seem to have the same frequency. Data are noisy or system is nonlinear?"
		print "approximating with average frequency %G" % af
		va, vf, vp = bestSineModel(dat[:,1], fs, af)
		print "modeling velocity data: %.3G*sin(2*pi*%.2G*x %+.2G)" % (va, vf, vp)
		aa, af, ap = bestSineModel(dat[:,0], fs, af)
		print "modeling angle data: %.3G*sin(2*pi*%.2G*x %+.2G)" % (aa, af, ap)
	gain = aa/va
	phase = ap-vp 
	print "--------- Transfer function data point -----------"
	print "Gain (radians / (m/s)): %.4G" % gain
	print "Phase (angle phase - velocity phase, radians): %.4G" % phase
	print "--------------------------------------------------"	
	return (gain, phase, af)

def calc_wn_transferfunc(dat, fs):
	if fs - int(fs) > 0.01:
		print('Warning: sampling rate is non-integer: %.03f. Rounding to %i.' % (fs,int(fs)))
	fs=int(fs)
	vd = fft.rfft(dat[:,1],fs)
	ad = fft.rfft(dat[:,0],fs)
	#change amplitude into real units
	vd = (vd*2)/(min(dat.shape[0],fs))
	ad = (ad*2)/(min(dat.shape[0],fs))
	#calculate amplitude and phase
	va = abs(vd)
	aa = abs(ad)
	vp = arctan2(vd.imag,vd.real)+pi/2 #add pi/2 to get FT in terms of sines, not cosines
	ap = arctan2(ad.imag,ad.real)+pi/2 #add pi/2 to get FT in terms of sines, not cosines
	#threshold va  
	va=smooth(va, 5)
	adj = (va.max()-va.min())*.2  #threshold here
	va = array([max(va[i],adj+va.min()) for i in range(len(va))])
	aa=smooth(aa, 5)	
	#Multiply gain and phase to put them on the same scale as velocity
	gain = aa/va*(va.max()/(aa/va).max()) 
	gainns = aa/va
	phase = (ap-vp)*(va.max()/(ap-vp).max())/3 
	phasens = ap-vp
	freq = arange(0,fs/2+1);
	return (gain, va, phase, freq, gainns, phasens)


def get_velocity(fn, sw, pfs):
	print "loading microflown data and converting to velocity..."
	mff=os.path.join(os.path.split(__file__)[0], 'MicroflownCalib.ncl')
	mff, ffs = read_ncl(mff)
	mff=mff[:,0]
	doc = io.read(fn)
	vdat = doc.getElements('Data')[0]
	vfs = vdat.fs()
	vdat = vdat.getData()
	#vdat, vfs = read_streamer(fn)
	vdat=vdat[:,sw['m']]
	#linear regression
	a=arange(float(len(vdat)))
	o=ones(vdat.shape[0])
	A=column_stack([a,o])
	l, resid, rank, s =linalg.lstsq(A,vdat)
	if l[0] > .001*(max(vdat)-min(vdat)):
		print('Warning: possible linear trend in velocity data. Slope of linear regression = %.3f, peak-to-peak velocity difference = %.3f.' % (l[0], max(vdat)-min(vdat)))
	#write_txt('test.txt', ffs, 'data 	linear 	final', column_stack([vdat,line,vdat-line]))
	if vfs!=ffs:
		mff= filterResample(mff, ffs, vfs)
	vdat=numfilter(vdat, mff)
	# write_txt('test.txt', ffs, 'filtered', vdat[:,newaxis])
	if vfs!=pfs:
		vdat=resample(vdat, vfs, pfs)
	if sw.get('startframe'):
		vdat=vdat[sw['startframe']:]
	vdat-=vdat.mean()
	return vdat	
	

def process(fn, switches):
	if switches.get('use_angles'):
		l=open(switches['use_angles']).readlines()
		pfs=int(l[0].split(':')[-1])
		of = array([map(float, s.split()) for s in l[2:]])
	else:
		angles, pfs = getAofT(fn[0], switches)
		vdat=get_velocity(fn[1], switches, pfs)
		vdat=vdat[:angles.shape[0]]
		of=column_stack([angles, vdat])
		write_txt(switches['raw_angles'], pfs, "Angle Velocity", of)
	if not sw.get('xfer'):
		return
	if switches['xfer'].lower().startswith('s'):
		if switches.has_key('xfer_freq'):
			gain, phase, freq = calc_cw_transferfunc(of, pfs, switches['xfer_freq'])
		else:
			gain, phase, freq = calc_cw_transferfunc(of, pfs)
		f=open(switches['xfer_file'], 'a')
		if not open(switches['xfer_file']).read():
			f.write("Frequency Gain Phase\n")
		f.write("%.4G %.4G %.4G\n" % (freq, gain, phase))
		f.close()
	elif switches['xfer'].lower().startswith('w'):
		gain, ftvel, phase, freq, gainns, phasens = calc_wn_transferfunc(of, pfs)
		tf=column_stack([freq, gain, ftvel, phase, gainns, phasens])
		tf=uniformsample(tf, 1.0)
		write_txt(switches['xfer_file'], 1.0, "Gain FTVelocity Phase", tf[:,:3])
		write_txt('batch_noscale.txt', 1.0,"Gain Phase",tf[:,3:])
			

def batch_process(fn, switches):
	aosfiles=os.listdir(fn[0])
	mffiles=os.listdir(fn[1])
	import re
	switches['xfer']='sin'
	fnn=re.compile("(\d+).*\.((raw)|(mdat)|(mien))")
	for f in aosfiles:
		if fnn.match(f):
			num=fnn.match(f).group(1)
			mnn=re.compile(num+".*\.((bin)|(mdat)|(mien))")
			for m in mffiles:
				if mnn.match(m):
					break
			mfn=os.path.join(fn[1], m)
			if os.path.isfile(mfn):
				print "processing file %s" % f
				try:
					process([os.path.join(fn[0], f), mfn], switches)
				except:
					print "error while processing %s" % f
					import traceback
					e= sys.exc_info()
					apply(traceback.print_exception, e)
			else:
				print "file %s has no corresponding stimulus data?? Skipping it." % f
		else:
			print "skipping file %s" % f		

def testme(fn, sw):
	print "No tests are currently implemented"
	

## --------------- CLI (interface) -------------------

usage='''Usage:
python batch.py [options] -l L video.raw microflown.bin

fname.raw needs to be a path to an AOS raw video generated by an 8 bit greyscale camera. 
L is the mean distance from the fulcrum point to the illumination point
The units of L should be in Nikon 4x image pixels
microflown.bin is a streamer file containing the recorded output of the microflown sensor

REQUIRED OPTIONS:	
-l # --  # is the distance from fulcrum to light as described above

GENERAL OPTIONS:

-m # -- channel index of the channel in microflown.bin that contains the microflown data. 
	Default is 2 (this third channel, since python counts 0,1,2 ...)
-f fname -- name of a file containing additional parameters (for example one written by the MIEN 
	gicaos block's findangle.writeParameterFile function )
-t  -- run unit tests rather than main script 
-w  # -- filter width in pixels (default is 5)
-h    -- help

IMAGE CROPPING AND CONDITIONING OPTIONS:

NOTE: writeParameterFile will assign approprite values to these parameters, so if you us that function, 
you should specify -f nameofparameterfile, and you won't need to specify these.

--startframe # -- start processing video frame # (default 0)
--nframes #    -- process only # frames. Values less than 1 indicate that all frames (from
	startframe to the end of the file) should be used. Default is end of file. Specifying a value larger 
	than the file size is not an error, but only the available frames will be processed.
--xmin #
--xmax #
--ymin #
--ymax # -- specify the bounding box of the region of interest. Unspecified "min" parameters default to 
	0, and "max" parameters default to the full size of the image.
--rotate # -- rotate the images # degrees counterclockwise before processing. Default is 0. The image 
	extraction algorithm assumes that the hair image is oriented vertically, so if it is not, you will 
	need to specify this value to correct it. 
--subtract_mean  -- if specified, remove the temporal mean of the image stack before processing. This 
	significantly improves contrast for non-rotated images, but may behave unexpectedly for rotated ones.
	
OUTPUT OPTIONS:

--use_angles fname -- if specified, load the raw angle/time data from fname, rather than reading video.
		If this is passed, you don't need to pass -l or any file names
	
--raw_angles fname -- write the raw angle/time data to file fname. Default is "batch_angles.txt"
--xfer_file  fname -- write the transfer function info to fname. Default is "batch_xfer.txt" ignored if 
	--xfer is not also specified.
--xfer mode		   -- calculate	transfer function information. Mode determines how it is calculated.
	mode=sin  -> calculate one gain and phase for sine wave data
	mode=wn   -> calculate an entire transfer function using fourier methods from white noise data. 
	mode=many -> attempt to calculate an entire transfer function from many sine wave inputs. 
		This requires that the input file names are actually directories, and that for each file in 
		the first directory there is a file with the same base name in the second. Also, of course, 
		all the files must use the same data conditioning parameters. If they don't, use many runs with 
		"sin". Each run will concatenate one point onto the xfer function file.
--xfer_freq  freq  -- calculate gain and phase from sine wave data while specifying the frequency of the 
	sine wave. Ignored if --xfer sin is not specified; no default.

example:
./batch.py -l 838 -f batch_parameters.txt --xfer sin 040.raw 40_1.bin
 '''

option_dtypes={
	'l':float,
	'startframe':int,
	'nframes':int,
	'xmin':int,
	'xmax':int,
	'ymin':int,
	'ymax':int,
	'rotate':float,
	'w':int,
	'm':int
}


default_options={
	'm':2,
	'w':5,
	'nframes':-1,
	'raw_angles':"batch_angles.txt",
	'xfer_file': "batch_xfer.txt"
}

def parse_options(l,switches):
	try:
		options, files = getopt.getopt(l, "hw:l:m:f:t", ['startframe=', 'nframes=', 'xmin=', 'xmax=', 'ymin=', 'ymax=', 'rotate=', 'raw_angles=', 'xfer_file=', 'xfer=', 'xfer_freq=', 'subtract_mean', 'use_angles='])
	except getopt.error:
		print("Options not recognized. Try -h for help")
		sys.exit()
	for o in options:
		if o=='-h':
			print usage
			sys.exit()
		switches[o[0].lstrip('-')]=o[1]
	return (switches, files)


def getParams():
	switches, files= parse_options(sys.argv[1:],default_options.copy())
	if switches.has_key('f'):
		os=open(switches['f']).read()
		s2, f2 = parse_options(os.split(),switches)
		f2=[f for f in f2 if f]
		switches.update(s2)
		files.extend(f2)
	for o in switches.keys():
		if option_dtypes.has_key(o):
			switches[o]=option_dtypes[o](switches[o])
	if 't' in switches.keys():
		testme(files, switches)
		sys.exit()
	if not switches.has_key('use_angles') and (not switches.has_key('l') or len(files)<2):
		print usage
		sys.exit()
	return (files, switches)
	
					
if __name__=='__main__':
	fn, sw = getParams()
	if sw.get('xfer')=='many':
		batch_process(fn, sw)
	else:
		process(fn, sw)
	
	
	
	
	
	
	
