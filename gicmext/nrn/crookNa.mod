TITLE Sodium channel for crickets

NEURON {
	SUFFIX crookNa
	USEION na READ ena WRITE ina
	RANGE gnabar, ina
	GLOBAL  vana, sana, minf, hinf, th
}

UNITS {
	(mV) = (millivolt)
	(mA) = (milliamp)
	: I made this millisiemens to make ik = gna*...*(v-vna) work right
	:(mS/cm2) = (millisiemens/cm2)
	:(mV) = (millivolt)
    : These units correspond to the paper Carrie gave me. (Microamps)
	:(muA/cm2) = (microamp/cm2)
	:(ms) = (milliseconds)
	:(muF/cm2) = (microfarad/cm2)
}

PARAMETER {
	gnabar = .120  (mho/cm2) :miller => .120 mho/cm2, crook => 120 mmho/cm2
	vana = 0 (mV)
 	sana = -8 (mV)
}

STATE {
	h
}

ASSIGNED { 
	v (mV)
	gna (siemens)
	ena (mV)
	ina (mA/cm2)
	minf
	hinf
	th (ms)
}

INITIAL { 
	rates(v)
	h = hinf
}

BREAKPOINT {
	SOLVE states METHOD cnexp
	ina = gnabar*minf*h*(v-ena)  : m^3 ?	
}

DERIVATIVE states {
	rates(v)
	h' = (hinf- h)/th
}

PROCEDURE rates(v(mV)) {
	TABLE minf, hinf, th DEPEND vana, sana FROM -100 TO 100 WITH 200
	minf = 1/(1+exp((v-vana)/sana))
	hinf = 1/(1+exp((v+40.4)/8.0))
	th = .15*exp(-.08*v)+0.45	
}
