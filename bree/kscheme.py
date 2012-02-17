#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-07-26.

# Copyright (C) 2009 Graham I Cummins
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

def renderKscheme(ds, ic=1.0, t1=1.0, t2=1.0, dt=.001, l=10000):
	soln = zeros(l)
	bci = 0
	for i in range(l):
		soln[i] = ic
		nic = ic+dt*(-t1*ic+t2*bci)
		bci = bci + dt*(-t2*bci+t1*ic)
		ic = nic
	ds.datinit(soln, {"SampleType":'timeseries', "SamplesPerSecond":1/dt})

def ediff(ds, ic=1.0, t1=.5, t2=1.0, t3=.02, dt=.001, l=10000):
	soln = zeros(l)
	bci = 0
	for i in range(l):
		soln[i] = ic - exp(-t1*dt*i) + exp(-t2*dt*i) -exp(-t3*dt*i)
	ds.datinit(soln, {"SampleType":'timeseries', "SamplesPerSecond":1/dt})

def envEdiff(ds, ic=1.0, t1=.5, t2=1.0, t3=.02, dt=.001, l=10000):
	soln = zeros(l)
	bci = 0
	for i in range(l):
		soln[i] = exp(-t3*dt*i)*( ic - exp(-t1*dt*i) + exp(-t2*dt*i))
	ds.datinit(soln, {"SampleType":'timeseries', "SamplesPerSecond":1/dt})
	
def bessel(ds, t1=.5, freq=.1, dt=.001, l=10000):
	soln = zeros(l)
	w = 2*pi*freq
	for i in range(l):
		soln[i] = exp(-dt*i*t1)*cos(w*i*dt)
	ds.datinit(soln, {"SampleType":'timeseries', "SamplesPerSecond":1/dt})
		
	
	
	