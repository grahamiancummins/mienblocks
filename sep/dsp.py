import gicspikesort.conditioning as gicc
import gicspikesort.spikes as spks
import mien.image.viewer as V
import mien.parsers.fileIO as IO
import numpy as n   
from mien.datafiles.dataset import *
import gicspikesort.sorter as srt 
import scipy.special as sc
import os  
#import otherfuncs as oth

def conditionEach(ds, dpathFrom='/', dpathEventsToConditionWith='/evts', dpathStimulus='/avstims'):
	''' 
	Applies gicspikesort.conditioning.eventCondition to all timeseries and events in ds
	'''
	dod = ds.getHierarchy()
	numberNames=dod[dpathFrom].getData()[:,1]

	for k in range(max(numberNames)+1):
		#print(k)
	
		#separate each unit to its own channel
		mm = list(numberNames).index(k)
		tmpName = '/'+ds.getLabels()[k]
		hdr = {'SampleType':'events','SamplesPerSecond':5e4, 'Labels':ds.getLabels()[k]}
		dta = dod[dpathFrom].getData()[mm:mm+list(numberNames).count(k),0]
		ds.createSubData(tmpName,dta, head=hdr)	
	
		#event condition
		newName='/sorted_'+ds.getLabels()[k]
		gicc.eventCondition(ds, dpathEventsToConditionWith, tmpName, 5, 35, newName, False)
	
		#remove the new channel
		dod = ds.getHierarchy()
		dod[tmpName].sever()	
	
def tmpWork(ds, prefChans=None):
	''' 
	Just the day's workflow, save keystrokes
	'''
	
	dataDict = ds.getHierarchy()	
	
	#set prefChans
	if not prefChans:
		prefChans = range(ds.shape()[1]-4,ds.shape()[1])
		print('Selecting stimulus channels')
		#print(prefChans)

	#get a marker of the base channel starting each stimulus seti
	_getStims(ds,prefChans, .006,.003)

	#remove the last element from isolateSpikes WIP
	#events=dataDict['/tmpname'].getData()
	#events=events[0:len(events)/2-1,:]
	#dataDict['/tmpname'].setData(events)
	#print(dataDict['/tmpname'].shape())

	#trigger on these marks to get the average stimulus
	gicc.eventCondition(ds,'/evts', '/', 40.0, 80.0, '/avstim', milliseconds=True)
	
	#remove the channel with multiple marks per stimulus run	
	dataDict = ds.getHierarchy()

	repNumber=dataDict['/avstim'].header()['Reps']
	
	#print(repNumber)	
	
	#average just the spikes and the base and tip stim
	average = dataDict['/avstim'].getData() 
	newdata = average[:,0:repNumber-1].mean(1)
	johnsData=average[:,0:repNumber-1]

	#try to find the base and stimulus channels, or arbitrarily set base and stim channels
	labelNames = ds.getLabels()
	if 'nozzle 1 (No Comment)' in labelNames:
		basenum = labelNames.index('nozzle 1 (No Comment)')
		tipnum = labelNames.index('nozzle 2 (No Comment)')
	else:
		basenum = prefChans[m]
		tipnum = prefChans[1]
	   
	for m in range(basenum,basenum+4):
			nd2=average[:,repNumber*m:repNumber*(m+1)-1].mean(1)
			newdata=n.column_stack((newdata,nd2))

	#nd2=average[:,repNumber*basenum:repNumber*(basenum+1)-1].mean(1)
	#newdata=n.column_stack((newdata,nd2))
	#nd2=average[:,repNumber*(basenum+1):repNumber*(basenum+2)-1].mean(1)
	#newdata=n.column_stack((newdata,nd2))

	hdr = {'SampleType':'timseries','SamplesPerSecond':ds.header()['SamplesPerSecond']}
	ds.datinit(newdata,hdr)
	dataDict['/avstim'].sever()
	ds.createSubData('/johns',johnsData, head=hdr)
	#dataDict['/'].sever()

	#remove the non stimulus channels from the conditioned data
	#evtsData = dataDict['/evts'].getData()
	#evtsNumber = len(evtsData)
	#evtsNumber=evtsNumber*10
	#resizeData=dataDict['/avstim'].getData()[:,evtsNumber:]
	#dataDict['/avstim'].sever()
	#hdr = dataDict['/avstim'].header()
	#ds.createSubData('/avstim',resizeData,hdr)
	   
	#save the new file
	newFName = ds.xpath(True)[0].fileinformation.get('filename','NoNameGiven')
	newFName = newFName[0:newFName.rfind('.')] + '.mat'
	IO.write(ds,newFName,newdoc=True)

def divideChunks(ds,chunkSize=50):
	''' 
	Divide a run into 50 stimulus segments, in keeping with Nov. 08 stimulus files. 
	Returns the number of chunks in the file in question
	'''
	#detect spikes in the stimulus channel
	stimChans=range(ds.shape()[1]-4,ds.shape()[1])
	_getStims(ds,stimChans,.006,.003)

	#set the division points
	dataDict = ds.getHierarchy()
	stimTimes = dataDict['/evts'].getData()[:,0]

	groupBreaks = [stimTimes[1]]
	m = 0 
	for m in range(1,len(stimTimes)/chunkSize):
		groupBreaks.append((stimTimes[chunkSize*m-1] + stimTimes[chunkSize*m]) / 2)
	lastStim = min(chunkSize*(m+1)-1,len(stimTimes)) 
	groupBreaks.append(stimTimes[lastStim])
	if stimTimes[-2]>max(groupBreaks):
		groupBreaks.append(max(stimTimes))  

	#remove extra channels
	dataDict['/evts'].sever()

	#hdr = {'SampleType':'timseries','SamplesPerSecond':5e4, 'Labels':ds.getLabels()}
	#crop to each area
	ds2=ds.clone(True)
	window=20*1e-3*ds.header()['SamplesPerSecond']
	for m in range(len(groupBreaks)-1):
		hdr = ds.header()
		dat = ds.getData()[groupBreaks[m]-window:groupBreaks[m+1]+window+1]
		ds2.datinit(dat,hdr)
		#ds2=ds.clone(True)
		#ds2.crop([groupBreaks[m]-window,groupBreaks[m+1]+window])
		ds2.setAttrib('StartTime',0)
		newFName = ds.xpath(True)[0].fileinformation.get('filename','NoNameGiven')
		newFName = newFName[-2:] + 'pt' + str(m+1) +'.mien'
		IO.write(ds2,newFName,newdoc=True)

	return len(groupBreaks)

def convertStim(ds,prefChans):
	""" 
	WORK IN PROGRESS
	FUNCTION: Turns voltage inputs into actual airmotion velocities using the Vin to mflown and mflown to air motion filters
	INs:	ds=data array
		prefChans= ordered vector of stimulus channels to be tranfered in ds
	"""
	fhandle=open("/home/mulderrosi/Desktop/localcal/Vin2mf")
	V2mf=loadtxt(fhandle)
	fhandle.close()

	#THIS PART DOESN'T EXIST YET
	#fhandle=open("/home/mulderrosi/Desktop/localcal/mf2air")
	#mf2air=loadtxt(fhandle)
	#fhandle.close

	#STILL NEED TO TEST THIS ALL
	transferFunc=V2mf*mf2hair
	for m in range(len(prefChans)):
		stimChan = getSelection(ds,(None,prefChans[m],None))
		stimChan = convolve(stimChan, transferFunc, mode='same')

def _translate_stims(stims):
	'''
	Very specific function for translating a list of of 4 channel stimuli into the nomenclature used by functions here.
	'''
	if not stims.shape[1] == 4:
		print 'Wrong inputs.- dsp._translate_stims'
		return stims, 0
	#reorder from channel number to order in physical experiment
	stimtmp = stims[:,[0,2,3,1]]
	#get basic stimulus output values
	stimsout = (stimtmp[:,3]-stimtmp[:,0])
	dar = diff(stimtmp)
 	#check if this is a unidirectional wave
	sweeps = dar - transpose(tile(dar[:,0],(3,1)))
	sweeps = not sweeps.any()
	newstim = int(not sweeps)
	#possibly add the 'newstim' correction
	if newstim:
		stimsout = 100*(stimtmp[:,1]-stimtmp[:,0])+stimsout
	return stimsout, newstim
	

def _stims_from_strng(ds, strng, maxstimlen=120.):
	'''
	uses a string marker in the channel name to id stimuli, then peak detects for the stimuli time, resorts these stimuli into the standard puffer format
	'''
	from gicspikesort.spikes import schmitTrigger
	fs = ds.header()['SamplesPerSecond']
	goodchans = [n for n in range(len(ds.getLabels())) if ds.getLabels()[n].find(strng) > -1]
	_findStims(ds,goodchans,.1,.5)#FIX THIS SO IT ITTERIVELY SEARCHES FOR THRESHOLDS?
	if not ds.getSubData('/tmpname'):
		return array(None), goodchans
	allstims = ds.getSubData('/tmpname').getData()
	events = _unique_events_from_stims(ds,maxstimlen)
	sortar = zeros((len(events),len(goodchans)))
	maxrng = maxstimlen*fs/1e3
	for m in range(len(events)):
		chk = abs(allstims[:,0] - events[m])
		locstims = allstims[where(chk < maxrng)[0],:]
		locstims = locstims[argsort(locstims[:,1]),:]
		locstims = (locstims)[:,0]
		locstims = hstack((locstims, -maxstimlen*ones((1,len(goodchans)))[0,:]))#fill for extra entries
		sortar[m,:] = locstims[:len(goodchans)]
	sortar = _reformatted_stims(sortar,fs)
	sortar = _unique_stims(sortar)
	return sortar, goodchans

def _reformatted_stims(sortar,fs):
	chanones = transpose(tile(sortar[:,0],(sortar.shape[1],1)))
	sortar = sortar - chanones
	sortar = sortar*1e3/fs
	sortar = sortar.round()
	return sortar
	
def _unique_stims(sortar):
	sortar, reps = unique_rows(sortar)
	sortar = sortar[[n for n in range(len(reps)) if reps[n] > 2],:]
	sortar = sortar[argsort(sortar[:,1]),:]
	return sortar
	
def dividebyStims(ds, prefChans=[9,10,11,12], thresh1=.5, thresh2=.3, path=None, stimchantag=None, newbasename=''):
		'''
		Find all the stimuli and sort each run into a limited number of classes, then put each class together in a new file
		Assumptions:	1) On repeated stimuli we're going faster than 30Hz
						2) We have at least 200ms between stimuli repeats
						3) Recording doesn't start in the middle of a stimulus
						4) Base is the first stimulus channel, tip is second
		'''
		#stimoptions=array([-9.,-7.,-5.,-3.,-1.,0.,1.,3.,5.,7.,9.])
		#stimoptions=array([-60,-55,-50,-45,-40,40,45,50,55,60])
		#stimoptions=array([-115,-100,-85,-60,-45,-30,-15,15,30,45,60,85,100,115])
		winl = 100*ds.header()['SamplesPerSecond']/1e3
		winh = 200*ds.header()['SamplesPerSecond']/1e3

		if stimchantag:
			jnk, prefChans = _stims_from_strng(ds,stimchantag)
		else:
			_findStims(ds,prefChans,thresh1,thresh2,pth=path)
		dataDict = ds.getHierarchy()
		tips = dataDict['/tmpname'].getData()
		#print tips, type(tips), shape(tips)

		#print len(tips), tips
		cheatvar = 0
		if not len(tips): #without stimuli detected on the channels in question we have some trouble with the following function.  Which wouldn't be a problem except THAT SOMEWHERE THIS FUNCTION RESIZES DATA, AND WE NEED TO RESIZE IN THE ABSENCE OF STIMULI AS WELL.  BUT WHILE ITS POSSIBLE TO RUN THROUGH THE PROGRAM, IT SOMEHOW STILL MISSES THE PLACE WHERE THINGS ARE RESIZED`
			tips = array([[0.,0.],[0.,1.],[0.,2.],[0.,3.],[5.,0.],[5.,1.],[5.,2.],[5.,3.]])
			cheatvar = 1
			ds.getSubData('/tmpname').sever()
			ds.createSubData('/tmpname',data=tips,head={})
			return True
			#print tips, type(tips), shape(tips)
	#		if newbasename == '':
	#			newfname = ds.xpath(True)[0].fileinformation.get('filename','nonamegiven')
	#		else:
	#			newfname = newbasename
	#		newfname = os.path.splitext(newfname)[0] + 'pt1.mien'
	#		print 'No stimuli found, saving only {0}.'.format(newfname)
	#		save_wo_leak(ds, newfname)
	#		return
	
		#take care of uneven numbers of stims on various channels
		runlengths = [len(tips[tips[:,1]==m,0]) for m in list(set(tips[:,1]))]
		shortchan = argmin(runlengths)
		others = list(set(range(len(runlengths)))-set([shortchan]))
		longchan=others[0]
		if not runlengths[shortchan]==runlengths[longchan]:
			frontdif = abs(tips[tips[:,1]==shortchan,0][0] - tips[tips[:,1]==longchan,0][0])
			endif = abs(tips[tips[:,1]==shortchan,0][-1] - tips[tips[:,1]==longchan,0][-1])
			badend =int(where(frontdif>endif,0,-1))
			tt=list(tips)
			for m in range(len(others)-1,-1,-1):
				tt.pop(where(tips[:,1]==others[m])[0][badend])
			tips = array(tt)

		stims = tips[where(tips[:,1]==0)[0],0]
		print 'bb', stims, range(1,len(prefChans))
		for m in range(1,len(prefChans)):
			addons = tips[where(tips[:,1]==m)[0],0]
			if not addons.shape[0] in stims.shape: #so far only fixed when one of addons not equal to number 2 is the wrong size
				if addons.shape[0]>max(stims.shape):
					raise NameError('do not know how to do')
				else:
					while addons.shape[0] != max(stims.shape):
						if addons[0]-stims[0,0] > addons[-1]-stims[0,-1]: #the double part reference to stims eliminates the chance to catch addons number 2 wrong size
							addons = hstack((0,addons))	
						else:
							addons = hstack((addons,0))	
					#return stims, addons
			stims = vstack((stims, addons))	
		stims = transpose(stims)
		#print 'aa', stims
			#datadict = ds.gethierarchy()
			#tips = datadict['/tmpname1'].getdata()
			#bases = datadict['/tmpname0'].getdata()
			#ch3 = datadict['/tmpname2'].getdata()
			#tips2 = datadict['/tmpname3'].getdata()
			#stims = n.hstack((bases,tips,ch3,tips2))
		stims = _reformatted_stims(stims, ds.header()['SamplesPerSecond'])
		#print 'vv', shape(stims)
#		stimoptions = _unique_stims(stims)
#		stimoptions, newstim = _translate_stims(stimoptions)
		#print 'hello', stims, stims.shape, type(stims), '\n\n\n', fubaru
		stims, newstim = _translate_stims(stims)	
		#print 'cc', shape(stims), newstim
#		stimoptions=array(stimoptions)
		events = _unique_events_from_stims(ds)
		if min(events)[0] < 30/1e3*ds.header()['SamplesPerSecond']:
			print('this recording may be starting in the middle of a stimulus and subsequent analysis will get wonky:- sep.dsp.dividebystims')
		stimlist = list(stims)
		if cheatvar:
			stimlist = [0]
		stimoptions=array(list(set(stimlist)))

		#clean up after myself  
		dataDict['/tmpname'].sever()
		#datadict['/tmpnametot'].sever()
		#datadict['/tmpname0'].sever()
		#datadict['/tmpname1'].sever()
		#datadict['/tmpname2'].sever()
		#datadict['/tmpname3'].sever()
		#datadict['/evts'].sever()

		#see if the spikes are already identified in this file and need to be distributed works ok without sorted spikes< but need some way to get "/hidden/stimulus' copied as well
		tempsin=ds.getElements()
		tempsin=[t for t in tempsin if t.name().startswith("spikesort_")]
		nams=[]
		temps=[]
		for m in range(len(tempsin)):#for each unit...
				temps.append(tempsin[m].getElements(attribs={'SampleType' :'events'},depth=1)[0])
				nams.append(tempsin[m].name())
				temps[m]=temps[m].getData()#get the event times off all spikes for a given unit

		#pull out chunks for each repeat, paste them together, save new file
		ds2=ds.clone(False)
		channum=ds.shape()[1]
		hdr = ds.header()
		#hd2 = {'SamplesPerSecond':50000.0,'StartTime':0.0,'SampleType':'events'}
		for m in range(len(stimoptions)):
				#print 'right here', stimoptions, m, events, stimlist, array(stimlist), stimoptions[m], len(events[array(stimlist)==stimoptions[m]])
				togets=events[array(stimlist)==stimoptions[m]]#get a list of all stimuli matching this stimoption
				data = n.zeros((1,channum))#preallocate
				locevts = []#preallocate 
				for r in range(len(tempsin)):
						locevts.append([])#preallocate
				for r in range(len(togets)):#for each matching stimulus event
						data=n.concatenate((data,dataDict['/'].getData()[int(togets[r]-winl):int(togets[r]+winh),:]))#append the chunk winl before the stimulus to winh after the stimulus to data
						for q in range(len(temps)):#for each unit...
								under=set(temps[q][temps[q]>togets[r]-winl])# find all the 'temps' in the appropriate within winl to winh of the event 
								over=set(temps[q][temps[q]<togets[r]+winh])
								ok=array(list(under.intersection(over)))
								for t in range(len(ok)):#for each individual spike of a certian unit...
										locevts[q].append(ok[t]-int(togets[r])+r*(winl+winh)+winl)#add each approved spike with the appropriate shift for how far along in the recording we are
				ds2.datinit(data,hdr)
				ds2.setAttrib('StartTime',0)
				for q in range(len(temps)):
						hd2['Labels']=nams[q]
						ds2.createSubData('/'+nams[q],data=locevts[q],head=hd2)
				if newbasename == '':
					newfname = ds.xpath(True)[0].fileinformation.get('filename','nonamegiven')
				else:
					newfname = newbasename
				if newfname==None:
					print 'could not read filename'
					newfname = os.path.expanduser('~') + '/Desktop/tempfile.mien'
				newfname = os.path.splitext(newfname)[0] + 'pt' + str(m+1) +'.mien'
				#print newfname
				save_wo_leak(ds2,newfname)
				if len(temps): #put this in standard format if the sorted spikes are already there
						ds2.createSubData('/evts',data=array(range(len(togets)))*(winl+winh)+winl,head=hd2)

						#get the data I want
						gicc.eventCondition(ds2,'/evts', '/', 120.0, 160.0, '/avstim', milliseconds=True)
						dataDict2 = ds2.getHierarchy()
						repNumber = dataDict2['/avstim'].header()['Reps']
						average = dataDict2['/avstim'].getData()
						newdata = average[:,0:repNumber-1].mean(1)

						#also get raw traces of the full recording
						fulldata = average[:,0:repNumber-1]
						for q in range(1,dataDict2['/'].shape()[1]):
								fulldata = n.column_stack((fulldata,average[:,repNumber*q:repNumber*(q+1)-1]))

						#get the stimulus channels I want
						ms2pts=ds.header()['SamplesPerSecond']*1e-3
						for q in range(len(prefChans)):
								upper=int(togets[0]-120*ms2pts)
								lower=int(togets[0]+40*ms2pts)
								nd2 = getSelection(ds,(path,prefChans[q],None))[upper:lower]
								newdata=n.column_stack((newdata,nd2))

						#write over ds2 so it doesn't have needless data as well
						avstim=dataDict2['/avstim'].getData()
						hd3=dataDict2['/avstim'].header()
						ds2.clearAll()
						hdr = {'SampleType':'timseries','SamplesPerSecond':ds.header()['SamplesPerSecond']}
						ds2.datinit(newdata,hdr)
						ds2.createSubData('/evts',data=array(range(len(togets)))*(winl+winh)+winl,head=hd2)
						ds2.createSubData('/avstim',avstim,head=hd3)
						ds2.createSubData('/fullstim',fulldata,head=hd3)

						#add the spikes in a single piece of data
						locdata=zeros((2,1))
						for q in range(len(temps)):
								indata=vstack((locevts[q],q*ones((1,len(locevts[q])))))
								locdata=hstack((locdata,indata))
						locdata=locdata[:,1:]
						hd3=hd2.copy()
						hd3['SampleType']='labeledevents'
						hd3['Labels']=nams
						ds2.createSubData('/spks',locdata.transpose(),head=hd3)

						nFN2=newFName[:-5]+'spks.mat'
						#print nFN2
						save_wo_leak(ds2,nFN2)
				ds2.clearAll()
		ds2.sever()
		ds.sever()			

def _unique_events_from_stims(ds,twin=120.):
	#used after _getStims, takes a dataset with a '/tmpname' child holding stimulus events on various channels and gets all the times of all the mulitchannel stimulus presentations
	twin = float(twin)
	dataDict = ds.getHierarchy()
	events=dataDict['/tmpname'].getData()[:,0]
	#print 'all events', events, dataDict['/tmpname'].getData(), dataDict.keys()
	hdr = {'SampleType':'events','SamplesPerSecond':ds.header()['SamplesPerSecond']}
	ds.createSubData('/tmpnametot',events,hdr)
	gicc.isolateSpikes(ds,'/tmpnametot','/evts',0.,twin,absolute=False)
	for m in range(4):#isolate spikes on each channel
		nam='/tmpname'+str(m)
		localevents=dataDict['/tmpname'].getData()
		#print 'bfr',localevents
		localevents=localevents[where(localevents[:,1]==m),0]
		hdr = {'SampleType':'events','SamplesPerSecond':ds.header()['SamplesPerSecond']}
		#print 'aftr',localevents
		ds.createSubData(nam,localevents.squeeze(),hdr)
		gicc.isolateSpikes(ds,nam,nam,0.,twin,absolute=False)#note that repeats slower than 30Hz cause problems here
	dataDict = ds.getHierarchy()
	events = dataDict['/evts'].getData()
	return events

def _getStims(ds,prefChans,thresh1,thresh2,pth=None):
	"""
	FUNCTION: Find the active stimulus channel and triger each discrete stimulus presentation.
	INs:	ds= data array
			prefChans= ordered vector of the numbers of the stimulus channels in ds.
			thresh1= first dectection threshold
			thresh2= second detection threshold
	"""
	_findStims(ds,prefChans,thresh1,thresh2,pth=pth)
	dataDict = ds.getHierarchy()
	events=dataDict['/tmpname'].getData()[:,0]
	hdr = {'SampleType':'events','SamplesPerSecond':ds.header()['SamplesPerSecond']}
	ds.createSubData('/tmpnametot',events,hdr)
	gicc.isolateSpikes(ds,'/tmpnametot','/evts',0.0,30.0,absolute=False)
	dataDict = ds.getHierarchy()
	dataDict['/tmpname'].sever()
	dataDict['/tmpnametot'].sever()

	if not '/evts' in dataDict or dataDict['/evts'].shape()[0] == 0:
		print('Could not find an active stimulus channel')

def _newTempMatch(ds, evt, temp, delshift):
	'''
	Sensible template matching to determine the best match for a given spike
	Assumptions: 'evt' is the spike minimum in channel 1 
		'delshift' is the reasonable shift, in data points, for every .75mm distance (between two electrodes)
		Each point along a trace comes from a normal distribution of possible values
		The covaraince of points in a spike train can be safely ignored when the goal is to compare two different possible spikes
	'''

	#check that the input data is good (ie same number of channels all around)
	templt = temp.getSubData('template').getData()
	shft = temp.getSubData('shift').getData()

	#check things mesh up
	channum = ds.shape()[1]
	if not shft.shape[0]==channum or not templt.shape[1]==2*channum:
		raise StandardError("Template and data not the same size.")
	templen=templt.shape[0]

	#correct for current shift state
	curshift = ds.getSubData('spikesorter_shiftstate').getData()
	if len(curshift)>0:
		shft=shft-curshift

	leads=[]
	for m in range(channum):
		leads.append(argmin(templt[:,2*m]))

	#excise and shift the data in question; matching within delshift
	dat = ds.getData()
	errarr = zeros((templen,channum))
	#datitos = zeros((templen,channum))
	shiftout = zeros(shft.shape)
	for m in range(channum):
		apmn = evt - shft[m] - leads [m]
		srchrng = delshift*m+2#always throw in an extra point each side
		locerr = n.zeros((templen,2*srchrng+1))
		locdat = zeros((templen,2*srchrng+1))
		errvals = []
		for r in range(2*srchrng+1):
			locstrt = int(apmn - srchrng + r)
			locdat[:,r] = dat[locstrt:locstrt+templen,m]
			locerr[:,r] = locdat[:,r]-templt[:,2*m]
			errvals.append(sum(locerr[:,r]**2))
		errarr[:,m]=locerr[:,argmin(errvals)]
		#datitos[:,m]=locdat[:,argmin(errvals)]
		shiftout[m] = shft[m] - srchrng + argmin(errvals)
	shiftout = shiftout - shiftout[0] + curshift

	#take the sum squared error (/standard error?) for all points
	#badness = sum(errarr**2)
	#badness = zeros(errarr.shape)
	#for m in range(errarr.shape[1]):
	#   badness[:,m]= errarr[:,m]**2/templt[:,2*m+1]
	#badness = sum(badness) 

	#use this to get the probability of data given the template
	ppointItemp = zeros(errarr.shape)
	for m in range(errarr.shape[1]):
		ppointItemp[:,m]= 1-sc.erf(abs(errarr[:,m])/(sqrt(2)*templt[:,2*m+1]))
	pdatItemp = ppointItemp.cumprod()[-1]*templen
	return pdatItemp, shiftout, errarr


def shiftTemplates(dat,evts,shifts,peaks=[], windw=5):
	''' 
	A way to take a set of templates used to sort one file and change it into the most appropriate set of templates to be used in a similar file on the same animal.
	Assumptions:
	'''
	window=round(2*dat.header()['SamplesPerSecond']/1e3/2)#+/- two ms

	if not len(evts):
		print('NO SPIKES')
		return shifts

	#check that templates need to be shifted
	diffs=zeros((dat.shape()[1],len(evts)))
	for m in range(len(evts)):
   		diffs[:,m]=srt.alignMinima(dat,(None,None,[evts[m]-window,evts[m]+window]))

	#check for linear regression in shift, eg moving template? Maybe in a later iteration

	shortdiffs=[]
	for m in range(diffs.shape[0]):
		torun=diffs[m,:]
		outside=max([std(torun),.001])*3
		torun=torun[abs(torun) < outside+abs(mean(torun))]
		if not peaks==[]:
			avg = sum(torun*peaks/float(sum(peaks)))#the weighted average
			shortdiffs.append(avg)
		else:
			shortdiffs.append(mean(torun))
	#shortdiffs=round(mean(diffs,1))
	shortdiffs=round(array(shortdiffs))

	newshifts=shifts.copy()
	if shortdiffs.any():
		for m in range(1,shifts.shape[0]):
			newshifts[m]=shifts[m] + sign(shortdiffs[m])* min(abs(shortdiffs[m]),abs(shifts[m-1]-newshifts[m-1])+windw)
		print "Moved shifts to %s" % (str(newshifts),)
		srt.blockShift(dat, newshifts, False) #apply shifts here
		newshifts = array(newshifts)
	else:
		newshifts = shifts

	#for when templates are way off
	if len(evts)>7 and sum(abs(mean(diffs, axis=1)))>2*dat.shape()[1]:
		mnshifts = mean(diffs, axis=1).T
		mnshifts = mnshifts.round()
		for m in range(1,shifts.shape[0]):
			newshifts[m]=shifts[m] + sign(mnshifts[m])* min(abs(mnshifts[m]),abs(shifts[m-1]-newshifts[m-1])+windw)
		print "Moved shifts to %s" % (str(newshifts),)
		srt.blockShift(dat, newshifts, False) #apply shifts here
		newshifts = array(newshifts)

	return newshifts


def _findStims(ds,prefChans,thresh1,thresh2,pth=None):
	'''
	Does the work of finding stims in each of the three channels and sticking them all in one place
	'''
	#check for stimulus path
	#print 'here now', pth, prefChans, prefChans[0], ds,pth,'here'
	getSelection(ds,(pth,prefChans[0],None))
	try: #simply testing for the existence of data in pth
		getSelection(ds,(pth,prefChans[0],None))
	except:
		pth='/hidden/stimulus'
		try:
			getSelection(ds,(pth,prefChans[0],None))
		except:
			raise NameError('Cannot find stimuli- _findStims')

	for m in range(len(prefChans)):
		chanZero = getSelection(ds,(pth,prefChans[m],None))
		chanZero = chanZero.mean()
		t1,t2 = thresh1+chanZero, thresh2+chanZero
		spks.schmitTrigger(ds, t1, t2, (pth, [prefChans[m]], None), '/tmpname', above=True, labs=None)
		dataDict = ds.getHierarchy()
		if '/tmpname' in dataDict and dataDict['/tmpname'].shape()[0] == 0:
			dataDict['/tmpname'].sever()
			dataDict = ds.getHierarchy()
		if not '/tmpname' in dataDict: #try for dips the other direction
			spks.schmitTrigger(ds, -t1, -t2, (pth, [prefChans[m]], None), '/tmpname', above=False, labs=None)
			dataDict = ds.getHierarchy()
			if '/tmpname' in dataDict and dataDict['/tmpname'].shape()[0] == 0:
				dataDict['/tmpname'].sever()
				dataDict = ds.getHierarchy()
		if not '/tmpname' in dataDict.keys():
			ds.createSubData('/tmpname',data=[], head={})

def new_x(ds,dpath='/' , newratio=1):
	datgroup = ds.getSubData(dpath)
	data = datgroup.getData()
	hdr = datgroup.header()
	if 'Xratio' in hdr.keys():
		curratio = hdr['Xratio']
	else:
		curratio = 1
	curfreq = hdr['SamplesPerSecond']
	if not hdr['SampleType']=='timeseries':
		print 'This function does not currently support this datatype.  It may run, but check the code to see if it does what you want.- sep.new_x'
	newfreq = round(curfreq)*newratio
	chans=[]
	for i in range(data.shape[1]):
		chans.append(array_resample(data[:,i], 1.0/curfreq, 1.0/newfreq, True))
	dat2 = transpose(array(chans))
	hdr['Xratio'] = curratio*newratio
	#Set the preferences to accept different lengths
	datgroup.datinit(dat2, hdr)

def save_wo_leak(ds,name):
	''' 
	Saves data in mien formats without the usual memory leaks of using the mien function directly
	'''
	import mien.parsers.fileIO as IO
	from mien.parsers.nmpml import blankDocument
	doc = blankDocument()
	doc.newElement(ds)
	IO.write(doc, name)
	ds.sever()
	doc.sever()

def unique_rows(ar):
	'''
	return a list of the unique rows of an array and their number of occurances
	'''
	rows, rowlen = ar.shape
	tocheck = range(rows)
	outs = []
	repcount = []
	while len(tocheck) > 0:
		locline = ar[tocheck[0],:]
		outs.append(locline)
		n=1
		repcount.append(n)
		while n < len(tocheck):
			if (ar[tocheck[n],:] == locline).all():
				tocheck.pop(n)
				repcount[-1]+=1
			else:
				n+=1
		tocheck.pop(0)
	outs = array(outs)
	return outs, repcount


#-------Depricated bits------------------------------------------------------------------
#		#clean up after myself  
#		stimlist = []
#		datadict = ds.gethierarchy()
#		tips=datadict['/tmpname1'].getdata()
#		bases=datadict['/tmpname0'].getdata()
#		ch3=datadict['/tmpname2'].getdata()
#		tips2=datadict['/tmpname3'].getdata()
#		for m in range(len(events)):#find time in chs 1 and 2, get the best match to stimoptions
#			if newstim and len(ch3)>0:
#				difval=(100*(ch3[m]-bases[m])+(tips2[m]-ch3[m]))*1e3/ds.header()['samplespersecond']
#			else:
#				difval=(tips[m]-bases[m])*1e3/ds.header()['samplespersecond']
#			id = abs(stimoptions-difval)
#			difval = stimoptions[argmin(id)]
#			stimlist.append(float(difval))
#		print 'opt2', shape(stimlist), stimlist
#		stimoptions=array(list(set(stimlist)))
#		print stimoptions

#  #clean up after myself  
#  tips=datadict['/tmpname1'].getdata()
#  bases=datadict['/tmpname0'].getdata()
#  ch3=datadict['/tmpname2'].getdata()
#  tips2=datadict['/tmpname3'].getdata()
#  for m in range(len(events)):#find time in chs 1 and 2, get the best match to stimoptions
#	  if newstim and len(ch3)>0:
#		  difval=(100*(ch3[m]-bases[m])+(tips2[m]-bases[m]))*1e3/ds.header()['samplespersecond']
#	  else:
#		  difval=(tips[m]-bases[m])*1e3/ds.header()['samplespersecond']
#	  id = abs(stimoptions-difval)
#	  difval=stimoptions[argmin(id)]
#	  stimlist.append(float(difval))
