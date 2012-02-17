import cPickle
from numpy import *
import gicmext.sysChar as sc

def get():
	foo=cPickle.load(file('foo.pickle'))
	print foo.keys()
	return foo
	
def ntrans(trans, dist, avoid=None):
	nt=0
	for k in trans.keys():
		if avoid:
			d=dist[k[0], k[1]]
			if d>=avoid:
				continue
		nt+=trans[k].shape[0]		
	return nt

def combine(trans, dist, avoid, nst):
	nt=ntrans(trans, dist, avoid)
	ci=zeros((nt,2), int32)-1
	ii=0
	for k in trans.keys():
		if avoid:
			d=dist[k[0], k[1]]
			if d>avoid:
				continue
		ta=trans[k]
		tl=ta.shape[0]
		#print tl
		#print ci[ii:ii+tl,0].shape,ta[:,0].shape 
		ci[ii:ii+tl,0]=ta[:,0]*nst+k[0]
		ci[ii:ii+tl,1]=ta[:,1]*nst+k[1]
		ii+=tl
	ci=concatenate([ci, ci[:,[1,0]]], 0)
	ind=argsort(ci[:,0])
	return ci[ind, :] 	
	return ci 	
	
def getfreq(btm):
	sid=unique1d(btm[:,0])
	counts=bincount(btm[:,1])
	counts=counts[sid]
	return (sid, counts)

def getequiv(btm, req=None):
	sid, count = getfreq(btm)
	cor={}
	ci=0
	for i in range(sid.shape[0]):
		co=count[i]
		if req and not co>=req:
			ci+=co
			continue	
		cor[sid[i]]=unique1d(btm[ci:ci+co,1])
		ci+=co
	return cor		
# 
# def ggid(btm, req=None):
# 	#no good, spikes are always in multiple groups
# 	sid, count = getfreq(btm)
# 	gids=[]
# 	ci=0
# 	sgroup=zeros_like(sid)-1
# 	for i in range(sid.shape[0]):
# 		co=count[i]
# 		if req and not co>=req:
# 			ci+=co
# 			continue	
# 		cor=unique1d(btm[ci:ci+co,1])
# 		ci+=co
# 		ti=intersect1d(cor, unique1d(gids))
# 		if ti.shape[0]==0:
# 			gids.append(sid[i])
# 			sgroup[i]=sid[i]
# 		elif ti.shape[0]==1:
# 			sgroup[i]=ti[0]
# 		else:
# 			print "Warning, spike %i links to %i groups" % (sid[i], ti.shape[0])
# 			sgroup[i]=ti[0]
# # 			print gids
# # 			print cor
# # 			break
# 	return (sid, sgroup)		

def fixcor(cor, req=None):
	#expensive
	k=unique1d(cor.keys())
	cycle=False
	for kk in k:
		cor[kk]=intersect1d(cor[kk], k)
		if req and len(cor[kk])<req:
			del(cor[kk])
			cycle=True
	if cycle:
		print "iterative removal"
		cor=fixcor(cor, req)		
	return cor	

def group(cor, sim, fix=None):
	'''sim is a similarity function that expects the arguments (cor, key1, key2) and returns Bool'''
	k=unique1d(cor.keys())
	v={}
	ci=0
	for ind, spike in enumerate(k):
		if v.has_key(spike):
			continue
		v[spike]=ci
		for s in cor[spike]:
			if not cor.has_key(s):
				continue
			if fix and cor[s]<fix:
				continue
			issym=sim(cor, spike, s)
			#print spike, s, issym
			if issym:
				v[s]=ci
		ci+=1
	id=zeros_like(k)
	for ind in range(id.shape[0]):
		id[ind]=v.get(k[ind], -1)
	return 	column_stack([k, id])	

def simgrp(cor, s1, s2, t=.5):
	g1=cor[s1]
	g2=cor[s2]
	gc=len(intersect1d(g1, g2))
	sv=float(gc)/max(len(g1), len(g2))
	return sv>=t

def unravel(gids, nst):
	a,b=divmod(gids[:,0], nst)
	return column_stack([a, b, gids[:,1]])
	

def resolve(gids, sts):
	for i in range(gids.shape[0]):
		st=sts[gids[i,1]][gids[i,0]]
		gids[i,0]=st	

def batch(req, thresh):
	f=get()
	trans, dist, avoid, nst=f['trans'], f['dist'], f['avoid'], len(f['order'])
	b=combine(trans, dist, avoid, nst)
	c=getequiv(b, req)
	#c=fixcor(c, req)
	sev=lambda x, y, z: simgrp(x, y, z, thresh)
	id=group(c,sev)
	id=unravel(id, len(f['order']))
	resolve(id, f['spikes'])
	return (f, id)

def getclass(cor, nt, lt, no):
	vis={}
	for i in range(nt):
		ss=p
