:highly parametric HH voltage gated K channel (gic 4-08-02)

NEURON {
	SUFFIX paraK
	USEION k READ ek WRITE ik
	RANGE gkbar, ik
	GLOBAL ninf, ntau, q10, nh, ts1, th2, ts2, tk1, tk2 
}

UNITS {
	(mA) = (milliamp)
	(mV) = (millivolt)
}

PARAMETER {
	gkbar=.622 (mho/cm2) <0,1e9>
	q10 = 20 (degC)
	nh = 26.32 (mV)
	ns = 9.45 (mV)
	th1 = -7.49(mV)
	ts1 = 34.83(mV)
	th2 = 8.46(mV)
	ts2 = 52.56(mV)
	tk1 = 1.76 (ms)
	tk2 = .16 (ms)
}

STATE {
	n
}

ASSIGNED {
	celsius (degC)
	v (mV)
	gk (siemens)
	ek (mV)
	ik (mA/cm2)
	ninf
	ntau (ms)
}

INITIAL {
	rates(v)
	n = ninf
}

BREAKPOINT {
	SOLVE states METHOD cnexp
	ik=gkbar*n^4*(v - ek)
}

DERIVATIVE states {
	rates(v)
	n' = (ninf - n)/ntau
}

FUNCTION inf(v(mV)) (1) { LOCAL dv
	dv = v + 60.1(mV)  :dv =0 at rest, depolarization positive
	inf= 1/(1+exp(-(dv-nh)/ns))
}

FUNCTION tau(v(mV))(ms) { LOCAL dv, q
	dv = v + 60.1(mV)  :dv =0 at rest, depolarization positive
	q = 10^((celsius - 20)/q10)
	tau=tk2/q+tk1/(q*(exp((dv-th1)/ts1)+exp(-(dv-th2)/ts2)))
}

PROCEDURE rates(v(mV)) {
	TABLE ninf, ntau DEPEND celsius, q10, nh, ns, th1, ts1, th2, ts2, tk1, tk2 FROM -100 TO 100 WITH 200
	ninf = inf(v)
	ntau = tau(v)
}

