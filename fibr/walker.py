#!/usr/bin/env python
# encoding: utf-8
#Created by Graham Cummins on 2007-06-20.

# Copyright (C) 2007 Graham I Cummins
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free Software
# Foundation; either version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU General Public License for more details.

# This program imports functionality from the
# Python Open Dynamics Engine Wrapper
# Copyright (C) 2004 PyODE developers (see file AUTHORS)
# All rights reserved.

'''Note that ODE uses "mathematically correct" quaternions (cos(theta/2), sin(theta/2)*(x, y, z)), but OpenGL, and many users, use "intuitive" quaternions (x,y,z, theta). The function convertQ in this module can be used to toggle between these two formulations. All the other "Q" functions in this module operate on ODE-style quaternions.'''

import ode, xode.parser
from numpy import *
from mien.nmpml.basic_tools import NmpmlObject

STARTZ=15.0

BODY=(12.0, 3.0, 2.0)
LEGRADIUS=.25
LEGDENSITY=1.0

LEGS=[{'name':'lf', 
		'anchor':[5.5,1.25], 
		'segments':[
			{'name':'f','length':4.0, 'joints':[('y', -90.0, 100.0), ('x', -60.0, 60.0)]},
			{'name':'t','length':6.0, 'joints':[('y', 0.0, 180.0)]}
			]},
	{'name':'rf', 
	'anchor':[5.5,-1.25], 
	'segments':[
		{'name':'f','length':4.0, 'joints':[('y', -90.0, 100.0), ('x', -60.0, 60.0)]},
		{'name':'t', 'length':6.0, 'joints':[('y', 0.0, 180.0)]},
		]},
	{'name':'lr', 
	'anchor':[-5.5,1.25], 
	'segments':[
		{'name':'f','length':2.0, 'joints':[('y', -100.0, 90.0), ('x', -60.0, 60.0)]},
		{'name':'t', 'length':4.0, 'joints':[('y', -180.0, 0.0)]}, 
		{'name':'p', 'length':4.0, 'joints':[('y', 0.0, 180.0)]}
		]},
	{'name':'rr', 
	'anchor':[-5.5,-1.25], 
	'segments':[
		{'name':'f','length':2.0, 'joints':[('y', -100.0, 90.0), ('x', -60.0, 60.0)]},
		{'name':'t', 'length':4.0, 'joints':[('y', -180.0, 0.0)]}, 
		{'name':'p', 'length':4.0, 'joints':[('y', 0.0, 180.0)]}
		]}
	]
	

def findByName(lod, n):
	for d in lod:
		if d['name']==n:
			return d
	return None

#front-back is y, side to side is x, rotation is z
JAXIS={'x':(1,0,0), 'y':(0,1,0), 'z':(0,0,1)}

def d2r(d):
	return d*pi/180
	
def r2d(r):
	return r*180.0/pi

def convertQ(Q, deg=False, convto='ODE'):
	'''Convert between ODE style quaternions (cos(theta/2), sin(theta/2)*(x, y, z)) and GL-style quaternions (x,y,z, theta)). The argument convto is "ODE" by default. This expects a GL input and returns ODE output. Set this to "GL" to get the inverso operation.  deg is False by default (angles in radians). Set it to true to specify angle (in the GL formulation) in degrees'''
	if convto=='ODE':
		(x,y,z,t)=Q
		if deg:
			t=t*pi/180.
		s=sin(t/2.)
		return (cos(t/2.), s*x, s*y, s*z)
	else:
		theta=2*arccos(Q[0])
		x,y,z=array(Q[1:])/sin(theta/2.)
		if deg:
			theta= theta*180/pi
		return array([x,y,z,theta])	
			
def qprod(q1, q2):
	'''returns the quaternion product of q1*q2'''
	m=outer(q2,q1)
	w = m[0,0] - m[1,1] - m[2,2] - m[3,3]
	x = m[0,1] + m[1,0] + m[2,3] - m[3,2] 
	y = m[0,2] - m[1,3] + m[2,0] + m[3,1]
	z = m[0,3] + m[1,2] - m[2,1] + m[3,0] 
	return array([w, x,y,z])

def qnorm(q):
	'''return a normalized version of a quaternion. This function is lazy, and just returns q if it is close to normalized.'''
	m=(q**2).sum()
	if abs(m-1.0)<.0001:
		return q
	return q/sqrt(m)

def qinv(q):
	'''return the negative of quaternion '''
	return array([q[0], -q[1], -q[2], -q[3]])

def qdiff(q1,q2):
	'''return the normalized quaternion difference between q1 and q2. This is the quaternion that would have to be applied to an object with rotation q1 to get it to have rotation q2'''
	return qnorm(qprod(qinv(q1),q2))
	
def qproject(q, a):
	'''express the projection of the rotation q onto rotation axis a (a 3vector). Return value is a scalar angle in radians.'''
	x,y,z,t=convertQ(q, False, 'GL')
	return t*dot([x,y,z], a)
	
def qfind(v1, v2):
	'''return the quaternion that, when applied to vector v1, renders it parallel with vector v2'''
	v1=v1/sqrt((v1**2).sum())
	v2=v2/sqrt((v2**2).sum())
	ar=cross(v1, v2)
	mr=sqrt((ar**2).sum())
	if mr==0.0:
		if dot(v1, v2)>0:
			return array([1.0,0,0,0])
		else:
			#ill-defined 180 rotation
			ar=v1+v1*[-1.2, .4, .8]
			#some vector not parallel to v1
			pv1= (dot(v1, ar)/dot(v1,v1))*v1
			#projection onto v1
			ar=ar-pv1
			#ar is now perpendicular to v1. Angle of rotation is pi. Construct quaternion
			return array([cos(pi/2), sin(pi/2)*ar[0], sin(pi/2)*ar[1], sin(pi/2)*ar[2]])
	ma=arcsin(mr)
	ar=ar/sqrt((ar**2).sum())
	return array([cos(ma/2), sin(ma/2)*ar[0], sin(ma/2)*ar[1],sin(ma/2)*ar[2]])		

def fixJointConstraints(j):
	'''move the downstream body of joint j so that the joint constraint is satisfied, if needed'''
	ap=array(j.getAnchor())
	nap=array(j.getAnchor2())
	tb=j.getBody(1)
	shift=ap-nap
	if any(shift):
		com=array(tb.getPosition())
		tb.setPosition(com+shift)

	
class Walker(object):
	"""
	Quadriped Legged Walker, loosely based on "BigDog" by Boston Dynamics
 	"""

	# INIT functions

	def __init__(self):
		"""
		Build an ODE World and Space, add a ground, and add a Walker
		"""
		self.buildWorld()
		self.reset()
		self.stateActions=[]
		self.internalstate={'current':{}, 'previous':{}, 'client':{}}

	def buildWorld(self):
		self.world=ode.World()
		self.world.setGravity( (0,0,-9.81) )
		self.space=ode.Space()
		self.bodies={'bot':{}}
		self.joints={'bot':{}}
		self.controls={'bot':{}}
		self.geoms={'env':{}, 'bot':{}}
		self.cjoints=ode.JointGroup()

		self.geoms['env']['ground']=ode.GeomPlane(self.space, (0,0,1), 0)

		self.bodies['bot']['body']=ode.Body(self.world)
		b=ode.Mass()
		b.setBox(1.0, BODY[0], BODY[1], BODY[2])
		self.bodies['bot']['body'].setMass(b)
		self.geoms['bot']['body']=ode.GeomBox(self.space, lengths=BODY)


		for leg in LEGS:
			for ls in leg['segments']:	
				sn=leg['name']+ls['name']
				self.bodies['bot'][sn]=ode.Body(self.world)
				b=ode.Mass()
				b.setCappedCylinder(LEGDENSITY, 3, LEGRADIUS, ls['length'])
				self.geoms['bot'][sn]=ode.GeomCapsule(self.space, LEGRADIUS, ls['length'])
				self.bodies['bot'][sn].setMass(b)

		for k in self.geoms['bot'].keys():
			self.geoms['bot'][k].setBody(self.bodies['bot'][k])

		self.setInitialPositions()

		for leg in LEGS:	
			anc=leg['anchor']
			anc=[anc[0], anc[1], STARTZ-(BODY[2]/2.0)]
			previous='body'
			for ls in leg['segments']:
				jn=leg['name']+ls['name']
				if len(ls['joints'])==2:
					self.joints['bot'][jn]=ode.UniversalJoint(self.world, None)
				elif len(ls['joints'])==1:
					self.joints['bot'][jn]=ode.HingeJoint(self.world, None)
				self.joints['bot'][jn].attach(self.bodies['bot'][previous], self.bodies['bot'][jn])
				previous=jn
				self.joints['bot'][jn].setAnchor(anc)
				anc[2]=anc[2]-ls['length']
				if len(ls['joints'])==2:
					self.joints['bot'][jn].setAxis1(JAXIS[ls['joints'][0][0]])
					self.joints['bot'][jn].setAxis2(JAXIS[ls['joints'][1][0]])
					self.joints['bot'][jn].setParam(ode.ParamLoStop2, d2r(ls['joints'][1][1]))
					self.joints['bot'][jn].setParam(ode.ParamHiStop2, d2r(ls['joints'][1][2]))
				elif len(ls['joints'])==1:
					self.joints['bot'][jn].setAxis(JAXIS[ls['joints'][0][0]])
				self.joints['bot'][jn].setParam(ode.ParamLoStop, d2r(ls['joints'][0][1]))
				self.joints['bot'][jn].setParam(ode.ParamHiStop, d2r(ls['joints'][0][2]))
		
		self.total_mass=0.0
		for b in self.bodies['bot'].values():
			self.total_mass+=b.getMass().mass
	
	def setInitialPositions(self):
		self.bodies['bot']['body'].setPosition((0,0,STARTZ)	)
		self.bodies['bot']['body'].setQuaternion(convertQ((1.0,0,0,0), True))
		for leg in LEGS:
			anc=leg['anchor']
			anc=[anc[0], anc[1], STARTZ-(BODY[2]/2.0)]
			for ls in leg['segments']:
				sn=leg['name']+ls['name']
				anc[2]=anc[2]-ls['length']/2.0
				self.bodies['bot'][sn].setPosition(anc)
				self.bodies['bot'][sn].setQuaternion(convertQ((1.0,0,0,0), True))
				anc[2]=anc[2]-ls['length']/2.0

	
	def reset(self):
		self.setInitialPositions()
		still=(0,0,0)
		for b in self.bodies['bot'].values():
			b.setLinearVel(still)
			b.setAngularVel(still)
		
		for leg in LEGS:
			for ls in leg['segments']:	
				jn=leg['name']+ls['name']
				self.controls['bot'][jn]=[[0, 0]]*len(ls['joints'])
				
		self.stateActions=[]
		self.internalstate={'current':{}, 'previous':{}, 'client':{}}
		self.time=0
	
	#GET FUNCTIONS
	
	def getCMV(self):
		'''returns the center of mass velocity of the bot'''
		m=0
		v=zeros(3)			
		for b in self.bodies['bot'].values():
			bm=b.getMass().mass
			v+=bm*array(b.getLinearVel())
			m+=bm
		v=v/m
		return v
	
	def getCMP(self):
		'''returns the center of mass position of the bot'''
		m=0
		v=zeros(3)			
		for b in self.bodies['bot'].values():
			bm=b.getMass().mass
			v+=bm*array(b.getPosition())
			m+=bm
		v=v/m
		return v
		
	def getAngMomentum(self):
		'''returns the total angular momentum of the bot (in world coordinates, around the COM of the bot)'''
		cmv=self.getCMV()
		cmx=self.getCMP()
		am=zeros(3)
		for bn in self.bodies['bot'].keys():
			b=self.bodies['bot'][bn]
			rv=array(b.getLinearVel())-cmv
			#print bn,'---'
			#print rv
			if any(abs(rv)>0.0001):
				rx=array(b.getPosition())-cmx
				#print "lin", b.getMass().mass*cross(rx, rv)
				am=am+b.getMass().mass*cross(rx, rv)
			av=array(b.getAngularVel())
			if any(abs(av)>.0001):
				I=array(b.getMass().I)
				#print "rot", dot(I,av)
				am=am+dot(I,av)
		return am
	
	def leginfo(self, leg):
		leg=findByName(LEGS, leg)
		ts=leg['name']+leg['segments'][-1]['name']
		ps=leg['name']+leg['segments'][0]['name']
		pja=array(self.joints['bot'][ps].getAnchor())
		bb=self.geoms['bot'][ts].getAABB()
		ts=self.bodies['bot'][ts]
		p=ts.getPosition()
		za=dot(reshape(ts.getRotation(), (3,3)), (0,0,1))
		tz=-1*za*(LEGRADIUS+leg['segments'][-1]['length']/2.0)
		ep=p+tz
		ep=ep-pja
		for j in self.internalstate['contacts']:
			if ts in j:
				gc=True
				break
		else:
			gc=False
		return (ep, gc)	
		
	def getHeading(self):
		'''Return the vector that the "head" of the bot is pointing towards'''
		brm=reshape(self.bodies['bot']['body'].getRotation(), (3,3))
		return dot(brm, array([1.0,0,0]))
		
	def getPosture(self):
		'''return a list of joint angles. This has the same specification as the "ja" argument to self.setPosture'''
		ja=[]
		jd=self.joints['bot']
		for l in LEGS:
			for ls in l['segments']:
				n=l['name']+ls['name']
				nd=len(ls['joints'])
				if nd==2:
					ja.append(r2d(jd[n].getAngle1()))
					ja.append(r2d(jd[n].getAngle2()))
				else:
					ja.append(r2d(jd[n].getAngle()))
		return ja
	
	def getLegMotion(self):
		'''returns a list of joint angular velocities, in the same order that getPosture returns angles. Angular velocities are in degrees/sec'''
		ja=[]
		jd=self.joints['bot']
		for l in LEGS:
			for ls in l['segments']:
				n=l['name']+ls['name']
				nd=len(ls['joints'])
				if nd==2:
					ja.append(r2d(jd[n].getAngleRate1()))
					ja.append(r2d(jd[n].getAngleRate2()))
				else:
					ja.append(r2d(jd[n].getAngleRate()))
		ja=map(r2d, ja)
		return ja
		
	def getFullState(self):
		'''Returns a vector of 40 numbers describing the complete state of the bot. These are: the center of the body object (x 0,y 1,z 2), the velocity of the body object (x 3,y 4,z 5),  the angular velocity of the body (x 6, y 7, z 8), the heading vector of the body (x 9,y 10,z 11), the joint angles, in the order specified by setPosture (12:26), and the joint angular velocities in the same order (26:40)'''
		b=self.bodies['bot']['body']
		state=[]
		state.extend(b.getPosition())
		state.extend(b.getLinearVel())
		state.extend(b.getAngularVel())
		state.extend(self.getHeading())
		state.extend(self.getPosture())
		state.extend(self.getLegMotion())
		return state
		
	# SET functions
	
	def setVel(self, v=(0,0,0), av=(0,0,0)):
		'''Sets the angular velocity of all bodies to [0,0,0], and the linear veloctiy to v (default 0,0,0). If av is not 0, then sets the angular velocity of the body object to av, and adjusts the velocities of the other bodies appropriately.'''
		for k in self.bodies['bot'].keys():
			b=self.bodies['bot'][k]
			b.setAngularVel((0.0,0,0))
			b.setLinearVel(v)
		if any(av):
			self.bodies['bot']['body'].setAngularVel(av)
			bp=array(self.bodies['bot']['body'].getPosition())
			for k in self.bodies['bot'].keys():
				if k=='body':
					continue
				b=self.bodies['bot'][k]
				b.setAngularVel(av)
				off=array(b.getPosition())-bp
				lva=cross(av, off)
				lv=array(b.getLinearVel())+lva
				b.setLinearVel(lv)	
			
	def setHeading(self, v):
		'''Causes the head of the walker to point along the vector v. Maintains joint angles'''
		q=qfind(array([1.0, 0,0]), array(v))
		cq=qdiff(self.bodies['bot']['body'].getQuaternion(), q)
		#self.bodies['bot']['body'].setQuaternion(q)
		for b in self.bodies['bot'].values():
			nq=qprod(b.getQuaternion(), cq)
			b.setQuaternion(nq)
		for l in LEGS:
			order=[l['name']+s['name'] for s in l['segments']]
			for jn in order:
		 		j=self.joints['bot'][jn]
		 		fixJointConstraints(j)		
			
	def setPos(self, x=(0,0,0)):
		'''Sets the position of the body object to x, and adjusts the positions of all other bodies appropriately'''
		b=self.bodies['bot']['body']
		bp=array(b.getPosition())
		x=array(x)
		for k in self.bodies['bot'].keys():
			if k=='body':
				continue
			off=array(self.bodies['bot'][k].getPosition())-bp
			self.bodies['bot'][k].setPosition(off+x)
		b.setPosition(x)
					
	def setJointAngle(self, j, ang, ax, dsb):
		if not ax:
			ax=''
		if type(ax)==int:
			ax=str(ax)
		cja=eval("j.getAngle%s()" % ax)
		aa=cja-ang
		if abs(aa)<.000001:
			return
		ax=eval("j.getAxis%s()" % ax)
		b=j.getBody(1)
		q=b.getQuaternion()
		aq=convertQ((ax[0], ax[1], ax[2], aa))
		b.setQuaternion(qprod(q, aq))
		fixJointConstraints(j)
		for b in dsb:
			j=self.joints['bot'][b]
			b=j.getBody(1)
			q=b.getQuaternion()
			b.setQuaternion(qprod(q, aq))
			fixJointConstraints(j)

	def setJointAngleRate(self, j, ar, ax, dsb):
		if not ax:
			ax=''
		if type(ax)==int:
			ax=str(ax)
		cja=eval("j.getAngleRate%s()" % ax)
		adj=cja-ar
		if abs(adj)<.000001:
			return
		ax=eval("j.getAxis%s()" % ax)
		anc=j.getAnchor()
		#FIXME: finish this function (set angle rates)

	def setPosture(self, ja):
		'''Sets the angles of every joint to the values specified in ja. Body velocities are set such that all joint angular velocities are 0 (actually, all angular velocities of every body part are also 0). ja gives angles in degrees, and orders them according to a depth-first search over LEGS: 
		(LEGS[0]['segments'][0]['joints'][0], LEGS[0]['segments'][0]['joints'][1], LEGS[0]['segments'][1]['joints'][0], ...)'''
		ind=0
		ja=map(d2r, ja)
		for l in LEGS:
			for li, ls in enumerate(l['segments']):
				dsb=[l['name']+s['name'] for s in l['segments'][li+1:]]
				nd=len(ls['joints'])
				j=self.joints['bot'][l['name']+ls['name']]
				if nd==1:
					self.setJointAngle(j, ja[ind], '', dsb)
				else:
					self.setJointAngle(j, ja[ind], '1', dsb)
					self.setJointAngle(j, ja[ind+1], '2', dsb)
				ind+=nd
			
	def setLegMotion(self, a):
		'''Sets the angular velocities of all the leg joints. A is in "setPosture" order, but specifies angle rates (degrees/sec)'''
		a=map(d2r, a)
		ind=0
		for l in LEGS:
			for li, ls in enumerate(l['segments']):
				dsb=[l['name']+s['name'] for s in l['segments'][li+1:]]
				nd=len(ls['joints'])
				j=self.joints['bot'][l['name']+ls['name']]
				if nd==1:
					self.setJointAngleRate(j, a[ind], '', dsb)
				else:
					self.setJointAngleRate(j, a[ind], '1', dsb)
					self.setJointAngleRate(j, a[ind+1], '2', dsb)
				ind+=nd	

	
	def setFullState(self, state):
		'''Accepts a 40 vector of the sort described by getFullState. Sets all body positions, velocities, and angular velocities so that that state is obtained.'''
		b=self.bodies['bot']['body']
		self.setPos(state[:3])
		self.setHeading(state[9:12])
		self.setPosture(state[12:26])
		self.setVel(state[3:6], state[6:9])
		self.setLegMotion(state[26:])
		
	# CONTROL and SIMULATION functions
		
	def nearcb(self, args, g1, g2):
		b1, b2 = g1.getBody(), g2.getBody()
		if (b1 is None):
			b1=ode.environment
		if (b2 is None):
			b2=ode.environment
		if ode.areConnected(b1, b2):
			#pass
			return
		contacts = ode.collide(g1, g2)
		for c in contacts:
			c.setBounce(0.0)
			c.setMu(10000)
			j=ode.ContactJoint(self.world, self.cjoints, c)
			j.attach(b1, b2)
			self.internalstate['contacts'].append((b1,b2))
				
	def bodyFrame(self, a):
		'''Returns the array a (Nx3) in body coordinates. These are calculated by subtracting the positon of the body element and subsequently rotating through the inverse of the body element rotation matrix.'''
		b=self.bodies['body']
		m=array(b.getPosition())
		a=a-m
		brm=reshape(b.getRotation(), (3,3))
		a=transpose(dot(brm, transpose(a)))
		return a		
			
	def descendingControl(self, a):
		'''Set the control angles and strengths. "a" is a sequence of 2-tuples of floats containing: (angle, strength). Angles are in degrees. The meaning of strength values depends on the calcControlTorques method used (for viscoelastic 700 is a reasonable value for postural control). Each 2-tuple specifies control for one joint. The joints are specified in the same order as for the "ja" argument to self.setPosture'''
		a=array(a)
		a[:,0]=a[:,0]*pi/180
		ind=0
		for l in LEGS:
			for ls in l['segments']:
				n=l['name']+ls['name']
				nd=len(ls['joints'])
				cont=array(a[ind:ind+nd]).astype(float32)
				ind+=nd
				self.controls['bot'][n]=cont
			
	def setControlTorques(self):
		for k in self.controls['bot'].keys():
			kl=self.controls['bot'][k]
			j=self.joints['bot'][k]
			#print k
			torques=[]
			na=len(kl)
			for ai in range(na):
				if not kl[ai][1]:
					torques.append(0)
					continue
				if na==1:
					ang=j.getAngle()
					angr= j.getAngleRate()
				else:
					#NOTE: getAngle1 and getAngleRate1 only work in my hacked version of PyODE
					ang=eval("j.getAngle%i()" % (ai+1,))
					angr=eval("j.getAngleRate%i()" % (ai+1,))
				t=self.calcControlTorque(ang, kl[ai][0], angr, kl[ai][1])	
				if t>5000:
					#HACK to prevent runaway viscoelastic torque
					#print k, t,  kl[ai], ang, angr
					t=5000
				torques.append(t)
			if any(torques):
				if na==1:
					j.addTorque(torques[0])
				else:
					apply(j.addTorques, torques)

	def calcControlTorque(self, aa, ca, av, mf):
		'''calculates and returns a control torque for a joint using the parameters joint angle (aa), command angle (ca), angular velocity (av) and a strength parameter (mf)'''
		#hooke spring
		#return (ca-aa)*mf
		
		#quadratic spring
		#return -1*abs(ca-aa)*(aa-ca)*mf
		
		#viscoelastic
		sf=(ca-aa)*mf
		vf=-av*mf*.1
		#FIXME - viscous torque can't create a reversal of velocity
		return sf+vf
		
		#intentional balistic movement
		# ad=ca-aa
		# if abs(ad)<.09:
		# 	return -av*mf
		# elif ad*av>0 and av>=mf:
		# 	return 0				
		# else:	
		# 	return mf*sign(ad)

		
	def stateEvents(self):
		'''Calculates the current internal state, and stores it in self.internalstate["current"]. Calls any functions stored in self.stateActions. If there is no self.internalstate["previous"], it is set to the same value as "current". State includes center of mass position and velocity, and leg endpoint positions and state of contact.'''
		# cmv=self.getCMV()
		# cmpos=self.getCMP()
		# state={'cmp':cmpos, 'cmv':cmv}
		# for leg in ['lf', 'rf', 'lr', 'rr']:
		# 	state[leg]=self.leginfo(leg)
		# state['bp']=self.bodies['bot']['body'].getPosition()
		# state['bo']=reshape(self.bodies['bot']['body'].getRotation(), (3,3))
		# self.internalstate['current']=state	
		# if not self.internalstate['previous']:
		# 	self.internalstate['previous']=state
		for f in self.stateActions:
			if callable(f):
				f(self)
			else:
				fun, args=f
				fun(self, args)	
		self.internalstate['previous']=self.internalstate['current']
		self.internalstate['current']={}	
		
	def step(self, t=.005):
		self.internalstate['contacts']=[]
		self.internalstate['dt']=t
		self.space.collide((), self.nearcb)
		self.setControlTorques()
		self.world.step(t)
		self.stateEvents()
		self.cjoints.empty()
		self.time+=t
		
class NMPMLWalker(Walker, NmpmlObject):
	def __init__(self, node, container=None):
		NmpmlObject.__init__(self, node, container)
		Walker.__init__(self)
	

if (__name__ == '__main__'):
	pass
