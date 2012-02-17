DSP=[('density', 'mixtureModel', 'Gaussian Mixture Model of Data'),
	'spectra'
	]
PARSERS=[('call','p', 'Call1 File')]
NMPML=[]
MECM=[('roberts', 'd2p', "convert to point container"), 
		('roberts', 'scale', "scale points"),
		('roberts', 'showGMM', "show gmm pars"),
		('roberts', 'testGMM', "test GMM"),
		('batlab', 'loadRaw', "Load Raw Recording")
		]
DV=[]
SPATIAL=[('density', 'gmmToSpatialField', 'gmm to spatial field'),
	('density', 'scaleSpatialFieldDens', 'scale spatial field')]
DEPENDENCIES=[]
DESCRIPTION="additions for use with data from the lab of Christine Portfors at WSU Vancouver"
