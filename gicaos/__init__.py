#!/usr/bin/env python
# encoding: utf-8
#Created by  on 2007-12-11.

# Copyright (C) 2007 Graham I Cummins
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

DEPENDENCIES=[('scipy', True, 'http://www.scipy.org/', 'python-scipy', '0.5')]
PARSERS=[('parsers','raw_d', 'AOS Camera RAW video')]
IMG=['hairtrack', 'findangle']
DSP=['fttools']
DESCRIPTION="Handles reading and analysis of video image data from AOS high speed cameras. Maintained by Graham Cummins."