DSP=['cellmodels', 'svg', 'gaussmodels', 'calibration', 'randproj', 'preproc', 'denoise', 'comparators', 'signal', 'composition', 'predictors', 'synapses', 'devmodels', 'temp', 'dimred', 'io']
PARSERS=[('olddsp','ftype', 'Simple DSP'), ('olddsp','qtype', 'Quick DSP')]
#NMPML=[('mpi', 'MpiGate','MpiGate')]
MECM=[('mecm', 'DP', "Generate Directional Projection"), 
	('cellbuilder', 'LC', "Gic Cell Editor"),
	('mecm', 'AS', "Add Synaptic Event"),
	('mecm', 'ESEQ_SEP', "Sep's Event Sequence"),
	('mecm', 'SS', "Event Sequence"),
	('mecm', 'MDL_S', "Model Sequence")
	]
DV=[('intcond','ThreshTool', 'Launch Threshold Conditioning Tool'), ('graphserv','launchGraphServer', 'Graphing Server')]
BINARIES=['gicconvolve']
DEPENDENCIES=[('scipy', True, 'http://www.scipy.org/', 'python-scipy', '0.5'), ('gicspikesort', True, 'http://mien.sf.net', 'python-mien-gicspikesort', '0.0.200')]
DESCRIPTION="Primary numerical extension to MIEN, including lots of DSP functions. Maintained by Graham Cummins."
