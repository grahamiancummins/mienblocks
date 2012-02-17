#! /usr/bin/env python
'''
a set of usefull tools for python and mien programming
'''
from numpy import *
import os

#Vector and Array Functions

def find_nearest(val,lst):
    '''
    finds the nearest value in a scalar to the input value and returns an index. Retruns first listed value if two equally near.
    Takes a scalar and a vector and returns an int
    '''    
    [val,lst] = check_inputs([val,lst],['scalar','vector'])
    diffs = array(lst)-val
    diffs = abs(diffs)
    minind = argmin(diffs)
    [minind] = check_inputs([minind],['int'])
    return minind

def smooth(dat,ofactor=.5):
    '''
    smoothes a vector input 'dat' using the two nearest points using a triangular filter whose shoulder values are defiend by ofactor.  Should be replaced at some point with a functional filter call. Takes a vector and a scalar and returns a vector of floats.
    '''	
    [dat,ofactor] = check_inputs([dat,ofactor],['vector','scalar'],['inputs','smooth'])
    dat = check_inputs(dat,['scalar']*len(out),[],['dat','smooth'])
    fctr=float(ofactor)
    out = copy(dat)
    for m in range(1,len(dat)-1):
        out[m]=(fctr*dat[m-1]+dat[m]+fctr*dat[m+1])/(1+2*fctr)
    out = check_inputs(out,['float']*len(out),[],['out','smooth'])
    return out

def unique_rows(ar):
    '''
    return a list of the unique rows of an array and their number of occurances.  Takes an array and retuns an array and a list of counts of each unique row in the original array
    '''
    #CHECK WITH ONLY 1 ROW, OR ONLY 1 COLUMN
    [ar] = check_inputs([ar],['ndarray'],[lambda x: len(x)==2],['ar','unique_rows'])
    rows, rowlen = ar.shape
    tocheck = range(rows)
    outs = []
    repcount = []
    while len(tocheck) > 0:
        locline = ar[tocheck[0],:]
        outs.append(locline)
	n=1
        repcount.append(n)
        while n < len(tocheck):
            if (ar[tocheck[n],:] == locline).all():
                tocheck.pop(n)
                repcount[-1]+=1
            else:
                n+=1
        tocheck.pop(0)
    outs = array(outs)
    [outs, repcount] = check_inputs([outs,repcount],['ndarray','list'],[lambda x: len(x)==2,lambda x: x==shape(outs)[0]])
    return outs, repcount

def near_unique_rows(ar,numdif=1, numchans=1):
    '''
    return a list of the rows in an array that are unique, +/- the calue 'numdif' in 'numchan' channels.
    '''
    #CHECK AS ABOVE	
    [ar, numdif, numchans] = check_inputs([ar,numdif,numchans],['ndarray','int','int'],[lambda x: len(x)==2,[],[]])
    rows, rowlen = ar.shape
    tocheck = range(rows)
    outs = []
    repcount = []
    while sum(tocheck) > 0:
        locline = ar[tocheck[0],:]
        outs.append(locline)
        repcount.append(1)
        n=1
        while n < len(tocheck):
            truthar = ar[tocheck[n],:] == locline
            difvals = abs(ar[tocheck[n],:] - locline)
            if sum(truthar) >= rowlen-numchans and max(difvals) <= numdif:
                tocheck.pop(n)
                repcount[-1]+=1
            else:
                n+=1
        tocheck.pop(0)
    outs = array(outs)
    [outs, repcount] = check_inputs([outs,repcount],['ndarray','list'],[lambda x: len(x)==2,lambda x: x==shape(outs)[0]])
    return outs, repcount

def flatten_list(lst):
    '''
    Takes a list of lists of strings and returns a single list of strings.  Seems to come up often
    '''
    [lst] = check_inputs([lst],['list'])
    outlist = []
    for weelist in lst:
        for line in weelist:
            outlist.append(line)
    return outlist



#File IO functions

def save_wo_leak(ds,name):
    '''
    Saves data in mien formats without the usual memory leaks of using the mien function directly
    '''
    [ds] = check_inputs([ds],[['Data','list','ndarray']])
    name = check_fname(name)
    from mien.parsers.fileIO import write
    from mien.parsers.nmpml import blankDocument
    doc = blankDocument()
    doc.newElement(ds)
    write(doc, name)
    ds.sever()
    doc.sever()

def NEURON_output_to_array(fname):
    fname = check_fname(fname)
    inf = open(fname, 'rb')
    l = inf.readlines()[2:]
    output = array(map(lambda x:map(float, x.split()), l))
    return output

def mienstruct_from_name(fname):
    '''
    Takes a filename assumed to be a mien readable file and retuns the associated structure in python  
    '''
    from mien.parsers.fileIO import read
    fname = check_fname(fname)
    ff = read(fname)
    ds = ff.getElements()[0]
    ds.sever()
    ff.sever()
    return ds

def miendat_from_name(fname):
    '''
    Takes a filename assumed to be a mien readable file and retuns the associated data in python  
    '''
    ds = mienstruct_from_name(fname)
    dat = ds.getData()
    ds.sever()
    dat.sever()
    return dat




#File Name Functions

def check_home_dir(strng):
    '''
    Checks an iput string includes UNIX shortcuts '~' or '.' and returns the full pathway string
    '''
    import os
    #make sure this is a string
    [strng] = check_inputs([strng], types=['str'])
    #replace UNIX-type characters
    if strng[0]=='~':
        from os.path import expanduser
        localhome = expanduser('~')
        strng = localhome + strng[1:]
    elif strng[0]==os.curdir:
        strng = os.getcwd() + strng[1:]
    return strng

def check_extension(strng):
    '''
    checks for missed extensions on files that should have one
    '''
    [strng] = check_inputs([strng], types=['str'])
    if len(os.path.splitext(strng)[1]) == 0:
        dirr, fname = os.path.split(strng)
        strout = scan_dir(fname, dirr)
        if len(strout)<1:
            strng = None
            print('this filename not found %s. -otherfuncs.check_home_dir' % strng)
        elif len(strout)>2:
            print('Choosing file %s for input file name %s,  -otherfuncs.check_home_dir' % (strout[0],strng))
        strng = strout[0]
    return strng

def check_fname(strng):
    '''
    Fixes anything with a filename type input that I've thought of.
    '''
    [strng] = check_inputs([strng], types=['str'], sizes=[lambda x: x>0])
    strng = check_home_dir(strng)
    strng = check_extension(strng)
    return strng




#Directory functions

def is_in_dir(strng, dirr=None):
    '''
    Returns true if the exact filename (input as strng) is in the current directory
    '''
    from dircache import listdir
    if dirr == None:
        from os import getcwd
        curdir = getcwd()
    else:
        curdir = check_fname(dirr)
    [strng,dirr] = check_inputs([strng, dirr],['str','str'])
    #allnames = listdir(curdir)
    #out = strng in allnames
    out = os.path.exists(dirr+strng)
    return out

def scan_dir(strng,dirct):
    '''	
    Returns a list of all matches to input 'strng', files or directories, in a given directory
    '''    
    dirct = check_home_dir(dirct)
    from dircache import listdir
    allnames = listdir(dirct)
    trus=[]
    for m in allnames:
        if m.find(strng)>=0:
            trus.append(dirct + os.sep + m)
    return trus




#Design by contract functions

def set_None(inpt):
    inpt=None
    return inpt

def nonzero(x):
    tru = sum(len(x))>0
    return tru 

def vector_size(x):
    tru = len(shape(x))<2 or (len(shape(x))<3 and 1 in shape(x))
    return tru

def true_shape(x):
    return True

def check_inputs(inpts, types=[], sizes=[], callingtag=[['UNK'],'UNK']):
    '''
    Function for specifying the types and sizes of an input for 'design-by-contract' type programming.  
    Takes a list of inputs, as well as a corresponding list of types (currently available types as in 
    funcdict) and sizes, and trys to cast each input to the required type and size.  Fails hard when 
    this is not possible.  If a variable can be any type, just leave a blank spot in the types.  To 
    allow subtyping, ie 'var' is a list of tupels, call first on 'var', then on the relevant parts of 'var'.
    Any 'None' elements in a size are read as any.  All inputs should be a list of variables, types should be
    a list of strings describing the type of each variable in inpts, sizes should be a list of lambda functions
    corresponding to each element of inpts.
    '''
    #make sure the inputs to this function are the right types with out using this function to avoid recursion
    if len(types)<1:
        while len(types)<len(inpts):
            types.append([])
    if len(sizes)<1:
        while len(sizes)<len(inpts):
            sizes.append([])
    righttypes = [type(inpts).__name__, type(types).__name__, type(sizes).__name__, type(callingtag).__name__]
    allright = 0
    for m in range(len(righttypes)):
        if righttypes[m]=='list':
            allright += 1
    if not allright==len(righttypes) or not type(callingtag[0]).__name__=='list':
        raise StandardError("Inputs to 'check_inputs' from {0} are incorrect".format(callingtag[1]))
    while len(callingtag[0])<len(inpts):
        callingtag[0].append('UNK')

    #STILL FILLING IN ALL THE TYPES
    #funcdict = {'str' : str,'list':list,'tuple':tuple,'int':int,'float':float,'dict':dict, 'ndarray':array,'NoneType':set_None,'int8':int8,'int16':int16,'int32':int32,'int64':int64,'float32':float32,'float64':float64, 'float128':float128}
    shapefunc = {'str' : len,'list':len,'tuple':len,'int':true_shape,'float':true_shape,'dict':len, 'ndarray':shape,'NoneType':true_shape, 'int8':true_shape,'int16':true_shape,'int32':true_shape,'int64':true_shape,'float32':true_shape,'float64':true_shape, 'float128':true_shape} 
    #if necessary, load the mien data types
    mientypes = ['Data'] #THIS ALL NEEDS TO BE MOVED
    if [True for n in types if n in mientypes]:
        from mien.parsers.nmpml import wrapInDocument
        funcdict['Data'] = wrapInDocument
        shapefunc['Data'] = None
        
    #ALSO ADD NEW DATA TYPES HERE, ie complex, bool, void, unsigned int, function; WOULD IT WORK TO USE THE TYPE DICTIONARY

    #define shorthand for certian 'types'
    vects = [n for n in range(len(types)) if types[n]=='vector']
    for m in range(len(vects)):
        types[vects[m]] = ['ndarray','tuple','list']
        sizes[vects[m]] = lambda x: len(shape(x))<2 or (len(shape(x))<3 and 1 in shape(x))
    scals = [n for n in range(len(types)) if types[n]=='scalar']
    for m in range(len(scals)):
        types[scals[m]] = ['float','int']
        sizes[scals[m]] = lambda x: True 
    #core of the function      
    for m in range(len(inpts)):
        if types and len(types) > m and types[m]:
            if not type(inpts[m]).__name__ in types[m]:
                print("Input {0} from function {1} is of type {2} and not of required type {3}, trying to cast. -otherfuncs.check_inputs".format(callingtag[0][m],callingtag[1],type(inpts[m]).__name__,types[m]))
                try:
                    if type(types[m]).__name__ == 'str':
                        inpts[m] = eval(types[m])(inpts[m])
                    elif type(types[m]).__name__=='list':#will try to cast arbitrarily to first valid type
                        inpts[m] = eval(types[m][0])(inpts[m])
                except:
                    raise StandardError("Input to variable {0} from function {1} could not be cast to type {2}. -otherfuncs.check_inputs".format(callingtag[0][m],callingtag[1],types[m]))
        if sizes and len(sizes)>m and sizes[m]:
            locshape = shapefunc[type(inpts[m]).__name__](inpts[m])
            if not sizes[m](locshape):
                 raise StandardError("Input to variable {0} from {1} needs meet criteria {1}. -otherfuncs.check_inputs".format(callingtag[0],callingtag[1],sizes[m]))#CAN I PRINT CRITERIA FUNCTIONS?
    return inpts

def check_namespace(varnames,fail=False):
    '''
    Searches the current namespace checking to make sure nothing is being overwritten in an attempt to avoid buggy behavior.  Will warn if fail=False, will raise an error otherwise
    '''
    varnames = check_inputs(varnames, ['str']*len(varnames))
    #Must have some way of accessing the complete namspace of the calling function, WIP
    for vn in varnames:
        if vn in namespc:
            print('Caution: variable name "%s" was used in a containing namespace.' % vn)
            if fail:
                raise NameError ('Failed hard.')





#Defining Globals

def globals_from_txt(fname, glbls):
    '''
    Still working on this
    '''
    #open file
    fname = check_home_dir(fname)
    fl = open(fname, 'r')
    #read into dictionary
    lns = fl.readlines()
    gldict = dict()
    for ln in lns:
        lockey = ln[:ln.find('=')]
        lockey = lockey.replace(' ','')
        locval = ln[ln.find('=') + 1:]
        locval = locval.replace(' ','')
        locval = locval.replace('\n','')
        if not locval.isalpha():
            locval = eval(locval)
    #set globals
    fl.close()

def change_defaults(gls,**changes):
    '''
    Send in (globals) as first argument, and list of global names with new values as **secondargument.  Get back changed global variables. WORK IN PROGRESS.
    '''
    kys=changes.key()
    for m in range(len(kys)):
        if not gls.has_key(kys[m]):
            raise NameError('global varaible "%s" not available' % kys[m])
        else:
            gls[kys[m]] = changes[kys[m]]





#Mien Helper Functions

def remove_mien_crashers(txt):
    '''
    For a still unknown reason, some text in the header of a mien file will render it unable to be opened.  This funciton replaces such off-limit characters with their capitalized description.    
    '''
    txt = txt.replace('&','AMPERSAND')
    txt = txt.replace('<','LEFT CARROT')
    txt = txt.replace('"','QUOTE')
    return txt




#English parsing
def word_entropy(wordin, keyword, type):
    ''' Take some word and some mode of determinging character by character distance and return the bit distance between 'wordin' and 'keyword' '''
    pass

def keyboard_distance(charin):
    '''WIP'''
    keyboardarray = array([])
    charin = check_inputs(charin, 'str', 1)
    pass


def new_func(name, description, inputs, inputypes, output=''):
    #automates teh set up of a new function
    tmpfile = open('/Users/jonasmulder-rosi/Desktop/tmp.txt', 'w')
    funcname = 'def ' + name + '(' 
    for m in range(len(inputs)-1):
        funcname += (inputs[m] + ', ')
    funcname += (inputs[len(inputs)-1] + '):\n')
    header = 4*' ' + "'''\n" + '    FUNCTION :' + description + '\n' + 4*' ' + 'INPUTS- ' + inputs[0] + ': ' + inputypes[0] + '\n'
    for m in range(1,len(inputs)):
        header += (9*' ' + inputs[m] + '- ' + inputypes[m] + '\n')
    header += (4*' ' + 'OUTPUTS: ' + output + '\n    ' + "'''" + '\n')
    inlist = '[' + funcname[funcname.find('(')+1:funcname.find(')')] + ']'
    typelist = "['"
    for m in range(len(inputypes)-1):
	typelist += (inputypes[m][0:inputypes[m].find(' ')] + "', '")
    itend = len(inputypes)-1
    typelist += (inputypes[itend][0:inputypes[itend].find(' ')] + "']")
    call = 4*' ' + inlist + ' = oth.check_inputs(' + inlist + ', ' + typelist +')\n'
    fulltext = funcname + header + call + '    return\n\n'
    tmpfile.close()





#Scraps

def tstfunc():
    pass
    #invars = [inpts,types,sizes]
    #for n in range(invars.count(None)):
    #    invars.remove(None)
    #intypes = tile('list',(1,len(invars)))
    #check_inputs(invars, intypes)    
