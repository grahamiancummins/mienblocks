DESCRIPTION="Extensions for cell viewer visualization used in cricket cercal system anatomy. Also includes a parser for importing image stacks form Leica microscopes, and a GUI cellviewer extension for aligning and browsing image stacks. Created by the Center for Computational biology, Montana State University"
CV=['dircolors', 'mapvis', 'auxvis', 'datamanagement', 'animate',
	('align_gui','AlignmentControls', 'Interactive Alignment Tool'),
	('gui_controls','ScopeControls', 'Microscope Emulator'),
	('convert_cercal_angle','CC', 'Cercal Angle Conversion Vis'),
	('yogo','DBTool', 'Yogo/persevere database tools')
	]
	
DEPENDENCIES=[('restclient', False, 'http://py-restclient.e-engura.org/', None, '1.3.2')]
SPATIAL=['metrics', 'align', 'density']
IMG=["image"]
DSP=["gmm"]
MECM=[('groups', 'CreG', 'Create Group From Selection'),
	  ('groups', 'ConsG', 'Consolidate Metadata in Group'),
	  ('groups', 'SubG', 'Create Group From Attribute'),
	  ('groups', 'FlatG', 'Remove All Subgroups'),
	  ('groups', 'DelG', 'Destroy Group')]
#PARSERS=[('leica','ftype', 'Leica Microscope Stack Information')]
