#!/usr/bin/python2

#pulldem.py - a DEMpy/PullSDTS module - 28 Dec 01
#Update at http://www.3dartist.com/WP/pullsdts/
#Created by Bill Allen <dempy@3dartist.com>
"""
This module holds miscellaneous functions common to both DEMpy and PullSDTS,
and to some of their constituent modules.
------
To get a mental grip on how metric and English units relate, think of 3 ft.
to a yard and 10 decimeters to a meter, and so, if a yard and meter were equal
in length, there would be 1/3 * 10 dec. to a foot, or 3.333 (actually 3.048).
     The old standard conversion was 1200/3937 m. = 0.3048006 m. = one foot,
thus one meter = 3.2808334 ft., so multiply meters x 3.2808 and decimeters
x 0.32808 to get feet, and multiply feet x 0.3048 to get meters and x 3.048
to get decimeters.
------
Index, functions:
  addSeps - insert commas into numeric strings
  convertUnits
  decDeg - convert min./sec. into decimal degrees
  fixDateTuple
  fixNonAscii
  fixPath
  fixSize
  getGeoTemp - get a temporary GIS file name 
  getMRC - extract map reference code (A1-H8) from lat/long
  text2list
  timeAdjust
  truncate - get a good, clean, properly-rounded floating point number
Index, classes:
  fileLikeObject
"""

#--- imports & constants ---

import os, string, sys, time

factorDict = {'d2f':0.32808,'d2m':0.1,
              'f2d':3.048,'f2m':0.3048,
              'm2d':10.0,'m2f':3.2808}      #conversion factors

unitDict = {'d':'d','dec':'d','dec.':'d','decimeter':'d','decimeters':'d',
            'f':'f','feet':'f','ft':'f','ft.':'f',
            'm':'m','m.':'m','meters':'m'}  #standardize measure unit ID

#--- common functions ---

def addSeps(t):
    t = str(t)                          #always works with & returns a string
    p = t.find('.')
    if p == -1:
        t1 = t
        t2 = ''
    else:
        t1 = t[0:p]
        t2 = t[p:len(t)]
    if len(t1) < 3:
        return t
    while 1:
        sz = len(t1)
        if sz < 3:
            t2 = t1 + t2
            break
        if sz > 3:
            t2 = ',' + t1[-3:] + t2
        else:
            t2 = t1[-sz:] + t2
        t1 = t1[:-3]
    return t2
    #def addseps

def convertUnits(num,unitOld,unitNew,places=-1):
    """
    switchUnits(number,from_unit,to_unit[,rounded places])
    ------
    Take a number of one unit (ft, dec, m) and convert it to another
    unit. An integer is returned if that is what is supplied, and
    floating point numbers optionally can be truncated.
    """
    uOld = unitDict[unitOld.lower()]    #get standard single-character code
    uNew = unitDict[unitNew.lower()]
    n = float(num)
    if uOld == uNew:                    #nothing to do
        return num
    else:                               #convert as floating point
        n = n * factorDict[uOld+'2'+uNew]
    if str(type(num)) == "<type 'int'>":
        return int(round(n,0))          #return integer
    elif places > -1:
        return truncate(n,places)       #return truncated floating point
    else:
        return n                        #return floating point
    #end def convertUnits

def decDeg(deg,min,sec=0,rnd=None):
    """
    decDeg(degrees,minutes[,seconds[,places]])
    ------
    Turn a standard latitude/longitude into decimal degrees.
    U.S. longitudes are negative, but may not be given as such. 
    """
    dd = float(deg)
    if dd < 0.0:
        dd = dd - (float(min)/60.0) - ((float(sec)/60.0)/60.0)
    else:
        dd = dd + (float(min)/60.0) + ((float(sec)/60.0)/60.0)
    if rnd:
        return truncate(dd,rnd)
    else:
        return dd
    #end def decDeg

def fixDateTuple(d):
    """
    Turn Unix-style text date into sortable form for file listings.
    0123456789.123456789.123
    Wed Jan 14 13:05:11 1998 becomes 1998-01-14 13:05:11
    """
    i = ['Jan','Feb','Mar','Apr','May','Jun',
         'Jul','Aug','Sep','Oct','Nov','Dec'].index(d[4:7]) + 1
    return d[20:24] + '-' + string.zfill(i,2) + '-' + d[8:10] + ' ' + d[11:19]
    #end def fixDateTuple

def fixNonAscii(t,sdts=0,nochar=0):
    """
    This function turns binary bytes into safe text characters.
    sdts=1 substitutes high-bit characters for terminators
    nochar=1 forces all data bytes to their ordinal numbers
    """
    s = ''
    flag = 0
    if nochar:
        for i in range(len(t)):
            if flag:
                s = s + '\\'
            else:
                flag = 1
            o = ord(t[i])
            s = s + string.rjust(str(o),3)
        return s
    for i in range(len(t)):
        o = ord(t[i])
        if (o >= 32 and o <= 126) or (o in [30,31] and sdts):
            if flag:
                s = s + '}'
                flag = 0
            if o < 32:
                if o == 30:
                    s = s + chr(176)
                else:
                    s = s + chr(185)
            else:
                s = s + t[i]
        else:
            if flag:
                s = s + '\\' + str(o)
            else:
                s = s + '{' + str(o)
                flag = 1
    if flag:
        s = s + '}'
    return s
    #end def fixNonAscii

def fixPath(pname,fname=''):
    if fname:                               #for this OS
        pname = os.path.join(pname,fname)   #  get correct concatenation
    return os.path.abspath(pname)           #  make whole path be correct

def fixSize(sz,useSeps=1):
    """
    Format a number (usually a file size) for presentation.
    """
    if useSeps:
        szStr = addSeps(sz)
    else:
        szStr = str(sz)
    if sz < 1024:
        s = szStr + ' bytes'
    else:
        if sz < 1048576:
            s = str(round(float(sz)/1024.0,2)) + 'Kb'
        else:
            s = str(round(float(sz)/1048576.0,2)) + 'Mb'
        s = s + ' (' + szStr + ' bytes)'
    return s
    #end def fixSize

def getGeoTemp(xfer):
    """
    Returns a unique GIS temporary file name.
    ---
    NOTE: Currently only works with DEMs, not GeoTIFFs.
    """
    k = xfer.keyInfo
    t = getMRC(k.geoCornerSE[0],k.geoCornerSE[1])    \
        + str(k.scaleXY) + k.level + xfer.setName
    if k.date[-4:] < '2001':
        t = t + 'o'
    else:
        t = t + 'n'
    return t.lower()
    #end def getGeoTemp

def getMRC(lat,Lon):                    #get Map Reference Code
    latDict = {0.0:'A',0.125:'B',0.25:'C',0.375:'D',0.5:'E',0.625:'F',
               0.75:'G',0.875:'H'}
    lonDict = {0.0:'1',0.125:'2',0.25:'3',0.375:'4',0.5:'5',0.625:'6',
               0.75:'7',0.875:'8'}
    lon = abs(Lon)                      #make value positive
    lat1 = int(lat)                     #get whole number
    lon1 = int(lon)
    lat2 = lat - lat1                   #get remainder
    if latDict.has_key(lat2):
        lat3 = latDict[lat2]
    else:
        lat3 = '_'
        print 'DEBUG pulldem.getMRC: latitude key error:',lat2
    lon2 = lon - lon1
    if lonDict.has_key(lon2):
        lon3 = lonDict[lon2]
    else:
        lon3 = '#'
        print 'DEBUG pulldem.getMRC: longitude key error:',lon2
    return str(lat1) + str(lon1) + lat3 + lon3
    #end def getMRC

def text2list(s,sz):
    """
    Turn a string into a list of strings of given length.
    """
    if len(s) < sz or not s:            #nothing to do here
        return [s]
    wlist = string.split(s)             #list of words
    L = []
    t = ''
    for w in wlist:
        if t:
            t = t + ' ' + w
        else:
            t = w
        if len(t) >= sz:
            L.append(t)
            t = ''
    if t:
        L.append(t)
    return L
    #end def text2list

def timeAdjust(t):
    """
    This function tries to correctly interpret original Unix file time.
    Python's ctime function delivers a date/time string assuming that the
    number of seconds it is given relates to local time since the epoch. The
    Mac epoch is 2,082,816,000 seconds older than the Unix epoch(24,107 days
    less 8 hours) and must be compensated for. On all machines, we must add in
    the local time zone difference, then check whether Python on this machine
    is aware of and using Daylight Savings Time and, if so, factor that out.
    """
    t = float(t) + float(time.timezone)
    if time.localtime(t)[8] == 1 and time.daylight != 0:
        t = t + float(time.altzone-time.timezone)
    if os.name == 'mac':
        t = t + 2082816000.0
    return t
    #end def timeAdjust

def truncate(num,places):
    """
    Try to get an exact, properly rounded truncated floating point number.
    If the number is presented as a string, a string is returned.
    """
    typ = type(num)
    n = float(num)                      #get decimal place
    s = str(abs(n))
    neg = (n < 0.0)
    n = abs(n)                          #get rid of negative sign
    for i in range(places):
        n = n * 10
    if n > sys.maxint:
        return round(float(num),places) #safety
    s = str(long(round(n)))
    sz = len(s)
    if sz < places:
        for i in range((places-sz)+1):  #extra zero to get 0.#
            s = '0' + s
    s = s[0:len(s)-places]+'.'+s[-places:]
    if neg:
        s = '-' + s
    if typ == type('string'):           #compatible with Python 2.0 & 2.2
        return s
    else:
        return float(s)
    #end def truncate

#--- common classes ---

class fileLikeObject:
    """
    This class can be used in place of a physical file for reading or
    writing, and supports an additional mode 'b' for both reading and
    writing as a buffer object (its popfifo function deletes what it
    has just read out). Unlike a disk file object, this "FLO" can be
    closed and reopened in different modes any number of times.
    """
    def __init__(self,name=''): 
        self.buf = ''           #these init values should
        self.changed = 0        #  NEVER be changed directly
        self.closed = 1
        self.dtu = time.time()  #default value as current sys time (float)
        self.mode = None
        self.name = name
        self.ptr = 0
    def close(self):
        if self.mode in ['b','w','wb'] and self.changed:
            self.dtu = time.time()
        self.closed = 1
        self.mode = None
    def error(self,msg):
        raise IOError,'fileLikeObj: ' + msg       
    def flush(self):
        """
        This currently does nothing and is here just for compatibility.
        """
        pass
    def len(self):
        return len(self.buf)
    def open(self,mode='r'):
        """
        This FLO object doesn't currently recognize a binary 'b,' like in 'rb'
        and 'wb', and any non-first-position mode characters are stripped.
        ASCII and binary data is handled without distinction.
        """
        self.mode = mode[0]
        if not self.mode in ['b','r','w']:  #b = both read & write
            self.error("unknown mode '"+mode+"'") 
        if self.mode == 'r':            #read only
            self.ptr = 0
        elif self.mode == 'w':          #write only
            self.ptr = len(self.buf)    #presume append
        self.changed = 0
        self.closed = 0
    def popfifo(self,size):     #read <= size & truncate buffer from its top
        if self.mode != 'b':
            self.error('popfifo on mode: '+str(self.mode)
                       +', closed: '+['false','true'][self.closed])
        self.ptr = 0
        b = self.read(size)
        if self.ptr == len(self.buf):
            self.buf = ''
        else:
            self.buf = self.buf[self.ptr:len(self.buf)]
        if self.mode == 'r':
            self.ptr = 0                #ready for next read
        else:
            self.ptr = len(self.buf)    #ready for next write
        return b
    def read(self,size):
        if not self.mode in ['b','r']:
            self.error('Read on mode: '+str(self.mode)
                       +', closed: '+['false','true'][self.closed])
        L = len(self.buf)
        if self.ptr == L:
            return ''
        elif self.ptr + size > L:
            b = self.buf[self.ptr:L]
            self.ptr = L
            return b
        else:
            b = self.buf[self.ptr:self.ptr+size]
            self.ptr = self.ptr + size
            return b
    def seek(self,ptr,whence=0,sub=None):
        """
        Allows seeking within a file, or within a subfile defined by
        the sub object, which is presumed to be a tarDirClass instance
        (it could be something else with pos, ptr, and size attributes).
        """
        if whence > 2 or whence < 0:
            self.error('Unknown whence attribute: '+str(whence))
        if sub:
            p = sub.ptr
            L = sub.size
        else:
            p = self.ptr
            L = len(self.buf)   #one past last data byte
        if whence == 0:         #constrain seek absolute
            if ptr > L:
                ptr = L - 1
            elif ptr < 0:
                ptr = 0
        elif whence == 1:       #constrain seek relative to current pointer
            ptr = ptr + p       #can be positive or negative
            if ptr > L:
                ptr = L - 1
            elif ptr < 0:
                ptr = 0
        elif whence == 2:       #seek relative to end of file
            if ptr > 0:         #make sure this is a negative number
                ptr = 0 - ptr   #  which is the convention
            ptr = L + ptr
            if ptr < 0:
                ptr = 0
        if sub:
            sub.ptr = ptr
            self.ptr = sub.pos + ptr
        else:
            self.ptr = ptr
        #end def seek
    def store(self,path='',name='',overwrite=0):
        """
        For safety and maximum flexibility, the buffer is saved to disk
          in full without regard to the FLO's mode.
        Use overwrite=1 to replace an earlier file, such as in successive
          saves, maybe for backup.
        """
        if not (self.name or name):
            self.error('No file name to store')
        if name or not self.name:
            path = fixPath(path,name)   #override self.name
        else:
            path = fixPath(path,self.name)
        if os.path.exists(path) and not overwrite:
            self.error('File already exists at '+path)
        f = open(path,'wb')
        f.write(self.buf)
        f.close
        if os.name != 'mac':            #do time attributes as floats
            os.utime(path,(time.time(),float(self.dtu)))
    def tell(self):
        return self.ptr
    def write(self,s):
        """
        Everything is converted to string, so data should come in as either
          string or struct-packed.
        Currently this does not support any kind of writing except appending.
          Other possibilities are pre-appending, inserting, and overwriting,
          which would need some other mode(s) or an additional mode code.
        """
        if not self.mode in ['b','w']:
            self.error('write on mode: '+str(self.mode)
                       +', closed: '+['false','true'][self.closed])
        self.buf = self.buf + str(s)    #str(s) for safety
        self.ptr = len(self.buf)
        self.changed = 1
    #end class fileLikeObject

if __name__ == '__main__':
    print '\nThis module (pulldem.py) is not a standalone program. It'      \
          '\ncontains functions and classes used by both DEMpy and PullSDTS.' \
          '\n\tMore info at http://www.3dartist.com/WP/pullsdts/'           \
          '\n(No tests were performed.)'

### end module ###
