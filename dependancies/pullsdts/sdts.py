#!/usr/bin/python2
#sdts.py - a DEMpy/PullSDTS module - 5 Jan 02
#Update at http://www.3dartist.com/WP/pullsdts/
#Created by Bill Allen <dempy@3dartist.com>
"""
This module is common to both DEMpy and PullSDTS. It contains functions and
classes for working with USGS SDTS transfers found in multiple forms:
DDFs already individually available 1) on disk or 2) as fileLikeObject (FLO)
instances from the pulldem.py module, or contained within a TAR file either
3) on disk or 4) in RAM as an FLO, not to mention 5) an unopened .tar.gz.
------
Theory:
1) locate/poll the SDTS transfer - where are the DDF files?
2) examine the transfer for its contents & how to access them, report this
3) extract the desired data
------
Index, miscellaneous functions:
  dataConv - convert SDTS values to local Python values
  dem2raw - output DEM elevations as 16-bit grayscale RAW  
  dem2raw8 - output DEM elevations as 8-bit grayscale RAW  
  dem2ppm - convert DEM values to 24-bit RGB (grayscale + fill/void colors)
  demSpeedReader - kludge for faster reading of large data blocks
  findCode - look for a specific code such as a field delimeter
  readBuffer
  test - test this module's functions and classes when it is run by itself
Index, SDTS query functions
  qFormat
  reform - reformat specific kinds of SDTS data for presentation
  sdtsQueryKludge - special handling, such as for DLG AHDR.DDFs
  sdtsQueryMore - for lateral queries & reading repeating values
  sdtsQuery
  sdtsDEMreport
  sdtsDLGreport
Index, SDTS access functions in the bottom-up order they are used   
  readData - read data per the Entry Map
  readFieldSpec
  readSubfieldSpec
Index, classes, in the bottom-up order that they are invoked
  demClass - holds key info about an SDTS DEM that has been examined
  dlgClass
  drDirectoryClass
  drLeaderClass
  drClass
  ddrDirectoryClass
  ddrLeaderClass
  ddrClass
  ddfClass
  sdtsClass - central reference to all the files in an SDTS transfer
"""

#--- modules & constants ---

debugg = 0

import array, os, struct, sys, time
from string import capwords, digits, lower, split

thisDir = os.path.split(sys.argv[0])[0]
if not thisDir in sys.path:
    sys.path.append(thisDir)
import pulldem
from gztar import tarClass
from pulldem import addSeps, fileLikeObject, fixPath

ENDIAN  = sys.byteorder
ISO_DATATYPE = 'AIRSCB'

"""
#the following is not presently used
SDTSLABEL = {
'ADMU':'Attribute Domain Value Measurement Unit',
'ATLB':'Attribute Label',
'AUTH':'Attribute Authority',
'CDLV':'Coding Level',
'CLOO':'Column Offset Origin',
'CMNM':'Cell Module Name',
'CODE':'Cell Code',
'COMT':'Comment',
'DAID':'Data ID',
'DAST':'Data Structure',
'DCDT':'Data Set Creation Date',
'DOCU':'Standard Documentation Reference',
'DSTP':'Domain Spatial Address Type',
'DTYP':'Spatial Domain Type',
'DVAL':'Domain Value',
'DVDF':'Domain Value Definition',
'EXSP':'External Spatial Reference',
'FFYN':'Composites',
'FTLV':'Features Level',
'GTYN':'Vector Topology',
'HDAT':'Horizontal Datum',
'INTR':'Intracell Reference Location',
'LLBL':'Layer Label',
'LDXT':'Layer Dimension Extent Field',
'MODN':'Module Name',
'MPDT':'Map Date',
'NGDM':'Nongeospatial Dimensions',
'NCOL':'Number of Columns',
'NPLA':'Number of Planes',
'NROW':'Number of Rows',
'PDOC':'Profile Recommendation Reference',
'PLOO':'Plane Offset Origin',
'PRID':'Profile Identification',
'PRVS':'Profile Version',
'RAVA':'Range or Value',
'RCID':'Record ID',
'RCYN':'Raster',
'RSNM':'Reference System Name',
'RWOO':'Row Offset Origin',
'SOCI':'Scan Origin Column',
'SOPI':'Scan Origin Plane',
'SORI':'Scan Origin Row',
'STID':'Standard Identification',
'STVS':'Standard Version',
'TITL':'Title',
'VDAT':'Vertical Datum',
'VEM':'Vertical Encoding Method',
'VGYN':'Vector Geometry',
'ZONE':'Zone Number'}
"""

#--- miscellaneous functions ---

def dataConv(data,dType):
    """
    Used to convert SDTS data being read in. Reading out to a new file is a
    different problem due to the endian issue.
    """
    if dType == 'A':
        d = subf[i]
    elif dType in ['C','I']:
        d = int(data)
    elif dType in ['R','S']:
        d = float(data)
    elif dType[0] == 'B':
        if dType == 'B(16)':
            a = array.array('h',data)
        elif dType == 'B(32)':
            a = array.array('f',data)
        else:
            d = None
            print 'DEBUG sdts.dataConv unknown data type',dType
        if ENDIAN == 'little':      #SDTS is always big-endian
            a.byteswap()            #put into local endianess
        try:
            d = a[0]
        except IndexError,ValueError:
            print 'DEBUG sdts dataConv data type',dataType,'a =',a
            raise
    else:
        print 'DEBUG sdts dataConv unknown data type',dType
        d = None
    return d
    #end dataConv

def dem2ppm(sdts,rept=None):
    fn = fixPath(sdts.parent.ini.tmpDir,pulldem.getGeoTemp(sdts)+'.ppm')
    k = sdts.keyInfo
    elev = k.elevDict
    fill = '\0' + chr(127) + chr(255)
    max = chr(255)*3
    min = chr(2)*3
    void = chr(255) + '\0\0'
    DDF = sdts.ddf[sdts.ddfDict['CEL0']][1]
    if not DDF.data:
        print 'DEBUG sdts.dem2ppm: No DEM data to process'
        raise IOError
    spred = float(elev['zMax']-elev['zMin'])
    buff = 'P6\n' + str(k.dimX) + ' ' + str(k.dimY) + '\n255\n'     #header
    ppm = open(fn,'wb')
    ppm.write(buff)
    if k.dimY > 500:
        modCk = 35
    else:
        modCk = 10
    pc = 100.0 / float(k.dimY-modCk)    #modCk for effect to match %modCk below
    spreadPt = 253.0 / float(elev['zMax']-elev['zMin'])
    for row in range(k.dimY):
        buff = ''
        for col in range(k.dimX):
            z = DDF.data[row][col]
            if z == elev['void']:
                buff = buff + void
            elif z == elev['fill']:
                buff = buff + fill
            elif z >= elev['zMax']:     #fuzzy for floating point
                buff = buff + max
            elif z <= elev['zMin']:     #  -ditto-
                buff = buff + min
            else:
                try:
                    z = chr(int(round((z-elev['zMin'])*spreadPt))+2)
                except ValueError:
                    print row,col,'z =',z,'zMin =',elev['zMin'],'spred =',spred
                    print 'zMax =',elev['zMax'],'void =',elev['void'],'fill =',elev['fill'],
                    print
                    for i in range(5):
                        for j in range(5):
                            print DDF.data[i][j]
                buff = buff + z*3
        ppm.write(buff)
        if rept and row%modCk == 0:        #only report progress every # rows
            rept.progress(float(row)*pc)
    ppm.flush()
    ppm.close()
    return fn
    #end def dem2ppm

def dem2raw(pn,ddf,endian,header,row,col,unitFactor,fill,void,distrib,
            rngMin,rngMax,fillWhite=0,rept=None):
    """
    Choices
    x) Keep exact 16-bit values, no redistribution.
    =) Redistribute from min/max elevation to 30 to 65505.
    r) Redistribute from a set range, such as Death Valley to Mt. Whitney.
    """
    fmt = endian
    raw = open(pn,'wb')
    if header:
        raw.write(header)
    if row > 500:                       #modCk for effect to match %modCk below
        modCk = 35                      #  fewer hits for 10m files
    else:
        modCk = 10
    pc = 100.0/float(row-modCk)
    if distrib == 'x' or rngMin == None or rngMax == None:
        #output eXact DEM values
        fmt = fmt + 'h'
        for i in range(row):
            b = ''
            for j in range(col):
                z = unitFactor * ddf.data[i][j]
                b = b + struct.pack(fmt,int(round(z)))
            raw.write(b)
            if rept and i%modCk == 0:   #only report progress every # rows
                rept.progress(float(i)*pc)
    elif distrib in ['=','r']:          #equalize to spread between 30 & 65505
        fmt = fmt + 'H'                 #  based on self- or specified range
        if fillWhite:
            fillVal = 65535
            voidVal = 0
        else:
            fillVal = 0
            voidVal = 65535
        spreadPt = 65515.0 / float(rngMax-rngMin)
        for i in range(row):
            b = ''
            for j in range(col):
                z = ddf.data[i][j]
                if z == fill:
                    z = fillVal
                elif z == void:
                    z = voidVal
                else:
                    z = unitFactor * z
                    if z < rngMin:
                        z = rngMin
                    elif z > rngMax:
                        z = rngMax
                    z = int(round((z-rngMin)*spreadPt)) + 10
                b = b + struct.pack(fmt,z)
            raw.write(b)
            if rept and i%modCk == 0:   #only report progress every # rows
                rept.progress(float(i)*pc)
    raw.flush()
    raw.close()
    b = ''                              #cleanup
    #end def dem2raw

def dem2raw8(pn,ddf,endian,header,row,col,unitFactor,min,max,fill,void,distrib,
             rngMin,rngMax,fillWhite=0,rept=None):
    """
    Same as dem2raw except 1) output is unsigned 8-bit, and 2) fill and
    void are handled as new values. It is different from dem2ppm in that it
    locates the gray range into values 1-254 rather than 2-255, and, since
    values are output as single bytes, fill and void can't be colors.
    ------
    The min/max values are needed here but not in dem2raw because this
    function needs to calculate an adjustment to keep all values positive if
    a negative elevation is involved.
    """
    fmt = endian + 'B'                  #unsigned 1-byte integer, not 'I'!
    if fillWhite:
        fillVal = 255
        voidVal = 0
    else:
        fillVal = 0
        voidVal = 255
    if row > 500:
        modCk = 35
    else:
        modCk = 10
    pc = 100.0/float(row-modCk)         #modCk for effect to match %modCk below
    raw = open(pn,'wb')
    if header:
        raw.write(header)
    if distrib == 'x' or rngMin == None or rngMax == None:
        #output eXact DEM values
        if min < 0:
            adj = abs(min)
        else:
            adj = 0
        spreadPt = 253.0 / 32767.0
        for i in range(row):
            b = ''
            for j in range(col):
                z = ddf.data[i][j]
                if z == fill:
                    z = fillVal
                elif z == void:
                    z = voidVal
                else:                   #reduce to 8 bits (256) less 2
                    z = unitFactor * (z+adj)
                    z = int(round(z*spreadPt)) + 1
                try:
                    b = b + struct.pack(fmt,z)
                except TypeError:
                    print i,j,'z =',z,'is',type(z),'fmt =',fmt,'hex',hex(z)
                    raise
            raw.write(b)
            if rept and i%modCk == 0:   #only report progress every # rows
                rept.progress(float(i)*pc)
    elif distrib in ['=','r']:          #equalize to spread between 30 & 65505
        spreadPt = 253.0 / float(rngMax-rngMin)
        for i in range(row):            #  min/max elevations
            b = ''
            for j in range(col):
                z = ddf.data[i][j]
                if z == fill:
                    z = fillVal         #darkest black = fill area
                elif z == void:
                    z = voidVal         #brightest white = void area
                else:
                    z = unitFactor * z
                    if z < rngMin:      #safety
                        z = rngMin
                    elif z > rngMax:
                        z = rngMax
                    z = int(round((z-rngMin)*spreadPt)) + 1
                b = b + struct.pack(fmt,z)
            raw.write(b)
            if rept and i%modCk == 0:   #only report progress every # rows
                rept.progress(float(i)*pc)        
    raw.flush()
    raw.close()
    b = ''                              #garbage cleanup
    #end def dem2raw8

def demSpeedReader(celFile,keyInfo,dataRecip,rept=None):
    if type(celFile) == type('string'): #compatible with Python 2.0 & 2.2
        f = open(celFile,'rb')
    else:
        f = celFile                     #fileLikeObject
        f.open('r')
    b = f.read(7)                       #load & check the leader record
    b = b + f.read(int(b[0:5])-7) 
    if b[6] != 'L' or ord(b[-1]) != 30:
        print 'DEBUG sdts.demSpeedReader bad leader record'
        f.close()
        return None
    if b.find('(B(16))') > -1:          #a big kludge that works fast
        dType = 'h'
    elif b.find('(B(32))') > -1:
        dType = 'f'
    else:
        print 'DEBUG sdts.demSpeedReader unknown data type'
        f.close()
        return None
    colCnt = keyInfo.dimX               #load & process the data records
    L = dataRecip                       #load directly to parent
    newFlag = 1                         #flag first data record
    haslead = 1                         #becomes =0 to flag leaderless records
    pc = 100.0/float(keyInfo.dimY-1)    #-1 for effect
    for i in range(keyInfo.dimY):       #read all the data records
        if haslead:
            b = f.read(24)              #get the DR leader        
            if newFlag:
                newFlag = 0             #don't do this again
                if b[6] != 'D':         #do following records have leaders?
                    if b[6] == 'R':     #no more leaders
                        haslead = 0
                    else:
                        print 'DEBUG sdts.demSpeedReader unknown record type'
            dPtr = int(b[12:17])        #data area starting point
            fLen = int(b[21]) + 1       #position of # giving jump past aPtr
            b = b + f.read(dPtr-24)     #read in the DR directory
            dPtr = int(b[dPtr-fLen:dPtr-1]) #calc jump past aPtr to the data
            b = f.read(dPtr)            #read to the end of attributes
        else:
            b = f.read(dPtr)            #read/lose data attributes (row#, etc.)
        a = array.array(dType)
        a.fromfile(f,colCnt)            #read in a full row of elevation data
        b = f.read(1)                   #read record terminator
        if ord(b) != 30:
            print 'sdts.demSpeedReader bad record terminator =',ord(b)
            print 'dType =',dType,'array type =',a.ArrayType
            raise ValueError
        if ENDIAN == 'little':          #SDTS is always big-endian
            a.byteswap()                #put into local endianess
        L.append(a)
        if rept:
            rept.progress((float(i))*pc)
    f.close()
    return dType
    #end def demSpeedReader

def findCode(o,b):
    for i in range(len(b)):
        if ord(b[i]) == o:
            return i
    return -1

def readBuffer(f,cc):
    try:
        s = f.read(cc)
        if not s:
            f.close()
            return 1,'eof'
        else:
            return 1,s
    except IOError, (errNo, strError):
        f.close()
        return 0,'I/O Error ('+str(errNo)+'): '+strError
    #end readBuffer

#--- SDTS query functions --- ### these need some work

def qFormat(item,q,match,good,bad):
    if item != '':
        s = item + ': '
    else:
        s = ''
    if q:
        s = s + str(q)
        if match == '' or (match != '' and match == q):
            if good != '':
                s = s + ' ' + good
        else:
            if bad == '':
                s = s + ' (oops?)'
            else:
                s = s + ' ' + bad
    else:
        s = s + '(not found)'
    return s
    #end def qFormat

def reform(q,m,v,prod='DEM'):
    """
    Reformat specific kinds of SDTS data for presentation.
    q = the SDTS label for the data being queried
    m = the DDF module being queried
    v = the data to be reported
    prod = 'dem' or 'dlg' (DEM is default, often works same for DLG)
    """
    if q == 'TITL':                     #quad name (in IDEN only?)
        p = v.find(',')
        t = capwords(v[0:p])+v[p:p+4]
        if prod == 'DLG':
            p = split(v)
            p = capwords(p[len(p)-1])
            return t,p
        else:
            return t
    elif q == 'DCDT':                   #data set date (in IDEN only?)
        if len(v) == 7:                 #bad date field in 2001 DEM revisions
            v = v[0:4] + '0' + v[4:7]
        mo = ['Jan','Feb','Mar','Apr','May','Jun',
             'Jul','Aug','Sep','Oct','Nov','Dec'][int(v[4:6])-1]
        return str(int(v[6:8]))+' '+mo+' '+v[0:4]
    else:
        return v
    #end def reform

def sdtsQueryKludge(sdts,q,module):
    if module == 'AHDR':
        for i in range(len(sdts.ddf)):
            if sdts.ddf[i][0].find('AHDR') > -1:
                sf = sdts.ddf[i][1].dr[0].subf
                L = split(sf[len(sf)-1])[-8:]
                L2 = []
                for j in range(8):
                    L2.append(float(L[j]))
                return L2
    else:
        return None
    #end def sdtsQueryKludge

def sdtsQueryMore(subfLabel,subf,get,repeating=0):
    """
    Query info from within a DR record already arrived at by some manner.
    Multiple labels in get can be used to retrieve multiple values in one call.
    With repeating=1, multiple values with repeating labels can be retrieved.
    ---
    global debugg
    if debugg:
        print '}',subfLabel
        print '}',subf
        print '}',get
    """
    L = []                              #list for retrieving multiple values
    if repeating:                       #handle alternately repeating labels
        sfList = split(get,'!')         #make a list of the repeating labels
        sfListMax = len(sfList) - 1     #  such as *X!Y
        sfListPtr = 0
        subfPtr = -1
        for i in range(len(subf)):
            lbl = subfLabel[i][1]
            if lbl[0] == '*':
                lbl = lbl[1:]
            if lbl == sfList[sfListPtr] and subfPtr < i:
                """
                Since this function will be used to retrieve huge amounts
                of binary data, leave it in its raw form to be processed
                as needed by the calling, or a subsequent, routine. The
                data is returned as a tuple of (label,data type,raw data).
                """
                L.append((lbl,subfLabel[i][2],subf[i]))
                subfPtr = i
                if sfListPtr == sfListMax:
                    sfListPtr = 0
                else:
                    sfListPtr = sfListPtr + 1
            else:
                continue                #loop again
    elif get[0] == 'ELEVATION':         #DEM data
        for i in range(len(subf)):
            if subfLabel[i][1] in ['ELEVATION','*ELEVATION']:
                L.append(subf[i])
        return L
    else:
        for fld in get:
            data = None
            for i in range(len(subf)):
                if subfLabel[i][1] == fld:
                    data = subf[i]
                    break               #one value per label
            L.append(data)
    return L
    #end def sdtsQueryMore

def sdtsQuery(sdts,q,module,detail=None):
    """
    Query an SDTS transfer.
    q is the field being queried
    module is the DDF, if specific, where the field should be found
    detail, usually =None, is for locating a value among multiple records
    """
    modFound = 0
    for i in range(len(sdts.ddf)):
        """
        If module = '', then, if DDF <> None, check it for the field wanted.
        """
        if module == sdts.ddf[i][0]:
            modFound = 1
            break
    if modFound and sdts.ddf[i][1].fileObj: #not a fileObj=None
        DDF = sdts.ddf[i][1]
        e = DDF.ddr.dir.entry           #all directory entries
        f = DDF.ddr.dir.field           #all field descriptions
        if detail:
            detail = lower(detail)
        drNoMax = len(DDF.dr) - 1
        for drNo in range(len(DDF.dr)):
            DR = DDF.dr[drNo].subf
            if module == 'CEL0' and q == 'ELEVATION':
                d = sdtsQueryMore(f[2][3]+f[3][3],DR,[q])
                sdts.ddf[i][1].data.append(d)   #accumulate DEM data
                if drNo == drNoMax:
                    return
                else:
                    continue            #loop
            z = -1
            for j in range(len(e)):
                if f[j][1]:             #if isn't empty
                    for k in range(len(f[j][3])):
                        z = z + 1
                        c = f[j][3][k][1]
                        if c[0] == '*':     #remove * from label
                            c = c[1:]
                        special = (module == 'SPDM' and c in ['X','Y']
                                   and q == 'X!Y')
                        if c == q or special:
                            if detail:
                                if lower(DR[z]).find(detail) == -1:
                                    continue            #loop again
                            #---special cases first
                            if module == 'DDOM' and c == 'DVDF':
                                t = sdtsQueryMore(f[2][3],DR,['DVAL','ADMU'])
                                s = ''
                                if t[1]:                #units: meters, feet
                                    t[1] = lower(t[1])
                                return t    #returning a tuple, not a string!
                            elif module == 'IDEN' and c == 'DAID':
                                v = split(DR[z])
                                i = len(v)
                                if i == 6:      #old SDTS
                                    return (float(v[1]),float(v[3])),v[5]
                                elif i == 12:   #new SDTS
                                    return (pulldem.decDeg(v[1],v[2],v[3],3),      \
                                            pulldem.decDeg(v[6],v[7],v[8],3)), \
                                           v[11]
                                else:
                                    print 'DEBUG sdts DAID field has',i,'elements'
                                    return (0.0,0.0),'?'
                            elif module == 'IDEN' and c == 'TITL':
                                return reform(q,module,DR[z],sdts.type[0:3])
                            elif module == 'SPDM' and c in ['X','Y']:
                                """
                                Because the data is all in one array, but the
                                fields of subfields each have their own array,
                                those arrays must be concatenated to relate
                                directly to the data to allow querying IF what
                                is wanted is not in the first field (remember
                                that the 0000 and 0100 fields aren't used here).
                                """
                                t = sdtsQueryMore(f[2][3]+f[3][3],DR,q,1)
                                return t
                            else:
                                return reform(q,module,DR[z])
                        #end for k loop
                #end for j loop
            #end for drNo loop
    return None                         #fell through without result
    #end def sdtsQuery

def sdtsDEMreport(sdts):
    """
    This function just kind of grew over time as a way to check out what
    had been made accessible in the SDTS file and probably needs to be
    reworked to get the key info first, then report.
    """
    sdts.getSelf(['DDOM','DQHL','IREF','LDEF','SPDM','XREF'])
    k = sdts.keyInfo
    r = []
    t = os.path.split(sdts.fname)
    r.append('FILE NAME: '+t[1])
    r.append('IN FOLDER: '+t[0])
    r.append('FILE DATE: '+pulldem.fixDateTuple(time.ctime(sdts.fileDate)))
    k.date = dt = sdtsQuery(sdts,'DCDT','IDEN')
    """
    #save this for when there's a way to look in 'any' DDF file
    #  which looks like it needs to have a new function, maybe
    #  DDF.fieldList, which also could be more efficient than current
    #  look-up system
    q = sdtsQuery(sdts,'MPDT','')     #any other internal date
    if q:
        dt = dt + ' (' + q + ')'
    """
    r.append('DATA DATE: '+dt)
    r.append('FILE SIZE: '+pulldem.fixSize(sdts.size))
    r.append('DATA TYPE: USGS SDTS transfer')
    k.name = sdtsQuery(sdts,'TITL','IDEN')
    r.append('QUAD NAME: '+k.name)
    r.append('-'*len(r[len(r)-1]))
    k.geoCornerSE,k.scale = sdtsQuery(sdts,'DAID','IDEN')
    q = sdtsQuery(sdts,'COMT','DQHL','DEM LEVEL')
    if q:
        if q.find('DEM LEVEL 2 means:') > -1 or q == 'DEM LEVEL-2':
            k.level = '2'
            q = 'Level 2 '
        elif q.find('DEM LEVEL 1 means:') > -1 or q == 'DEM LEVEL-1':
            k.level = '1'
            q = 'Level 1 '
        else:
            q = ''
    else:
        q = ''
    t = sdtsQuery(sdts,'XHRS','IREF')
    if t:
        k.scaleXY = int(t)
        t = str(int(t)) + 'm '
    else:
        t = ''
    r.append('Data set type: raster')
    r.append('  1:'+str(k.scale)+'-scale '+q+t+sdts.type)
    if k.date[-4:] < '2001':
        r.append('  WARNING: Pre-2001 DEM, errors likely')
    else:
        r.append('  Note: Newly corrected DEM ('+k.date[-4:]+')')
    t = 'Coordinate system: '           #UTM info
    q = sdtsQuery(sdts,'RSNM','XREF')
    if q:
        t = t + q
        if q != 'UTM':
            t = t + ' WARNING!'
        else:
            q = sdtsQuery(sdts,'ZONE','XREF')
            if q:
                t = t + ' Zone ' + q
                k.utmZone = q
            else:
                t = t + ' (zone?)'
    else:
        t = t + '(not found)'
    r.append(t)
    q = sdtsQuery(sdts,'HDAT','XREF')       #horizontal datum
    if q == 'NAS':
        k.datum = 'NAD27'
    else:
        k.datum = q
    r.append(qFormat('Datum',q,'NAS','(NAS-C aka NAD27)','WARNING!'))
    q = k.corner('nw')
    r.append('NW corner: UTM '+str(q[0])+', '+str(q[1]))
    q = k.corner('se')
    r.append('SE corner: UTM '+str(q[0])+', '+str(q[1]))
    r.append(' '*11+'lat. '+str(k.geoCornerSE[0])+' long. '
             +str(k.geoCornerSE[1]))
    q = sdtsQuery(sdts,'NCOL','LDEF')
    k.dimX = q
    t = 'Dimension: ' + str(q)
    q = sdtsQuery(sdts,'NROW','LDEF')
    k.dimY = q
    t = t + 'x' + str(q) + ' points wide x high'
    r.append(t)
    #r.append(qFormat('',sdtsQuery('',''),'','','')) #extra blank copy
    q = sdtsQuery(sdts,'DVDF','DDOM','minimum')
    k.elevDict['zMin'] = q[0]
    t = sdtsQuery(sdts,'DVDF','DDOM','maximum')
    k.elevDict['zMax'] = t[0]
    k.unitZ = t[1]
    s = 'Elevation: '+addSeps(q[0])+' - '+addSeps(t[0])
    if t[1] == 'meters':
        if str(type(q[0])) == "<type 'float'>":
            r.append('Elev unit: decimal meters')
        else:
            r.append('Elev unit: whole meters')
        s = s + 'm (' + addSeps(int(float(q[0])*3.2808)) + '-'      \
            + addSeps(int(float(t[0])*3.2808)) + "')"
        r.append(s)
    elif t[1] == 'feet':
        r.append('Elev. unit: feet')
        s = s + "' (" + addSeps(round(float(q[0])/3.2808,1)) + '-'   \
            + addSeps(round(float(t[0])/3.2808,1)) + 'm)'
        r.append(s)
    else:
        print 'DEBUG sdts.sdtsDEMreport z units =',t[1]
        r.append('Elevation: '+str(q[0])+'-'+str(t[0])+' '+t[1])        
    k.elevDict['fill'] = sdtsQuery(sdts,'DVDF','DDOM','fill')[0]
    k.elevDict['void'] = sdtsQuery(sdts,'DVDF','DDOM','void')[0]
    """
    q = ''                                  #look for odd LDEF values
    if sdtsQuery(sdts,'CODE','LDEF') != 'V': # cud do separately or switch off
        q = q + 'CODE<>V'
    if sdtsQuery(sdts,'INTR','LDEF') != 'CE':
        q = q + '/INTR<>CE'
    if sdtsQuery(sdts,'SORI','LDEF') != 1     \
       or sdtsQuery(sdts,'SOCI','LDEF') != 1:
        q = q + '/origin<>1'
    if sdtsQuery(sdts,'RWOO','LDEF') != 0     \
       or sdtsQuery(sdts,'CLOO','LDEF') != 0:
        q = q + '/offset<>0'
    if sdtsQuery(sdts,'VDAT','XREF') != 'NGVD':
        q = q + '/VDAT<>NGVD'
    if q != '':
        r.append('Problem: '+q)
    """
    return r
    #end sdtsDEMreport

def sdtsDLGreport(sdts):
    sdts.getSelf(['AHDR','XREF'])
    k = sdts.keyInfo
    r = []
    t = os.path.split(sdts.fname)
    r.append('FILE NAME: '+t[1])
    r.append('IN FOLDER: '+t[0])
    r.append('FILE DATE: '+pulldem.fixDateTuple(time.ctime(sdts.fileDate)))
    k.date = dt = sdtsQuery(sdts,'DCDT','IDEN')
    r.append('DATA DATE: '+dt)
    r.append('FILE SIZE: '+pulldem.fixSize(sdts.size))
    r.append('DATA TYPE: USGS SDTS transfer')
    k.name,k.dlgType = sdtsQuery(sdts,'TITL','IDEN')
    r.append('QUAD NAME: '+k.name)
    r.append('-'*len(r[len(r)-1]))
    k.scale = sdtsQuery(sdts,'SCAL','IDEN')
    r.append('Data set type: vector')
    r.append('  1:'+str(k.scale)+'-scale '+sdts.type+' '+k.dlgType)
    t = 'Coordinate system: '           #UTM info
    q = sdtsQuery(sdts,'RSNM','XREF')
    if q:
        t = t + q
        if q != 'UTM':
            t = t + ' WARNING!'
        else:
            q = sdtsQuery(sdts,'ZONE','XREF')
            if q:
                t = t + ' Zone ' + q
                k.utmZone = q
            else:
                t = t + ' (zone?)'
    else:
        t = t + '(not found)'
    r.append(t)
    q = sdtsQuery(sdts,'HDAT','XREF')       #horizontal datum
    if q == 'NAS':
        k.datum = 'NAD27'
        r.append('Datum: NAS (NAS-C aka NAD27)')
    else:
        k.datum = q
        r.append('Datum: '+q)
    k.geoCorners = sdtsQueryKludge(sdts,'','AHDR')
    q = k.getCorner('se')
    if q:
        r.append('SE corner: lat. '+str(round(q[0],3))
                 +' long. '+str(round(q[1],3)))
    r.append('')
    r.append('Note: Because PullSDTS doesn\'t handle')
    r.append('  DLG data, no related load or other')
    r.append('  functions are available here.')
    return r
    #end def sdtsDLGreport

#--- SDTS access functions in the bottom-up order they are used ---

def readData(fld,eMap,buff):            #---STEP #4c---
    if fld[0][0].find('SPDM.DDF') > -1:
        """
        The following is to force run-on handling where the * flag has been
        omitted, such as seen in 2001-revised SDTS DEMs.
        """
        if fld[3][3][0][1] == 'X':
            fld[3][3] = [(fld[3][3][0][0],'*X',fld[3][3][0][2]),fld[3][3][1]]
    data = []
    e = eMap
    f = fld
    if f[0][0][:4] == '0000':           #normalize leader/data field list
        f = f[1:]                       #  by removing first non-field
    for i in range(len(e)):             #iterate through number of entry maps
        b = buff[e[i][2]:e[i][2]+e[i][1]]   #grab the buffer portion
        binaryCnt = -1                  #store's bytes-to-go for binary repeats
        if ord(b[-1]) != 30:
            return 0,'Error in DR directory or data.',None
        b = b[:-1]                  #remove the unit terminator
        if f[i][0][:4] == '0100':   #ignore DDF record ID
            pass                    #***can anything else match this condition? 
        else:
            sf = -1
            runOnField = [('','')]  #holds queue of repeat data field/types
            runOnFlag = 0           #turn on after * to collect data types
            runOnPtr = -1           #points to queue, -1 if not active
            while 1:
                flagEnd = 0
                sf = sf + 1         #subfield pointer
                try:
                    dataType = f[i][3][sf][2]
                except IndexError:
                    #print '\nsf =',sf,'fi3 = ',f[i][3],'runOnFlag:',runOnFlag,'runOnPtr:',runOnPtr,buff
                    if runOnFlag:
                        runOnFlag = 0   #no more collecting data types
                        runOnPtr = 0
                        dataType = runOnField[0][1]
                        #add corresponding DDR field to match repeat data field
                        #has to be i+1 because i here doesn't count 0000 field
                        fld[i+1][3].append((f[i][0],runOnField[0][0],
                                            runOnField[0][1]))
                    elif runOnPtr > -1:
                        if runOnPtr+1 < len(runOnField):
                            runOnPtr = runOnPtr + 1
                        else:
                            runOnPtr = 0
                        dataType = runOnField[runOnPtr][1]
                        fld[i+1][3].append((f[i][0],
                                            runOnField[runOnPtr][0],
                                            runOnField[runOnPtr][1]))
                    else:       #presume undelimited data for normal subfield
                        break   #  **DEVnote: may be a potential bug source
                if dataType in ['B(16)','B(32)']:   #undelimited binary data
                    if dataType == 'B(16)':
                        byteCnt = 2
                    else:
                        byteCnt = 4
                    if binaryCnt == -1:
                        binaryCnt = len(b) - byteCnt  #will be removed below
                    else:
                        if binaryCnt == byteCnt:
                            binaryCnt = 0
                            flagEnd = 1         #no more binary values = done
                        else:
                            binaryCnt = binaryCnt - byteCnt
                    d = b[0:byteCnt]
                    b = b[byteCnt:]
                else:
                    ft = findCode(31,b)     #delimited data
                    if ft == -1:            #no more field terminators = done
                        flagEnd = 1
                        d = b
                    else:
                        d = b[:ft]
                        b = b[ft+1:]
                if runOnFlag:
                    runOnField.append((f[i][3][sf][1],dataType))
                elif runOnPtr == -1:
                    if f[i][3][sf][1][0] == '*':  #flags repeat fields
                        runOnField[0] = ((f[i][3][sf][1][1:],dataType))
                        runOnFlag = 1
                #---handle data types-------------------------------------
                #   done here rather than in dataConv for speed
                if dataType[0] == 'B':          #AIRSCB
                    if dataType == 'B(16)':
                        a = array.array('h',d)  #SDTS is always big-endian
                    elif dataType == 'B(32)':
                        a = array.array('f',d)
                    else:
                        a = d
                        print 'DEBUG sdts unknown data type',dataType
                    if ENDIAN == 'little':
                        a.byteswap()            #put into native endianess
                    try:
                        v = a[0]                #turn into a signed integer
                    except IndexError,ValueError:
                        print 'DEBUG sdts data type',dataType,'error: a =',a
                        raise
                elif dataType == 'A':
                    v = d
                elif dataType in ['C','I']:
                    v = int(d)
                elif dataType in ['R','S']:
                    v = float(d)
                else:
                    return 0,'DEBUG sdts unknown data type: '+dataType,None
                data.append(v)
                if flagEnd:
                    break
                #end while true
        #end for i in range(len(eMap))
    return 1,'',data
    #end def readData

def readFieldSpec(u):                   #---STEP #3c1---
    f = ['','','',[]]
    if ord(u[-1:]) != 30:               #must have unit terminator
        return 0,f
    else:
        j = 0
        for i in range(len(u)-1):       #don't read unit terminator
            if ord(u[i]) == 31:
                j = j + 1
            else:
                f[j] = f[j] + u[i]
        if f[1] !='' or f[2] !='':
            if not (f[1] !='' and f[2] !=''):       #need both or none
                return 0,f
            ok,subf = readSubfieldSpec(f[0],f[1],f[2]) #subfield labels/types
            if ok:
                f[3] = subf
            else:
                return 0,f
        return 1,f
    #end def readFieldSpec

def readSubfieldSpec(p,f,t):            #---STEP #3c2---
    sf = []
    T = []
    t = t[1:-1]
    n = ''
    bPlus = ''
    for i in range(len(t)):             #get the format types
        if bPlus != '':
            bPlus = bPlus + t[i]
            if t[i] == ')':
                if n == '':
                    T.append(bPlus)
                else:
                    for j in range(int(n)):
                        T.append(bPlus)
                    n = ''
                bPlus = ''
        elif t[i] == ',':
            n = ''
        elif t[i] in digits:
            n = n + t[i]
        elif t[i] in ISO_DATATYPE:
            if t[i] == 'B':
                if i < len(t):
                    if t[i+1] == '(':
                        bPlus = t[i]
            if bPlus == '':
                if n == '':
                    T.append(t[i])
                else:
                    for j in range(int(n)):
                        T.append(t[i])
                    n = ''
    j = -1
    lab = ''
    for i in range(len(f)):             #get the labels
        if f[i] == '!':
            j = j + 1
            sf.append((p,lab,T[j]))
            lab = ''
        else:
            lab = lab + f[i]
    sf.append((p,lab,T[j+1]))           #get the last one
    if len(T) != len(sf):
        return 0,sf
    else:
        return 1,sf
    #end def readSubfieldSpec

#--- classes (in bottom-up rather than alpha order) ---

class demClass:
    """
    For storing key info needed to work with an SDTS DEM.
    self.elevDict, etc. can be expanded on-the-fly to include other key
      values, such as a lake level, that may be needed for later reference.
    """
    def __init__(self,parent):
        self.parent = parent
        self.name = None                #usually a quad name
        self.geoCornerSE = None,None    #geo coordinates for SE quad corner
        self.datum = None
        self.date = None
        self.dimX = None                #column count
        self.dimY = None                #row count
        self.cornerDict = {'xMin':None,'xMax':None,'yMin':None,'yMax':None}
        self.elevDict = {'fill':None,'zMax':None,'zMin':None,'void':None}
        self.level = None
        self.scale = None
        self.scaleXY = None
        self.unitXY = None
        self.unitZ = None
        self.utmZone = None
    def corner(self,c='nw'):            #defaults to NW corner
        if self.cornerDict['xMin'] == None:
            if not self.findCorners():
                return None,None
        if c == 'ne':
            return self.cornerDict['xMax'],self.cornerDict['yMax']
        elif c == 'se':
            return self.cornerDict['xMax'],self.cornerDict['yMin']
        elif c == 'sw':
            return self.cornerDict['xMin'],self.cornerDict['yMin']
        else:
            if c != 'nw':
                print 'DEBUG demClass corner error, call =',c
            return self.cornerDict['xMin'],self.cornerDict['yMax']
    def findCenter(self):
        if self.cornerDict['xMin'] == None:
            if not self.findCorners():
                return None,None
        x = float(self.cornerDict['xMin'])                  \
                  + ((float(self.cornerDict['xMax'])        \
                     - float(self.cornerDict['xMin']))/2.0)
        y = float(self.cornerDict['yMin'])                  \
                  + ((float(self.cornerDict['yMax'])        \
                     - float(self.cornerDict['yMin']))/2.0)
        return round(x,1),round(y,1)
    def findCorners(self):
        q = sdtsQuery(self.parent,'X!Y','SPDM')
        if q == None:
            return 0
        c = self.cornerDict
        for e in q:
            #this comes in the tuple, (label, datatype, data)
            d = round(dataConv(e[2],e[1]),1)
            if e[0] == 'X':
                if not c['xMin'] or d < c['xMin']:
                    c['xMin'] = d
                if not c['xMax'] or d > c['xMax']:
                    c['xMax'] = d
            elif e[0] == 'Y':
                if not c['yMin'] or d < c['yMin']:
                    c['yMin'] = d
                if not c['yMax'] or d > c['yMax']:
                    c['yMax'] = d
        if c['xMin'] == c['xMax'] or c['yMin'] == c['yMax']:
            print 'DEBUG sdts findCorners failure'
            return 0
        return 1
    #end class demClass

class dlgClass:
    """
    For storing key info needed to work with an SDTS DLG.
    Note: currently there is no implementation for working with DLG data here.
    """
    def __init__(self,parent):
        self.parent = parent
        self.name = None                #usually a quad name
        self.date = None
        self.dlgType = None
        self.geoCorners = []
        self.scale = None
    def getCorner(self,c):
        if not self.geoCorners:
            return None
        if c == 'sw':
            return self.geoCorners[0],self.geoCorners[1]
        if c == 'nw':
            return self.geoCorners[2],self.geoCorners[3]
        if c == 'ne':
            return self.geoCorners[4],self.geoCorners[5]
        if c == 'se':
            return self.geoCorners[6],self.geoCorners[7]
    #end class dlgClass

class drDirectoryClass:                 #---STEP #4b---
    def __init__(self,map,b):
        self.buff1 = b                  #directory entries
        self.map = map
        self.entryLen = map[0] + map[1] + map[2]
        self.entry = []                 #have 2x for safety
    def getSelf(self):                  #load up DDR directory entries
        b = self.buff1
        m = self.map
        self.entry = []                 #have 2x for safety
        for i in range(self.entryCount()):
            b2 = b[0:self.entryLen]     #get this portion
            b = b[self.entryLen:]       #  & deduct it from the whole
            e = ( b2[0:m[0]],
                  int(b2[m[0]:m[0]+m[1]]),
                  int(b2[m[0]+m[1]:self.entryLen]) )
            self.entry.append(e)
    def entryCount(self):
        return (len(self.buff1)-1) / self.entryLen
    def test(self,parent):
        return ( (ord(self.buff1[-1:]) == 30)    \
             and ((len(self.buff1)-1)%self.entryLen == 0) )
    #end drDirectoryClass

class drLeaderClass:                    #---STEP #4a---
    def __init__(self,b):
        self.buff = b
    """
    These functions are in the order of the data locations they report.
    """
    def recLen(self):
        try:
            v = int(self.buff[0:5])
            return v
        except ValueError:
            return -1
    def startData(self):
        try:
            v = int(self.buff[12:17])
            return v
        except ValueError:
            return -1
    def entryMap(self):
        b = self.buff
        try:
            v = int(b[23]),int(b[20]),int(b[21])
            return v
        except ValueError:
            return -1,-1,-1
    """
    Other functions.
    """
    def test(self):
        if self.recLen() < 1 or self.startData() < 1:
            return 0,'Length specs aren\'t integer values.\n'   \
                     +'\t(Check bytes 0-4 and 12-16.)'
        if self.buff[6] not in ['D','R']:
            return 0,'Code is <'+self.buff[6]+'>, should be <D>.'
        if self.entryMap()[0] == -1:
            return 0,'ValueError in entry map'
        return 1,''
    #end class drLeaderClass

class drClass:                          #---STEP #4--- (ONE data record)
    def __init__(self,parent):
        self.ddfFile = parent
        self.subf = None
    def getSelf(self):
        f = self.ddfFile.fileObj
        ok,buff = readBuffer(f,24)      #get DR leader
        if buff  == 'eof':
            return 1,buff
        elif not ok:
            return 0,buff+'\n\tUnable to read from '+parent.fileName
        self.leader = drLeaderClass(buff)
        ok,msg = self.leader.test()     #test DR leader
        if not ok:
            return 0,msg
        ok,b = readBuffer(f,self.leader.startData()-24)       #get DR entries
        if not ok:
            return 0,b
        self.dir = drDirectoryClass(self.leader.entryMap(),b) #get DR dir
        if not self.dir.test(self):                           #test DR dir
            return 0,'DR directory error in '+self.ddfFile.fileName
        self.dir.getSelf()
        ok,b = readBuffer(f,self.leader.recLen()-self.leader.startData())
        if not ok:                      #get data area
            return 0,b
        #send DR entry maps & DDR fields/subfields
        ok,msg,d = readData(self.ddfFile.ddr.dir.field,self.dir.entry,b)
        if not ok:
            return 0,msg
        if msg == 'eof':
            return 1,msg
        self.subf = d
        return 1,''
    #end class drClass

"""
--- ABOVE data record classes -- data descriptive record classes BELOW ---
"""

class ddrDirectoryClass:                #---STEP #3b---
    def __init__(self,map,b,c):
        self.buff1 = b                  #directory entries
        self.buff2 = c                  #data descriptive area
        self.map = map
        self.entryLen = map[0] + map[1] + map[2]
        self.entry = []                 #have 2x for safety
        self.field = []
    def getSelf(self):                  #load up DDR directory entries
        b = self.buff1
        c = self.buff2
        m = self.map
        self.entry = []                 #have 2x for safety
        self.field = []
        for i in range(self.entryCount()):
            b2 = b[0:self.entryLen]     #get this portion
            b = b[self.entryLen:]       #  & deduct it from the whole
            e = ( b2[0:m[0]],
                  int(b2[m[0]:m[0]+m[1]]),
                  int(b2[m[0]+m[1]:self.entryLen]) )
            self.entry.append(e)
            ok,fld = readFieldSpec(c[e[2]:e[1]+e[2]])
            if ok:
                self.field.append(fld)
            else:
                self.bail('Error in field '+c[e[2]:e[1]+e[2]])
    def entryCount(self):
        return (len(self.buff1)-1) / self.entryLen
    def test(self,parent):
        return ( (ord(self.buff1[-1:]) == 30)               \
             and ((len(self.buff1)-1)%self.entryLen == 0)   \
             and (ord(self.buff2[-1:]) == 30) )
    def bail(self,msg):
        return 0,msg
    #end ddrDirectoryClass

class ddrLeaderClass:                   #---STEP #3a---
    def __init__(self,b):
        self.buff = b
    """
    These functions are in the order of the data locations they report.
    """
    def recLen(self):
        try:
            v = int(self.buff[0:5])
            return v
        except ValueError:
            return -1
    def fieldLabelLen(self):
        try:
            v = int(self.buff[10:12])
            return v
        except ValueError:
            return -1
    def startArea(self):
        try:
            v = int(self.buff[12:17])
            return v
        except ValueError:
            return -1
    def entryMap(self):
        b = self.buff
        try:
            v = int(b[23]),int(b[20]),int(b[21])
            return v
        except ValueError:
            return -1,-1,-1
    """
    Other functions.
    """
    def test(self):
        if self.recLen() < 1 or self.fieldLabelLen() < 1    \
            or self.startArea() < 1:
            return 0,'Length specs aren\'t integer values.\n'   \
                     +'\t(Check bytes 0-4, 10-11, 12-16.)'
        if self.buff[5] != '2':
            return 0,'Interchange level is <'+b[5]+'>, should be <2>.'
        if self.buff[6] != 'L':
            return 0,'Code is <'+b[6]+'>, should be <L>.'
        if self.entryMap()[0] == -1:
            return 0,'ValueError in entry map'
        return 1,''
    def bail(self,msg):
        return 0,msg
    #end class ddrLeaderClass

class ddrClass:                         #---STEP #3--- (leader record)
    def __init__(self,parent):
        self.ddfFile = parent
        self.dir = None
    def getSelf(self):
        if not self.ddfFile.fileObj:
            return 0,''
        f = self.ddfFile.fileObj
        ok,buff = readBuffer(f,24)      #get DDR leader
        if not ok:
            return 0,buff+'\n\tUnable to read from '+parent.fileName
        elif buff == 'eof':
            return 0,'Premature end of '+parent.fileName
        self.leader = ddrLeaderClass(buff)
        ok,msg = self.leader.test()     #test DDR leader
        if not ok:
            return 0,msg
        ok,b = readBuffer(f,self.leader.startArea()-24)     #get DDR entries
        if not ok:
            return 0,b
        ok,c = readBuffer(f,self.leader.recLen()-self.leader.startArea())
        if not ok:                              #get DDR data descriptive area
            return 0,c
        self.dir = ddrDirectoryClass(self.leader.entryMap(),b,c) #get DDR dir
        if not self.dir.test(self):                              #test DDR dir
            self.bail('DDR directory error in '+self.ddfFile.fileName)
        self.dir.getSelf()
        return 1,''
    #end class ddrClass

"""
--- ABOVE record classes -- DDF & SDTS classes BELOW ---
"""

class ddfClass:                         #---STEP #2---
    def __init__(self,parent,fn):
        self.sdtsXfer = parent
        self.fileName = fn
        self.fileObj = None
        self.ddr = None
        self.data = []                  #for holding DEM or DLG big data block
        self.dataType = None            #big data block's incoming data type
    def getSelf(self):
        """
        global debugg
        if self.fileName.find('CEL0.DDF') > -1:
            debugg = 1
        else:
            debugg = 0
        """
        try:
            self.fileObj = open(self.fileName,'rb')
        except IOError, (errNo, strError):
            return 0,'I/O Error ('+str(errNo)+'): '+strError        \
                      +'\nFile '+self.fileName+' not available.'
        self.ddr = ddrClass(self)       #init DDR class
        ok,msg = self.ddr.getSelf()     #work DDR class, test for errors
        if not ok:
            self.fileObj.close
            return 0,msg
        self.dr = []                    #init list DR class, 1 or more records
        while 1:
            dataRec = drClass(self)
            ok,msg = dataRec.getSelf()  #leader, directory, data
            if ok:
                if msg == 'eof':
                    break
                else:
                    self.dr.append(dataRec)
            else:
                self.fileObj.close
                return 0,msg
        self.fileObj.close
        return 1,''
    #end class ddfClass

class sdtsClass:                        #---STEP #1---
    """
    sdtsClass()
    ------
    An SDTS transfer can consist of a .tar.gz file needing to be opened, or
      an intact TAR file on disk or in memory as an FLO, or as a collection
      of DDF files in one folder on disk or as individual FLOs. So, first
      off, which is it?
    1) individual DDFs, hand off the iden.ddf path or as an FLO set
    2) the original TAR file, hand off the .tar path or the FLO
    3) the original .tar.gz, hand off its path
    """
    def __init__(self,master,fn,orig=''):
        """
        Origin can equal fn for a DDF, otherwise is a TAR or tarball file.
        """
        if orig:
            self.fname = orig
        else:
            self.fname = fn
        self.parent = master
        s = os.stat(self.fname)
        self.keyInfo = None             #self.initKeyInfo to DEM or DLG
        self.size = s[6]
        self.fileDate = s[8]
        self.inDir,nm = os.path.split(fn)
        self.setName = nm[0:len(nm)-8]  #e.g., '1168' from 1168iden.ddf
        self.ddf = []                   #searchable, referenceable DDF list
        self.ddfDict = {}               #directory of DDFs
        self.type = None
    def close(self):
        """
        Currently has no use, but is here for file-like compatibility.
        """
        pass
    def getSelf(self,fList):
        """
        Note that this function works progressively, so just key info DDFs
        can be loaded first for determining type of SDTS and giving a report,
        and the big data DDF(s) can be loaded later when and if needed.
        """
        for f in fList:
            fn = fixPath(self.inDir,self.setName+f+'.DDF')
            DDF = ddfClass(self,fn)
            ok,msg = DDF.getSelf()
            if not ok and fn.find('IDEN.DDF') > -1:     #shouldn't happen
                return 0,msg
            else:
                self.ddf.append((f,DDF))        #append even not-found DDFs
                self.ddfDict[f] = len(self.ddf) - 1     #index this DDF
        return 1,''
    def getSpecial(self,f,rept=None):           #getSelf for special DDFs
        fn = fixPath(self.inDir,self.setName+f+'.DDF')
        DDF = ddfClass(self,fn)
        if f == 'CEL0':
            DDF.data = []                       #re-init for safety
            retval = demSpeedReader(fn,self.keyInfo,DDF.data,rept)  #fast kludge
            if retval:
                DDF.dataType = retval
            else:
                return
        self.ddf.append((f,DDF))
        self.ddfDict[f] = len(self.ddf) - 1     #index this DDF
    def initKeyInfo(self):
        if self.type:
            if self.type[0:3] == 'DEM':
                self.keyInfo = demClass(self)
            elif self.type[0:3] == 'DLG':
                self.keyInfo = dlgClass(self)
            else:
                print 'DEBUG unknown sdts type:',self.type
                return 0
            return 1
        else:
            return 0
    #end class sdtsClass

#--- testing ---

def test():
    #sdts = sdtsClass(None,'C:/Python/DemTest/tmp/1393iden.ddf')
    sdts = sdtsClass(None,'C:/Python/DemTest/tmp/1168iden.ddf')
    #sdts = sdtsClass(None,'C:/Python/DemTest/tmp/TR01iden.ddf')
    ok,msg = sdts.getSelf(['IDEN'])
    if ok:
        sdts.type = sdtsQuery(sdts,'DAST','IDEN')
        sdts.initKeyInfo()
        if sdts.type == 'DEM':
            r = sdtsDEMreport(sdts)
        else:
            r = sdtsDLGreport(sdts)
        print '\tSDTS',sdts.type,'loaded OK\n'
        for i in range(len(r)):
            print r[i]
        if sdts.type == 'DEM':
            pass
            """
            raw = open('c:\\python\\demtest\\raw.raw','wb')
            for row in range(len(L)):
                for col in range(len(L[row])):
                    raw.write(struct.pack('>h',L[row][col]))
            raw.flush()
            raw.close()
            """
        print '\tDone'
    else:
        print '\tSDTS error:',msg
    #end def test

if __name__ == '__main__':
    print '\nThis module (sdts.py) is NOT a standalone program. It contains',  \
          '\nfunctions and classes used by both DEMpy and PullSDTS.', \
          '\n\tMore info at http://www.3dartist.com/WP/pullsdts/',      \
          '\nTesting now follows...'
    test()

### end module ###
