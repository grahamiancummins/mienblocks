#!/usr/bin/python2

#geotiff.py - a DEMpy/PullSDTS module - 24 Sep 01
#Update at http://www.3dartist.com/WP/pullsdts/
#Created by Bill Allen <dempy@3dartist.com>
"""
This module is common to both DEMpy and PullSDTS. It contains functions and
classes for working with USGS GeoTIFF files.
------
Index, functions
  tifTime2unix - convert time in TIFF header to Unix time
  test - tests the components of this module when it is run by itself
Index, classes
  tifEntryClass - class for TIFF IFD entries
  tifIFDclass - class for TIFF IFDs
  tifFileClass
"""

#--- imports & constants ---

import os, struct, sys, time
from string import find, replace

thisDir = os.path.split(sys.argv[0])[0]
if not thisDir in sys.path:
    sys.path.append(thisDir)
import pulldem
from gztar import gzOpen
from pulldem import fixPath

TIF2PYDICT = {1:'B',
              2:'s',
              3:'H',
              4:'L',
              5:'LL',
              6:'b',
              8:'h',
              9:'l',
             10:'ll',
             11:'f',
             12:'d'}        #converts TIFF field types to Python struct types

               #123456789.123456
TIFDICT = {254:'NewSubfileType',
           256:'ImageWidth',
           257:'ImageLength',
           258:'BitsPerSample',
           259:'Compression',
           262:'PhotometrInterp',
           270:'ImageDescription',
           273:'StripOffsets',
           277:'SamplesPerPixel',
           278:'RowsPerStrip',
           279:'StripByteCounts',
           282:'XResolution',
           283:'YResolution',
           284:'PlanarConfigurat',
           296:'ResolutionUnit',
           305:'Software',
           306:'DateTime',
           320:'ColorMap',
           332:'InkSet',
           333:'InkNames',
           334:'NumberOfInks',
         33550:'ModelPixelScale',
         33922:'ModelTiepoint',
         34264:'ModelTransformat',
         34735:'GeoKeyDirectory',
         34736:'GeoDoubleParams',
         34737:'GeoAsciiParams'}

#--- functions ---

def tifTime2unix(t):
    """
    0123456789.12345678
    1997:01:28 18:36:24
    """
    y = int(t[0:4])
    doy = {'01':0,  '02':31, '03':59, '04':90, '05':120,'06':151,
           '07':181,'08':212,'09':243,'10':273,'11':304,'12':334}[t[5:7]]
    #count days by year + leap year extra + year days + day of month less 1
    d = ((y-1970)*365) + ((y-1968)/4) + doy + (int(t[8:10])-1)
    if y%4 == 0 and t[5:7] < '03':
        d = d - 1                       #remove leap day if hasn't happened
    s = long( (int(d)*86400) + (int(t[11:13])*3600)
              +(int(t[14:16])*60) + int(t[17:19]) ) + time.timezone
    if time.localtime(s)[8] == 1 and time.daylight != 0:
        s = s + (time.altzone - time.timezone)
    return s
    #end tifTime2unix

#--- classes ---

class tifEntryClass:                    #class for TIFF IFD entries
    def __init__(self,tag,type,count,value,pyType,vo):
        self.tag = tag
        self.type = type
        self.count = count
        self.value = value
        self.pyType = pyType
        self.vo = vo                    #v=value, o=offset, ?=undefined
    def report(self):
        if self.tag in TIFDICT.keys():
            s = TIFDICT[self.tag]
        else:
            s = ''
        if self.vo == 'v':
            v = str(self.value)
        elif self.vo == 'o':
            v = 'jump->' + str(self.value)
        else:
            v = ''        
        return '%5d %16s %2s %5d'%(self.tag,s,self.pyType,self.count),v
    #end class tifEntryClass

class tifIFDclass:                      #class for TIFF IFDs
    def __init__(self,f,cnt,bo):        #bo = byte order - < or >
        self.entryList = []
        for i in range(cnt):
            b = f.read(12)
            tag,type,count = struct.unpack(bo+'HHL',b[0:8])
            if type in TIF2PYDICT.keys():
                pyType = TIF2PYDICT[type]
                if count < 5 and pyType in ['b','B','s']:
                    t = pyType
                    while len(t) < count:
                        t = t + pyType
                    value = struct.unpack(bo+t,b[8:8+count])[0]
                    vo = 'v'                   
                elif count < 3 and pyType in ['h','H']:
                    t = pyType
                    if count == 2:
                        t = t + pyType
                    value = struct.unpack(bo+t,b[8:8+(count*2)])[0]
                    vo = 'v'                   
                elif count == 1 and pyType in ['f','l','L']:
                    value = struct.unpack(bo+pyType,b[8:12])[0]
                    vo = 'v'
                else:                   #this is an offset to the value
                    value = struct.unpack(bo+'L',b[8:12])[0]
                    vo = 'o'
            else:
                pyType = '?'
                value = b[8:12]
                vo = '?'
            entry = tifEntryClass(tag,type,count,value,pyType,vo)
            self.entryList.append(entry)
    #end class tifIFDclass

class tifFileClass:                     #class for TIFF files
    def __init__(self,parent,fp):
        """
        Much of the init work here gets done with the call to self.getIFD.
        """
        self.file = None
        self.name = ''
        self.path = ''
        self.dimX = 0
        self.dimY = 0
        self.fileDate = None
        self.gzStat = None
        self.ifdList = []
        self.kill = ''            #temp ungzipped TIFF to delete (no override)
        self.parent = parent
        self.size = None
        msg = self.getIFD(fp)
        if msg != 'OK':
            raise IOError,'tifFileClass: '+msg
    def close(self):
        self.file.close()
        if self.kill:
            if os.path.exists(self.kill):
                try:
                    os.remove(self.kill)
                except OSError:   #file was moved, deleted, or might be locked
                    pass
    def compression(self):
        for entry in self.ifdList[0].entryList:
            if entry.tag == 259:
                if entry.value in [1,2,5,6,32773]:
                    return {1:'none',2:'CCITT Group 3 Modified Huffman RLE',
                            5:'LZW',6:'JPEG',32773:'PackBits'}[entry.value]
                else:
                    return 'Unknown value '+str(entry.value)
        return 'Not found'
    def geoAsciiParams(self):
        for entry in self.ifdList[0].entryList:
            if entry.tag == 34737:
                cnt = entry.count
                jmp = entry.value
                f = self.file
                f.seek(jmp)
                b = f.read(cnt)
                b = self.tifText(b,1)
                return b                #return string
        return 'not found'
    def geoModelPixelScale(self):
        for entry in self.ifdList[0].entryList:
            if entry.tag == 33550:
                if entry.count != 3:
                    return 0,'count <> 3'
                jmp = entry.value
                f = self.file
                f.seek(jmp)
                b = f.read(24)
                t = struct.unpack(self.endian+'3d',b)
                return 1,t              #return tuple of 3 doubles
        return 0,'not found'
    def geoModelTiepoint(self):       
        for entry in self.ifdList[0].entryList:
            if entry.tag == 33922:
                if entry.count != 6:
                    return 0,'Count <> 6'
                jmp = entry.value
                f = self.file
                f.seek(jmp)
                b = f.read(48)
                t = struct.unpack(self.endian+'6d',b)
                return 1,t              #return tuple of 6 doubles
        return 0,'not found'
    def getColorType(self):
        BPS = 0
        Cmap = 0
        PMI = BPScnt = None
        for entry in self.ifdList[0].entryList:
            if entry.tag == 258:        #BitsPerSample count
                BPScnt = entry.count
                if BPScnt == 1:
                    BPS = entry.value
                break
        for entry in self.ifdList[0].entryList:
            if entry.tag == 262:        #PhotometricInterpretation value
                PMI = entry.value
                break
        for entry in self.ifdList[0].entryList:
            if entry.tag == 320:        #ColorMap found
                Cmap = 1
                break
        if PMI == 3 and Cmap:
            return 'indexed ('+str(BPS)+'-bit) color'
        elif PMI == 2 and not Cmap:
            if BPScnt == 3:
                return 'RGB'
            elif BPScnt == 4:
                return 'RGB with alpha'
        elif PMI in [0,1] and BPS in [4,8]:
            return 'grayscale ('+str(BPS)+'-bit)'
        elif PMI in [0,1]:
            return 'bitmap ('+('white','black')[PMI]+' is zero)'
        elif BPScnt == 4 and PMI == 5:
            return 'CMYK'
        print 'DEBUG unknown geotiff color'
        print '\n\tBPS =',str(BPS),' BPScnt =',str(BPScnt)
        print '\tPMI =',str(PMI),' Cmap =',str(Cmap)
        return 'unknown'
    def getDate(self):
        ifd = self.ifdList[0].entryList
        for entry in ifd:
            if entry.tag == 306:
                jmp = entry.value
                f = self.file
                f.seek(jmp)
                b = f.read(19)
                return b
        return 'None'
    def getDim(self):
        for entry in self.ifdList[0].entryList:
            if entry.tag == 256:
                self.dimX = entry.value
                break
        for entry in self.ifdList[0].entryList:
            if entry.tag == 257:
                self.dimY = entry.value
                break
    def getIFD(self,fp):                #get 1 or more Image File Dir's (IFDs)
        self.path,self.name = os.path.split(fp)
        if fp[-7:] == '.tif.gz':
            s = os.stat(fp)
            self.gzStat = s[6],s[8]
            fp = gzOpen(fp,self.parent.ini.tmpDir)
            self.kill = fp
        s = os.stat(fp)
        self.size = s[6]
        self.fileDate = s[8]
        f = self.file = open(fp,'rb')
        try:                            #1st 8 bytes are the TIFF file header
            b = f.read(2)
        except IOError:                 #trap empty-file error
            f.close()
            return 'bad or missing file'
        n = struct.unpack('2s',b)[0]    #magic name & byte order
        if n == 'MM':
            endian = self.endian = '>'
        elif n == 'II':
            endian = self.endian = '<'
        else:
            f.close()
            return 'not a TIFF: 1'
        b = f.read(2)
        i = struct.unpack(endian+'H',b)[0]          #also part of magic name
        if i != 42:
            f.close()
            return 'not a TIFF: 2'
        b = f.read(4)
        jmp = struct.unpack(endian+'L',b)[0]        #0-based jump to 1st IFD
        while 1:                                    #loads multiple ifd
            f.seek(jmp)
            b = f.read(2)
            cnt = struct.unpack(endian+'H',b)[0]    #get the entry count
            list = tifIFDclass(f,cnt,endian)        #this does the cnt loop
            self.ifdList.append(list)               #  to assemble the directory
            b = f.read(4)                           #the end or next jump
            jmp = struct.unpack(endian+'L',b)[0]    #jump to next IFD
            if jmp == 0:
                break
        return 'OK'
        #end def getIFD
    def imageDescription(self):
        ifd = self.ifdList[0].entryList
        for entry in ifd:
            if entry.tag == 270:
                cnt = entry.count
                jmp = entry.value
                f = self.file
                f.seek(jmp)
                b = f.read(cnt)
                b = self.tifText(b,0)
                i = find(b,'.')
                if i > 33:
                    if find(b,'USGS GeoTIFF DRG 1:24000 Quad of ') == 0:
                        b = b[33:i] + ', 1:24,000 scale'
                    elif find(b,'USGS GeoTIFF DRG 1:100000 Quad of ') == 0:
                        b = b[34:i] + ', 1:100,000 scale'
                return b
    def isGeoTIFF(self):
        """
        To be GeoTIFF compatible, must pass these successive tests
        --PackBits compression (259)
        --PhotometricInterpretation (262) = 3 (palette color) or 0 or 1 (black/white/gray)
          other 262: 2 = RGB, 4 = mask, 5 = separated (usually CMYK), 8 = CIE Lab
          for 262 = 5, InkSet (332) = 1 is CMYK, 2 is other, see InkNames (333)
        --tags 34735 & 34737
        --what else? ID?
        """
        ifd = self.ifdList[0].entryList
        flag = 1
        geokey = 0
        for entry in ifd:
            if entry.tag == 259 and entry.value != 32773:
                flag = 0
            if entry.tag == 262 and entry.value != 3:
                flag = 0
            if entry.tag == 34735:
                geokey = 1
        return (flag and geokey)
    def report(self):
        t = []
        t.append('FILE NAME: '+self.name)
        t.append('IN FOLDER: '+self.path)
        t.append('FILE DATE: '+pulldem.fixDateTuple(time.ctime(self.fileDate)))
        t.append('DATA DATE: '+self.getDate())
        t.append('FILE SIZE: '+pulldem.fixSize(self.size))
        if self.gzStat:
            t.append('gzip DATE: '
                     +pulldem.fixDateTuple(time.ctime(self.gzStat[1])))
            t.append('gzip SIZE: '+pulldem.fixSize(self.gzStat[0]))
        t.append('DATA TYPE: '+['TIFF','USGS GeoTIFF'][self.isGeoTIFF()])
        self.getDim()
        t.append('DIMENSIONS: '+str(self.dimX)+'x'+str(self.dimY)
                 +' pixels wide x high')
        t.append('COLOR MODEL: '+self.getColorType())
        t.append('COMPRESSION: '+self.compression())
        if len(self.ifdList) > 1:
            t.append('NOTE: Contains additional image(s)')
        if self.isGeoTIFF():
            t.append('QUAD NAME: '+self.imageDescription())
            t.append('-'*len(t[len(t)-1]))
            t.append('ASCII params: '+self.geoAsciiParams())
            ok,x = self.geoModelTiepoint()
            if ok:
                t.append('NW tie point: UTM '+str(round(x[3],1))+', '
                         +str(round(x[4],1)))
                if x[0] > 0.0 or x[1] > 0.0:
                    t.append('  Offset: '+str(round(x[0],1))+', '
                             +str(round(x[1],1)))
            ok,x = self.geoModelPixelScale()
            if ok:
                t.append('Pixel scale: '+str(x[0])+' meters/pixel')
        else:
            t.append('-'*len(t[len(t)-1]))
            t.append('Note: Not a GeoTIFF')
            x = self.imageDescription()
            if x:
                x = 'Description: ' + x
                L = pulldem.text2list(x,37)
                for i in range(len(L)):
                    t.append(L[i])
            else:
                t.append('Description: None')
        return t
    def tifText(self,t,isGeo):
        """
        Could set this up to return multiple strings, as in:
        return cnt,t    where t is or can be a tuple
        """
        if t[len(t)-1] == '\0':
            t = t[0:len(t)-1]
        if isGeo and t[len(t)-1] == '|':
            t = t[0:len(t)-1]
        t = replace(t,'\0','\\')
        if isGeo:
            t = replace(t,'|','\\')
        return t
    #end class tifFileClass

#--- testing ---

def test():
    #fn = 'D:/topo/110-37_ut_Escalante-E/o37110f5_ut_TicabooMesa/o37110f5.drg.tif'
    fn = 'D:\\topo\\111-36\\o36111g5_az_LeesFerry\\o36111g5.drg.tif.gz'
    fn = 'D:\\topoMisc\\quad100\\f37110a1.tif'
    #fn = 'D:\\DC120\\_billOfc.tif'
    fn = 'D:\\3DA\\45\\byliners\\undirobe\\shaghair\\urShag3rgb.tif'
    tiff = tifFileClass(None,fn)
    r = tiff.report()
    for i in range(len(r)):
        print r[i]
    print '\nMore...'
    for ifd in tiff.ifdList:
        for entry in ifd.entryList:
            s1,s2 = entry.report()
            print s1,s2
    td = tiff.getDate()
    if td:
        tu = tifTime2unix(td)
        print '\tdate/time:',td,tu,time.ctime(tu)
    if not tiff.isGeoTIFF():
        tiff.close()
        return
    ok,x = tiff.geoModelTiepoint()
    if ok:
        print '\ttiepoint =',x[0],x[1],x[2],x[3],x[4],x[5]
    else:
        print '\ttiepoint error:',x
    ok,x = tiff.geoModelPixelScale()
    if ok:
        print '\tpixel scale =',x[0],x[1],x[2]
    else:
        print '\tpixel scale error:',x
    print '\tASCII params:',tiff.geoAsciiParams()
    tiff.close()
    #end def test

if __name__ == '__main__':
    print '\nThis module (geotiff.py) is not a standalone program. It ',  \
          '\ncontains functions and classes used by both DEMpy and PullSDTS.', \
          '\n\tMore info at http://www.3dartist.com/WP/pullsdts/',      \
          '\nTesting now follows...'
    test()

### end module ###
