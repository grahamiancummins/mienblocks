#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2008-11-10.

# Copyright (C) 2008 Graham I Cummins
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 59 Temple
# Place, Suite 330, Boston, MA 02111-1307 USA
#
'''
        NbLines
            272                      [Number of lines in the data file]
        PbDimension
            2                        [Dimension sample]
        NbCriterion
            1                        [One criterion]
        ListCriterion
            BIC                      [BIC criterion]
        NbNbCluster
            1                        [List of size 1]
        ListNbCluster
            2                        [2 components specified]
        NbModel
            1                        [One model]
        ListModel
            Gaussian_pk_Lk_I         [Gaussian spherical model [pk_Lk_I]]
        NbStrategy
            1                        [One strategy]
        InitType
            RANDOM                   [Starting parameter by random centers]
        NbAlgorithm
            1                        [One algorithm in the strategy]
        Algorithm
            EM                       [EM algorithm]
        StopRule
            NBITERATION              [Stopping rule for EM is number of iterations]
        StopRuleValue
            200                      [200 iterations desired]
        DataFile
            ../DATA/geyser.dat       [Input data set (Old Faithful Geyser)]
        WeightFile
            ../DATA/geyser.wgt       [Weight file for data]


required:

# NbLines : Specifies the number of rows in the data set file.
# NbNbCluster : Specifies the length of the list of number of clusters.
# ListNbCluster : Specifies the list of number of clusters defined by NbNbCluster.
# DataFile : Specifies the path and name of the data file.
# PbDimension : Specifies the problem dimension : an integer which gives the number of colums in the data file. 

'''

import os, re
import mien.parsers.fileIO as io
import mien.parsers.nmpml as nmpml
import numpy as N
import mien.math.array as mma

def array2mm(a, fname, params=None):
	'''Accept a 2D array instance and a string "fname", and write a data file (fname.dat) and a control file (fname.xem) usable by MIXMOD. Params may be a dictionary specifying any of the MIXMOD parameters that are not determined directly from the data, or from other parameters. These parameters include ListNbCluster (default value [2]), ListCriterion (['BIC']), ListModel (['Gaussian_pk_Lk_C'], InitType (default: "RANDOM", specify a file name here to get USER behavior with InitFile set to this file), Algorithm (which is a list: default ['EM']), StopRule ('NBITERATION'), and StopRuleValue (200).
	'''
	rpar = {'ListNbCluster':[2], 'ListCriterion':['BIC'], 'ListModel':['Gaussian_pk_Lk_C'], 'InitType':"RANDOM", 'Algorithm':['EM'], 'StopRule':'NBITERATION', 'StopRuleValue':200}
	if params:
		rpar.update(params)
	cfile = open(fname+".xem", 'w')
	cfile.write('NbLines\n\t%i\n' % a.shape[0])
	cfile.write('PbDimension\n\t%i\n' % a.shape[1])
	cfile.write('NbCriterion\n\t%i\n' % (len(rpar['ListCriterion']),))
	cfile.write('ListCriterion\n\t%s\n' % (" ".join(map(str, rpar['ListCriterion'])),))
	cfile.write('NbNbCluster\n\t%i\n' % (len(rpar['ListNbCluster']),))
	cfile.write('ListNbCluster\n\t%s\n' % (" ".join(map(str, rpar['ListNbCluster'])),))
	cfile.write('NbModel\n\t%i\n' % (len(rpar['ListModel']),))
	cfile.write('ListModel\n\t%s\n' % (" ".join(rpar['ListModel']),))
	cfile.write('NbStrategy\n\t1\n')
	if rpar['InitType'] in ['RANDOM']:
		cfile.write('InitType\n\t%s\n' % rpar['InitType'])
	else:
		cfile.write('InitType\n\tUSER\n')
		cfile.write('InitFile\n\t%s\n' % rpar['InitType'])
	cfile.write('NbAlgorithm\n\t%i\n' % (len(rpar['Algorithm']),))
	cfile.write('Algorithm\n\t%s\n' % (" ".join(rpar['Algorithm']),))
	cfile.write('StopRule\n\t%s\n' % rpar['StopRule'])
	cfile.write('StopRuleValue\n\t%s\n' % (str(rpar['StopRuleValue']),))
	cfile.write('DataFile\n\t%s\n' % (fname+".dat",))
	cfile.close()
	dfile=open(fname+".dat", 'w')
	lfs = "%.4g "*a.shape[1]
	lfs = lfs[:-1]+"\n"
	for i in range(a.shape[0]):
		dat = tuple(a[i,:])
		dfile.write(lfs % dat)
	dfile.close()


def compressMap(fname):
	'''Opens a document fname which should contain appropriately meta-tagged afferent reconstructions of cercal system afferents. Groups the included varicosities (sphere fiducials) in such a way that each length/cercus/class group is represented by a single fiducial. Discards slide number metadata, and any elements that are not sphere or line fiducials. '''
	bfn, ext = os.path.splitext(fname)
	nfn = bfn+"_compressed.nmpml"
	doc = io.read(fname)
	d2 = nmpml.blankDocument()
	lfids = doc.getElements('Fiducial', {'Style':'line'})
	i = 1
	for f in lfids:
		nf = nmpml.createElement('Fiducial', {'Style':'line', 'color':[255,255,255], 'meta_slide_number': 123, 'Name':'standard_outline_123_at1p344scale_line%i' % i})
		i+=1
		nf.setPoints(f.getPoints())
		d2.newElement(nf)
	for side in ['left', 'right']:
		for length in ['long', 'medium', 'short']:
			for clas in range(1,14):
				fids = doc.getElements('Fiducial', {'Style':'spheres', 'meta_class':clas, 'meta_length':length, 'meta_cercus':side})
				if fids:
					nf = nmpml.createElement('Fiducial', {'Style':'spheres', 'color':fids[0].attrib('color'), 'meta_class': clas, 'meta_length':length, 'meta_cercus':side, 'Name':'class%i%s%s' % (clas, length, side)})
					for f in fids:
						nf.setPoints(f.getPoints(), True)
					d2.newElement(nf)
	io.write(d2, nfn)

def getAllSpheres(fname):
	'''Opens the document fname, and calls array2mm for every sphere fiducial in the document.''' 
	doc = io.read(fname)
	fids = doc.getElements('Fiducial', {'Style':'spheres'})
	for f in fids:
		array2mm(f.getPoints()[:,:3], f.name())
		break
		

class Gaussian(object):
	def __init__(self, mean, cov):
		mean = N.array(mean)
		self.dims = mean.shape[0]
		self.mean = mean
		if type(cov) in [float, int]:
			self.cov = N.identity(self.dims)*cov
		else:
			cov = N.array(cov)
			if len(cov.shape) == 1:
				self.cov = N.identity(self.dims)*cov
			else:
				self.cov = cov 
		try:		
			self.norm =1.0 / ( N.linalg.det(self.cov)*(2*N.pi)**(self.dims/2.0) )
		except:
			print N.linalg.det(self.cov), self.dims
			print self.cov
		self.invcov = N.matrix(self.cov).I
		
	def __getitem__(self, v):
		'''calculate the value of the gaussian at v. v may be a 1D python collection (list, tuple, ndarray) of length == self.dims, or it may be a collection of such collections (for example a 2D array of shape (N, self.dims). The function assumes a collection of points are provided, and simply converts a 1D argument into an array of 1 point. The return value is alway a 1D array, with length equal to the number of provided points (thus, it will be an array of length 1, not a float, if a 1D argument is provided). Values are always normalized by area, according to the definition of gaussian PDFs. If you prefer to have values normalized such that evaluation of a Gaussian G at the mean returns 1, use G[v]/G.norm. '''
		if type(v)!=N.ndarray:
			v=N.array(v)
		if len(v.shape)==1:
			v=N.reshape(v, (1, v.shape[0]))	
	 	x= v - self.mean
		res = N.zeros(x.shape[0])
		for i in range(res.shape[0]):
			res[i]=N.dot(N.dot(x[i,:], self.invcov), N.transpose(x[i,:]))[0,0]
		return self.norm*N.exp(-.5*res)
		
	def range(self, sigma=3):
		''' Returns an array of shape (2, self.dims) specifying a reasonable bounding box for the Gaussian. The first row is a minimum, and the second is a maximum, such that "most of" the density of the function lies in the specified range. "Most of" is defined heuristically in terms of the input parameter sigma. For 1D, and spherical gaussians this is identical to choosing the number of standard deviations around the mean. For full and diagonal multi-D gaussians it will be an upper bound on the number of standard deviations'''
		r = sigma * N.sqrt(self.cov.sum(0))
		return N.row_stack([self.mean - r, self.mean+r]) 	
		
class GMM(object):
	'''Class that implements Gaussian Mixture Models of the sort '''
	def __init__(self, components):
		''' components should be a list of tuples, (weight, Gaussian instance) '''
		self.components = components
	
	def __len__(self):
		return len(self.components)
	
	def __str__(self):
		return "%i component GMM" % len(self)
	
	def __getitem__(self, v):
		'''Evaluates the model at a point, or points, v. This behaves identically to Gaussian.__getitem__, except that the mixture calculates the weighted sum of all of the components.'''
		if type(v)!=N.ndarray:
			v=N.array(v)
		if len(v.shape)==1:
			v=N.reshape(v, (1, v.shape[0]))	
		res = N.zeros(v.shape[0])
		for c in self.components:
			res += c[0]*c[1][v]
		return res

	

	def sample(self, edge=1.0, sigma=3, maxvox=1e8):
		'''return a tuple (origin, array). Array has the same number of dimensions as the models in self.components (D). It contains a uniform sampling of the models, such that each value represents a voxel which is a hypercube in D dimensions with edge length equal to the (float) input parameter edge. Origin is a tuple of length D specifying the minimal value corner of the sampled region. The region to sample is calculated by calling "range" on the consituent gaussians, with parameter sigma. The smallest supperset of the range of all models is used as the sampling volume. The dimensions of the return array are chosen so as to sample this region with the specified edge. If maxvox is specified as a positive integer, then this function will return None, rather than try to construct the sampling, if it would be contain more than maxvox voxels (this can be used to avoid a memory error caused by specifying a small edge on a model with very broad components.'''
		m = self.components[0][1].range(sigma)
		mini = m[0,:]
		maxi = m[1,:]
		for c in self.components[1:]:
			m = c[1].range(sigma)
			mini = N.minimum(mini, m[0,:])
			maxi = N.maximum(maxi, m[1,:])
		ra = maxi-mini
		ra = N.ceil(ra/edge).astype(N.int32)
		if maxvox and N.multiply.reduce(ra)>maxvox:
			return None
		coords = mma.nDindex(ra)
		vals = self[ mini + coords*edge]
		return (tuple(mini), N.reshape(vals, ra))
	
	
def readModels(fname):
	'''Read the output (e.g. "complete.txt") of '''	
	lines = open(fname).readlines()
	models = []
	lastline = ''
	current_model = None
	current_component = None
	current_cov = None
	for index, line in enumerate(lines):
		line = line.strip()
		if line and not line.strip('-'):
			current_cov = None
			lab = lastline
			if lab.startswith('Number of Clusters'):
				if current_model:
					if current_component:
						current_model['components'].append(current_component)	
					models.append(current_model)
				current_model = {'size': int(lastline.split(':')[-1]), 'components':[]}
			elif lab.startswith('Component'):
				if current_component:
					current_model['components'].append(current_component)
				current_component={'weight':None, 'mean':None, 'cov':None}
			elif lab.startswith("Model") and current_model:
				current_model['type']=lab.split(':')[1:]
			else:
				if current_model:
					if current_component:
						current_model['components'].append(current_component)
					models.append(current_model)
				current_model = None
				current_component = None
				current_cov = None
			lastline = '-'	
			continue
		lastline = line
		if not current_model:
			continue
		if not current_component:
			if 'Criterion' in line:
				current_model['validation']=float(line.split(':')[-1])
		else:
			if current_cov!=None:
				if not line:
					current_component['cov']=current_cov
					current_cov = None
				else:
					try:
						dat = map(float, line.split())
						current_cov.append(dat)
					except:
						print("warning: expected covariance row. got %s" % line)
						current_component['cov']=current_cov
						current_cov = None
			elif line.startswith('Covariance'):
				current_cov = []
			elif line.startswith('Mixing'):
				current_component['weight'] = float(line.split(':')[-1])
			elif line.startswith('Mean'):
				current_component['mean'] = map(float, line.split(':')[-1].split())
	
	if current_model:
		if current_component:
			current_model['components'].append(current_component)	
		models.append(current_model)
	gmms = []
	for m in models:
		if m['size']!=len(m['components']):
			print("WARNING: model reports %i components, but %i found. Discarding model" % (m['size'], len(m['components'])))
			continue
		c  = [(comp['weight'], Gaussian(comp['mean'], comp['cov'])) for comp in m['components']]
		gmms.append((m['validation'], GMM(c)))
	return gmms

if __name__ == '__main__':
	import sys
	if sys.argv[1]=='write':
		getAllSpheres(sys.argv[2])
	elif sys.argv[1]=='read':
		m=readModels(sys.argv[2])	
		for mod in m:
			print mod[0], mod[1]
	else:
		print "masking.py command file\nsupported commands: read, write"
	
