TITLE Potasium A current for crickets

NEURON {
	SUFFIX crookA
	USEION k READ ek WRITE ik
	RANGE gabar, ik
	GLOBAL  pinf, jinf, tj
}

UNITS {
	(mV) = (millivolt)
	(mA) = (milliamp)
}
	
PARAMETER {
	gabar = .005 (mho/cm2)
}

STATE {
	jg
}

ASSIGNED {
	v (mV)
	gk (siemens)
	ik (mA/cm2)
	ek (mV)
	pinf
	jinf
	tj (ms)
}

INITIAL {
	rates(v)
	jg=jinf
}

BREAKPOINT {
	SOLVE states METHOD cnexp
	ik = gabar*pinf*jg*(v-ek)
} 

DERIVATIVE states {
	rates(v)
	jg'= (jinf -jg)/tj
}

PROCEDURE rates(v(mV)) {
	TABLE jinf, pinf, tj FROM -100 TO 100 WITH 200
	jinf = 1/(1+exp((v+40.8)/12.3)) :From text for Kloppenburg and Horner 5D
	pinf = (1/(1+exp((v+27.4)/(-3.6))))^3 :From text for Kloppenburg and Horner 5B
	tj = 5+exp(-.1*v+2.99)
}
