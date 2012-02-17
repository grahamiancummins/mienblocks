#!/usr/bin/env python
# encoding: utf-8
#Created by Graham Cummins on 2007-06-28.

# Copyright (C) 2007 Graham I Cummins
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

from mien.wx.graphs.graphGL import *
from mien.wx.base import BaseGui
import mien, time, os, sys
from OpenGL.GLUT import *
import fibr.controls as controls
import mien.optimizers.arraystore as ast
from mien.interface.widgets import FileBrowse


class RoboGraph(GraphGL):
	def __init__(self, master):
		GraphGL.__init__(self, master)
		
		self.SetCurrent()
		self.styles['ode_sim']=self.makeSimDisplay
		self.styles['ode_cm']=self.makeCMDisplay
		self.perspective=1
		self.geomDrawingFunctions={"<type 'ode.GeomBox'>":self.drawGeomBox,
			"<type 'ode.GeomPlane'>":self.drawGeomPlane,
			"<type 'ode.GeomCapsule'>":self.drawCapsule}
		
	def addSimPlot(self, geoms, **opts):
		'''geoms is a list of ode geometry objects. These should probably be part of the same island, but thats up to the calling function.'''
		opts['boundingbox']=self.getSimBB(geoms)
		#print opts['boundingbox']
		name=self.defaults(opts)
		opts['moving']=False
		for g in geoms:
			if g.getBody():
				opts['moving']=True
				break
		opts['style']='ode_sim'
		opts['geoms']=geoms
		self.plots[name]=opts
		dl=self.makeSimDisplay(name)
		return name
		
	def addCMPlot(self, sim, **opts):
		opts['boundingbox']=None
		name=self.defaults(opts)
		opts['style']='ode_cm'
		opts['sim']=sim
		self.plots[name]=opts
		dl=self.makeCMDisplay(name)
		return name

	def makeSimDisplay(self, name):
		self.SetCurrent()
		plot=self.plots[name]
		dl=glGenLists(1)
		glNewList(dl, GL_COMPILE)
		materialColor(plot['color'])
		for g in plot['geoms']:
			gc=str(g.__class__)
			if self.geomDrawingFunctions.has_key(gc):
				glMatrixMode(GL_MODELVIEW)
				glPushMatrix()
				self.geomDrawingFunctions[gc](g)
				glPopMatrix()
			else:
				self.report("Don't know how to draw geom %s" % gc)
		glEndList()
		self.plots[name]['displaylist']=dl
		
	def makeCMDisplay(self, name):
		plot=self.plots[name]
		sim=plot['sim']
		dl=glGenLists(1)
		glNewList(dl, GL_COMPILE)
		materialColor(plot['color'])
		sp=sim.getCMP()
		sp=sp+plot.get('offset', array([0,0.0,0]))
		v=sim.getCMV()*plot.get('vscale', array([1.0,1.0,1.0]))
		self.drawSphere([sp[0], sp[1], sp[2], .2])
		glBegin(GL_LINES)
		glVertex3fv(sp)
		glVertex3fv(sp+v)
		glEnd()		
		glEndList()
		self.plots[name]['displaylist']=dl
		
	def getSimBB(self, geoms):
		geoms=[g for g in geoms if not str(g.__class__)=="<type 'ode.GeomPlane'>"]
		if not geoms:
			return array([[0,0,0],[1,1,1.0]])
		bb=array(geoms[0].getAABB())
		mini=bb[::2]
		maxi=bb[1::2]
		for g in geoms[1:]:
			bb=array(g.getAABB())
			mini=minimum(mini, bb[::2])
			maxi=maximum(maxi, bb[1::2])
		return vstack([mini, maxi])
	
	def redrawSims(self):
		for k in self.plots.keys():
			if self.plots[k]['style']=='ode_sim':
				if self.plots[k]['moving']:
					self.recalc(k)
			elif self.plots[k]['style']=='ode_cm':
				self.recalc(k)	
		self.OnDraw()	
			
	def geomTransform(self, g):
		x,y,z=g.getPosition()
		rot=g.getRotation()
		return (rot[0], rot[3], rot[6], 0.0,
				rot[1], rot[4], rot[7], 0.0,
				rot[2], rot[5], rot[8], 0.0,
				x,		y,		z,		1.0)
		
	def drawGeomBox(self, g):
		glMultMatrixd(self.geomTransform(g))
		x, y,z=g.getLengths()
		glScalef(x,y,z)
		if min([x,y,z])>1.0:
			glutWireCube(1)
		else:
			glutSolidCube(1)
		#glScalef(1.0/x, 1.0/y, 1.0/z)
		
	def drawCapsule(self, g):
		glMultMatrixd(self.geomTransform(g))
		r,l=g.getParams()
		glTranslatef(0, 0, -l/2)
		gluSphere(self.quad, r, self.slices, self.slices)
		gluCylinder(self.quad, r, r, l, self.slices, 1)
		glTranslatef(0 , 0, l)
		gluSphere(self.quad, r, self.slices, self.slices)
		
	def drawGeomPlane(self, g):
		tp=os.path.split(__file__)[0]
		tp=os.path.join(tp,'tex.jpg')
		im=wx.Image(tp)
		w=im.GetWidth()
		h=im.GetHeight()
		id=im.GetData()
		pix=fromstring(id, 'B')
		pix= reshape(pix, (w, h, 3))
		norm, d = g.getParams()
		glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
		glTexImage2Dub(GL_TEXTURE_2D,0,GL_RGB,0,GL_RGB, pix)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
		glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
		glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_REPLACE)
		glEnable(GL_TEXTURE_2D)
		glBegin(GL_QUADS)
		glNormal3f(*norm)
		glTexCoord2f(0,0)
		glVertex3f(100, 10, 0.0)
		glNormal3f(*norm)
		glTexCoord2f(0,10.0)
		glVertex3f(100, -100, 0.0)
		glNormal3f(*norm)
		glTexCoord2f(10.0,10.0)
		glVertex3f(-100, -100, 0.0)
		glNormal3f(*norm)
		glTexCoord2f(10.0,0.0)
		glVertex3f(-100, 100, 0.0)
		glEnd()
		glDisable(GL_TEXTURE_2D)
		

CROUCH=(-30.,-9.,60., -30., 9., 60., 30., -9., -45., 60., 30., 9., -45., 60.)
	
	
class RoboViewer(BaseGui):
	def __init__(self, sim=None, **kwargs):
		BaseGui.__init__(self, None, title="Robo Viewer", menus=["File", "Sim", "Controls"], pycommand=True,height=4, showframe=False)
		
		controls=[["File", "Preferences", self.setPreferences],
				  ["File", "Quit", lambda x:self.Destroy()],
				  ["File", "Save State", self.saveState],
				  ["File", "Load State", self.loadState],
				  ["Sim", "Run 1 Frame", lambda x:self.runSim(1.0, 'frame')],
				  ["Sim", "Run", lambda x:self.runSim('auto', 'sec')],
				  ["Sim", "Clear recording", self.flushRec],
				  ["Sim", "Reset", self.resetSim],
				  ["Controls", "simple posture/control", self.simpCon],
				  ["Controls", "Test random step", self.randTest],
				  ["Controls", "Test custom step", self.stepTest],
				  ["Controls", "Open Control File", self.getSteps],
				  ["Controls", "Show Control File", self.showSteps],
				]
		self.fillMenus(controls)
		self.preferenceInfo=[]
		self.preferences = {'delay':0, 'step':.005, 'frame rate':24, 'record':0, 'runtime':2.0}
		self.load_saved_prefs()

		self.mainSizer = wx.BoxSizer(wx.VERTICAL)
		self.main.SetSizer(self.mainSizer)
		self.main.SetAutoLayout(True)
		
		self.graph=RoboGraph(self.main)
		self.graph.report=self.report
		self.graph.keybindings['y']=lambda x:self.runSim(1.0, 'frame')
		
		self.mainSizer.Add(self.graph, 1, wx.GROW|wx.ALIGN_CENTRE|wx.ALL, 5)
		self.graph.Show(True)
		self.mainSizer.Fit(self.main)
		self.SetSize(wx.Size(600,700))
		self.recdir=os.path.join(os.getcwd(), 'roboviewer')
		self.frame=0
		if not os.path.isdir(self.recdir):
			os.mkdir(self.recdir)
		self.sim=sim
		from distutils.util import get_platform
		if 'linux' in get_platform():
			#this is a black magic bug workaround.
			self.addmenucommand(["File", "Init", self.postInit])
		else:
			self.postInit()
		
		
	def postInit(self, event=None):
		self.graph.addSimPlot(self.sim.geoms['env'].values())
		self.graph.addSimPlot(self.sim.geoms['bot'].values())
		self.graph.addCMPlot(self.sim)

		self.sim.setPosture(CROUCH)
		self.graph.redrawSims()
		self.graph.OnDraw()
		
		self.graph.stdView('y')
		self.graph.zoom(9)
		self.graph.hPan(-2)
		self.ipinteract(ns={'sim':self.sim, 'bod':self.sim.bodies['bot'], 'joint':self.sim.joints['bot']})
		self.stored_controls=zeros((0,20))
		

	def runSim(self,n, mode=False):
		if n=='auto':
			n=int(ceil(float(self.preferences['runtime'])/self.preferences['step']))
		elif mode=='time':
			n=int(ceil(float(n)/self.preferences['step']))
		elif mode=='frame':
			n=float(n)/self.preferences['frame rate']
			n=int(ceil(float(n)/self.preferences['step']))	
		if self.preferences['record']:
			nframes=int(ceil((1.0/self.preferences['frame rate'])/self.preferences['step']))
		for i in range(n):
			self.sim.step(self.preferences['step'])
			self.graph.redrawSims()
			if self.preferences['delay']:
				time.sleep(self.preferences['delay'])
			if self.preferences['record'] and not self.frame % nframes:
				fn=os.path.join(self.recdir, 'frame%06i.jpg' % (self.frame/nframes,))
				self.graph.screenShot(fn)
			self.frame+=1
			

	def flushRec(self, event=None):
		for f in os.listdir(self.recdir):
			os.unlink(os.path.join(self.recdir,f))
			
	def simpCon(self, event):
		a=self.askParam([{'Name':'Reach', 'Value':60.0},
						 {'Name':'Side', 'Value':0.0},
						 {'Name':'Extend', 'Value':1.0},
						{'Name':'Lead', 'Value':0},
						{'Name':'Q sym', 'Value':-1.0},
						{'Name':'S Sym', 'Value':1.0},
						{'Name':'Power', 'Value':1.0} ])
						
		if a:
			if a[-1]<=0.0:
				controls.simplifiedPosture(self.sim, a[:-1])
				self.graph.redrawSims()
			else:
				controls.concurrentControl(self.sim, a)
	
	def randTest(self, event):
		z=controls.randomStep()
		print z
		q=controls.testStep(self.sim, z, self.graph.redrawSims)
		print q
		
	def stepTest(self, event):
		fn=os.environ.get("FIBR_TEST_FILE")
		if fn:
			z=file(fn).read()
		else:
			try:	
				tp=os.path.split(__file__)[0]
				tp=os.path.join(tp,'teststep.txt')
				z=file(tp).read()
			except:
				a=self.askParam([{'Name':'File', 'Type':str, 'Browser':FileBrowse}])
				if not a:
					return
				tp=a[0]
				z=file(tp).read()
			os.environ["FIBR_TEST_FILE"]=tp
		z=z.split("##")[0]
		z=z.split()
		z=[z[i] for i in range(1, len(z), 2)]
		z=array(map(float, z))
		q=controls.testStep(self.sim, z, self.graph.redrawSims)
		print q
		
	
	def resetSim(self, event=None):	
		self.sim.reset()
		self.sim.setPosture(CROUCH)
		self.frame=0
		self.graph.redrawSims()
		
	def getSteps(self, event):
		a=self.askParam([{'Name':'File', 'Type':str, 'Browser':FileBrowse}])			
		if a:
			a=ast.ArrayStore(a[0])
			a=a.toarray()
			self.stored_controls=a[:,3:]
			self.report("loaded %i controls" % (self.stored_controls.shape[0],))
	
	def showSteps(self, event):
		a=self.askParam([{'Name':"First step", "Value":0}, {'Name':"Last step", "Value":self.stored_controls.shape[0]-1}])
		if a:
			for si in range(a[0], a[1]+1):
				self.resetSim()
				c=self.stored_controls[si,:]
				print si
				q=controls.testStep(self.sim, c, self.graph.redrawSims)
				print q

	def saveState(self, event):	
		z=self.sim.getFullState()
		z=repr(z)
		dlg=wx.FileDialog(self, message="Save to File", style=wx.SAVE)
		dlg.CenterOnParent()
		if dlg.ShowModal() == wx.ID_OK:
			fname=str(dlg.GetPath())
		else:
			self.report("Canceled")
			return	
		file(fname, 'w').write(z)
		
	def loadState(self, event):
		dlg=wx.FileDialog(self, message="Load from File", style=wx.OPEN)
		dlg.CenterOnParent()
		if dlg.ShowModal() == wx.ID_OK:
			fname=str(dlg.GetPath())
		else:
			self.report("Canceled")
			return	
		z=eval(file(fname).read())
		self.sim.setFullState(z)
		self.graph.redrawSims()

if __name__=='__main__':
	h=mien.getHomeDir()
	cd=os.path.join(h, '.mien')
	os.environ['MIEN_CONFIG_DIR']=cd
	app=wx.PySimpleApp()
	s=controls.Walker()
	z=RoboViewer(s)
	z.Show(True)
	app.MainLoop()
