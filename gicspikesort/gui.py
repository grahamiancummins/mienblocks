#!/usr/bin/env python

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

import guianalysis
reload(guianalysis)
from guianalysis import *

import discriminants
import errors, time
reload(errors)
reload(discriminants)
try:
	import profile
except:
	print "profiler is not available. Some methods may fail"
	
def calc_mean(data, pars=(), template=None):
	return data.mean(1)
							
def no_error(data, pars=(), template=None):
	return None							
							
DISC_FUNCTIONS={"Mean":calc_mean}
ERROR_FUNCTIONS={"None":no_error}	

class PASpikeSorter(BaseGui):
	def __init__(self, dv):
		self.dv=dv
		BaseGui.__init__(self, dv, title="Spike Sorter Panel", menus=["Data", "Templates", "Detect", "Refine"], pycommand=True,height=4, showframe=False)
		commands=[
			['Data', 'Export Spikes', self.exportSpikes], 
			['Data', 'Import Spikes', self.getSpikes], 
			['Data', 'Export Templates (With All Data)', lambda x:self.exportTemps(True)], 
			['Data', 'Export Templates (For Reuse)', lambda x:self.exportTemps(False)],
			['Data', "Preferences", self.setPreferences],
			['Data', 'Close', self.onClose],
			['Templates', 'New Template', self.newTemp],
			['Templates', 'Choose Template', self.chooseTemp],
			["Templates", "Align", self.alignMin],
			["Templates", "Align From Marks", self.alignMarks],
			["Templates", "Align From Marks (Reversed)", lambda x:self.alignMarks(None, True)],
			['Templates', 'Apply Shift (from previous template)', self.applyShift],
			['Templates', 'Remove All Shifts', self.unShift],
			['Templates', 'Restore Last Shifts', self.reShift],
			['Templates', 'Save Selected Spike as Ideal', self.setIdeal],
			["Detect", "Detect", self.doDetect],
			["Detect", "Set Thresholds (Auto)", self.autoThresh],
			["Detect", "Set Thresholds (Markers)", self.markThresh],
			["Detect", "Clear Spikes", self.clearSpikes],
			["Refine", "Calculate Template PCA", self.pcaTemp],
			["Refine", "Recalculate Template", self.recalcTemp],
			["Refine", "Align Template", self.realignTemp],
			["Refine", "Get Template Jitter", self.djTemp],
			["Refine", "Minimize Jitter", self.optimTemp],
			["Refine", "Subtract Templates", self.removeTemp],
			["Refine", "Blank Template Regions", self.blankTemps],
			["Refine", "Blank Current View", self.blankView],
			["Refine", "Add Templates Back", lambda x:self.removeTemp(None, 'add')]
			]
				  
		self.fillMenus(commands)
		id = wx.NewId()
		self.menus["Data"].AppendCheckItem(id, "Show Subdata in Viewer")
		wx.EVT_MENU(self, id, self.dvShowNested)
		self.menus["Data"].Check(id, bool(self.dv.preferences["Display Nested Data to Depth"]))
		self.dv.preferences['Show Only Same Length Data']=True
		self.template=None
		self.spikes=None
		self.preferences={}
		self.components=['scale', 'shift', 'spikes', 'waves', 'template', 'shiftjitter']
		self.discriminant=None
		self.error_func=None
		self.preferences={"Threshold Level":.08, 
			"Template Lead (ms)":1.3,
			"Template Length":3.0,
			"Full Logging":1.0,
			"Remove Shifts on Template Exit":0,
			"Save Raw Waves":1,
			"Screen Width":1600,
			"Screen Height":1200}
		self.current_spike=-1	

		lpan=wx.BoxSizer(wx.VERTICAL)
		self.main.SetSizer(lpan)
		cbox = wx.BoxSizer(wx.HORIZONTAL)
		reload(discriminants)
		DISC_FUNCTIONS.update(discriminants.DISC_FUNCTIONS)
		modes = DISC_FUNCTIONS.keys()
		cbox.Add(wx.StaticText(self.main, -1, "Discriminant"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		self.chooseMode = wx.Choice(self.main, -1, choices=modes)
		self.inMode = "Mean"
		self.chooseMode.SetSelection(modes.index("Mean"))
		cbox.Add(self.chooseMode, 5, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		cbox.Add(wx.StaticText(self.main, -1, "Params"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		self.discPars= wx.TextCtrl(self.main, -1, "None", style=wx.TE_PROCESS_ENTER, size=(12,-1))
		wx.EVT_TEXT_ENTER(self.main, self.discPars.GetId(), lambda x:self.update_self())
		cbox.Add(self.discPars, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		wx.EVT_CHOICE(self.main, self.chooseMode.GetId(), self.doSelectMode)
		cbox.Add(wx.StaticText(self.main, -1, "Show Error"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		ERROR_FUNCTIONS.update(discriminants.ERROR_FUNCTIONS)
		ERROR_FUNCTIONS.update(discriminants.DISC_FUNCTIONS)
		modes = ERROR_FUNCTIONS.keys()
		self.showErr = wx.Choice(self.main, -1, choices=modes)
		self.errMode = "None"
		self.showErr.SetSelection(modes.index("None"))
		wx.EVT_CHOICE(self.main, self.showErr.GetId(), self.doSelectErr)
		cbox.Add(self.showErr, 5, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		cbox.Add(wx.StaticText(self.main, -1, "Params"), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
		self.errPars= wx.TextCtrl(self.main, -1, "None", style=wx.TE_PROCESS_ENTER, size=(12,-1))
		wx.EVT_TEXT_ENTER(self.main, self.errPars.GetId(), lambda x:self.update_self())
		cbox.Add(self.errPars, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 1)
		btn = wx.Button(self.main, -1, " Analysis Window ")
		cbox.Add(btn, 0, wx.ALIGN_BOTTOM|wx.ALL, 5)
		wx.EVT_BUTTON(self.main, btn.GetId(), self.launchAnalysis)
		
		lpan.Add(cbox, 0, wx.GROW|wx.ALIGN_TOP|wx.ALL, 5)
		cbox = wx.BoxSizer(wx.HORIZONTAL)
		btn = wx.Button(self.main, -1, " Del Spike ")
		cbox.Add(btn, 0, wx.ALIGN_BOTTOM|wx.ALL, 5)
		wx.EVT_BUTTON(self.main, btn.GetId(), self.delSpike)
		btn = wx.Button(self.main, -1, " Add Spikes ")
		cbox.Add(btn, 0, wx.ALIGN_BOTTOM|wx.ALL, 5)
		wx.EVT_BUTTON(self.main, btn.GetId(), self.addSpikes)
		btn = wx.Button(self.main, -1, " Previous ")
		cbox.Add(btn, 0, wx.ALIGN_BOTTOM|wx.ALL, 5)
		wx.EVT_BUTTON(self.main, btn.GetId (), self.lastSpike)
		btn = wx.Button(self.main, -1, " Next ")
		cbox.Add(btn, 0, wx.ALIGN_BOTTOM|wx.ALL, 5)
		wx.EVT_BUTTON(self.main, btn.GetId(), self.nextSpike)
		self.spikeInfo=wx.StaticText(self.main, -1, " No Spikes ")
		cbox.Add(self.spikeInfo, 0, wx.ALIGN_BOTTOM|wx.ALL, 5)
		self.rgraph=GraphFSR(self.main, -1)
		lpan.Add(self.rgraph, 3, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		cbox.SetMinSize((100,40))
		lpan.Add(cbox, 0, wx.GROW|wx.ALIGN_BOTTOM|wx.ALL, 5)	
		
		self.load_saved_prefs()

		sw=self.preferences['Screen Width']
		sh=self.preferences["Screen Height"]
		dvw=round(3*sw/4.0)
		dvh=round(.55*sh)
		self.last_shifts=None

		self.dv.SetDimensions(0, 0, dvw, dvh)		
		gsize=self.dv.graph.GetSize()
		gsize=(gsize[0], round(gsize[1]/1.5))
		fsize=(round(gsize[0]*1.3), gsize[1]+200)
		
		self.rgraph.limit(self.dv.graph.limits)
		self.rgraph.fs=self.dv.graph.fs
		#self.rgraph.SetSize(gsize)
		
		self.main.SetSizer(lpan)
		self.SetDimensions(0, dvh, dvw, sh-dvh)
		#self.main.SetClientSize(self.main.GetBestSize())
		
		self.dv.graph.linked_graphs.append(self.rgraph)
		self.rgraph.linked_graphs.append(self.dv.graph)
		
		#self.CentreOnParent(wx.HORIZONTAL)
		
		self.dv.preferences["Number of Undo Steps"]=0
		self.dv.data.setUndoLength(0, True)
		self.dv.report('Spike Sorter Disabled Undo. Use Checkpoints Instead.')
		
		temps=self.dv.data.getElements('Data', 'spikesorter_setup',depth=1)
		if not temps:
			self.condition_data()
		csfd=self.dv.data.getElements('Data', 'spikesorter_shiftstate', depth=1)
		if csfd:
			self.shiftstate_record=csfd[0]
		else:
			self.shiftstate_record=writeShifts(self.dv.data, zeros(self.dv.data.data.shape[1]))
		self.chooseTemp('auto')
		#self.dv.setcheck(None, 'StartSpikeSorter')
 		
		lpan.Layout()
		self.update_self()
		self.Show(True)
		
		
	def __del__(self):
		try:
			self.release_template()
		except:
			pass			
		
		
	# def alignMinProf(self, event):
	# 	profile.runctx('self.alignMin(None)', globals(), locals())
		
	def log(self, s):
		if not self.preferences["Full Logging"]:
			return
		ts=time.strftime("%m/%d/%y-%H:%M:%S - ")
		s=ts+s
		print s
		try:
			tdi=self.dv.data.getSubData(self.template)
			tdi.addComment(s)
		except:
			self.report("Warning: can't log to template. Something is VERY wrong. You should probably restart")
		
	def getSpikes(self, event):
		d=self.load(returndoc=True)
		ct=d.getElements('Data')
		ct = [e for e in ct if isSampledType(e)=='e']
		if not ct:
			self.report("The are no events in this data file")
			return
		el={}
		for e in ct:
			if e.stype()=='events':
				n=e.getLabels()[0]
				if "- " in n:
					n=n.split("- ")[-1]
				if el.has_key(n):
					un="%s - %s" % (e.dpath(), n)
					self.report('warning: event element %s defines events for unit name %s redundantly. Renaming to %s' % (e.dpath(), n, un))
					n=un
				el[n]=e
			else:
				for i in range(e.shape()[1]):
					n=e.getLabels()[i]
					if "- " in n:
						n=n.split("- ")[-1]
					if el.has_key(n):
						un="%s(%i) - %s" % (e.dpath(), i, n)
						self.report('warning: event element %s channel %i defines events for unit name %s redundantly. Renaming to %s' % (e.dpath(), i, n, un))
						n=un
					el[n]=getLabeledEvent(e, i)

		temps=self.dv.data.getElements('Data', depth=1)
		tns=[foo.name() for foo in temps if foo.name().startswith('spikesort_')]	
		for k in el.keys():
			tn="spikesort_%s" % k
			if tn in tns:
				self.chooseTemp(tn)
			else:
				self.newTemp(k)		
			self.dv.data.createSubData('/'+tn+'/spikes', el[k].getData(), el[k].header(),  delete=True)
			otemp=self.dv.data.getSubData('/'+tn+'/template')
			if otemp:
				otemp.setName('old_template')
				
			nevts=el[k].getData().shape[0]				
			if nevts:
	 			sil="%i spikes" % (nevts, )
			else:
				sil="No Spikes"		
			self.report("Assigned %i spikes to template %s" % (nevts, tn))	
			self.spikeInfo.SetLabel(sil)
			self.calc_templ()
			self.update_all(object=self.dv.data.getSubData('/'+tn+'/spikes'), nossrecalc=True)
		self.log('imported spikes')
					
		
	def dvShowNested(self, event):
		ic=event.IsChecked()
		if ic:
			self.dv.preferences["Display Nested Data to Depth"]=4
		else:	
			self.dv.preferences["Display Nested Data to Depth"]=0
		self.dv.onSetPreferences()
			
	def exportSpikes(self, event):
		tems=[d for d in self.dv.data.getElements('Data', depth=1) if d.name().startswith('spikesort_')]
		tems.sort(sortByOrder)
		sst=[d.getSubData('spikes') for d in tems if d.getSubData('spikes')]
		if not sst:
			self.report("No Spikes")
			return
		opts=self.askParam([{'Name':"Export where?", "Type":"List",
			"Value":["New disk file", "Top level of current file"]},
			{"Name":"Move or Copy", "Type":"List", "Value":["Copy", "Move"]},
			{"Name":"Target Format", "Type":"List",
			"Value":["Labled Events", "Multiple Event Records"]},
			{"Name":"Include Stimulus", "Type":"List", "Value":["True","False"]}])
		if not opts:
			return
		delete=(opts[1]=='Move')
		if opts[0]=="New disk file":
			new=blankDocument()
		else:
			new=self.dv.data		
		if opts[2]=='Multiple Event Records':
			for sp in sst:
				if delete:
					sp.move(new)
				else:
					new.newElement(sp.clone())
		else:
			print [d.dpath() for d in sst]
			spnames=[d.dpath() for d in sst]	
			combine(self.dv.data, spnames, newpath='/sortedEvents', newtype='labeledevents', delete=delete)	
		if opts[0]=="New disk file":
			if opts[2]=="Labled Events":
				evts=self.dv.data.getSubData('/sortedEvents')
				evts.move(new)
				try:
					evts.setAttrib("datafile", self.dv.document.fileinformation["filename"])
				except:
					pass
				d1=evts
			else:
				d1=new
			if opts[3]!=False:
				s=opts[3].strip("'")
				s=s.strip('"')
				stim=self.dv.data.getSubData(s)
				if stim:
					stim=stim.clone()
					stim.setAttrib('Name', 'stimulus')
					d1.newElement(stim)				
			self.save(doc=new)
		self.log("export spikes %s" % (repr(opts),))
					
	def exportTemps(self, all=False):
		sst=self.dv.data.getElements('Data', 'spikesorter_setup', depth=1)+[d for d in self.dv.data.getElements('Data', depth=1) if d.name().startswith('spikesort_')]	
		if not sst:
			self.report("No Templates")
			return
		new=blankDocument()
		if all:		
			for t in sst:
				new.newElement(t.clone(True))
		else:
			for t in sst:
				tc=t.clone(False)
				for n in ['shift', 'template', 'shiftjitter', 'idealspike']:
					st=t.getElements('Data', n)
					if st:
						st=st[0].clone(True)
						if st.attrib('Applied'):
							st.setAttrib('Applied', 0)
						tc.newElement(st.clone(True))
				new.newElement(tc)	
		self.save(doc=new)
		self.log("exportTemps(%s)" % (str(all),))

	def hideDvSpikes(self, hide):
		if hide:
			if not "spikesort_" in self.dv.preferences["Hide Data In"]:
				self.dv.preferences["Hide Data In"].append("spikesort_")
				self.dv.onNewData()
		else:
			if "spikesort_" in self.dv.preferences["Hide Data In"]:
				self.dv.preferences["Hide Data In"].remove("spikesort_")
				self.dv.onNewData()
		
	def onClose(self,event):
		try:
			self.dv.graph.linked_graphs.remove(self.rgraph)
		except:
			raise
		self.release_template()	
		self.Destroy()
		
	def release_template(self):
		if not self.template:
			return 
		if self.preferences["Remove Shifts on Template Exit"]:
			self.unShift()	
		self.log('release_template')
		self.template=None	
		self.update_analysis(['Template'])
		
	def doSelectMode(self, event):
		self.inMode= event.GetString()
		self.update_self()	

	def doSelectErr(self, event):
		self.errMode= event.GetString()
		self.update_self()		

	def newTemp(self, event):
		self.current_spike=-1	
		order=0
		last=self.template
		fix=[]
		if last:
			temps=self.dv.data.getElements('Data', depth=1)
			for i in temps:
				if not i.name().startswith('spikesort_'):
					continue
				o=i.attrib('Order')
				if o == None:
					fix.append(i)
					continue
				order = max(order, o+1)
			for i, f in enumerate(fix):
				self.report("Warning! Templates %s has ill-defined order. This is a bad thing. Assigning it order %i, but batch sorting will be broken anyway" % (f.name(), i+order))
				f.setAttrib('Order', i+order)
			last=self.dv.data.getSubData(last)
		if type(event)==str:
			tn="spikesort_%s" % event
		else:	
			l=self.askParam([{"Name":"Template Name", "Value":"unit%i" % order}])
			if not l:
				return
			tn="spikesort_%s" % l[0]
		self.release_template()	
		if self.dv.data.getSubData(tn):
			c=self.askUsr("Element %s exists. Overwrite?" % tn, ['Yes', 'No'])
			if c=="No":
				self.report('Canceled')
				return
			sd=self.dv.data.getSubData(tn)
			sd.sever()
		head={'SampleType':'group', 'Note':'SpikeSorter Template', 'Order':order, 'subtracted':0}
		self.dv.data.createSubData(tn, head=head)
		self.template=tn
		self.log('newTemp')
		self.update_self()	
		self.update_analysis(['Template'])
		self.report("Active template is %s" % tn)
		
	def import_template(self):
		d=self.load(returndoc=True)
		ct=d.getElements('Data', 'spikesorter_setup', depth=1)
		if not ct:
			return None
		else:
			ct=ct[0]	
		self.dv.data.newElement(ct)
		precondition(self.dv.data, ct, self.report)
		for tem in d.getElements('Data', depth=1):
			if tem.name().startswith('spikesort_'):
				self.report('Importing template %s' % (tem.name(),))
				self.dv.data.newElement(tem)
		self.update_all(object=self.dv.data, ss_ignore=True)
		return True	
		
	def condition_data(self, event=None):
		def dvChanBrowse(master, dict, control):
			chans=master.selectChannels()
			if chans:
				control.SetValue(repr(chans))
		nchans=self.dv.data.shape()[1]
		z=None
		while not z:
			m=self.dv.askUsr("Would you like to import existing templates?", ['No', 'Yes'])
			if m=='Yes':
				z=self.import_template()
				if z:
					return
				else:
					self.report("Couldn't get templates from external file")
			else:
				z=1		
		d=self.dv.askParam([{"Name":"Remove Mean",
							"Type":"List",
							"Value":["Yes", "No"]},
							{"Name":"Set Start Time to 0",
							"Type":"List",
							"Value":["Yes", "No (_Will_ cause detection errors!)"]},
							{"Name":"Normalize on Noise Amplitude",
												"Type":"List",
												"Value":["Yes", "No"]},
							{"Name":"Stimulus Channels",
							"Value":[nchans-6, nchans-5, nchans-4, nchans-3, nchans-2, nchans-1],
							'Browser':dvChanBrowse},
							{"Name":"Delete Channels",
							"Value":[5,6],
							'Browser':dvChanBrowse},
							])
		if not d:
			self.dv.report("Condtioning data is required to use the spike sorter")
			self.onClose()
			return
		head={'SampleType':'group'}
		if d[0]=='Yes':
			head['zeroMean']=1
		else:
			head['zeroMean']=0
		if d[1]=='Yes':
			head['zeroStart']=1
		else:
			head['zeroStart']=0
		if d[2]=='Yes':	
			head['normalize']=1
		else:
			head['normalize']=0
		if d[3]:
			head['stimulus']=d[3]
		else:
			head['stimulus']=[]
		if d[4]:
			kill=[]
			for c in d[4]:
				for c2 in head['stimulus']:
					if c2<=c:
						c-=1
				kill.append(c)
			head['deleted']=kill
		self.dv.data.createSubData('/spikesorter_setup', head=head, delete=True)
		ct=self.dv.data.getElements('Data', 'spikesorter_setup', depth=1)[0]
		precondition(self.dv.data, ct, self.report)
		self.update_all(object=self.dv.data, ss_ignore=True)


	def userSelectTemplate(self):
		temps=self.dv.data.getElements('Data', depth=1)
		temps=[foo for foo in temps if foo.name().startswith('spikesort_')]
		tns=[foo.name() for foo in temps]
		if not temps:
			self.report('No templates in this data set')
			return None
		elif len(tns)==1:
			tn=tns[0]
		else:	
			l=self.askParam([{"Name":"Select Template", "Type":"List", "Value":tns}])
			if not l:
				return	
			tn=l[0]
		return tn
	
	def chooseTemp(self, event):
		self.current_spike=-1	
		if type(event)==str:
			if event!='auto':
				tn=event
			else:
				temps=self.dv.data.getElements('Data', depth=1)
				temps=[foo for foo in temps if foo.name().startswith('spikesort_')]
				if not temps:
					self.newTemp('unit0')
					tn=None
				else:
					temps.sort(sortByOrder)
					tn=temps[-1].name()			
		else:	
			tn= self.userSelectTemplate()
		print tn
		if tn==None:
			return
		if not self.template==tn:
			self.release_template()	
			self.template=tn
		shifts=self.dv.data.getSubData(tn+"/shift")
		if shifts:
			self.setShiftState(shifts.getData()[:,0], False)
		else:
			self.update_self()	
		self.update_analysis(['Template'])
		self.report("Active template is %s" % self.template)
		self.log('chooseTemp')
		
	def setShiftState(self, shifts, rel=False):
		self.last_shifts=self.dv.data.getSubData("/spikesorter_shiftstate").getData()[:,0]
		blockShift(self.dv.data, shifts, rel)
		self.report("Set shifts")
		self.log("setShiftState %s" % repr(self.dv.data.getSubData("/spikesorter_shiftstate").getData()[:,0])) 
		tn=self.template
		try:
			self.update_all(object=self.dv.data, calc_offsets=False)
		except TypeError:
			#Here we have your basic WTF bug. Somehow, on relaunch only, the identiy of self changes during update_all, and self.template for the new self is None, causing a TypeError in update_self->getTemp. WTF?
			self.template=tn
			self.update_self(object=self.dv.data, calc_offsets=False)	
		
				
	def applyShift(self, event):
		tn=self.userSelectTemplate()
		shifts=self.dv.data.getSubData(tn+"/shift")
		if not shifts:
			self.report("Can't Apply. Selected template has no shift data.")
			return
		self.setShiftState(shifts.getData()[:,0], False)

	def unShift(self, event=None):
		self.setShiftState(zeros(self.dv.data.shape()[1]), False)
		
	def reShift(self, event=None):
		if self.last_shifts==None:
			self.report("No stored shifts")
			return
		lss=self.last_shifts.copy()
		self.setShiftState(lss, False)
		
	def getTemp(self, comp):
		try:
			t=self.dv.data.getSubData(self.template)
			if not t:
				raise
		except:
			self.chooseTemp('auto')
			t=self.dv.data.getSubData(self.template)
		if comp:
			n=self.template+"/"+comp
			return (n, self.dv.data.getSubData(n))
		else:	
			return t	
			
	def tempRef(self, comp):
		tn=self.getTemp(comp)
		if tn[1]:
			tn[1].sever()
		return tn[0]

	def getSelect(self):
		r=self.rgraph.limits[:2]
		r=round((r-self.dv.data.start())*self.dv.data.fs())
		r[0]=max(0, r[0])
		r[1]=min(self.dv.data.shape()[0], r[1])
		r=tuple(r)
		return(None, None, r)
	
	def calc_disc(self):
		pars=parseParams(self.discPars.GetValue())
		temp=self.getTemp(None)
		disc=DISC_FUNCTIONS[self.inMode](self.dv.data.getData(), pars, temp)	
		temp._error_cache=None
		if disc==None:
			self.report("Falling back to 'Mean' discriminant function")
			self.inMode=='Mean'
			self.chooseMode.SetSelection(self.chooseMode.GetStrings().index("Mean"))
			disc=mean(self.dv.data.getData(), 1)
		self.discriminant=disc	
		del(temp._cache)
	 
	def calc_error(self):
		pars=parseParams(self.errPars.GetValue())
		self.error_func=None
		temp=self.getTemp(None)
		temp._cache={"ll":self.getLL()}
		er=ERROR_FUNCTIONS[self.errMode](self.dv.data.getData(), pars, temp)
		temp._cache['error']=(self.errMode, pars, er)
		if self.errMode!='None' and er==None:
			self.report('Error measure function failed')
		else:
			self.error_func=er
			
	def update_self(self, **kwargs):
		#print "called update"
		if kwargs.get('ss_ignore'):
			return
		self.rgraph.plots={}
		self.rgraph.ymarkers=[]
		if not kwargs.get('nossrecalc'):
			self.calc_error()
			self.calc_disc()
		disc=self.discriminant

		opts={"name":"discriminant", "style":"envelope",
			'start':domain(self.dv.data)[0]}
		self.rgraph.addPlot(disc, **opts)
		err=self.error_func
		if err!=None:
			opts={"name":"error", "style":"envelope",
				'start':domain(self.dv.data)[0]}
			self.rgraph.addPlot(err, **opts)
			ma=max(err.max(), disc.max())
			mi=min(err.min(), disc.min())
		else:
			ma=disc.max()
			mi=disc.min()
		pad=float(max(.0001, ma-mi))
		pad*=.05
		self.rgraph.limits[2]=mi-pad	
		self.rgraph.limits[3]=ma+pad
			
		#print self.rgraph.limits	
		spi=self.getTemp('spikes')
		if spi[1]:
			dat=spi[1].getData()
			n=self.template.split("_")[-1]
			opts={"name":n, "style":"evts",
				'start':domain(self.dv.data)[0],
				'color':(250, 0, 0)}
			self.rgraph.addPlot(dat, **opts)	
			if self.current_spike>-1:
				sil="%i of %i spikes" % (self.current_spike+1, dat.shape[0])
			else:
				sil="%i spikes" % (dat.shape[0],)
		else:
			sil="No spikes"
		self.spikeInfo.SetLabel(sil)	
		tdi=self.dv.data.getSubData(self.template)
		if tdi:
			tht=tdi.attrib('Thresholds')
			if tht:
				color = wx.Color(250,0,250)
				self.rgraph.ymarkers.append({"loc":tht[0], "color":color})
				self.rgraph.ymarkers.append({"loc":tht[1], "color":color})
		try:
			self.rgraph.DrawAll()
		except:
			pass
			
	def update_analysis(self, what):
		pass
		
	def launchAnalysis(self, event):
		a=SSAnalysis(self)
		a.Show(True)
		
	def calc_templ(self):
		en=self.tempRef('waves')
		tn=self.tempRef('template')
		spi=self.getTemp('spikes')
		if spi[1]:
			evts=spi[1].getData()[:,0]
			lead=self.preferences["Template Lead (ms)"]
			length=self.preferences["Template Length"]
			eventCondition(self.dv.data, spi[0], (None, None, None), lead, length, en)
			ei=self.getTemp('waves')
			if ei[1]:
				ensembleStats(self.dv.data, ei[0], tn, 2)
			else:
				self.report("No events")
			if not self.preferences["Save Raw Waves"]:
				en=self.tempRef('waves')
		self.update_analysis('template')
		
	def alignMin(self, event):
		temp=alignMinima(self.dv.data, self.getSelect())
		self.setShiftState(temp, True)

	
	def alignMarks(self, evt, reverse=False):
		q=self.dv.getMarkIndexes()
		if q.shape[0]<2:
			self.report("Need 2 markers")
			return 
			q=q[-2:]
		else:
			q=q[-2:]
			ns=(max(q)-min(q))/self.dv.data.shape()[1]
		if ns==0:
			self.report("No shift specified")
			return
		if not reverse:
			ns=-1*ns
		temp=arange(self.dv.data.shape()[1])*ns	
		self.setShiftState(temp, True)
			
	def	realignTemp(self, evt):
		tem=self.getTemp('template')
		if not tem[1]:
			self.report("No wave template")
			return	
		stn=self.getTemp('shift')
		td=tem[1].getData()
		mc=range(0, td.shape[1], 2)
		temp=alignMinima(self.dv.data, (tem[0], mc, None))
		self.setShiftState(temp, True)
		self.report("Shift Done. You will need to re-detect spikes, or recalucalate template to change the template")

	def getLL(self):
		"""return (lead, length) correctly"""
		tem=self.getTemp('template')
		if tem[1]:
			lead=tem[1].attrib('Lead')
			length=tem[1].getData().shape[0]
		else:
			lead=round(self.dv.data.fs()*self.preferences["Template Lead (ms)"]/1000.0)
			length=round(self.dv.data.fs()*self.preferences["Template Length"]/1000.0)
		return (lead, length)

	def djTemp(self, evt):
		spi=self.getTemp('spikes')
		if not spi[1]:
			self.report("Requires spikes.")			
			return
		st=spi[1].getData()	
		lead, length=self.getLL()
		dat=self.dv.data.getData()
		out=zeros((st.shape[0], dat.shape[1]-1))
		for i, s in enumerate(st):
			ds=dat[s-lead:s-lead+length,:]
		 	temp=zeros(ds.shape[1], int32)
			for j in range(ds.shape[1]):
				temp[j]=argmin(ds[:,j])
				
			temp=-1*(temp-temp[0])[1:]
			out[i,:]=temp
		if out.shape[0]<10:	
			print out
		me=out.mean(0)
		print me
		sd=out.std(0)
		print sd
		path=self.getTemp('shiftjitter')[0]
		self.dv.data.createSubData(path, out, {'SampleType':'generic'}, True)
		self.update_analysis(['Template', 'Jitter'])
		self.log('djTemp')
		return out

	def optimTemp(self, event):
		out=self.djTemp(None)
		self.setShiftState(out, True)			
	
	def autoThresh(self, event=None):
		dat=self.discriminant
		mi=dat.min()
		me=dat.mean()
		sd=dat.std()
		tl=self.preferences["Threshold Level"]
		lt=me-(abs(mi-me)*(1.0-tl))
		ht=me-3*sd
		if ht<lt:
			self.report("Warning: data are too noisy!")
			print lt, ht, mi, me, sd
			ht=(lt+me)/2
		tdi=self.dv.data.getSubData(self.template)
		tdi.setAttrib('Thresholds', [ht, lt])
		self.report("set thresholds %s" % (str([ht, lt]),))
		if event:
			self.update_self(nossrecalc=True)
			
	def markThresh(self, event):
		q=[foo['loc'] for foo in self.rgraph.ymarkers]
		if len(q)<2:
			self.report("Need 2 markers")
			return 
		tdi=self.dv.data.getSubData(self.template)
		tdi.setAttrib('Thresholds', [q[-2], q[-1]])
		self.report("set thresholds %s" % (str([q[-2], q[-1]]),))
		self.update_self(nossrecalc=True)
		
	def doDetect(self, event):
		self.current_spike=-1	
		tdi=self.dv.data.getSubData(self.template)
		tdi.setAttrib('Discriminant', self.inMode)
		tdi.setAttrib('DiscriminantParameters', self.discPars.GetValue())
		tht=tdi.attrib('Thresholds')
		tdi.setAttrib('ManualCorrection', 0)
		if not tht:
			self.markThresh(None)
			tht=tdi.attrib('Thresholds')
			if not tht:
				self.autoThresh()
				tht=tdi.attrib('Thresholds')
		spikes=self.tempRef('spikes')
		evts=schmitTrigger(self.discriminant, tht[0], tht[1])
		writeSpikeData(self.dv.data, evts, self.template+"/spikes", False, lab=self.template)
		evts=self.dv.data.getSubData(spikes)
		if evts:
 			sil="%i spikes" % (evts.getData().shape[0], )
		else:
			sil="No Spikes"
		self.spikeInfo.SetLabel(sil)
		shifts=self.dv.data.getSubData("/spikesorter_shiftstate").getData()	
		writeShifts(self.dv.data, shifts, self.template+"/shift")
		self.calc_templ()
		self.update_all(object=evts, nossrecalc=True)
		self.log('detect %s'  % (repr(tht),))

	def recalcTemp(self, event):	
		self.calc_templ()
		tdi=self.dv.data.getSubData(self.template)
		self.update_all(object=tdi, nossrecalc=True)
		self.log('recalcTemp')

	def delSpike(self, event):
		if self.current_spike<0:
			self.report("Select a spike first")
			return
		spi=self.getTemp('spikes')	
		if not spi[1]:
			self.report("No spikes")
			self.current_spike=-1
			return
		evts=spi[1].getData()
		if self.current_spike>=evts.shape[0]:
			self.report("Selected spike doesn't exist")
			self.current_spike=-1
			return
		if self.current_spike==0:
			evts=evts[1:]
		elif self.current_spike==evts.shape[0]-1:
			evts=evts[:-1]
		else:
			evts=concatenate([evts[:self.current_spike], evts[self.current_spike+1:]])
		spi[1].datinit(evts, spi[1].header())
		self.log('delSpike %i' % (self.current_spike,))	
		self.current_spike-=1
		if self.current_spike <=0:
			self.current_spike=0
		tdi=self.dv.data.getSubData(self.template)
		tdi.setAttrib('ManualCorrection', 1)
		sil="%i of %i spikes" % (self.current_spike+1, evts.shape[0])
		self.spikeInfo.SetLabel(sil)	
		self.update_all(object=spi[1], nossrecalc=True, calc_offsets=False)
		self.calc_templ()
		
	def setDetectedEvents(self, evts):
		self.current_spike=-1	
		tdi=self.dv.data.getSubData(self.template)
		tdi.setAttrib('ManualCorrection', 1)
		spi=self.getTemp('spikes')	
		spi[1].datinit(evts, spi[1].header())
		sil="%i spikes" % (evts.shape[0], )
		self.spikeInfo.SetLabel(sil)	
		self.update_all(object=spi[1], nossrecalc=True, calc_offsets=False)
		self.calc_templ()
		self.log('setDetectedEvents %s'  % (repr(evts),))
	
	def addSpikes(self, event):
		spi=self.getTemp('spikes')	
		if not spi[1]:
			self.report("No spikes")
			return
		q=[m['loc'] for m in self.rgraph.xmarkers]
		if not q:
			self.report("No markers")
			return
		q.sort()
		q=(array(q)-self.dv.data.start())*self.dv.data.fs()
		q=round(q)	
		evts=unique1d(concatenate([spi[1].getData(), reshape(q, (-1,1))]))
		spi[1].datinit(evts, spi[1].header())
		self.current_spike=-1
		tdi=self.dv.data.getSubData(self.template)
		tdi.setAttrib('ManualCorrection', 1)
		sil="%i spikes" % (evts.shape[0], )
		self.spikeInfo.SetLabel(sil)	
		self.update_all(object=spi[1], nossrecalc=True, calc_offsets=False)
		self.calc_templ()
		self.log('addSpikes %s' % (repr(evts),))	
		
	def lastSpike(self, event):
		self.current_spike-=1
		self.show_spike()
		
	def nextSpike(self, event):
		self.current_spike+=1
		self.show_spike()
		
	def clearSpikes(self, evt):
		spi=self.getTemp('spikes')	
		if spi[1]:
			spi[1].sever()
			del(spi)
			self.current_spike=-1
			self.update_all(object=self.dv.data, nossrecalc=True, calc_offsets=False)	
			self.calc_templ()
		self.spikeInfo.SetLabel("No Spikes")
		self.log('clearSpikes')	
	
	def getSelectedSpikeWindow(self, index=False):
		spi=self.getTemp('spikes')	
		if not spi[1]:
			self.current_spike=-1
			self.report("No spikes")
			return None
		evts=spi[1].getData()
		if not evts.shape[0]:
			self.current_spike=-1
			self.report("No spikes")
			return None
		if self.current_spike<0 or self.current_spike>=evts.shape[0]:
			self.current_spike=0
		ind=evts[self.current_spike]
		lead=self.preferences["Template Lead (ms)"]/1000.0
		length=self.preferences["Template Length"]/1000.0
		if index:
			lead=round(lead*self.dv.data.fs())
			length=round(length*self.dv.data.fs())
			lims=[ind-lead, ind-lead+length]
		else:
			et=domain(self.dv.data)[0]+ind/self.dv.data.fs()
			lims=[et-lead, 0]
			lims[1]=lims[0]+length
		return lims
						
	def show_spike(self):
		z=self.getSelectedSpikeWindow()
		if not z:
			return
		lims=self.rgraph.limits[:]
		lims[0], lims[1]=z
		self.rgraph.limit(lims)
		if self.inMode=='Spike Match':
			self.update_self()
		else:	
			self.rgraph.DrawAll()
		
		spi=self.getTemp('spikes')	
		evts=spi[1].getData()
		sil="%i of %i spikes" % (self.current_spike+1, evts.shape[0])
		self.spikeInfo.SetLabel(sil)
		self.update_analysis('selectspike')	
		
	def setIdeal(self, event):
		z=self.getSelectedSpikeWindow(True)
		if not z:
			return
		spi=self.getTemp('spikes')	
		evt=self.dv.data.getData()[z[0]:z[1],:].copy()
		path=self.getTemp('idealspike')[0]
		self.dv.data.createSubData(path, evt, {'SampleType':'generic'}, True)
		self.log('setIdeal %i' % self.current_spike)
		self.report("ideal spike recorded")
		
	def removeTemp(self, evt, md='subtract'):	
		spi=self.getTemp('spikes')
		if not spi[1]:
			self.report("No events")
			return	
		tem=self.getTemp('template')
		if not tem[1]:
			self.report("No wave template")
			return	
		tdi=self.dv.data.getSubData(self.template)	
		nsub=tdi.attrib('subtracted')
		if nsub==None:
			tdi.setAttrib('subtracted', 0)
			nsub=0
		if md=="add":
			md=True
			if nsub<1:
				a=self.askUsr("this template is not currently subtracted. Are you sure you want to add it back?", ["Yes", "No"])
				if a=="No":
					return		
		else:
			if nsub>0:
				a=self.askUsr("this template is already subtracted once. Are you sure you want to do it again?", ["Yes", "No"])
				if a=="No":
					return
			md=False
		
		shi=self.getTemp('shift')
		if not all(shi[1].getData()==self.dv.data.getSubData("/spikesorter_shiftstate").getData()):
			self.self.askUsr("The current shift state is different than the one that created this template. Adding or subtracting the template will produce data that can't be batch sorted. Continue?", ["Yes", "No"])
			if a=="No":
				return
			self.log('ILLEGAL USE OF TEMPLATE REMOVAL')
		subtractTemplate(self.dv.data, spi[1].getData()[:,0], tem[1], md)
		if md:
			tdi.setAttrib('subtracted', nsub-1)
		else:
			tdi.setAttrib('subtracted', nsub+1)
		self.update_all(object=self.dv.data, calc_offsets=False)
		
		self.log('removeTemp %s' % (md,) )
	
	def blankTemps(self, evt):
		spi=self.getTemp('spikes')
		if not spi[1]:
			self.report("No events")
			return	
		evts=spi[1].getData()	
		lead, length=self.getLL()
		evts=evts-lead
		dat=self.dv.data.getData(copy=True)
		for ind in evts:
			dat[ind:ind+length]=0.0
		self.dv.data.setData(dat)	
		tdi=self.dv.data.getSubData(self.template)
		tdi.setAttrib('blanked', [lead, length])
		self.update_all(object=self.dv.data, calc_offsets=False)
		self.log('blankTemps')
		
	def blankView(self, event):
		blank(self.dv.data, self.getSelect())
		self.update_all(object=self.dv.data, calc_offsets=False)
		self.log('blankView %s' % (repr(self.getSelect()),) )
		
	def pcaTemp(self, event):
		try:
			templatePCA(self.dv.data, self.template)
			self.report('Calculated PCA')	
		except:
			raise
			self.report('Cant calculate PCA (Do you have waveforms for this template?')
		
def ProfSS(dv):
	l=[]
	profile.runctx("l.append(PASpikeSorter(dv))", globals(), locals())
	return l[0]
