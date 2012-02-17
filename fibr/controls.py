#!/usr/bin/env python
# encoding: utf-8
#Created by Graham Cummins on 2007-08-13.

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

from walker import *
from ikmsc import *
import mien.optimizers.arraystore as astore

# controls:
# two phases (extention and retraction)
# Each phase is specified by:
# front reach (-180, 180 - angle in degrees)
# left reach (-60 to 60 - angle in degrees)
# Extension (0 to 1 - fraction of total extension)
# lead leg (0,1,2, or 3 = lf, rf, lr, rr)
# time (.2 to 3 - seconds)
# power (.1 to 1 - fraction of total strength)
# f/b lag (0 to 1 - fraction of "time")
# f/b symetry (-1 to 1 - scalar multiple for x axis of target point)
# l/r lag (0 to 1 - fraction of "time")
# l/r symetry (-1 to 1 - - scalar multiple for y axis of target point)


CONTROLLABELS=['Reach', "Side", "Extend", "Lead", "Time", "Power", "Q lag", "Q sym", "Side lag", "Side sym"]

CHAMBER=[0.0, 0.0, 15.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, -60, -5, 120, -60, 5, 120, 70, -5, -120, 120, 70, 5, -120, 120, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

STATERANGES=[[10.0, 22.0, .5],
			 [.2, 20.0, .2]]
CONTROLRANGES=[[-90, 90, 1.0],
				[-60, 60, 1.0],
				[0, 1, .05],
				[0, 3, 1.0],
				[.2, 3, .05],
				[.1, 1, .05],
				[0, .6, .05],
				[-1, 1, .1],
				[0, .2, .05],
				[-.1, .1, .1]
				]

STEPRANGES=vstack([array(STATERANGES), array(CONTROLRANGES), array(CONTROLRANGES)])
STEPRANGES[:,1]=STEPRANGES[:,1]-STEPRANGES[:,0]

LEGSTRENGTHS={'f':array([1400., 900, 1200]),
	'r':array([1800.,900,1200,1100])}


LEGIDS=['lf', 'rf', 'lr', 'rr']

SIZEOFSTATE=3

def mapToRange(ints, r):
	'''ints is an N-vector of Int16s. Ranges is Nx3. Each row in ranges specifies [Min, Max, Precision]. The return value is an N-vector of floats where the ith element is constructed by mapping ants[i] onto the range ranges[i,0] to ranges[i,1] and constraining the precison such that the value is equal to ranges[i,0]*n*ranges[i,2] for some integer n.'''
	p=r[:,2]
	ints=(ints.astype(float64)+32768)/65536.
	ints=(ints*r[:,1])+r[:,0]
	cv=divmod(ints-r[:,0], p)
	cv=cv[0]+(cv[1]>(.5*p))
	cv=r[:,0]+p*cv
	return 	cv
	
def randomStep():
	z=random.randint(-32768, 32768, STEPRANGES.shape[0])
	return mapToRange(z, STEPRANGES)
	
def setState(w, s):
	'''w is a walker instance. s is a tuple of (height, heading, speed). Heading is an angle in degrees, counterclockwise, with 0 at the positive X axis.'''
	state=array(CHAMBER)
	h, he, sp = s
	he=he*pi/180
	v=array([sp*cos(he), sp*sin(he), 0.0])
	state[:3]=[0,0,h]
	state[3:6]=v
	state[9:12]=v
	w.setFullState(state)
	

def getJointAngles(lt, r, s, e):
	#FIXME: this is a dumb implementation of getJointAngles
	#in RADIANS!
	if lt=='f':
		return (d2r(r), d2r(s), pi-e*pi)
	else:
		return (d2r(r), d2r(s), -pi+e*pi, pi-e*pi)

def setLegControl(w, leg, c):
	'''Apply descending control inputs to walker w for the named leg (leg is a string, e.g. "lf"), using a compressed control array c. C has the following components: [Reach, Side, Extend, Power].
	'''
	ja=getJointAngles(leg[-1], c[0], c[1], c[2])
	strength=LEGSTRENGTHS[leg[-1]]*c[3]
	cont=array(zip(ja, strength))
	ind=0		
	l=findByName(LEGS, leg)
	for ls in l['segments']:
		n=leg+ls['name']
		nd=len(ls['joints'])
		c=array(cont[ind:ind+nd]).astype(float32)
		ind+=nd
		w.controls['bot'][n]=c

def simplifiedPosture(w, c):
	'''Sets leg positions of walker w using c=["Reach", "Side", "Extend", "Lead", "Q sym", "Side sym"]'''
	angles=[]
	ll=LEGIDS[int(c[3])]
	for l in LEGIDS:
		r,s,e=c[:3]
		if ll[0]!=l[0]:
			s=s*c[-1]
		if ll[1]!=l[1]:
			r=r*c[-2]
		ja= map(r2d, getJointAngles(l[-1], r, s, e))
		angles.extend(ja)
	w.setPosture(angles)
	
def concurrentControl(w, c):
	'''Sets all leg controls of walker w using c=["Reach", "Side", "Extend", "Lead", "Q sym", "Side sym", "Power"]'''	
	ll=LEGIDS[int(c[3])]
	for l in LEGIDS:
		setLegControl(w, l, (r, s, e, c[-1]))


#FIXME: everything after this point needs work

#['Reach', "Side", "Extend", "Lead", "Time", "Power", "Q lag", "Q sym", "Side lag", "Side sym"]

def chamberControl(w):
	p=concatenate([LEGSTRENGTHS['f'], LEGSTRENGTHS['f'], LEGSTRENGTHS['r'], LEGSTRENGTHS['r']])
	c=zip(CHAMBER[12:26], p)
	w.descendingControl(c)

def timeStep(w, c, t, flags, phase):
	done=greater_equal(flags, phase)
	ll=LEGIDS[int(c[3])]
	for li in range(4):
		if flags[li]<phase:
			r,s,e=c[:3]
			nt=0
			ln=LEGIDS[li]
			if ll[0]!=ln[0]:
				nt+=c[4]*c[8]
				s=s*c[-1]
			if ll[1]!=ln[1]:
				nt+=c[4]*c[6]
				r=r*c[-3]
			if t>=nt:
				setLegControl(w, ln, (r,s,e,c[5]))
				flags[li]=phase

def timeMonitor(w, args):
	'''call from inside w.stateActions. args should contain keys "c":a full step control array (20 elements), "start": a float representing a time, and "set": a list of ints'''
	cont=args['c']
	if args['set'][0]>2:
		return
	elif w.internalstate['client']['lo'] or w.time-args['start']>=cont[4]+cont[14]:
		chamberControl(w)
		args['set'][0]=3
	elif w.time-args['start']>=cont[4]:
		#in retraction phase
		rt=w.time-args['start']-cont[4]
		timeStep(w, cont[10:], rt, args['set'], 2)
	else:
		rt=w.time-args['start']
		timeStep(w, cont[:10], rt, args['set'], 1)
	
			
def stateMonitor(w):
	cis=w.internalstate['client']
	p=w.getCMP()
	#center of mass too low: ERROR CODE 1
	if p[2]<4:
		w.test_result=ones(SIZEOFSTATE, float32)*-1
		return
	#time expired: ERROR CODE 2		
	if w.time>=cis['end']:
		w.test_result=ones(SIZEOFSTATE, float32)*-2
		return
	#check state		
	v=w.getCMV()
	gc=False
	for cj in w.internalstate['contacts']:
		if ode.environment in cj:
			gc=True
			break
	if gc and cis["contact"]>=0:
		cis["contact"]+=1
	elif not gc and cis["contact"]<=0:
		cis["contact"]-=1
	else:
		cis["contact"]=0
	if cis['td'] and cis['contact']<-6 and v[2]>0:
		cis['lo']=1
	elif cis["contact"]>6:
		cis['td']=True
	if sqrt((v**2).sum())<.01:
		cis['rest']+=1
	else:
		cis['rest']+=0
	#at rest. ERROR CODE 3
	if cis['rest']>20:
		w.test_result=ones(SIZEOFSTATE, float32)*-3
		return
	if cis['lo']:
		if cis['lo']==1:
			dx=v[2]**2/(2*9.81)
			mcmh=p[2]+dx
			if mcmh<STATERANGES[0][0]:
				#Apex COM too low: ERROR CODE 4
				w.test_result=ones(SIZEOFSTATE, float32)*-4
				return
			cis['lo']=2
		if v[2]<=0:
			#Apex atained. Done
			w.test_result=evalState(w)
			return

def evalState(w):
	h=w.getHeading()
	brm=reshape(w.bodies['bot']['body'].getRotation(), (3,3))
	side=dot(brm, array([0.0,1.0,0]))
	if abs(dot(h, array([0,0,1.0])))>.15 or abs(dot(side, array([0,0,1.0])))>.15:
		#Apex body posture not flat. ERROR CODE 5
		return ones(SIZEOFSTATE, float32)*-5
	cmx=w.getCMP()
	cmv=w.getCMV()
	
	if dot(h, cmv)<.3*sqrt((cmv**2).sum()):
		#going backwards. ERROR CODE 6
		return ones(SIZEOFSTATE, float32)*-6
		
	speed=sqrt(cmv[0]**2+cmv[1]**2)
	head=arcsin(cmv[1]/speed)
	head=head*180/pi
	h=cmx[2]
	return  (h, head, speed)

def endStep(w):
	if w.test_result!=None:
		return
	pass
	

def testStep(w, c, df=None):
	'''w is a walker instance. C is a 22 vector. The state of the walker is set using the first two elements of C as the height and speed (heading is set to 0 and other variables are set to "chamber"). Simulation is then run until the next apex phase, control temination, or until a state failure. Return value is a tuple of the new state, or is a tuple (-N, -N, -N) where N is an error code. N=1 - no liftoff, N=2 - rotation'''
	w.reset()
	#print c
	w.time=0
	setState(w, (c[0], 0.0, c[1]))
	tma={"c":c[2:], "start":w.time, "set":[0,0,0,0]}
	w.stateActions=[stateMonitor, (timeMonitor, tma)]
	w.internalstate['client']={"lo":False, "td":False, "rest":0, "contact":0, "rebound":0, 'end':w.time+7.0}
	w.test_result=None
	while w.test_result==None:
		w.step(.005)
		if df!=None:
			df()
	#print w.test_result
	return w.test_result

def testManySteps(w, stfn, N):
	if not astore.verify(stfn, 23):
		astore.empty(stfn, 23)
	a=astore.ArrayStore(stfn, 'w')
	for i in range(N):
		if not i%100:
			print i
		z=randomStep()
		r=testStep(w, z)
		r=concatenate([z, array(r)])
		a.append(r)
		if not r[0]<0:
			print i, r
	a.close()	


	
if __name__=='__main__':
	import sys
	w=Walker()
	stfn=sys.argv[1]
	if len(sys.argv)>2:
		N=int(sys.argv[2])
	else:
		N=1000
	testManySteps(w, stfn, N)

	