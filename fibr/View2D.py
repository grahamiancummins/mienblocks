#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2007-12-10.

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


from mien.wx.graphs.graphframe import *
from mien.wx.base import BaseGui
import mien, time, os, sys
import fibr.nav as nav


class RoboGraph2D(Graph):
	def __init__(self, master):
		Graph.__init__(self, master)
		self.fixAR=1.0
		self.legend=False
		self.drawingFunctions["walls"]=self.drawWalls
		self.styleOrder=["map", "walls", "hazard", "target", "view", "xforms", "bot"]
		
	def drawWalls(self, name, data, dc):
		points = self.graphCoords(data)
		points=reshape(points, (-1,4))
		dc.SetPen(wx.Pen(self.plots[name]['color'],self.plots[name]['width'], style=wx.SOLID))
		dc.DrawLineList(points)
		
	def sortPlots(self, k1, k2):
		try:
			return cmp(self.styleOrder.index(self.plots[k1]['style']), self.styleOrder.index(self.plots[k2]['style']))
		except:
			return Graph.sortPlots(self, k1, k2)
			
	def addSim(self, sim):
		w=vstack(sim.env.walls)
		self.addPlot(w, style="walls", width=4)
	
	
class RoboViewer2D(GraphFrame):
	graph_type=RoboGraph2D
	
	def __init__(self, sim=None, **kwargs):
		self.sim=sim
		self.init_defaults['title']="Robo Viewer 2D"
		self.init_defaults['menus'].append('Sim')
		GraphFrame.__init__(self, None, **kwargs)

	def graphKeyBind(self):
		self.graph.keybindings['y']=lambda x:self.runSim(1.0, 'frame')	

	def onNewGraph(self):
		self.graph.addSim(self.sim)
		self.graph.fullScale()
		self.graph.DrawAll()
			

if __name__=='__main__':
	h=mien.getHomeDir()
	cd=os.path.join(h, '.mien')
	os.environ['MIEN_CONFIG_DIR']=cd
	app=wx.PySimpleApp()
	s=nav.Sim()
	for i in range(8): s.env.randomWall()
	z=RoboViewer2D(s)
	z.Show(True)
	app.MainLoop()
		