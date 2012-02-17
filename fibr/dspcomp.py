import controls
from analysis import writeStepFile

def evalWalkerStep(ds, upathWalker, sHt, sSpd, eReach, eSide, eExtend, eLead, eTime, ePower, eQlag, eQsym, eSlag, eSsym, rReach, rSide, rExtend, rLead, rTime, rPower, rQlag, rQsym, rSlag, rSsym):
	pars=controls.array([sHt, sSpd, eReach, eSide, eExtend, eLead, eTime, ePower, eQlag, eQsym, eSlag, eSsym, rReach, rSide, rExtend, rLead, rTime, rPower, rQlag, rQsym, rSlag, rSsym])
	w=ds.getInstance(upathWalker)
	res=controls.testStep(w, pars)
	if res[0]>0:
		fit=1
		#print "tested %s and got %s" % (repr(pars), repr(res))
		writeStepFile([1, res[0], res[1], res[2]]+list(pars), 'good.txt')
	else:
		fit=0
	ds.setAttrib('Fitness', fit)	
	ds.setAttrib('EvalConditions', list(res))