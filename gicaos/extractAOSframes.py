#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2009-06-16.

# Copyright (C) 2009 Graham I Cummins
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

import sys
import gicaos.parsers as parse

'''fname.raw offset nframes output.raw'''


	
f = open(sys.argv[1], 'rb')
h = parse.read_raw_header(f)
bpp=h['bits_per_pixel']/8
sof=bpp*h['dims'][1]*h['dims'][0]
of = open(sys.argv[4], 'wb')
f.seek(0)
of.write(f.read(1024))
offset = int(sys.argv[2])
n = int(sys.argv[3])
btr = n*sof
f.seek(1024+offset*sof)
of.write(f.read(btr))

