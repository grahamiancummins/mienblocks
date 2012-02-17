import numpy as n

import os, sys
v=sys.version.split()[0]
from distutils.util import get_platform
dn="build/lib.%s-%s/gicconvolve.so" % (get_platform(), v)
os.system('rm gicconvolve.so')
os.system('python setup.py build | grep error')
os.system('cp %s .' % dn)
import gicconvolve as gc
print gc.__file__
print dir(gc)

dat=n.random.uniform(-1, 1, 300).astype(n.float32)
tem=n.random.uniform(-1, 1, 30).astype(n.float32)

rec=n.zeros_like(dat)


print
print "match ..."
gc.match(dat, tem, rec)

print "ok"

stem=n.random.uniform(-1, 1, (30,30)).astype(n.float32)


print
print "apply2dkern"
gc.apply2dkern(dat, stem, rec)
print "ok"

var=n.random.uniform(-1, 1, 30).astype(n.float32)

print
print 'invar'
gc.invar(dat, tem, var, rec, 0)
print "ok"


print
print 'mhnd'
gc.mhnd(dat, tem, var, rec)
print "ok"


pc=n.random.uniform(-1, 1, (30, 4)).astype(n.float32)

print
print 'pcafilt'
gc.pcafilt(dat, pc, rec)
print "ok"

print
print 'pcaproj'
gc.pcaproj(dat, pc, rec)
print "ok"



print
print 'spike dist'
gc.spikeDistance(tem, var, 0)
print "ok"


print
print 'lif'

q=gc.lif(dat**2, .8, .1, 1.0)
print q.shape, q.dtype.str
print "ok"

print
print 'transform'
e2=n.array([2,4,10,23,24,25])
e1=n.array([1,3,5,9,15,21,25,30])
l=gc.evttransform(e1,e2,.5)
print e1
print e2
print l
print "ok"


print
print 'getindex_full'
e1=n.arange(20)
e2=n.array([1,3,5,3, 9, 21, 30, 8])
l=gc.getindex_full(e1,e2)
# print e1
# print e2
# print l
print "ok"
print

print 'getindex_set'
e1=n.arange(20)
e2=n.array([1,3,5,9])
l=gc.getindex_set(e1,e2)
# print e1
# print e2
# print l
print "ok"
