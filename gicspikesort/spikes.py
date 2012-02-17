
## Copyright (C) 2005-2006 Graham I Cummins
## This program is free software; you can redistribute it and/or modify it under 
## the terms of the GNU General Public License as published by the Free Software 
## Foundation; either version 2 of the License, or (at your option) any later version.
## 
## This program is distributed in the hope that it will be useful, but WITHOUT ANY 
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
## PARTICULAR PURPOSE. See the GNU General Public License for more details.
## 
## You should have received a copy of the GNU General Public License along with 
## this program; if not, write to the Free Software Foundation, Inc., 59 Temple 
## Place, Suite 330, Boston, MA 02111-1307 USA
## 

from mien.datafiles.dataset import *



def _assignEvents(evts, data, dpath, lab):
	ed=data.getSubData(dpath)
	if ed==None:
		data.createSubData(dpath, evts, {'Name':lab, 'SampleType':'events', 'SamplesPerSecond':data.fs(), 'Labels':[lab]})
		return
	if isSampledType(ed)!='e' or ed.fs()!=data.fs():
		print ed.header(), isSampledType(ed), ed.fs()!=data.fs()
		raise StandardError('Attempt to assign events to a data element that exists, but does not support storing these events')	
	head=ed.header()
	old=ed.getData()
	if ed.stype()=='events':
		head['SampleType']='labeledevents'
		old=concatenate([old, zeros(old.shape, old.dtype)], 1)
	id=old[:,1].max()+1
	evts = reshape(evts, (-1, 1))
	evts=concatenate([evts, ones(evts.shape, evts.dtype)*id], 1)
	if not evts.dtype==old.dtype:
		evts=evts.astype(old.dtype)
	evts = concatenate([old, evts])
	lab=ed.getLabels()+[lab]
	head["Labels"]=lab
	ed.datinit(evts, head)

def _peak_find(wd, tol):
	'''find the unique maxima in wd. Tol is a fraction that determines how many are found'''
	me=median(wd)
	st=std(wd)
	ma=max(wd)
	ut=ma-(ma-me)*tol
	lt=me+st
	if lt>=ut:
		raise StandardError("Data are too noisy for automatic detection")
	if lt<ma-2*(ma-me)*tol:
		lt=ma-2*(ma-me)*tol
	ready=False
	trig=False
	pmv=(0,0)
	cut=nonzero1d(logical_and(shift(wd,1)<ut, wd>=ut))
	clt=nonzero1d(logical_and(shift(wd,1)>=lt, wd<lt))
	close=-1
	evts=[]
	for i in cut:
		if i<close:
			continue
		close=nonzero1d(clt>i)
		if close.shape[0]==0:
			evts.append(argmax(wd[i:])+i)
			break
		close=clt[close[0]]
		si=argmax(wd[i:close])+i
		evts.append(si)
	return evts	

def _splitLabeledEvents(evts):
	labs=evts.getLabels()
	dat=evts.getData()
	ll=dat[:,1].max()+1
	if not ll==len(labs):
		print str(evts)+" has the wrong number of labels."
		labs=["ec%i" % i for i in range(ll)]
	ed={}
	for i in range(ll):
		n=labs[i]
		e=take(dat[:,0], nonzero1d(dat[:,1]==i))
		ed[n]=e
	return ed	

def _blockShift(ds, temp):
	dat=ds.getData()
	for i in range(temp.shape[0]):
		s=temp[i]
		s=int(s)
		if s>0:
			#FIXME: "array" in the next line is bug-compatible with numpy 1.04. It should be removed when the numpy bug is fixed
			bit = copy(dat[-s:,i])
			dat[s:,i]=array(dat[:-s,i])
			dat[:s,i]=bit
		elif s<0:
			s=abs(s)
			print s, i
			bit = copy(dat[:s,i])
			dat[:-s,i]=dat[s:,i]
			dat[-s:,i]=bit

def _writeShifts(ds, dpath, temp, select=None, rel=True):
	temp=reshape(temp, (-1,1))
	h={'SampleType':'generic','ValuesAreTimes':False}
	if select:
		h['fromSelection']=repr(select)
	if not rel:
		n=ds.createSubData(dpath, temp, h, delete=True)	
	else:
		tem=ds.getSubData(dpath)
		try:
			od=tem.getData()		
			tem.setData(od+temp)	
			print 'updated template'
		except:
			n=ds.createSubData(dpath, temp, h, delete=True)
				
def _applyShifts(ds, temp, select):
	if select==(None, None, None):
		_blockShift(ds, temp)
	else:
		dat=getSelection(ds, select)
		q=dat.copy()
		for i in range(temp.shape[0]):
			q[:,i]=shift(dat[:,i], temp[i])
		setSelection(ds, q, select)		


def _spikeAssign(ds, newpath, evts, select, labs):
	if labs in [None, False]:			
		labs=getSelectionHeader(ds, select)
		labs=["%s - Spikes" % (foo,)  for foo in labs["Labels"]]
	h=getSelectionHeader(ds, select)
	start=h.get('StartTime', 0)
	if start:
		start=round(start*h.get('SamplesPerSecond', 1))
	for ec in evts.keys():
		if len(evts[ec]):
			e=array(evts[ec])
			if start:
				e+=start
			_assignEvents(e, ds, newpath, labs[ec])
			
			
def schmitTrigger(ds, thresh1, thresh2, select=(None, [0], None), newpath='/spikes', above=True, labs=None):
	'''Apply a shmidt dual thresholding scheme to the selected data, generating 
events. The events are stored in a subdata element with the indicated dpath. If 
that element exists and is of an event type, the events are added as a new 
labeledevents channel. Otherwise, a new events element is created. If select 
specifies multiple channels, this will be a labeledevents element. 

"above" determines the direction of the threshold. If it is False, detect minima

Note that if select specifies a subdata element, and dpath does not begin with 
"/" it is interpreted relative to the element specified by select.

SWITCHVALUES(above)=[True, False]
'''
	dat =getSelection(ds, select)
	if not above:
		dat=dat*-1
		thresh1*=-1
		thresh2*=-1
	ht=max(thresh1, thresh2)
	lt=min(thresh1, thresh2)
	evts = {}
	for i in range(dat.shape[1]):
		cd=dat[:,i]
		evts[i]=[]
		hit=nonzero1d(cd>ht)
		if len(hit)==0:
			continue
		fcross=take(hit, nonzero1d((hit-shift(hit, 1))!=1))
		evts[i].append(hit[0])
		for j in range(1, fcross.shape[0]):
			if any(cd[fcross[j-1]:fcross[j]]<lt):
				evts[i].append(fcross[j])
	_spikeAssign(ds, newpath, evts, select, labs)

	# evt = ds.getSubData(newpath)
	# if not above:
	# 	thre = [lt*-1, ht*-1, -1]
	# else:
	# 	thre = [lt, ht, 1]
	# evt.setAttrib('thresholds', thre)  
	# if fnameSave:
	# 	from mien.parsers.fileIO import write
	# 	write(evt, fnameSave, newdoc=True)
	
def localSchmidt(ds, highThresholdProportion=.4, safetyProportion=.1, select=(None, [0], None), window=1.0, newpath='/spikes', above=True, labs=None):
	'''Apply a schmidt trigger detection to each sequential (tiled) window of length "window" (in seconds) in the data specified by "select". The thresholds are set such that the higher threshold is "highThesholdProportion" of 
the range between the mean and the max of the local window above the mean, and the low threshold is "safetyProportion" of this range less than the high threshold. Other parameters are as for schmidtTrigger.
	SWITCHVALUES(above)=[True, False]
	'''
	dat =getSelection(ds, select)
	h = getSelectionHeader(ds, select)
	if not above:
		dat=dat*-1
	evts = dict([(i, []) for i in range(dat.shape[1])])
	off = 0
	wlen = int(window*h['SamplesPerSecond'])
	frange = dat.max(0) - dat.mean(0)
	stagger = int(.1*window*h['SamplesPerSecond'])
	while off < dat.shape[0] -1:
		ldat = dat[off:off+wlen+stagger]
		for i in range(dat.shape[1]):
			cd=ldat[:,i]
			dmean = cd.mean()
			dr = cd.max() - dmean
			if dr < frange*.01:
				print "This window looks blank. Skipping it"
				continue
			ht = dmean + highThresholdProportion*dr
			lt = ht - safetyProportion*dr
			hit=nonzero1d(cd>ht)
			if len(hit)==0:
				continue
			if not evts[i]:
				lgot = -1
			else:
				lgot = evts[i][-1]+1
			if hit[0]+off > lgot:
				if any(ldat[lgot:hit[0]+off, i]) < lt:
					evts[i].append(hit[0]+off)
			fcross=take(hit, nonzero1d((hit-shift(hit, 1))>1))
			for j in range(1, fcross.shape[0]):
				if fcross[j]+off <= lgot:
					continue
				if any(cd[fcross[j-1]:fcross[j]]<lt):
					if evts[i] and fcross[j]+off < evts[i][-1]+5:
						print j, lgot, off
					evts[i].append(fcross[j]+off)
		off+=wlen
	e = array(evts[0])
	z = e[1:] - e[:-1]
	if any(z <=1):
		print "WTF"
		raise(StandardError("Negative Index Exception"))
	_spikeAssign(ds, newpath, evts, select, labs)	
	
def peakDetect(ds, thresh, select=(None, [0], None), newpath='/spikes', labs=None):
	'''
	Detect spikes, finding the index of the actual extremum, rather than the index of a threshold crossing. Uses a single threshold, and assumes that the data begins and ends on the "non-event" side of the threshold, so if the threshold is less than the first data point, event minima are detected, and otherwise event maxima are detected. 	
	'''
	dat =getSelection(ds, select)
	evts = {}
	if dat[0]>thresh:
		argop = argmin
		if dat[-1]<=thresh:
			raise StandardError("The start and end of the data stream must be on the same side of the threshold.")
	else:
		argop = argmax
		if dat[-1]>thresh:
			raise StandardError("The start and end of the data stream must be on the same side of the threshold.")
	for i in range(dat.shape[1]):
		cd=dat[:,i]
		evts[i]=[]
		hit=(cd>thresh)
		shifthit = shift(hit, 1)
		cross=nonzero1d(hit!=shifthit)
		if len(cross)==0:
			continue
		cross = reshape(cross, (-1, 2))
		for j in range(cross.shape[0]):
			k = argop(dat[cross[j, 0]:cross[j,1]])
			evts[i].append(cross[j,0]+k)
	_spikeAssign(ds, newpath, evts, select, labs)
	
def spikeStats(ds, dpathSpikes = "/spikes", select=(None, [0], None), newpath="/spikestats", maxlength = .01):
	'''Calculate the min value, subsequent max value, relative time of return to mean, and time between min and max for extracellular spikes stored in dpathSpikes, drawn from data stored at select. Uses only the first channel of select, so select should specify one channel, and dpathSpikes should specify non-labeled events'''
	dat =getSelection(ds, select)
	h = getSelectionHeader(ds, select)
	fs = float(h['SamplesPerSecond'])
	spikes = ds.getSubData(dpathSpikes).getData()
	od = ones((spikes.shape[0], 5))*-1
	meanv = dat[:,0].mean()
	maxlength = int(round(maxlength*fs))
	for i in range(spikes.shape[0]):
		si = spikes[i]
		t = si/fs
		od[i,0] = t
		od[i,1]= dat[si, 0]-meanv
		maxind = si + maxlength
		if maxind>=dat.shape[0]:
			maxind = dat.shape[0]-1
		if i < spikes.shape[0]-1 and spikes[i+1]-1< maxind:
			maxind = spikes[i+1]-1
		dseg = dat[si:maxind]
		mc = nonzero1d(dseg>=meanv)
		if mc.shape[0]:
			od[i, 2] = mc[0]/fs
		else:
			print('warning: no mean crossing for event %i' % i)
		maxi = argmax(dseg)
		od[i,3] = dseg[maxi]-dat[si, 0]
		maxi+=si
		od[i, 4] =  maxi/fs - t	
		if od[i, 1]>=0 or od[i,3]<0:
			print i, od[:,i]
			raise StandardError('relative values do not have the correct sign')	
	head={'SampleType':"Function", 'Labels':['time', 'minval', 'dtmean', 'maxval', 'dtmax'] }
	ds.createSubData(newpath, od, head, True)	

def _exactmin(dat, si,rng):
	'''
	Interpolates on the first local minimum within si-range/2:si+range/2
	'''
	rng = round(rng/2)
	derivs = cdiff(dat[si-rng:si+rng])
	try:
		zcross = diff(sign(derivs))
		zcrossinds = argmax(zcross)
		d1, d2 = derivs[zcrossinds:zcrossinds+2]
		tao=d1/(d1-d2)
		if tao <0 or tao > 1:
			raise StandardError()
	except:
		print "maxslope", si, derivs, zcross
		return (None, None)
	x = zcrossinds+tao-rng   
	y = dat[si-rng+zcrossinds]+tao*d1
	return (x, y)	
		
def _maxslope(dat, si, rng):
	'''
	finds the first max slope
	'''
	rng = round(rng/2)
	fderivs = cdiff(dat[si-rng:si+rng])
	sderivs = cdiff2(dat[si-rng:si+rng])
	print('t2.1')
	try:
		zcross = diff(sign(sderivs))
		zcrossinds = argmax(zcross)
		d1, d2 = sderivs[zcrossinds:zcrossinds+2]
		tao=d1/(d1-d2)
		print('t2.2')
		if tao <0 or tao > 1:
			raise StandardError()
	except:
		y = max(fderivs)
		x = argmax(fderivs)-rng
		print('t2.3')
		return (x, y)
	x = zcrossinds+tao-rng   
	y = dat[si-rng+zcrossinds]+tao*fderivs[zcrossinds]
	print('t2.3')
	return (x, y)			
		
def spikeStats2(ds, 	dpathSpikes = "/spikes", select=(None, [0], None), newpath="/spikestats2", maxlength = .0005):
	'''Similar to spikeStats, but generates somewhat different statistics. The region of length "maxlength" following an event is searched for a point of maximal positive slope. This point, rather than the mean, is used as a reference for reporting the length and amplitude of the spike. There are four output statistics, the first column being time of occurrence, the second being the value of the minimum (note that these are slightly different than the versions measured in spikeStats, as described below), the third being the half width (measured as the time from the occurrence of the min to the occurrence of the slope max), and the last being the amplitude, estimated as the difference between the y value corresponding at the maximal slope and the Y value at the min. 

Unlike the reference points used in spikeStats, the positions of the minimum and the max max slope are NOT constrained to be the locations of actual sample points. Instead, the locations are found by fitting models. The minimum is found by linear approximation to the zero of the first derivative, and the maximum slope is found by fitting a quadratic model to the points around the minimum. This model is fit to 2*filtwidth-1 points, centered on the previously identified minimum. 
	'''
	dat =getSelection(ds, select)
	h = getSelectionHeader(ds, select)
	fs = float(h['SamplesPerSecond'])
	searchrng = fs*.5e-3
	spikes = ds.getSubData(dpathSpikes)
	ss = spikes.start()
	spikes=spikes.getData()[:,0]
	sa = h['StartTime']
	offset = sa-ss
	if offset:
		offset = int(round(offset*fs))
		spikes = spikes - offset
	od = ones((spikes.shape[0], 4))*-1
	maxlength = int(round(maxlength*fs))
	for i in range(spikes.shape[0]):
		si = spikes[i]
		if si < searchrng/2 or si > dat.shape[0] - searchrng/2:
			print('spike %i is too close to the edge of the data set. Skipping it' % i)
			continue
		xm, ym = _exactmin(dat[:,0], si, searchrng)
		if xm == None:
			print('spike %i is not at a minimum' % i )
			continue
		xm = xm/fs
		rise = dat[si:si+maxlength,0]
		mpr = argmax(cdiff(rise))
		print('time2')
		xs, ys = _maxslope(dat[:,0], si+mpr, (si-mpr)*2)
		print('time3')
		if xs == None:
			print('spike %i does not have a clear max slope' % i )
			continue
		xs = xs/fs
		od[i,0] = xm
		od[i,1]= ym
		od[i,2]= xs - xm
		od[i,3]= ys - ym 
	head={'SampleType':"Function", 'Labels':['time', 'minval', 'halfwidth', 'amplitude'] }
	ds.createSubData(newpath, od, head, True)	

		
	

def _topEvt(dat, tr):
	if dat.max()<=tr:
		return None
	e = argmax(dat)
	bi = e
	while dat.shape[0]-1>bi and dat[bi]>tr:
		dat[bi] = tr
		bi+=1
	bi = e -1
	while bi>=0 and dat[bi]>tr:
		dat[bi] = tr
		bi-=1
	return e	

def topNSpikes(ds, threshReset, nSpikes, select=(None, [0], None), newpath='/spikes', above=False, labs=None):
	'''Operates similarly to schmitTrigger, but only detects the "nSpikes" (integer) strongest events. The specified threshReset is used as the reset threshold for detection, meaning that at most one event can be detected between one crossing of threshReset and the next. There is no detection threshold, however. First, the single strongest event is detected, and then the next strongest, until a total of  nSpikes are collected (or until no new events are crossing even threshReset. The effect is similar to using a set of progressively decreasing detection thresholds with a typical trigger, and stopping the threshold reduction manually, but in this case the search is automatic. Arguments select, newpath, above, and labs work as for schmitTrigger. Since this sort of analysis is usually used on extracellular recordings, the default value of "above" is False.

SWITCHVALUES(above)=[False, True]	
	'''
	dat =getSelection(ds, select)
	if not above:
		dat=dat*-1
		threshReset*=-1
	evts = {}
	for i in range(dat.shape[1]):
		cd=dat[:,i].copy()
		evts[i]=[]
		while len(evts[i])<nSpikes:
			e  = _topEvt(cd, threshReset)
			if e == None:
				break
			evts[i].append(e)
	_spikeAssign(ds, newpath, evts, select, labs)


def tsToEvents(ds, select=(None, None, None), newpath='/spikes'):
	'''Creates a set of events from a time series containing only 
zeros and ones. If used on a general time series, this will produce an
event for every non-zero sample.'''
	dat =getSelection(ds, select)
	evts = {}
	for i in range(dat.shape[1]):
		evts[i]=nonzero1d(dat[:,i])
	labs=getSelectionHeader(ds, select)
	labs=["%s - Spikes" % (foo,)  for foo in labs["Labels"]]
	for ec in evts.keys():
		_assignEvents(array(evts[ec]), ds, newpath, labs[ec])

def bidirectionalThreshold(ds, select=(None, [1], None), thresh=.5, newpath='/ttl'):
	'''Creates a labeled event set where event type 0 is all the positive-going crossings of thresh, and event type 1 is the negative going ones. If select has several channels, event type 2*i will be channel i on, and 2*i+1 will be channel i off.'''
	dat =getSelection(ds, select)
	evts = {}
	for i in range(dat.shape[1]):
		gt = dat[:,i]>=thresh
		pc = nonzero1d(gt[1:]>gt[:-1])+1
		evts[2*i]=pc
		nc = nonzero1d(gt[1:]<gt[:-1])+1
		evts[2*i+1]=nc
	h=getSelectionHeader(ds, select)
	labs = []
	for foo in h["Labels"]:
		labs.append("%s - on" % (foo,))
		labs.append("%s - off" % (foo,))
	_spikeAssign(ds, newpath, evts, select, labs)


def eventHistogram(ds, dpath='/', newpath='/hist', filterWidth=.0005):
	ed = ds.getSubData(dpath)
	fs = ed.fs()
	start = ed.start()
	dat = ed.getData()
	mv = dat[:,0].max()+1
	etags = unique1d(dat[:,1])
	events = [dat[dat[:,1]==i,0] for i in etags]
	hist = zeros(mv)
	for e in events:
		hist[e]+=1
	fw = int(round(filterWidth*fs))
	if fw > 1:
		hist = convolve(hist, ones(fw), 'same')
	ds.createSubData(newpath, hist, {"SampleType":"timeseries", "SamplesPerSecond":fs, "StartTime":start})		
			
def tsFromEvents(ds, dpath='/spikes', newpath='/binarytimeseries'):
	'''Creates a time series of ones and zeros, with ones at the locations 
of each event in dpath. If newpath exists, this sequence will be appended
to that timeseries data. Otherwise a new sub data element will be created'''
	d=ds.getSubData(newpath)
	e=ds.getSubData(dpath)
	if d and not d.noData():
		l=d.shape()[0]
		s=d.start()
	else:
		l=None
		s=e.start()	
	ts=events2ts(e, l, s)
	if d:
		d.addChans(ts)
	else:
		head={'SampleType':"timeseries"}
		head['SamplesPerSecond']=e.fs()
		head['StartTime']=e.start()
		ds.createSubData(newpath, ts, head)
	
def combine(ds, events, newpath='/compoundEvents', newtype='labeledevents', delete=False):
	'''Make a new data element with path "newpath" containing the event records 
from the elements in "events" (this is a list of strings specifying the dpaths 
of the events). 'newtype' determines what sort of element is created, and can be
histogram, labledevents, or events (if it is events, the identities of the 
separate event elements wil be lost). If 'delete' is true, the selected event 
elements will be removed after they are added to the new element.
SWITCHVALUES(newtype)=['events', 'labeledevents', 'histogram']
SWITCHVALUES(delete)=[False, True]
''' 	
	evts=[ds.getSubData(e) for e in events]
	for e in evts:
		if not e.fs()==ds.fs():
			raise StandardError("can't combine events with different sampling rates")
	h={'SamplesPerSecond':ds.fs()}		
	if newtype=='histogram':
		h['Labels']=['compiled events']
		h['SampleType']='histogram'
		h['binwidth']=1
		h['StartTime']=ds.start()
		l=ds.shape()[0]
		s=ds.start()
		dat=None
		for q in evts:
			qd=events2ts(q, l, s)
			if qd.shape[1]>1:
				qd=sum(qd, 1)
			if dat==None:
				dat=qd
			else:
				dat+=qd
	else:
		evtd={}
		for e in evts:
			if e.shape()==(0,0):
				print "%s contains no data. Skipping it" % (str(e),)
				continue
			if e.stype()=='labeledevents':
				d= _splitLabeledEvents(e)
			else:
				d={e.getLabels()[0]:e.getData()}
			for k in d.keys():
				k2="%s - %s" % (e.name(), k)
				i=2
				while evtd.has_key(k2):
					k2="%s(%i)" % (e.name(), i)
					i+=1
				evtd[k2]=d[k]
		if newtype=='events':
			h['Labels']=['compiled events']
			h['SampleType']='events'
			q=evtd.values()
			dat=q[0]
			for qe in q[1:]:
				dat=concatenate([dat, qe])
			dat=unique1d(dat)
		else:			
			h['SampleType']='labeledevents'
			dat=None
			evtdk=evtd.keys()
			evtdk.sort()
			h['Labels']=evtdk
			for i, k in enumerate(evtdk):
				#print i, k
				e=reshape(evtd[k], (-1, 1))
				l=ones(e.shape, e.dtype)*i
				d=concatenate([e,l],1)
				if dat==None:
					dat=d
				else:
					dat=concatenate([dat,d])
	if ds.getSubData(newpath):
		print 'Selected Path Exists. Deleting it'
		sd=ds.getSubData(newpath)
		sd.sever()
	ds.createSubData(newpath, dat,h)
	if delete:
		for sd in evts[:]:
			sd.sever()


def alignMinima(ds, selectSearch=(None, None, None), selectApply=(None, None, None), newpathTemplate=False):
	'''Create a template that would timeshift all the channels in the 
selectSearch so that their minima occur at the same time. 

If selectApply is not False, shift the channels in this data region according to 
the template. 

If newpathTemplate has a true value, the norm template will be saved to that 
dpath. If there is already a data elemnt there, it will be ammended (it's values
will be multiplied by the new template)

(Note that if selectApply and newpathTemplate are both False, this funcion does 
nothing other than generate heat and benchmarking numbers :)
'''
	dat=getSelection(ds, selectSearch)
 	temp=zeros(dat.shape[1], Int32)
	for i in range(dat.shape[1]):
		temp[i]=argmin(dat[:,i])
	temp=-1*(temp-temp[0])
	print temp
	if newpathTemplate:
		_writeShifts(ds, newpathTemplate, temp, selectSearch)
	if selectApply:
		_applyShifts(ds, temp, selectApply)


def linearShift(ds, ns, select=(None, None, None), newpathTemplate=None):
	'''Shift data in select such that the channels are offset by ns samples
each'''
 	dat=getSelection(ds, select)
 	temp=arange(dat.shape[1])*ns
	if newpathTemplate:
		_writeShifts(ds, newpathTemplate, temp)
	_applyShifts(ds, temp, select)


def icDetrend(ds, select=(None, [0], None), ws=.030):
	'''Attempt to condition an intracellular spike waveform for easier threshholding (by removing drift and amplification changes. Ws is a time window parameter is seconds. Smaller ws provides finer grained detrending, but is more likely to damage actual spike data. Select should specify one channel.'''
	ws=round(ws*ds.fs())
	dat=getSelection(ds, select).copy()
	nwin, left=divmod(dat.shape[0], ws)
	all=reshape(dat[left:], (nwin, ws))
	shi=-1*median(transpose(all))
	shi=array_resample(shi, ws, 1)
	if left:
		shi=concatenate([ones(left)*shi[0], shi])
	dat=dat+shi[:,NewAxis]
	ws=4*ws
	nwin, left=divmod(dat.shape[0], ws)
	all=reshape(dat[left:], (nwin, ws))
	me=median(transpose(all))
	ma=all.max(1)
	sca=1.0/(ma-me)
	sca=array_resample(sca, ws, 1)
	if left:
		sca=concatenate([ones(left)*sca[0], sca])			
	dat=dat*sca[:,NewAxis] 	
	setSelection(ds, dat, select)	
		
		
def localPeakFind(ds, select=(None, [0], None), ws=0.04, tol=.5, newpath="/spikes"):
	'''Smarter (but slower) spike detection. Should not be confused by drifting baseline and amplitude. ws=window size, tol = fraction of peak amplitute (eg .5 detects events that are at least .5x as strong as the largest event.'''
	dat=ds.getSubData(select[0])
	ws=round(ws*dat.fs())
	st=round(dat.start()*dat.fs())
	dat=getSelection(ds, select)
	ind=0
	evts=[]
	while ind<dat.shape[0]:
		wd=dat[ind:ind+ws]
		e=_peak_find(wd, tol)
		evts.extend(list(array(e)+ind+st))
		ind+=ws
	if evts:
		evts=array(evts)
		_assignEvents(evts, ds, newpath, 'spikes')


	
	

#from mien.dsp.targetdata import SPIKE10_3,BLANKSPIKE
# 
# #========================Spike Detection=========================
# 
# def quickECThreshold(a, tv):
# 	'''a is 1D, tv is a percentage of the global min. Use on extracellular data'''
# 	t1=a.mean()
# 	ex=a.min()
# 	ex=ex-t1
# 	tv=(100-tv)/100.0
# 	t2=t1+ex*tv
# 	hist=shift(a, 1)
# 	bthresh=(a<=t2)
# 	athresh=(hist>=t2)
# 	cross=nonzero(athresh*bthresh)
# 	return cross
# 	
# 
# def single_stddev_threshold(a, p):
# 	chan=a.astype(Float64)
# 	mean=sum(chan)/len(chan)
# 	sumsqdif=sum(chan**2)/len(chan)
# 	std=(sumsqdif-mean**2)**.5
# 	return [mean+p*std]
# 
# def single_percent_threshold(a, p):
# 	chan=a.astype(Float64)
# 	maxi=max(chan)
# 	mini=min(chan)
# 	p=(p/100.0)*(maxi-mini)
# 	return [maxi-p]
# 
# def double_percent_threshold(a, p1, p2):
# 	chan=a.astype(Float64)
# 	mean=sum(chan)/len(chan)
# 	maxi=max(chan)
# 	mini=min(chan)
# 	p1=(p1/100.0)*(maxi-mean)
# 	t1=maxi-p1
# 	p2=(p1/100.0)*(mean-mini)
# 	t2=mini+p2
# 	return [t1, t2]
# 
# def double_stddev_threshold(a, p1, p2):
# 	chan=a.astype(Float64)
# 	c1=chan*(chan>=0)
# 	mean=float(sum(c1))/len(nonzero(c1))
# 	sumsqdif=sum(c1**2)/len(nonzero(c1))
# 	std=(sumsqdif-mean**2)**.5
# 	t1= mean+(p1*std)
# 	c2=chan*(chan>=0)
# 	mean=float(sum(c2))/len(nonzero(c2))
# 	sumsqdif=sum(c2**2)/len(nonzero(c2))
# 	std=(sumsqdif-mean**2)**.5
# 	t2= mean+(p2*std)
# 	return [t1, t2]
# 
# 
# def detectAbove(a, thresh, eventlength=5):
# 	thresh=thresh[0]
# 	ismore=greater_equal(a,thresh)
# 	isless=less(a,thresh)
# 	poscross= nonzero(logical_and(ismore[1:],isless[:-1]))
# 	return poscross
# 
# def detectBelow(a, thresh, eventlength=5):
# 	thresh=thresh[0]
# 	ismore=greater_equal(a,thresh)
# 	isless=less(a,thresh)
# 	negcross= nonzero(logical_and(isless[1:],ismore[:-1]))
# 	return negcross	
# 
# 
# 
# def detectAcross(a, thresh, eventlength=5):
# 	ht=max(thresh)
# 	lt=min(thresh)
# 	pc=detectAbove(a, [ht], eventlength)
# 	nc=detectBelow(a, [lt], eventlength)
# 	rc=[]
# 	for e in pc:
# 		try:
# 			e2=nonzero(abs(nc-e)<=eventlength)[0]
# 			#rc.append(e)
# 			rc.append(int(round((e+nc[e2])/2.0)))
# 		except:
# 			pass
# 	return array(rc)
# 
# def detectMaxBetween(a, thresh, eventlength=5):
# 	ht=max(thresh)
# 	lt=min(thresh)
# 	be=detectAbove(a, [lt], eventlength)
# 	tb=detectAbove(a, [ht], eventlength)
# 	rc=[]
# 	for e in be:
# 		if nonzero(abs(tb-e)<=eventlength):
# 			continue
# 		rc.append(e)
# 	return array(rc)
# 
# def detectMinBetween(a, thresh, eventlength=5):
# 	#print eventlength
# 	ht=max(thresh)
# 	lt=min(thresh)
# 	be=detectBelow(a, [ht], eventlength)
# 	tb=detectBelow(a, [lt], eventlength)
# 	rc=[]
# 	for e in be:
# 		if nonzero(abs(tb-e)<=eventlength):
# 			#print "%i near %i" % (e, tb[nonzero(abs(tb-e)<=eventlength)[0]])
# 			continue
# 		#print "found %i" % e
# 		rc.append(e)
# 	return array(rc)
# 		
# def difference_detect(a, thresh, eventlength=5, method=detectAbove):
# 	diff=a-concatenate((a[:eventlength], a[:-eventlength]))
# 	thresh=single_stddev_threshold(diff, 2)
# 	times=method(diff, thresh, eventlength)
# 	return times
# 
# 	
# threshold_alg_dict={"Std Dev (single)":single_stddev_threshold,
# 					"Max (single)":single_percent_threshold,
# 					"Std Dev (double)":double_stddev_threshold,
# 					"Max (double)":double_percent_threshold}
# 
# spikefind_alg_dict={"Above": detectAbove,
# 					"Below": detectBelow,
# 					"Schmit Above": detectSchmit,
# 					"Max between": detectMaxBetween,
# 					"Min Between": detectMinBetween,
# 					"Above and Below": detectAcross}
# 
# 
# #Spike Analysis =======================
# 
# def getSpikeError(d, target=SPIKE10_3):
# 	'''d is a dict of the sort returned by getSpikeStats, and opitonally
# a second dict containing an "ideal" spike. The second argument defaults to
# the internal constant SPIKE10_3 defined in the module mien.ga.targetdata.
# Returns a single float that is an error measure between d and target.'''
# 	e=0
# 	if d.has_key("N"):
# 		if d["N"]==0:
# 			d=BLANKSPIKE
# 			e+=1000
# 		else:
# 			e+1000*(d["N"]-1)
# 			del(d["N"])	
# 	for k in target.keys():
# 		if k=='wave':
# 			em=(target[k]-d[k])**2
# 			em=em.sum()
# 			skm=target[k]**2
# 			skm=skm.sum()
# 			em=em/skm
# 			e+=em
# 		elif k in ['t']:
# 			continue
# 		else:
# 			em=(target[k]-d[k])**2/target[k]**2
# 			e+=em
# 	return e
# 
# def getExtraSpikeStats(dat, fs, evts):
# 	'''dat (1d array), fs(float), evts(array of ints)=>dict
# 	Input is data, resting potenial, sampling rate, and an array of
# 	indeces into data at which spikes occur.
# 	Returns a list of dicts (one for each spike) containing:
# 		"t":time of occurence of the min of the spike (float)
# 		"size":The minimum voltage
# 		"width":the width of the negative wave (between zero crossings) 
# 		"lmax":the max before the negative phase
# 		"rmax":the max after the negative phase
# 		"mwidth":the time between lmax and rmax
# 		"sym":the fraction of the time between flanking zero crossings
# 		      at which the minimum occurs
# 		"wave":the spike waveform, resampled to 50KHz. The wave is
# 		       200 samples (4 ms) long, with the minimum at sample 100
# 			   '''
# 	spms=int(fs/1000)
# 	spst=[]
# 	for evt in evts:
# 		if dat.shape[0]-evt<spms*2:
# 			continue
# 		d={}
# 		mi=argmin(dat[evt:evt+spms])+evt
# 		d['t']=float(mi)/fs
# 		if fs==50000:
# 			d['wave']=dat[mi-100:mi+100]
# 		else:
# 			wave=dat[mi-2.1*spms:mi+2.1*spms]
# 			wave=array_resample(wave, 1.0/fs, 1.0/50000)
# 			mi=argmin(wave)
# 			d['wave']=wav[mi-100:mi+100]
# 		wav=d['wave'].copy()
# 		d['size']=wav[100]
# 		m1=argmax(wav[:100])
# 		m2=argmax(wav[100:])+100
# 		d["lmax"]=wav[m1]
# 		d["rmax"]=wav[m2]
# 		d["mwidth"]=(m2-m1)/50000.0
# 		zc1=findCrossing(wav[m1:100], 0)+m1
# 		zc2=findCrossing(wav[100:m2], 0)+100
# 		d["width"]=(zc2-zc1)/50000.0
# 		d["sym"]=(100.0-zc1)/(zc2-zc1)
# 		spst.append(d)
# 		#print d
# 	return spst
# 
# 		
# 	
# 
# def getIntraSpikeStats(dat, fs, rp, t1, t2=None):
# 	'''dat (1d array), fs(float), rp(float), t1(float),t2(float=None)=>dict
# 	Input is data, sample frequency, resting potenial, threshold,
# 	and an optional second threshold.
# 	Detects spikes using a simple threshold, or a schmidt trigger if
# 	2 thresholds are given.
# 	Returns a list of dicts (one for each spike)
# 		containing:
# 		"t":time of occurence of the max of the spike (float)
# 		"width":the width at threshold
# 		"height":max-rest
# 		"depth":rest-min of AHP
# 		"attack":the slope of a best fit line through the rising
# 		         threshold crossing
# 		"decay":the slope of a best fit line through the falling
# 		         threshold crossing
# 		"zc1":time of the first zero crossing after the peak
# 		"tmin":time of the AHP minimum
# 		"ahprec":potential 1 ms after the min
# 		"wave":the spike waveform, resampled to 20KHz, with the
# 		       rest potential set to a value of 0. The wave is
# 			   80 samples (4 ms) long with the max of the spike at
# 			   sample 20.
# 	'''
# 	if t2:
# 		evts=detectSchmit(dat,(t1,t2))
# 	else:
# 		evts=detectAbove(dat, (t1,))
# 	spms=int(fs/1000)
# 	spst=[]
# 	for evt in evts:
# 		if dat.shape[0]-evt<spms*2:
# 			continue
# 		d={}
# 		ma=argmax(dat[evt:evt+spms])+evt
# 		a=dat[evt:evt+spms]
# 		d['t']=float(ma)/fs
# 		d['rp']=rp
# 		d['height']=dat[ma]-rp
# 		mi=argmin(dat[ma:ma+3*spms])
# 		d['tmin']=float(mi)/fs
# 		mi+=ma
# 		d['depth']=rp-dat[mi]
# 		if dat[mi]>rp:
# 			try:
# 				zc1=nonzero(dat[mi:]<=rp)[0]+mi
# 			except:
# 				zc1=dat.shape[0]-1
# 		else:
# 			zc1=findCrossing(dat[ma:mi],rp)+ma	
# 		d['zc1']=float(zc1)/fs-d['t']
# 		if mi+spms<dat.shape[0]:
# 			d['ahprec']=rp-dat[mi+spms]
# 		else:
# 			d['ahprec']=rp-dat[-1]
# 		try:
# 			tc1=findCrossing(dat[ma-2*spms:ma],t1)+ma-2*spms
# 			tc2=findCrossing(dat[ma:ma+3*spms],t1)+ma+1
# 			d['width']=float(tc2-tc1)/fs
# 			short=max(int(.1*spms), 2)
# 			at=dat[tc1-short:tc1+short]
# 			d['attack']=(at-shift(at,1)).mean()*fs
# 			dec=dat[tc2-short:tc2+short]
# 			d['decay']=(dec-shift(dec,1)).mean()*fs
# 		except:
# 			d['width']=.005
# 			d['attack']=float(dat[ma]- dat[ma-2*spms])/.002
# 			d['decay']=float(dat[ma]- dat[ma+3*spms])/.003
# 		if fs!=20000:
# 			wav=dat[ma-int(1.2*spms):ma+int(3.2*spms)]
# 			wav=array_resample(wav, 1.0/fs, 1.0/20000)
# 			ma=argmax(wav[:40])
# 			d['wave']=wav[ma-20:ma+60]-rp
# 		else:
# 			d['wave']=dat[ma-20:ma+60]-rp
# 		spst.append(d)
# 	return spst
# 
# 
# # ============== spike files ==============
# 
# def writeSpikeFile(fname, spikes):
# 	of=open(fname, 'w')
# 	for k in spikes.keys():
# 		print "%i spikes for template %s" % (len(spikes[k]), k)
# 	
# 
# 	
# 
# 
# def simpleShift(ds, delay, firstchannel=2):
# 	'''Shift every channel in ds (except the firstchannel and those
# 	before it) by an amount delay*(n-firstchannel)'''
# 	i=firstchannel
# 	while i<ds.data.shape[1]:
# 		shift=(firstchannel-i)*delay
# 		ds.shiftChannels([i], shift, True)
# 		i+=1
# 	return ds	
# 
# def storeStimulus(ds, channels=[0,1], rename=True):
# 	'''Makes a key ds.special["stim"] and stores the indicated channels
# in it (removing them from ds.data. If rename is True, also renames the
# remaining channels with sequential integers.'''
# 	ds.special["stim"]=take(ds.data, channels, 1)
# 	nonstim=[i for i in range(ds.data.shape[1]) if not i in channels]
# 	ds.data=take(ds.data, nonstim, 1)
# 	if rename:
# 		ds.labels=[str(i) for i in range(ds.data.shape[1])]
# 	else:
# 		ds.labels=[ds.labels[x] for x in nonstim]
# 	return ds
# 
# def makeShiftTemplateFromMarkers(ds, xcoord1, xcoord2, sKeyTemplate="phasedArrayTemplate"):
# 	'''Generates a shift template, and stores it in
# ds.special[sKeyTemplate]. This template assumes
# constant delays between channels, and attempts to shift from xcoord1 to
# xcoord2 across whole array of channels.'''
# 	shift=xcoord2-xcoord1
# 	temp=arange(ds.data.shape[1])*-1.0*shift/ds.data.shape[1]
# 	ds.special[sKeyTemplate]=temp
# 	return ds
# 
# def makeShiftTemplateFromMinima(ds, xcoord1, xcoord2, sKeyTemplate="phasedArrayTemplate"):
# 	'''Generates a shift template, and stores it in
# ds.special[sKeyTemplate]. This template attempts to align minima'''
# 	start=ds.xind(xcoord1)
# 	xcoord2=ds.xind(xcoord2)
# 	temp=zeros(ds.data.shape[1], Float32)
# 	mag=ds.data[start:xcoord2,:].mean()-ds.data[start:xcoord2,:].min()
# 	for c in range(ds.data.shape[1]):
# 		dseg=ds.data[start:xcoord2, c]
# 		if dseg.mean()-dseg.min()<.15*mag:
# 			print "channel %i is a bad record. not aligning" % c
# 			mpt=0
# 		else:	
# 			mpt=argmin(dseg)
# 		temp[c]=mpt
# 		start=start+mpt
# 	temp[0]=0
# 	temp=cumsum(temp.astype(Float32))
# 	temp=-1*temp/ds.fs
# 	ds.special[sKeyTemplate]=temp
# 	return ds
# 
# 
# def forceAlignMinima(ds, xcoord1=.10541, xcoord2=.12006):
# 	'''Generates a shift template, and stores it in
# ds.special[sKeyTemplate]. This template attempts to align minima'''
# 	start=ds.xind(xcoord1)
# 	xcoord2=ds.xind(xcoord2)
# 	temp=zeros(ds.data.shape[1], Float32)
# 	mag=ds.data[start:xcoord2,:].mean()-ds.data[start:xcoord2,:].min()
# 	for c in range(ds.data.shape[1]):
# 		dseg=ds.data[start:xcoord2, c]
# 		mpt=argmin(dseg)
# 		temp[c]=mpt
# 	temp-=temp[0]
# 	for i, s in enumerate(temp):
# 		ind=int(s)
# 		if ind:
# 			ds.data[:,i]=shift(ds.data[:,i], -ind)
# 	return ds	
# 
# 
# def getLargestUnits(ds, fractionOfMax=.9, shmidtCutoff=.5):
# 	'''Trys to find event times in the channel named "Superpossition" using
# a Schmidt trigger with heuristic thresholds designed to find units
# bigger than fractionOfMax (e.g. .9 finds units within 10% of the max)'''
# 	if not "Superpossition" in ds.labels:
# 		ds=	sumAllChannels(ds)
# 	chan=ds.data[:,ds.labels.index("Superpossition")]
# 	me=chan.mean()
# 	ma=chan.max()
# 	mi=chan.min()
# 	if me-mi>ma-me:
# 		chan=-1*chan
# 		me=-1*me
# 		ma, mi= (-1*mi, -1*ma)
# 	exc = ma-me
# 	thresh=[me+fractionOfMax*exc, me+shmidtCutoff*exc]
# 	evts=detectSchmit(chan, thresh)
# 	print len(evts)
# 	evts=take(ds.get_x(), evts)
# 	if not "EventTimes" in ds.labels:
# 		c=zeros(len(ds), ds.data.dtype.char)
# 		ds.addchannel("EventTimes", c)
# 	ec=ds.labels.index("EventTimes")
# 	ds.setRaster(ec, evts)
# 	return ds
# 
# def extractSpikes(ds, windowLength=.004, windowLead=.002):
# 	'''Gets only the spike waveforms of the events named in
# the channel EventTimes (this must exist)'''
# 	evts=ds.getChannel("EventTimes")
# 	evts=nonzero(evts)
# 	ds.special["EventTimes"]=(evts.astype(Float32)/float(ds.fs))+ds.start
# 	windowLead= int(windowLead*ds.fs)
# 	evts=evts-windowLead
# 	while evts[0]<0:
# 		evts[evts[1:]]
# 	ds.killchannel(ds.labels.index("EventTimes"))
# 	ds.getWindows(windowLength, evts, "int")	
# 	return ds
# 
# def simpleEqualize(ds, throwOut=.3, killNullChannels=True):
# 	'''Attempt to equalize channel ampiltiudes. Does not amplify channels
# 	with starting amplitude less than thowOut*mean amplitude. If
# 	killNullChannels is True, the non-amplified channels are deleted'''
# 	amps=zeros(ds.data.shape[1], Float32)
# 	for c in range(ds.data.shape[1]):
# 		d=ds.data[:,c]
# 		a=max(abs(d.mean()-d.min()), abs(d.mean()-d.max()))
# 		amps[c]=a
# 	nullchannels=[]	
# 	for i, a in enumerate(amps):
# 		if a<throwOut*amps.mean():
# 			print i, " Throwing out"
# 			nullchannels.append(i)
# 			continue
#  		factor=amps.max()/a
# 		print i, factor
# 		ds.data[:,i]*=factor
# 	if killNullChannels:
# 		nullchannels.sort()
# 		nullchannels.reverse()
# 		for c in nullchannels:
# 			ds.killchannel(c)
# 	return ds	
# 		
# 
# def getSpikeStatistics(ds, sKey="spikestats"):
# 	'''Operates on a dataset with event times and Superpossition.
# Saves list of  dicts in ds.special[sKey] that contains the result of
# getExtraSpikeStats on the superpossition channel'''
# 	evts=nonzero(ds.getChannel("EventTimes"))
# 	lod=getExtraSpikeStats(ds.getChannel("Superpossition"), ds.fs, evts)
# 	ds.special[sKey]=lod
# 	return ds
# 	
# 	
# def spikeDeviation(ds):
# 	ds2=ds.copy()
# 	ds2.foldWindows(["Average"]*ds2.data.shape[1])
# 	ds2.data=reshape(ds2.data[:,ds2.labels.index("Superpossition")], (-1, 1))
# 	ds2.labels=["Average"]
# 	dat=ds2.data[:,0]
# 	d={"wave":dat}
# 	errors=[]
# 	s=0
# 	while s<ds.data.shape[0]-ds.window:
# 		d2={"wave":ds.data[s:s+ds.window,ds.labels.index("Superpossition")]}
# 		errors.append(getSpikeError(d2,d))
# 		s+=ds.window
# 	print errors	
# 	
# 	ds.addData(ds2)
# 	return ds
# 	
# def refineSelection(ds, best=.3, sKey="spikestats", spikeIndex=0):
# 	'''Relies on a list stored in ds.special[sKey] that contains the output
# of getExtraSpikeStats. Selects the spike at index spikeIndex, and calculates
# the error of each other spike relative to this one. Selects the fraction of
# these units (specified by "best") that have the lowest errors. Uses this set
# to recalculate equalization and temporal shifts'''
# 	spst=ds.special[sKey][:]
# 	opt=spst[spikeIndex]
# 	del(spst[spikeIndex])
# 	errors=array([getSpikeError(d, opt) for d in spst])
# 	order=argsort(errors)
# 	bs=order[:max(1, int(best*order.shape[0]))]
# 	times=[opt['t']]+[spst[i]['t'] for i in bs]
# 	times.sort()	
# 	ec=ds.labels.index("EventTimes")
# 	ds.setRaster(ec, times)
# 	return ds
# 
# def refineTemplates(ds, sKeyTemplate='phasedArrayTemplateCorrection'):
# 	'''Operates on a ds with EventTimes. Equalizes the channels and
# generates a new template (stored in ds.special["phasedArrayTemplates"][sKeyTemplate]),
# using the average waveforms from all the indicated events. The new
# templates will be relative to the current state of the ds (so if there
# are already shifts, the new template will be a correction)'''
# 	ds2=ds.copy()
# 	extractSpikes(ds2, .004, .002)
# 	if "Superpossition" in ds2.labels:
# 		ds2.killchannel(ds2.labels.index("Superpossition"))
# 	ds2.foldWindows(["Average"]*ds2.data.shape[1])
# 	#normalize
# 	amps=zeros(ds2.data.shape[1], Float32)
# 	for c in range(ds2.data.shape[1]):
# 		d=ds.data[:,c]
# 		a=max(abs(d.mean()-d.min()), abs(d.mean()-d.max()))
# 		amps[c]=a
# 	for i, a in enumerate(amps):
#  		factor=amps.max()/a
# 		print i, factor
# 		ds.data[:,i]*=factor
# 	#get new template
# 	makeShiftTemplateFromMinima(ds2, ds2.start, ds2.start+.0039, 'tempCor')
# 	temp=ds2.special['tempCor']
# 	ds.special[sKeyTemplate]=temp	
# 	return ds	
