import numpy as n

import os, sys
v=sys.version.split()[0]
from distutils.util import get_platform
dn="build/lib.%s-%s/optext.so" % (get_platform(), v)
os.system('rm optext.so')
os.system('python setup.py build | grep error')
os.system('cp %s .' % dn)
import optext as oe
print dir(oe)

dat=n.random.randint(0, 15, 10).astype(n.int64)
tem=n.random.randint(0, 10, 9).astype(n.int64)

print
print "index ..."
a=oe.findindex(dat, tem)
print dat
print tem
print a
print "ok"

print
print "addcompress ..."
a=oe.addcompress(n.array([1,2,3,3,3,4,5,5]), n.ones(8)*.1)
print a
print "ok"


print
print "pcompress ..."
v=n.reshape(n.arange(32), (8,4))*.1
v[:,0]=1.0
a=oe.pcompress(n.array([1,2,3,3,3,4,5,5]), v, n.array([0,3,1,2]))
print n.hstack([n.reshape(n.array([1,2,3,3,3,4,5,5]), (-1, 1)), v])
print 
print n.array(a)
print "ok"
