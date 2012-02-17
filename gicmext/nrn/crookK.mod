TITLE Potassium channel for crickets

NEURON {
	SUFFIX crookK
	USEION k READ ek WRITE ik
	RANGE gkbar, ik
	GLOBAL vana, sana, tn, ninf
: Crook sez:
: SUFFIX KC
: USEION k READ vk WRITE ik
: perhaps I have been too liberal with range, should some of these be global?
: RANGE gk, vk, vana, sana
}

UNITS {
	(mV) = (millivolt)
	(mA) = (milliamp)
: Crook sez:
: These units correspond to the paper Carrie gave me. (Microamps)
:	(mS/cm2) = (millisiemens/cm2)
:	(muA/cm2) = (microamp/cm2)
:	(ms) = (milliseconds)   : neuron understands (ms) by default
:	(muF/cm2) = (microfarad/cm2)
}

PARAMETER {
	gkbar = .036 (mho/cm2) :miller => .622 mho/cm2, crook => 36 mmho/cm2
	vana = 0 (mV)
	sana = -8 (mV)
}

STATE {
	n
}

ASSIGNED { 
	v (mV)
	gk (siemens)
	ik (mA/cm2)
	ek(mV)
	ninf
	tn
}

INITIAL { 
	rates(v)
	n = ninf 
}

BREAKPOINT {
	SOLVE states METHOD cnexp
	ik = gkbar*n*(v-ek) : REALLY should be n^4
}

DERIVATIVE states {
	rates(v)					:gic added rates call
	n' = (ninf- n)/tn		:changed minf to ninf
}

PROCEDURE rates(v(mV)) {
	TABLE ninf, tn DEPEND vana, sana FROM -100 TO 100 WITH 200	
	: no relative dv, so vana must be in absolute voltage
	ninf = 1/(1+exp((v-vana)/sana)) : I think this should be negative!
	tn = 7.3063*exp(-0.0254*v) : many fixed parameters. No offset!!!!!
}