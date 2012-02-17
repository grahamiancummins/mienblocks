:HH voltage gated Na channel for cricket (gic 4-08-02)
:based on Theunissen, Eeckman, and Miller formulation and data

NEURON {
	SUFFIX paraNa
	USEION na READ ena WRITE ina
	RANGE gnabar, ina
	GLOBAL minf, hinf, mtau, htau, mh, ms, hh, hs, q10, hts1, hth2, hts2, htk1, htk2, mth1, mts1, mth2, mts2, mtk1, mtk2
}

UNITS {
	(mA) = (milliamp)
	(mV) = (millivolt)
}

PARAMETER {
	gnabar=.120 (mho/cm2) <0,1e9>
	q10 = 20 (degC)
	mh = 22.73 (mV)
	ms = 9.55 (mV)
	hh = 26.84 (mV)
	hs = 5.07 (mV)
	hth1 = 24.06(mV)
	hts1 = 14.04(mV)
	hth2 = 19.54(mV)
	hts2 = 20.4(mV)
	htk1 = .45 (ms)
	htk2 = .03 (ms)
	mth1 = 24.06(mV)
	mts1 = 14.04(mV)
	mth2 = 19.54(mV)
	mts2 = 20.4(mV)
	mtk1 = 0.001 (ms)
	mtk2 = 0.0 (ms)
}

STATE {
	m h
}

ASSIGNED {
	celsius (degC)
	v (mV)
	ena (mV)
	gna (siemens)
	ina (mA/cm2)
	minf hinf
	mtau (ms)
	htau (ms)
}

INITIAL {
	rates(v)
	h = hinf
	m=minf
}

BREAKPOINT {
	SOLVE states METHOD cnexp
	ina = gnabar*m^3*h*(v - ena)
}

DERIVATIVE states {
	rates(v)
	m' = (minf - m)/mtau
	h' = (hinf - h)/htau
}

FUNCTION inf(v(mV), sign(1), half(mV), slope(mV)) (1) { LOCAL dv
	dv = v + 60.1(mV)  :dv =0 at rest, depolarization positive
	inf= 1/(1+exp(sign*(dv-half)/slope))
}

FUNCTION tau(v(mV), tk1(ms), tk2(ms), th1(mV), ts1(mV), th2(mV), ts2(mV))(ms) { LOCAL dv, q
	dv = v + 60.1(mV)  :dv =0 at rest, depolarization positive
	q = 10^((celsius - 20)/q10)
	tau=tk2/q+tk1/(q*(exp((dv-th1)/ts1)+exp(-(dv-th2)/ts2)))
}

PROCEDURE rates(v(mV)) {
	TABLE minf,hinf, htau DEPEND celsius, q10, mh, ms, hh, hs, hth1, hts1, hth2, hts2, htk1, htk2,  mth1, mts1, mth2, mts2, mtk1, mtk2 FROM -100 TO 100 WITH 200
	minf = inf(v, -1, mh, ms)
	hinf = inf(v, 1, hh, hs)
	mtau = tau(v, mtk1, mtk2, mth1, mts1, mth2, mts2)
	htau = tau(v, htk1, htk2, hth1, hts1, hth2, hts2)
}


