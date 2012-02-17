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

from numpy import *

BOT_PARAMS={"optimism":0}

class Enviro:
	def __init__(self):
		self.walls=[]
		self.goals=[]
		self.hazards=[]

	def randomWall(self):
		start=random.uniform(0, 500, 2)
		orient=random.uniform(0, 2*pi)
		length=random.normal(30, 10)
		stop=start+array([length*cos(orient), length*sin(orient)])
		print start, orient, length, stop
		self.walls.append(vstack([start, stop]))
	
class Bot:
	def __init__(self, params={}):
		d={}
		d.update(BOT_PARAMS)
		d.update(params)
		self.p=d
		self.heading=0.0
		self.v=0.0
		self.x=[10,10]
		


class Sim:
	def __init__(self, bot=None, env=None):
		if not bot:
			bot=Bot()
		if not env:
			env=Enviro()
		self.env=env
		self.bot=bot
	
