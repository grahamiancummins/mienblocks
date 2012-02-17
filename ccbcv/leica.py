#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2008-06-23.

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

from numpy import array, transpose, where
import mien.nmpml.data as mdat
import re

	# 
	# def load(self, event=None):
	# 	dlg=wx.FileDialog(self, message="Select file", defaultDir=self.cv.loaddir, style=wx.OPEN)
	# 	dlg.CenterOnParent()
	# 	if dlg.ShowModal() == wx.ID_OK:
	# 		fname=dlg.GetPath()
	# 	else:
	# 		self.report("Canceled File Load.")
	# 		return
	# 	dir, bfn=os.path.split(fname)
	# 	bfn, fext=os.path.splitext(bfn)
	# 	if fext=='.stackinfo':
	# 		pars=cPickle.load(open(fname))
	# 		pars['images']=[]
	# 		if not os.path.isfile(pars['files'][0]):
	# 			pars['files']=[os.path.join(os.path.split(fname)[0], os.path.split(f)[1]) for f in pars['files']]
	# 		for f in pars['files']:
	# 			pars['images'].append(wx.Image(f))
	# 		del(pars['files'])
	# 	else:	
	# 		files=os.listdir(dir)
	# 		cre=re.compile(r"_z(\d+)_ch\d+$") #leica multichannel extension
	# 		if not cre.search(bfn):
	# 			cre=re.compile(r"(\d+)$") #generic numerical name
	# 		m=cre.search(bfn)
	# 		if not m:
	# 			#image is not a sequence
	# 			ims=[imageSizePow2(wx.Image(fname))]
	# 		else:
	# 			sname=bfn[:-len(m.group())]
	# 			imd={}
	# 			iml=[]
	# 			for f in files:
	# 				tb, te= os.path.splitext(f)
	# 				if te!=fext or not tb.startswith(sname):
	# 					continue
	# 				lm=cre.search(tb)
	# 				if lm:
	# 					id=int(lm.groups()[0])
	# 					iml.append((id, os.path.join(dir, f)))
	# 			if len(iml)>10:
	# 				d=self.cv.askParam([
	# 								  {'Name':'%i Images' % (len(iml),),'Type':'Label'},
	# 								{'Name':'Load every nth image',
	# 								'Value':1}
	# 								])
	# 				if not d:
	# 					return
	# 				iml=[x for i, x in enumerate(iml) if not i % d[0]]
	# 			for x in iml:	
	# 				imd[x[0]]=imageSizePow2(wx.Image(x[1]))
	# 			kl=imd.keys()
	# 			kl.sort()
	# 			ims=[imd[k] for k in kl]
	# 		if not ims:
	# 			self.report('no images')
	# 			return
	# 		ul, w, h=self.cv.graph.frontPlane()
	# 		#anc=ul+self.graph.forward*self.graph.depthoffield/2.0+w/2+h/2
	# 		anc=array([0.0,0,0])
	# 	
	# 		h=ims[0].GetHeight()
	# 		w=ims[0].GetWidth()
	# 		n=len(ims)
	# 		ap=round(array([n/2.0, w/2.0, h/2.0]))
	# 		asp=float(ims[0].GetHeight())/ims[0].GetWidth()
	# 	
	# 	
	# 		d=self.cv.askParam([
	# 						  {'Name':'Image width (microns)','Value':665.4, 'Precision':2},
	# 						 {'Name':'Z aspect', 'Value':.0225, 'Precision':2},
	# 						 {'Name':'Y aspect', 'Value':asp, 'Precision':2},					     
	# 						  {'Name':'Rotation (degrees)', 'Value':0.0},
	# 						  {'Name':'Anchor Pixel (Slice#, Horiz, Vert)', 'Value':ap},
	# 						  {'Name':'Anchor coordinates', 'Value':anc, 'Precision':2}])
	# 		pars={}			      
	# 		pars['width']=d[0]
	# 		pars['zstep']=d[1]
	# 		pars['aspect']=d[2]
	# 		pars['rot']=d[3]
	# 		pars['imsize']=(n, w, h)
	# 		pars['center']=d[4].astype(int32)		
	# 		pars['anchor']=d[5].astype(float32)		
	# 		pars['images']=ims
	# 	self.cv.report("Loaded %i images" % (len(pars['images']),))
	# 	self.stacks[bfn]=pars
	# 	self.drawImageStack(bfn)
	# 

def read(f, **kwargs):
	fn=f.name
	f.close()
	name, data, header=getDem(fn)
	
	node={'tag':"Nmpml", 'attributes':{'Name':'0'}, 'elements':[], 'cdata':''}
	document = mdat.basic_tools.NmpmlObject(node)
	
	name=re.sub("\W+", "_", name)
	node={'tag':"Data", 'attributes':{'Name':name}, 'elements':[], 'cdata':''}
	dc=mdat.Data(node)
	if kwargs.get('literal'):
		header['SampleType']='sfield'
	else:
		header['SampleType']='timeseries'
		header['SamplesPerSecond']=1.0
		tm=where(data==header['elevationVoid'],data.max(), data)
		if header['elevationVoid']!=header['elevationFill']:
			data=where(data==header['elevationFill'],data.max(), data)
		mini=data.min()
		data=where(data==header['elevationVoid'], mini, data)
		if header['elevationVoid']!=header['elevationFill']:
			data=where(data==header['elevationFill'],mini, data)
		header['elevationVoid']=mini
		header['elevationFill']=mini
		header['conertedForDataViewer']=1		
	document.newElement(dc)
	dc.datinit(data, header)
	return document
	
ftype={'notes':'Reads image stacks described by the text files written by leica microscopes. Will not read .lei binary files. The extension .leica is supported for the txt format, since many other file formats use .txt',
		'read':read,
		'data type':'image data',
		'elements':['Data'],
		'extensions':['.txt', '.leica']}