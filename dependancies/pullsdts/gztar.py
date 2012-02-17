#!/usr/bin/python2

#gztar.py - a DEMpy/PullSDTS module - 6 Dec 01
#Update at http://www.3dartist.com/WP/pullsdts/
#Created by Bill Allen <dempy@3dartist.com>
"""
This module is common to both DEMpy and PullSDTS. It contains functions for
extracting from gzip and TAR files, and for writing gzip files from existing
files or from a file-like object (FLO), which is supported in the pulldem
module, and which can be used as a buffer object to progressively archive a
file to gzip without that file pre-existing as a file by itself.
------
Index, functions:
  gzOpen - extract from .gz files to disk or FLO
  test - test this module's functions and classes when it is run by itself
Index, classes:
  gzClass - create .gz from disk file or FLO, or actively from FLO as buffer
  tarClass - scan .tar as disk file or FLO, extract to disk or FLO
  tarDirClass - hold info on one constituent of a TAR file
"""

#--- modules & constants ---

import os, struct, sys, time, zlib
from string import lower

thisDir = os.path.split(sys.argv[0])[0]
if not thisDir in sys.path:
    sys.path.append(thisDir)
from pulldem import fileLikeObject, fixNonAscii, fixPath, timeAdjust

GZBLKSZ, TARBLKSZ = 1024, 512           #block sizes

#--- functions ---

def gzOpen(gzPath,savePath='',nameOver=0,makeFLO=0):
    """
    gzOpen(path[,savePath[,overwritename[,makeFLO]]])
    ------
    This function presumes, per the gzip standard, that there will be only
      one file archived in a .gz/.tar.gz/.tgz file. If there are files in
      addition to the first, they will likely cause CRC32 and size check
      failures, but otherwise will be ignored without notice to the user.
    Use nameOver=1 to extract the original archived file name.
    Use makeFLO=1 to return a fileLikeObject containing the extracted file
      instead of extracting a file to disk.
    Note that the gzOpen function has no direct relationship with gzClass.
    This is handled as a function rather than as a class because, without
      random accessability, there's no reason to do more than just open a
      read-only gzip disk file and extract from it.
    """
    if not lower(gzPath[-3:]) in ['.gz','.tgz']:
        raise IOError,'gzOpen: Not a gzip file'
    gz = open(gzPath,'rb')
    if gz.read(2) != '\037\213':
        raise IOError,'gzOpen: Not a gzip file'
    if ord(gz.read(1)) != 8:
        raise IOError,'gzOpen: Unsupported compression method'
    flag = ord(gz.read(1))
    dtu = struct.unpack('<L',gz.read(4))[0]
    if dtu == 0:
        dtu = long(time.time())
    extra = gz.read(1)
    osys = gz.read(1)                   #OS (can be used to watch for Mac)
    if flag & 4:                        #FEXTRA: extra fields flag
        L = struct.unpack('<i',gz.read(2))[0]
        b = gz.read(L)                  #discard special field(s)
    name = ''
    if flag & 8:                        #FNAME: file name flag
        while 1:
            b = gz.read(1)
            if b == '\0':
                break
            name = name + b
    if flag & 16:                       #FCOMMENT: comment flag
        x = ''
        while 1:
            b = gz.read(1)
            if b == '\0':
                break
            x = x + b
        print '\nGZ file comment:',x,'\n'
    if flag & 2:                        #FHCRC: CRC16 header check flag
        b = gz.read(2)                  #discard
    pn,fn = os.path.split(gzPath)       #original path name & file name
    if savePath:
        pn = savePath                   #use different path for extracted file
    if name and nameOver:
        fn = name                       #use file name taken from .gz header
    else:
        if lower(fn[-4:]) == '.tgz':
            fn = fn[:-4] + '.tar'
        else:
            fn = fn[:-3]
    crc32 = zlib.crc32('')
    size = 0
    decobj = zlib.decompressobj(-15)
    if makeFLO:
        f = fileLikeObject(fn)
        f.open('w')
    else:
        fn = fixPath(pn,fn)
        f = open(fn,'wb')
    done = 0
    while 1:
        chunk = gz.read(GZBLKSZ)
        if chunk:
            b = decobj.decompress(chunk)
        else:
            b = ''
        if decobj.unused_data or not chunk:
            b = b + decobj.flush()
            done = 1
        size = size + len(b)
        crc32 = zlib.crc32(b,crc32)
        f.write(b)
        if done:
            break
    f.close()
    gz.seek(-8,2)   #if the .gz contains multiple files, this next will fail
    if struct.unpack('<l',gz.read(4))[0] != crc32:      #  but the extracted
        gz.close()                                      #  1st file may be OK
        raise ValueError,'gzOpen: CRC32 check failed'
    if struct.unpack('<l',gz.read(4))[0] != size:
        gz.close()
        raise ValueError,'gzOpen: data length discrepancy'
    gz.close()
    if makeFLO:
        f.open('r')                     #hand off FLO as opened
        f.dtu = float(dtu)
        return f
    else:
        if os.name != 'mac':            #do time attributes as floats
            os.utime(fn,(time.time(),float(dtu)))
        return fn                       #hand off TAR/etc. path
    #end def gzOpen

#--- classes ---

class gzClass:
    """
    gzClass(path[,savepath[,secs[,fileLikeObject]]])
    ------
    This class is used for immediately creating gzip files from either
      existing (closed) disk files (fileObj=None), and for creating gzip
      files immediately or piecemeal from an instance of fileLikeObject
      (FLO) from the pulldem module.
    An FLO can be handed off as either open for reading (mode 'b', 'r', or
      'rb') or closed (it will be opened in mode 'r'). In all instances except
      an FLO in mode 'b', the .gz file is immediately output and closed.
    FLO mode 'b': The calling script can use the FLO's popfifo function to
      output <= size value to the gzip file on an incremental basis from the
      FLO as a buffer object, clearing what it has just read out (this reduces
      the memory load), or it can simply iterate through the FLO's write
      function to output the entire buffer. Either way is not automatic, so
      the calling script must handle it directly, and also must take care
      to close the gzip file and FLO when finished.
    Unless forcing a date/time stamp, have dtu (date/time Unix) seconds be 0.
      An example of why the dtu might be forced are files with internal dates
      more relevant than disk file dates, such as for downloaded files.
    Note that the gzOpen function is not directly unrelated. 
    """
    def __init__(self,fn,savePath='',dtu=0,fileObj=None):
        if fn:
            self.fname = os.path.split(fn)[1]   #fn trumps fileObj.name
        elif fileObj:                           #  otherwise the FLO needs
            self.fname = fileObj.name           #  to arrive already named
        if fn == '' and self.fname == '':
            raise IOError,'gzClass: Need file name'
        physical = (fileObj == None)            #fileObj trumps physical file
        if physical and not os.path.exists(fn):
            raise IOError,'gzClass: Need valid file or file-like object'
        self.crc32 = zlib.crc32('')
        self.size = 0
        self.cobj = zlib.compressobj(8,8,-15)
        if savePath:
            gzpn = fixPath(savePath,self.fname)
        else:
            if fn:
                gzpn = fn
            else:
                gzpn = self.fname
        if gzpn[-3:].lower() != '.gz':
            if gzpn[-5:].lower() == '.tiff':    #only .tif, not .tiff
                gzpn = gzpn[0:len(fn)-1]
            gzpn = gzpn + '.gz'
        gz = self.outf = open(gzpn,'wb')
        gz.write('\037\213\010\010')    #magic, compression type, name flag
        if dtu > 0:
            dtu = long(dtu)             #allows float input
        else:
            if physical:
                t = os.path.getmtime(fn)
                if os.name == 'mac' and t > 2082816000.0:
                    t = t - 2082816000.0
                dtu = long(t)
            else:
                t = time.time()         #for file-like obj, this will be the
                if os.name == 'mac':    #  time the file write started,
                    t = t - 2082816000.0 # not ended
                dtu = long(t)
        gz.write(struct.pack('<L',dtu)) #date/time in Unix secs, little-endian
        gz.write('\002')                #extra flag = max compress
        if os.name == 'mac':
            gz.write('\007')            #Mac OS, may need for troubleshooting
        else:
            gz.write('\377')            #any other OS (not identified)
        gz.write(self.fname+chr(0))     #file name
        if physical:
            self.inf = open(fn,'rb')
            writenow = 1
        else:
            if fileObj.closed:
                fileObj.open('r')
            elif fileObj.mode[0] == 'w':
                raise IOError,"gzClass: Cannot read from FLO mode 'w'"            
            writenow = (fileObj.mode != 'b')
            self.inf = fileObj
        if writenow:        #otherwise, leave open for incremental writing
            while 1:
                if not self.write():
                    break
            self.close()
        #end def __init__
    def close(self):
        self.inf.close()
        self.outf.write(self.cobj.flush())
        self.outf.write(struct.pack('<l',self.crc32))
        self.outf.write(struct.pack('<l',self.size))
        self.outf.flush()
        self.outf.close()
    def write(self):
        chunk = self.inf.read(GZBLKSZ)
        if not chunk:
            return 0
        self.size = self.size + len(chunk)
        self.crc32 = zlib.crc32(chunk,self.crc32)
        self.outf.write(self.cobj.compress(chunk))
        return 1
    #end class gzClass

class tarClass:
    """
    tarClass(filename[,tarpath[,makeFLO]])
    ------
    Must be handed an open TAR file, either on disk or as a fileLikeObject
      (FLO) instance from the pulldem module.
    If the filename is a gzip file, and if tarFLO=1, then the TAR file will
      be extracted as an FLO
    The tarPath statement will be ignored if filename is a .tar or if
      makeFLO=1.
    """
    def __init__(self,fname,tarPath='',makeFLO=0):
        self.fname = fname              #preserve case
        fname = fname.lower()           #lower case for name testing
        self.killList = []              #temp files to delete (no override)
        if fname[-4:] == '.tgz' or  \
           fname[-7:] in ['.tar.gz','_tar.gz']:
            if makeFLO:
                self.tar = gzOpen(self.fname,tarPath,0,1)
            else:
                fname = gzOpen(self.fname,tarPath)
                self.killList.append(fname)         #use new fname from gzOpen
                self.tar = open(fname,'rb')
        elif fname[-4:] == '.tar':
            self.tar = open(self.fname,'rb')
        else:
            raise IOError,"tarClass: not a TAR file"
        self.closed = 0
        self.dir = []
        self.dirLenMax = {'order':0,'name':0,'type':0,'time':0,'size':0}
        self.fileNames = []             #used to watch for duplicate names
        self.scan()                     #get the constituent file directory
        self.sdtsAttr = None            #name key if this is an SDTS transfer
        for e in self.dir:
            p = e.name.lower().find('iden.ddf')
            if p > -1:
                self.sdtsAttr = e.name[0:p]     #get the transfer group name
                break
        #end def __init__
    def cleanup(self):
        if not self.closed:
            self.close()
            self.closed = 1
        for f in self.killList:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except OSError:         #file moved, deleted, or maybe locked
                    pass
        self.killList = []
    def close(self):
        self.tar.close()        #not self.close(), which would be reentrant
        self.closed = 1
        self.cleanup()
    def deFold(self,n):
        """
        As a simple solution, any folder names found with file names are
        discarded and all files are dumped into the same destination folder.
        NOTE: Duplicate file names get "_" characters inserted.
        """
        n1 = n
        if n:
            if n[len(n)-1] == '/':
                n = ''
        while 1:
            p = n.find('/')                 #presumes forward slash always
            if p > -1:                      #loop through any slashed names
                n = n[p+1:len(n)]           #  (folder names)
            else:                           #stop looping if no slashes found
                if n == '':
                    n = n1              #probably empty file as folder creator
                while n in self.fileNames:  #duplicate file name found, so
                    p = n.find('.')         #  append or insert a "_"
                    if p == -1:             #  underscore for the name
                        n = n + '_'
                    else:
                        n = n[0:p] + '_' + n[p:len(n)]
                self.fileNames.append(n)    #add to file name list
                return n
        #end def deFold
    def getHeader(self,block,timeSort=0):
        fileNm = block[0:99]            #file name is in 1st 99 bytes
        fileNm = fileNm[0:fileNm.find('\0')]
        fileNm = self.deFold(fileNm)    #deal with any folder names
        fileLen = int(block[124:135],8) #convert from octal
        if timeSort:                    #octal time as sortable string
            modTime = fixDateTuple(time.ctime(timeAdjust(int(block[136:147],8))))
        else:                           #octal time as integer
            modTime = timeAdjust(int(block[136:147],8))
        try:
            cksum = int(block[148:155],8)
        except ValueError:
            print 'DEBUG gztar TAR checksum ValueError on',fileNm
        L = 256                         #where did 256 come from?
        for i in range(0,148):
            L = L + ord(block[i])
        for i in range(156,512):        #skip the checksum's own 8 bytes
            L = L + ord(block[i])
        if L != cksum:
            print 'DEBUG gztar TAR checksum error on',fileNm,str(cksum),str(L)
        #print fixNonAscii(block[146:157],0,1),int(block[148:155],8),L,fileNm
        return fileNm,fileLen,modTime
    def isFLO(self):
        return isinstance(self.tar,fileLikeObject) 
    def isHeader(self,block):
        magic = block[257:264]
        p = magic.find('\0')
        if p == -1:
            p = magic.find(' ')
            if p == -1:
                p = len(magic)
        if magic[0] != '\0':
            magic = magic[0:p]
        if magic in ['GNUtar','ustar'] \
           or (magic == '\0\0\0\0\0\0\0' and block[0] != '\0'
           and block[106:108] == ' \0' and block[114:116] == ' \0'
           and block[122:124] == ' \0'
           and block[TARBLKSZ-1] == '\0'):  #old TAR header format
            return 1
        else:
            return 0
        #end isHeader
    def scan(self):
        data = self.tar.read(TARBLKSZ)
        ptr = 0
        cnt = 0
        if not self.isHeader(data):
            raise IOError,'tarClass: Not a TAR file, magic = '  \
                  +fixNonAscii(data[257:264])
        self.tar.seek(0)                #set to read the first block again
        eof = 0
        while 1:
            data = self.tar.read(TARBLKSZ)
            if not data:                #end of file
                break
            ptr = ptr + TARBLKSZ
            fptr = ptr
            if self.isHeader(data):     #if not, then it is filler, so loop
                h = self.getHeader(data)
                if h[1] == 0:
                    continue            #loop
                c = h[1]/TARBLKSZ       #get count of full blocks
                if h[1] % TARBLKSZ > 0: #see if there is one more block
                    c = c + 1
                for i in range(c):
                    data = self.tar.read(TARBLKSZ)
                    if not data:
                        eof = 1
                        break
                    ptr = ptr + TARBLKSZ
                if eof:         #if premature EOF, don't add the file to the
                    break       #  directory because it is filler or flawed
                else:
                    cnt = cnt + 1
                    self.dir.append(tarDirClass(cnt,fptr,h))
        self.dirLenMax['order'] = len(str(len(self.dir)))
        for e in self.dir:              #get longest line length for each field
            c = len(e.name)
            if c > self.dirLenMax['name']:
                self.dirLenMax['name'] = c
            c = len(e.type)
            if c > self.dirLenMax['type']:
                self.dirLenMax['type'] = c
            c = len(str(e.time))
            if c > self.dirLenMax['time']:  #needed for sorting later
                self.dirLenMax['time'] = c
            c = len(str(e.size))
            if c > self.dirLenMax['size']:
                self.dirLenMax['size'] = c
        #end def scan
    #--- TAR extraction routines ---
    """
    extract() pulls out a single file by its order within the TAR
    extractName() performs a lookup on a given name & then calls extract()
    extractAll() pulls out all the files within a TAR using extract()
    """
    def extract(self,order,savePath='',add2kill=0,makeFLO=0):
        #find this file & create new disk file or FLO
        e = self.dir[order]
        if e.type != ' ':               #not a folder
            self.tar.seek(e.pos)
            b = self.tar.read(e.size)
            fn = fixPath(savePath,e.name)
            f = open(fn,'wb')
            f.write(b)
            f.close()
            if add2kill:
                self.killList.append(fn)
            else:                   #don't need time attribute on a temp file
                if os.name != 'mac':
                    os.utime(fn,(time.time(),float(e.time)))
    def extractName(self,name,savePath='',add2kill=0,makeFLO=0):
        for e in self.dir:
            if e.name.upper() == name.upper():
                self.extract(e.order-1,savePath,add2kill,makeFLO)
                return 1
        return 0
    def extractAll(self,savePath='',add2kill=0,makeFLO=0):
        for i in range(len(self.dir)):
            self.extract(i,savePath,add2kill,makeFLO)
    """
    #--- debug routines ---
    def reportDir(self):        # ** just for debug
        for e in self.dir:
            print e.order,e.name,e.type,e.size,e.time
    def store(self,path):       # ** just for debug
        if self.isFLO:
            self.tar.store(path)
    """
    #end class tarClass

class tarDirClass:
    """
    tarDirClass(fileorder,filestart,(filename,filelen,filetime))
    ------
    This puts into one entry a file's name, location and length within
      the TAR, and time/date, as well as original order within the TAR
      and its individual file type.
    This is a class rather than a dictionary so that its instances can
      be sorted and resorted for file listings.
    """
    def __init__(self,cnt,ptr,hdrTup):
        self.order = cnt                #order within TAR file, 1st, 2nd, etc.
        self.pos = ptr                  #byte position within TAR file
        self.ptr = 0                    #ptr within subfile
        self.name = hdrTup[0]
        self.size = hdrTup[1]
        self.time = hdrTup[2]
        if self.name.find('/') > -1 or self.size == 0:
            self.type = ' '             #it's a folder name, sort to the top
        elif self.name.lower() == 'readme':
            self.type = 'txt'           #it's a text file
        elif self.name.find('.') == -1:
            self.type = '!'             #unknown file type
        else:
            p = self.name.rfind('.')
            self.type = self.name[self.name.rfind('.')+1:]
    #end class tarDirClass

def test():
    print '\tTesting create new .txt.gz file & extracting it...'
    nm = 'test_gz_py.txt'
    fn = fixPath(thisDir,nm+'.gz')
    flo = fileLikeObject(nm)
    flo.open('w')
    t = 'This is a test of the gz.py module. '*50 + '\n'
    flo.write(t)
    flo.close()
    gz = gzClass(fn[:-3],'',0,flo)
    gzOpen(fn,'')
    print '\t\tDone -',nm,'extracted from',nm+'.gz'
    """
    fn = 'C:\\Python\\DemTest\\o37110f5.d10.tar.gz'
    tar = tarClass(fn,'C:\\Python\\DEMpy\\tmp')
    print 'Is this an FLO?:',['no','yes'][tar.isFLO()]
    tar.reportDir()
    tar.cleanup()
    print 'Is the TAR closed?:',['no','yes'][tar.closed]
    """
    print '\t(tarClass was not tested)'

if __name__ == '__main__':
    print '\nThis module (gztar.py) contains functions and classes for',   \
          '\nreading gzip and TAR files, and for writing gzip files.',  \
          '\n\tMore info at http://www.3dartist.com/WP/pullsdts/',      \
          '\nTesting may now follow...'
    test()
    """
    for e in tar.dir:
        if e.name.lower().find('iden.ddf') > -1:
            if tf:
                tar.tar.seek(0,0,e)         #for FLO seek
            else:
                tar.tar.seek(e.pos+e.ptr,0) #for physical seek
            print tar.tar.read(e.size)
            break
    """

### end module ###
