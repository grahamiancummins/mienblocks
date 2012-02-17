import numpy as n

import os, sys
v=sys.version.split()[0]
from distutils.util import get_platform
dn="build/lib.%s-%s/ssbe.so" % (get_platform(), v)
os.system('rm ssbe.so')
os.system('python setup.py build | grep error')
os.system('cp %s .' % dn)
import ssbe as gc
print gc.__file__
print dir(gc)

dat=n.random.uniform(-1, 1, 300).astype(n.float32)
tem=n.random.uniform(-1, 1, 30).astype(n.float32)

rec=n.zeros_like(dat)


print
print "match ..."
gc.match(dat, tem, rec)

print "ok"

var=n.random.uniform(-1, 1, 30).astype(n.float32)
print
print 'mhnd'
gc.mhnd(dat, tem, var, rec)
print "ok"

c=n.random.uniform(-1, 1, (20,5)).astype(n.float32)
print
print 'optmin'
o=gc.optmin(c, 2, 4)
#print c
#print o
print 'ok'