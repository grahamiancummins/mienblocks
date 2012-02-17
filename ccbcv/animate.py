import numpy as N


def _greyscale(x, r):
	x = (x - r[0])/(r[1] - r[0])
	return [(c,c,c) for c in x]


CFUNS = {
	'grey':_greyscale
}

#To add a coloring function, write the function, and assign it a name in the CFUNS dictionary. 
#The function should take an array of floats, x, and a 2-tuple r, and should return a list of 3 tuples
#The floats in x are the values you want to represent with colors. The values in r are the minumum and 
#maximum posible values you will need to represent, respectively. 
#The output list should have the same length as x, and contains the colors that you mapped the x values
#to, as OpenGL color tuples (these are 3-tuples of floats, (R,G,B), where each value is on the range [0.0, 1.0]
#with 1.0 = white.

#After you load data with this custom function, you can use the "show" and "animate" functions that are provided
#in mien.spatial.animate to view the data. 

def loadCellVoltageData(self):
	cell=self.getCell()		
	pn=self.getPlotName(cell)
	if not pn:
		self.report("Cell isn't plotted")
		return
	data = self.document.getElements(["Recording"])
	cdata={}
	timestep={}
	for e in data:
		dat=e.getCellData(cell.upath())
		if dat!=None:
			cdata[e.upath()]=dat
			timestep[e.upath()]=e.timestep()
	if not cdata:
		self.report("No data for this cell")
		return
	if len(cdata.keys())==1:
		datname=cdata.keys()[0]
	else:	
		d = self.askParam([{"Name":"Where",
							"Type":"List",
							"Value":cdata.keys()}])
		if not d:
			return
		datname=d[0]	
	data=cdata[datname]
	timestep=timestep[datname]
	d = self.askParam([{"Name":"Select Coloring Function",
						"Type":"List",
						"Value":CFUNS.keys()},
						{"Name":"Color Range Min",
						"Value":data.min()},
						{"Name":"Color Range Max",
						"Value":data.max()}
						])
	if not d:
		return
	r = [d[1], d[2]]
	colordat = [CFUNS[d[0]](x, r) for x in data]
	scalecolors = CFUNS[d[0]](N.linspace(r[0], r[1], 30), r)
	self.graph.modelRefs[pn]["TimeSeries"]=colordat
	self.graph.modelRefs[pn]["TimeSeriesStep"]=timestep
	if self.graph.plots.has_key('ColorScale'):
		del(self.graph.plots['ColorScale'])
	self.graph.addColorScale(min=r[0], max=r[1], colors=scalecolors, name="ColorScale")
	self.graph.showTimeSeries(0.0)



