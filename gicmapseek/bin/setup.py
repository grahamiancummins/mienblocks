
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
'''python setup.py build will build the extension module 
optext.so in ./build/lib.arch-id/'''

from distutils.core import setup, Extension
import sys, os, numpy

includen=[numpy.get_include()]

module1 = Extension('optext',
					include_dirs=includen,
                    sources = ['optext.c'])

setup (name = 'OptExt',
       version = '1.0',
       description = 'Numpy extensions used by map seeking circuits and optimizers',
       ext_modules = [module1])
	   

