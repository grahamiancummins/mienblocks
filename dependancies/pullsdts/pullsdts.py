#!/usr/bin/python2

#pullsdts.pyw - PullSDTS 2.0 beta 2c4 - 5 January 2002
#Update at http://www.3dartist.com/WP/pullsdts/
#Created by Bill Allen <dempy@3dartist.com>
#This is free, non-copyrighted, unguaranteed software, unwarranted for any
#task or purpose. Use it at your own risk.
"""
This is a cross-platform script to examine TAR, tarball, and TIFF files, and
to extract TAR and tarball contents, primarily aimed at working with USGS 
SDTS transfers and GeoTIFFs, and specifically designed to view, convert, and
optimize SDTS DEMs in ways suited to the author's own landscape projects.
Export is, or will be, to heightfield grayscale, and to triangles/mesh:
  2D: 8-bit GIF, 16-bit RAW
  3D: OBJ mesh, RAW triangles, RIB entity as PointsPolygons
------
Index, custom modules needed for, or related to, this program
  __init__ - allows these modules to be properly recognized
  dempy - probably not present, a future main application script
  geotiff - functions & classes to handle TIFFs & USGS GeoTIFFs
  guinter - GUI (Tkinter) functions & classes common to PullSDTS & DEMpy
  gztar - functions & classes for working with gzip & TAR files
  pulldem - other functions & classes common to PullSDTS & DEMpy
  pullsdts - the utility's main script (what you are reading now)
  sdts - functions & classes needed to deal with USGS SDTS transfers
Index, classes
  mainWindowClass - the big enchilada, sets up main interface
  initsLocalClass - derived from guinter.initsClass
"""

#--- user-chosen preferences ---

copyadd = 0     #use =1 to append file reports to the clipboard, =0 clear+copy
copyauto = 0    #set to =1 to copy file reports directly to the clipboard

#--- user-defined initialization constants ---

usingIDLE = 0   #normally =0, =1 to run from IDLE or other Tkinter-based editor 
usingINI = 1    #change to =0 to disable using an .ini file, otherwise =1

#--- author's constants ---

__version__ = '2.0 beta 2c4'
versionDate = '5 Jan. 2002'

#--- other constants + various module imports ---

import os, string, sys, tkMessageBox
import Tkinter as tk
from tkFileDialog import askopenfilename as tkFileGet

#--- custom module imports ---

thisDir = os.path.split(sys.argv[0])[0]
if not thisDir in sys.path:
    sys.path.append(thisDir)
import geotiff, guinter, gztar, pulldem, sdts
from pulldem import fixPath

#--- classes ---

class initsLocalClass(guinter.initsClass):
    def __init__(self):
        guinter.initsClass.__init__(self)
        self.iniFile = fixPath(self.startup,'pullsdts.ini')
        self.width = '400'          #top frame width -- DOESN'T CHANGE
        self.height = '520'         #top frame height -- DOESN'T CHANGE
        self.setDefault()           #set defaults first
        if usingINI:
            self.reload()           #try to overwrite from .ini file
        """
        Find or make a folder for temporary files. First look for a \tmp or
        \temp folder in the startup folder. If not found, then check to see
        if the startup is named \pullsdts or \dempy (case not critical),
        and, if so, create a new \tmp folder. Otherwise, create a new folder
        named \pull_tmp.
        """
        if not self.outDir:
            self.outDir = self.startup  #keep OS from defaulting to \tmp
        if not self.tmpDir or not os.path.exists(self.tmpDir):
            pn1 = fixPath(self.startup,'tmp')
            pn2 = fixPath(self.startup,'temp')
            if os.path.isdir(pn1):
                self.tmpDir = pn1
            elif os.path.isdir(pn2):
                self.tmpDir = pn2
            else:
                if os.path.split(self.startup)[1].lower()   \
                   in ['dempy','pullsdts']:
                    os.mkdir(pn1)
                    self.tmpDir = pn1
                else:
                    pn1 = fixPath(self.startup,'pull_tmp')
                    if not os.path.isdir(pn1):
                        os.mkdir(pn1)
                    self.tmpDir = pn1
    #end initsLocalClass

class mainWindowClass:
    def __init__(self,master):
        color = guinter.colorClass()
        self.frame = tk.Toplevel(master,relief='flat',bd=2)
        self.fname = ''                 #currently selected file name
        self.file = None                #currently selected file object
        self.fileHold = None            #the alternate working file
        self.holdList = []              #previous report, held as a list
        self.saveList = []              #current report, held as a list
        self.killList = []              #list of files to delete upon Quit
        self.aButt = []                 #list of action buttons
        self.aButtMax = 2               #max number of action buttons
        self.title = 'PullSDTS'
        self.frame.title(self.title)
        self.logoIcon = tk.PhotoImage(format='gif',
          data='R0lGODlhKwAQAJEAACWgA/3bYYNOGgAAACwAAAAAKwAQAAACfIyPqcsrD2M0'
            +'oAJqa8h29yAkITiG3HWmKWiUrdtpseZdtcfmJSyjvf2Z5Q671u0wA9I+RtLj'
            +'ZcwgfxglTTchjqS34JUrCUMQySOzih07Tb62eeneqSfU8vsmf65xZa8S/zI3'
            +'dlLD5deRl1dlxdT4MYIA2TBJuSZ2iZkZVgAAOw==')  #made by img2pytk.py
        #--- process inits including tkVariables
        self.ini = initsLocalClass()
        self.showTips = tk.IntVar()
        self.showTips.set(self.ini.tips)
        self.dock = tk.IntVar()
        self.dock.set(self.ini.dock)
        self.gamma = self.ini.gamma
        self.frame.geometry(self.ini.topGeo(self))
        self.frame.resizable(0,0)
        self.frame.protocol('WM_DELETE_WINDOW',self.quit)   #Close button 
        """
        Without setting the above protocol, the Mac window close button won't
        work. On Win/Linux, it is needed to invoke the correct close-down.
        """
        #--- top tray with logo & tips check box
        grp = self.topGrp = tk.Frame(self.frame)
        grp.pack(anchor='n',side='top',fill='x')
        idLogo = tk.Label(grp,image=self.logoIcon,bg=color.tan)   #logo
        idLogo.pack(side='left',padx=7,pady=4)
        idLabel = tk.Label(grp,text=self.title+' '+__version__,
                           font=self.ini.fontBold)
        idLabel.pack(anchor='w',side='left',pady=3)
        #--- dock check box
        b = self.dockCheck = guinter.buttClass(grp,self,'check','Dock','normal')
        b.butt.config(var=self.dock)
        b.cfg(tip='Turn window docking on/off',uline=3,altkey='k')
        b.butt.pack(anchor='ne',side='right',padx=0,pady=3)
        #--- tips check box
        b = self.tipCheck = guinter.buttClass(grp,self,'check','Tips','normal')
        b.butt.config(var=self.showTips)
        b.cfg(tip='Turn tips on/off',uline=0,altkey='t')
        b.butt.pack(anchor='ne',side='right',padx=0,pady=3)
        #--create start group with Open/Help/About/Quit buttons
        grp = self.startGrp = tk.Frame(self.frame,relief='solid',
                                       height=28,bd=1)
        grp.pack_propagate(0)
        grp.pack(anchor='n',side='top',fill='x')
        #--- select button
        b = self.bOpen = guinter.buttClass(grp,self,'text','Select File',
                                           'normal')
        b.butt.config(command=self.select)
        b.cfg(tip='Choose a file to inspect',uline=0,altkey='s')
        b.butt.pack(side='left',padx=1,pady=1,fill='y')
        #--- quit button
        b = self.bQuit = guinter.buttClass(grp,self,'text','Exit','normal')
        b.butt.config(command=self.quit)
        b.cfg(tip='Exit this program',uline=1,altkey='x')
        b.butt.pack(side='right',padx=1,pady=1,fill='y')
        #--- sort bar
        self.sort = guinter.sortBarClass(self.frame,self,378,17,
                                         self.ini.fontSmall,1)
        #--- report area
        self.list = tk.Listbox(self.frame,font=self.ini.fontList,
                               exportselection=0,bg=color.white,
                               selectbackground=color.white,
                               selectborderwidth=0,
                               selectforeground=color.black)
        yScroll = tk.Scrollbar(self.list,command=self.list.yview)
        yScroll.pack(side='right',fill='y')
        xScroll = tk.Scrollbar(self.list,orient='horizontal',
                               command=self.list.xview)
        xScroll.pack(side='bottom',fill='x')
        self.list.pack(side='top',fill='both',expand=1)
        self.list.config(yscrollcommand=yScroll.set,
                         xscrollcommand=xScroll.set)
        #--- create working group with Copy & action buttons
        grp = self.workGrp = tk.Frame(self.frame,relief='solid',
                                       height=28,bd=1)
        grp.pack_propagate(0)
        grp.pack(anchor='n',side='top',fill='x')
        #--- copy button
        self.bCopy = guinter.buttClass(grp,self,'text','Copy','normal')
        self.bCopy.butt.config(command=self.listCopy)
        self.bCopy.cfg('Copy report text to clipboard',3,'y')
        self.bCopy.butt.pack(side='left',padx=1,pady=1)
        #--- action buttons (empty)
        for i in range(self.aButtMax):
            self.aButt.append(guinter.buttClass(grp,self,'text','','disabled'))
            self.aButt[i].butt.pack(side='left',padx=1,pady=1)
        #--- special Mac configuration (mostly frame colors)
        if os.name == 'mac':
            wg = color.winGray
            filler = tk.Label(grp,width=0,bg=wg)  #make room for window handle
            filler.pack(side='right',padx=3)
            self.frame.config(bg=wg)
            self.topGrp.config(bg=wg,highlightbackground=wg)
            idLabel.config(bg=wg)
            self.startGrp.config(bg=wg,highlightbackground=wg)
            self.workGrp.config(bg=wg,highlightbackground=wg)            
        #--- final details
        self.listSet(['  Welcome to '+self.title+' (beta)',
                      '    version '+__version__+' of '+versionDate,
                      '  a utility for GIS related files.',
                      '  For more info & latest version, visit',
                      '    www.3dartist.com/WP/pullsdts','',
                      'Use \'Pull\' to inspect SDTS transfers without',
                      'extracting files from the .tar.gz, which is',
                      'easier and more efficient. Extracted file',
                      'sets also can be inspected. Pull can extract',
                      'files (but not folders) from most .tar and',
                      '\'tarball\' .tar.gz, _tar.gz, and .tgz files.',
                      '  Inspection includes getting most info',
                      'normally needed such as quad name, location,',
                      'and extents. Any SDTS DEM can be previewed',
                      'as an overhead-view grayscale image that',
                      'can be saved as a GIF.',
                      '  GeoTIFFs also can be inspected, though not',
                      'viewed. TIFFs can be gzipped as .tif.gz,',
                      'which can cut GeoTIFF size in half, and Pull',
                      'can inspect GeoTIFFs in .tif.gz form.',
                      '','NEW as of version 2 beta 2c:',
                      '> Any SDTS DEM can be exported as an 8- or',
                      '  16-bit RAW file with exact or equalized',
                      '  (spread) values, or equalized to a common',
                      '  project-based elevation range.'])
        self.sort.hide()
        for i in range(self.aButtMax):
            self.aButt[i].status = None
            self.aButt[i].butt.pack_forget()
        if copyadd:     #if not copyadd, clipboard will be cleared each time
            self.frame.clipboard_clear()    # clear here for session only once
        self.frame.focus_set()
        #end def __init__                   # & do it after the above listSet
    #--- basic functions ---
    def cleanup(self,final=0):
        if self.file:
            try:
                self.file.close()
            except AttributeError,IOError:
                pass
            self.file = None
        if self.fileHold:
            try:
                self.file.close()
            except AttributeError,IOError:
                pass
            self.fileHold = None
        notDeleted = []
        for i in range(len(self.killList)): #delete working files (no override)
            f = self.killList[i]
            if f[-4:].lower() == '.ppm' and not final:  #preserve previews
                notDeleted.append(f)
                continue                #loop to the next one, leave for later
            if os.path.exists(f):       #need here for safety on Mac
                try:
                    os.remove(f)
                except OSError:         #file open, moved, deleted, or locked
                    notDeleted.append(f) #try again later
                    pass
        self.killList = notDeleted
    def quit(self):
        if usingINI:                    #first, save preferences, etc.
            self.ini.save(self)
        self.cleanup(1)
        if usingIDLE:
            self.frame.grab_release()   #help IDLE regain control
            self.frame.destroy()
        else:
            self.frame.quit()
            root.quit()
    #--- action button functions ---
    def actionClear(self,match=''):
        """
        If a multiple-use action-button has something assigned to its
        text attribute, then it is presumed to be visible.
        """
        flag = 0
        if match:
            if match < 0 or match > self.aButtMax-1:
                print 'DEBUG mainWindowClass actionButton out of range:',match
                return
            start = match
            stop = match + 1
        else:
            start = 0
            stop = self.aButtMax
        for i in range(start,stop):
            if self.aButt[i].status:
                flag = 1
                self.aButt[i].butt.config(text='',state='disabled',cmd=None)
                self.aButt[i].butt.pack_forget()
                self.aButt[i].cfg(tip='')
                self.aButt[i].label = ''
                self.aButt[i].status = None
                if self.aButt[i].bindings:  #clear the bindings
                    for b in self.aButt[i].bindings:                   
                        self.aButt[i].callerParent.frame.unbind(b)
                    self.aButt[i].bindings = []
                    self.aButt[i].butt.config(underline=-1)
        if flag:
            self.frame.update_idletasks()
    def actionSet(self,lab,st,cmd,t,alt):
        for i in range(self.aButtMax):
            if not self.aButt[i].status:    #empty button found
                break
        if i+1 == self.aButtMax and self.aButt[i].status:
            print 'DEBUG mainWindowClass no actionButton available'
            return None
        if alt:
            alt = alt[0].lower()        #safety
            ul = lab.lower().find(alt)  #find first occurrence in either case
            if ul == -1:                #Alt-key needs to be in label text
                ul = 0
                alt = ''
        self.aButt[i].butt.config(text=lab,state=st,command=cmd)
        self.aButt[i].cfg(tip=t,uline=ul,altkey=alt,stat=st)
        self.aButt[i].butt.pack(side='right',padx=1,pady=1)
        self.frame.update_idletasks()
        return i
    #--- list functions in name order ---
    def listAlert(self,L):              #displays info screens
        self.listClear()                #  such as process in progress
        self.list.config(fg=color.brown,selectforeground=color.brown,
                         font=self.ini.fontBold)
        self.listSet(L)
    def listClear(self):
        self.bCopy.state('disabled')
        self.saveList = []              #empty display, set type to black
        self.list.delete(0,'end')       #  turn off selection appearance
        self.list.config(font=self.ini.fontList,bg=color.white,fg=color.black,
                         selectforeground=color.black,
                         selectbackground=color.white,selectborderwidth=0)
    def listCopy(self):
        if copyadd:
            self.frame.clipboard_append('\n')
        else:
            self.frame.clipboard_clear()
        for t in self.saveList:
            self.frame.clipboard_append(t+'\n')
    def listSet(self,L):
        self.bCopy.state('normal')
        self.saveList = []
        for t in L:             #save original list
            self.saveList.append(t)
        if copyauto:
            self.listCopy()     #automatic copy to clipboard
        maxIdx = -1             #calculate horiz space to clear scrollbar
        maxLen = 0
        for i in range(len(L)):
            sz = len(L[i])
            if sz > 0:
                L[i] = ' ' + L[i]
                if sz > maxLen:
                    maxLen = sz
                    maxIdx = i
        if maxIdx > -1:
            L[maxIdx] = L[maxIdx] + '   '
        L.insert(0,'')          #extra top line
        L.append('')            #extra lower vertical space to clear scrollbar
        L.append('')
        for t in L:
            self.list.insert('end',t)
        self.frame.update_idletasks()
    #--- DEM grayscale functions ---
    def demView(self):
        if self.fileHold:
            xfer = self.fileHold
        else:
            xfer = self.file
        if xfer and xfer.type == 'DEM':
            k = xfer.keyInfo
            t = k.name + ' - '
            if k.date[-4:] < '2001':
                t = t + 'old '
            else:
                t = t + 'new '
            t = t + str(k.scaleXY) + 'm Level ' + k.level + ' DEM'
            w = guinter.demPreviewClass(self,xfer,t)
            if self.fileHold:                       #=None if not using a TAR
                self.tar2ddf(self.file,['CEL0'])    #extract DEM DDF from TAR                
            #xfer.getSelf(['CEL0'])     #standard method to load the DEM DDF
            #sdts.sdtsQuery(xfer,'ELEVATION','CEL0')  #standard data loading
            need = 1
            if xfer.ddfDict.has_key('CEL0'):        #do we have DDF & data?
                need = (xfer.ddf[xfer.ddfDict['CEL0']][1].data == None)
            if need:
                w.progressLabel('Loading DEM data % complete')
                xfer.getSpecial('CEL0',w)
            fn = ''
            sn = pulldem.getGeoTemp(xfer) + '.ppm'
            for i in range(len(self.killList)):     #do we have preview image?     
                if self.killList[i].lower().find(sn) > -1:
                    if os.path.exists(self.killList[i]): #make sure it's there
                        fn = self.killList[i]
                        break
            if not fn:
                w.progressLabel('Creating preview image % complete')
                fn = sdts.dem2ppm(xfer,w)           #change data to 8-bit file
            if fn:
                self.killList.append(fn)
                w.setImage(fn)
                w.frame.focus_set()
                w.frame.grab_set()
                w.frame.update_idletasks()
                self.frame.wait_window(w.frame)
            else:
                print 'DEBUG demView problem getting PPM file'
                w.quit()
    #--- file selection & inspection functions ---
    def doDDF(self,fn,tar=None):
        self.listAlert(['Inspecting USGS SDTS transfer...',fn])
        if tar:
            self.tar2ddf(tar,['IDEN','XREF'])   #DDFs common to DEMs & DLGs
        xfer = sdts.sdtsClass(self,fn)
        ok,msg = xfer.getSelf(['IDEN'])
        if ok:
            xfer.type = sdts.sdtsQuery(xfer,'DAST','IDEN')
            xfer.initKeyInfo()
            self.file = xfer
            if xfer.type[0:3] == 'DEM':
                if tar:                 #get DDFs needed for DEM report
                    self.tar2ddf(tar,['DDOM','DQHL','IREF','LDEF','SPDM'])
                self.listClear()
                self.listSet(sdts.sdtsDEMreport(xfer))
                i = self.actionSet('Load DEM','normal',self.demView,
                                   'Load this DEM to\nview or export','l')
                self.aButt[i].bright()
            elif xfer.type[0:3] == 'DLG':
                if tar:
                    self.tar2ddf(tar,['AHDR'])
                self.listClear()
                self.listSet(sdts.sdtsDLGreport(xfer))
            else:
                print 'DEBUG pullsdts unknown SDTS type',xfer.type
        else:
            self.listSet([msg])
        #end doDDF
    def tarExtract(self):
        if self.file.sdtsAttr:          #use iden.ddf as file save name
            pn = guinter.saveAsFile(self,'Save extracted files',
                    self.ini.outDir,self.file.sdtsAttr+'IDEN.DDF',
                    [('SDTS transfer','*IDEN.DDF'),('All Files','*.*')])
        else:                           #use first file as file save name
            pn = guinter.saveAsFile(self,'Save extracted files',
                                    self.ini.outDir,self.file.dir[0].name,
                                    [('All Files','*.*')])
        if pn[0]:
            self.file.extractAll(pn[0])
    def getSDTS(self):
        if self.file.sdtsAttr:          #safety
            self.actionClear()          #remove any action buttons
            self.sort.hide()            #remove TAR file list sort bar
            tarFile = self.file         #the TAR file is still open
            self.holdList = self.saveList
            self.actionSet('Return to TAR','normal',self.ret2tar,
                           'Return to TAR contents list','r')
            self.doDDF(fixPath(self.ini.tmpDir,self.file.sdtsAttr+'IDEN.DDF'),
                       tarFile)
            self.fileHold = self.file   #keep reference to the SDTS transfer
            self.file = tarFile         #restore the TAR as central file
    def ret2tar(self):
        """
        Presumes to be called after self.getSDTS(), where self.file has
        already been restored.
        """
        self.listClear()
        self.listSet(self.holdList)
        self.actionClear()
        self.sort.unhide()
        self.tarAction()
    def select(self):
        self.frame.title(self.title)    #clear the window bar title
        self.listClear()                #clear the list box
        self.actionClear()              #clear the action buttons
        if self.sort.visible:
            self.sort.hide()            #remove file list sorting buttons
        self.cleanup()
        ft = [('Any Pull File','*iden.ddf *.gz *.tar *.tgz *.tif'),
              ('Tarballs','*.tar.gz *_tar.gz *.tgz'),
              ('TAR','*.tar'),
              ('gzip','*.gz'),
              ('TIFF','*.tif *.tiff *.tif.gz'),
              ('SDTS transfer','*iden.ddf'),
              ('All Files','*.*')]
        if self.ini.inDir:
            fn = tkFileGet(title='Select a file',parent=self.frame,
                           filetypes=ft,initialdir=self.ini.inDir)
        else:
            fn = tkFileGet(title='Select a file',parent=self.frame,
                           filetypes=ft)
        if fn:
            fn = self.fname = fixPath(fn)
            self.ini.inDir,x = os.path.split(fn)
            self.frame.title(self.title + ': ' + x)
            if fn.find('.tif') > -1:            #also allows .tiff & .tif.gz
                self.tifAction(fn)
            elif fn[-6:].lower() == 'tar.gz'        \
               or fn[-4:].lower() in ['.tar','.tgz']:   #also allows _tar.gz
                self.listAlert(['Loading TAR contents list for...',fn])
                tar = self.file = gztar.tarClass(fn,self.ini.tmpDir)
                L = self.sort.load(tar)
                if not self.sort.visible:
                    self.sort.unhide()
                self.listClear()
                self.listSet(L)
                self.tarAction()
            elif fn[-8:].lower() == 'iden.ddf': #allows 8.3 & 9.3 file names
                self.doDDF(fn)
            else:
                self.listSet(["Nothing to report on","this file's contents."])
        #end def select
    def tar2ddf(self,tar,modules):              #get 1 or more DDFs from TAR
        for L in modules:                       # if not in tmp folder already
            fn = tar.sdtsAttr+L+'.DDF'
            if not os.path.exists(fixPath(self.ini.tmpDir,fn)):
                tar.extractName(fn,self.ini.tmpDir,1)
    def tarAction(self):
        """
        Called by either self.select() or self.ret2TAR().
        """
        self.actionSet('Extract All','normal',self.tarExtract,
                       'Extract all files from TAR','e')
        #can also have a button here for 'Extract Selected'
        #  once selection capability is implemented
        if self.file.sdtsAttr:
            s = 'SDTS Report'
            t = 'Report SDTS contents'
            x = self.file.sdtsAttr + 'CEL0'
            for e in self.file.dir:
                if e.name.find(x) == 0:
                    s = s + '/Load'
                    t = t + '& optionally\nload/export DEM'
                    break
            i = self.actionSet(s,'normal',self.getSDTS,t,'r')
            self.aButt[i].bright()      #make this button stand out
    #--- TIFF functions ---
    def tifAction(self,fn):
        tiff = self.file = geotiff.tifFileClass(self,fn)
        self.listSet(tiff.report())
        if fn[-3:].lower() == '.gz':
            self.actionSet('Extract TIFF','normal',self.tifExtract,
                           'Extract TIFF from .tif.gz file','e')
        else:
            self.actionSet('Gzip TIFF','normal',self.tifGzip,
                           'Compress TIFF into .tif.gz file','g')
        tiff.close()
    def tifExtract(self):
        fn = self.file.name[:-3]
        pn = guinter.saveAsFile(self,'Ungzip TIFF file',
                            self.ini.outDir,fn,
                            [('TIFF Files','*.tif *.tiff'),('All Files','*.*')])
        if pn[0]:                       #closes automatically after creation
            gztar.gzOpen(fixPath(self.file.path,self.file.name),pn[0])
    def tifGzip(self):
        fn = self.file.name
        if fn[-5:].lower() == '.tiff':
            fn = fn[0:len(fn)-1]
        fn = fn + '.gz'
        pn = guinter.saveAsFile(self,'Compress TIFF file',
                            self.ini.outDir,fn,
                            [('gzTIFF Files','*.tif.gz'),('All Files','*.*')])
        if pn[0]:                       #closes automatically after creation
            gztif = gztar.gzClass(fixPath(self.file.path,self.file.name),pn[0])
            self.actionClear()
            self.listAlert([fn+' successfully created in',
                            pn[0],'',
                            '   WARNING: Do NOT delete your original',
                            '           TIFF without first backing it up.','',
                            'This TIFF gzip function is beta software and',
                            'should not be trusted yet with the only copy',
                            'of a file that you value (unless perhaps the',
                            'file tests OK with another ungzip program).'])
    #end class mainWindow

#--- go to work ---

root = tk.Tk()
root.withdraw()
root.title('PullSDTS')
color = guinter.colorClass()            #get the standard colors
mainWin = mainWindowClass(root)
if not usingIDLE:
    root.mainloop()
    root.destroy()

### end script ###
