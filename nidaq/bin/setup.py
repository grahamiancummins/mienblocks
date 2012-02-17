
## Copyright (C) 2005-2006 Graham I Cummins
## This program is free software; you can redistribute it and/or modify it under 
## the terms of the GNU General Public License as published by the Free Software 
## Foundation; either version 2 of the License, or (at your option) any later version.
## 
## This program is distributed in the hope that it will be useful, but WITHOUT ANY 
## WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
## PARTICULAR PURPOSE. See the GNU General Public License for more details.
## 
## You should have received a copy of the GNU General Public License along with 
## this program; if not, write to the Free Software Foundation, Inc., 59 Temple 
## Place, Suite 330, Boston, MA 02111-1307 USA
## 
'''python setup_gicconv.py build will build the extension module 
gicconvolve.so in ./build/lib.arch-id/'''

from distutils.core import setup, Extension
import sys, os, numpy

includen=[numpy.get_include(), '/usr/local/include']
ldirs=[]
ela=[]
libs=['nidaqmxbase']
if "darwin" in sys.platform:
    libs.pop(0)
    ela.append('-framework nidaqmxbase')
    includen.append("/Applications/National\ Instruments/NI-DAQmx\ Base/includes/")
elif 'linux' in sys.platform:
    includen.append("/usr/local/natinst/nidaqmxbase/include/")
elif 'win' in sys.platform:
    includen.pop(1)
    includen.append("C:\gic\include")
    ldirs.append('c:\gic\lib')
    

module1 = Extension('pyni',
            include_dirs=includen,
            extra_link_args=ela,
            library_dirs=ldirs,
            libraries=libs,
            sources = ['pyni.c'])

setup (name = 'PyNI',
       version = '1.0',
       description = 'NI-DAQmx Base wrapper for python',
       ext_modules = [module1])



