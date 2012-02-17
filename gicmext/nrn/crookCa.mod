TITLE Calcium Channel for Crickets

NEURON {
	SUFFIX crookCa
	USEION ca READ eca WRITE ica
	RANGE gcabar, ica
	GLOBAL  qinf, finf, tf
}

UNITS {
	(mV) = (millivolt)
	(mA) = (milliamp)
}
	
PARAMETER {
	gcabar = .005 (mho/cm2)
}

STATE {
	f
}

ASSIGNED {
	v (mV)
	gca (siemens)
	ica (mA/cm2)
	eca(mV)
	qinf
	finf
	tf (ms)
}

INITIAL {
	rates(v)
	f=finf
}

BREAKPOINT {
	SOLVE states METHOD cnexp
	ica = gcabar*qinf*f*(v-eca) :exponents ?
}

DERIVATIVE states {
	rates(v)
	f'= (finf -f)/tf
}

PROCEDURE rates(v(mV)) {
	TABLE qinf, finf, tf FROM -100 TO 100 WITH 200
	qinf = 1/(1+exp((v+25)/(-2.5)))
	finf = 1/(1+exp((v+55)/9))
	tf = 6.632*exp(-.0188*v)

}