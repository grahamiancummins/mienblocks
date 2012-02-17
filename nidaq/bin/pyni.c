/*
Copyright (C) 2005-2006 Graham I Cummins
This program is free software; you can redistribute it and/or modify it under 
the terms of the GNU General Public License as published by the Free Software 
Foundation; either version 2 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY 
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with 
this program; if not, write to the Free Software Foundation, Inc., 59 Temple 
Place, Suite 330, Boston, MA 02111-1307 USA
*/

#include <Python.h>
#include <numpy/arrayobject.h>
#include <math.h>
#include "NIDAQmxBase.h"
#include <stdio.h>
#include <time.h>

#define DAQmxErrChk(functionCall) { if( DAQmxFailed(error=(functionCall)) ) { goto _fail; } }
#define C_ARRAY NPY_ALIGNED | NPY_CONTIGUOUS | NPY_FORCECAST

#define PI	3.1415926535

static PyObject *
pyni_reset(PyObject *self, PyObject *args)
{
	char *dev;
    int32       error = 0;
    char        errBuff[2048]={'\0'};

	if (!PyArg_ParseTuple(args, "s", &dev))
		return NULL;
	DAQmxErrChk (DAQmxBaseResetDevice(dev));
	Py_RETURN_NONE;
	
	_fail:
		DAQmxBaseGetExtendedErrorInfo(errBuff,2048);
	   	printf("DAQmxBase Error: %s\n",errBuff);	
		return PyErr_Format(PyExc_StandardError,
				errBuff);			
}
/*
 *

static int gRunning=0;

int main(int argc, char *argv[])
{
    // Task parameters
    int32       error = 0;
    TaskHandle  taskHandle = 0;
    int32       i = 0;
    char        errBuff[2048]={'\0'};
    time_t      startTime;
    bool32      done=0;

    // Channel parameters
    char        chan[] = "Dev2/ao0";
    float64     min = -10.0;
    float64     max = 10.0;

    // Timing parameters
    #define     bufferSize 512
    uInt64      samplesPerChan = bufferSize;
    float64     sampleRate = 20000.0;

    // Data write parameters
    float64     data[bufferSize];
    int32       pointsWritten;
    float64     timeout = 10.0;


    for(;i<bufferSize;i++)
        data[i] = 9.95*sin((double)i*20.0*PI/(double)bufferSize);

    DAQmxErrChk (DAQmxBaseCreateTask("",&taskHandle));
    DAQmxErrChk (DAQmxBaseCreateAOVoltageChan(taskHandle,chan,"",min,max,DAQmx_Val_Volts,NULL));
    DAQmxErrChk (DAQmxBaseCfgSampClkTiming(taskHandle,"",sampleRate,DAQmx_Val_Rising,DAQmx_Val_ContSamps,samplesPerChan));

    DAQmxErrChk (DAQmxBaseWriteAnalogF64(taskHandle,samplesPerChan,0,timeout,DAQmx_Val_GroupByChannel,data,&pointsWritten,NULL));

    DAQmxErrChk (DAQmxBaseStartTask(taskHandle));
    gRunning = 1;
    // The loop will quit after 10 seconds
    startTime = time(NULL);
    while( gRunning && !done && time(NULL)<startTime+10 ) {
        DAQmxErrChk (DAQmxBaseIsTaskDone(taskHandle,&done));
        if( !done )
            usleep(100000);
    }

Error:
    if( DAQmxFailed(error) )
        DAQmxBaseGetExtendedErrorInfo(errBuff,2048);
    if( taskHandle!=0 ) {
        DAQmxBaseStopTask(taskHandle);
        DAQmxBaseClearTask(taskHandle);
    }
    if( DAQmxFailed(error) )
        printf("DAQmxBase Error: %s\n",errBuff);
    return 0;
}
 *
 */
static PyObject *
pyni_ao(PyObject *self, PyObject *args)
{
    float sampr;
    int32       error = 0;
    TaskHandle  taskHandle = 0;
    int32       i = 0;
    int32       pointsWritten;
    char        errBuff[2048]={'\0'};
    time_t      startTime;
    bool32      done=0;
    PyObject *monitor;
    PyArrayObject *data;
    Py_ssize_t	l;
    int64	bs=20000;
    int gRunning = 1;
    double	data2[20000];
    char *name, *chanids;
    
    if (!PyArg_ParseTuple(args, "OfsO", &monitor, &sampr, &chanids, &data))
		    return NULL;
		    
    data=PyArray_FROM_OTF(data,  NPY_FLOAT64 , C_ARRAY);
    DAQmxErrChk (DAQmxBaseCreateTask("",&taskHandle));
    // for (i=0;i<PyList_Size(chanids);i++)
    // {
    // 	name=PyString_AsString(PyList_GetItem(chanids, i));
    // 	printf("%s\n", name);
    // }
    
    for(;i<bs;i++)
        data2[i] = 9.95*sin((double)i*20.0*PI/(double)bs);

    DAQmxErrChk (DAQmxBaseCreateTask("",&taskHandle));
    DAQmxErrChk (DAQmxBaseCreateAOVoltageChan(taskHandle,"Dev2/ao0","",-10,10,DAQmx_Val_Volts,NULL));
    DAQmxErrChk (DAQmxBaseCfgSampClkTiming(taskHandle,"", 10000,DAQmx_Val_Rising,DAQmx_Val_ContSamps,bs));

    DAQmxErrChk (DAQmxBaseWriteAnalogF64(taskHandle,bs,0,10.0,DAQmx_Val_GroupByChannel,data2,&pointsWritten,NULL));

    DAQmxErrChk (DAQmxBaseStartTask(taskHandle));
    // The loop will quit after 10 seconds
    startTime = time(NULL);
    while( gRunning && !done && time(NULL)<startTime+10 ) {
        DAQmxErrChk (DAQmxBaseIsTaskDone(taskHandle,&done));
        //if( !done )
        //    usleep(100000000);
    }


    //DAQmxErrChk (DAQmxBaseCreateAOVoltageChan(taskHandle, chanids ,"", 0.0, 5.0, DAQmx_Val_Volts,NULL));

    //DAQmxErrChk (DAQmxBaseCfgSampClkTiming(taskHandle,"",sampr,DAQmx_Val_Rising,DAQmx_Val_FiniteSamps,data->dimensions[0]));
   // DAQmxErrChk (DAQmxBaseWriteAnalogF64(taskHandle, data->dimensions[0] ,FALSE, 10 ,DAQmx_Val_GroupByScanNumber ,PyArray_DATA(data),&pointsWritten,NULL));
   // DAQmxErrChk (DAQmxBaseStartTask(taskHandle));
   // startTime = time(NULL);
   // while( !done && time(NULL)<startTime+10 ) {
   //         DAQmxErrChk (DAQmxBaseIsTaskDone(taskHandle,&done));
   //         if( !done )
   //     	    usleep(1000);
   //         }
   // startTime=time(NULL)-startTime;
   // DAQmxBaseStopTask(taskHandle);
   // DAQmxBaseClearTask(taskHandle);
    
    i=PyList_SetItem(monitor, 1, Py_BuildValue("i", pointsWritten) );
    i=PyList_SetItem(monitor, 0, Py_BuildValue("i", 1) );
    
    printf("wrote %i samples in %.2f sec\n", pointsWritten, (double)startTime);
    
    Py_XDECREF(data);	
    //Py_XDECREF(monitor);
    //Py_XDECREF(chanids);
    return monitor;
    
    _fail:
	if( taskHandle!=0 ) 
		    {
	    DAQmxBaseStopTask(taskHandle);
		    DAQmxBaseClearTask(taskHandle);
	    }
	if( DAQmxFailed(error) ) {
	    DAQmxBaseGetExtendedErrorInfo(errBuff,2048);
	    printf("DAQmxBase Error: %s\n",errBuff);
	    }
    
			    
	    Py_XDECREF(data);	
	    //Py_XDECREF(monitor);
	    //Py_XDECREF(chanids);	
		
	    return PyErr_Format(PyExc_StandardError,
				errBuff);	
								
}

/* module initialization */

static PyMethodDef PyNiMethods[] = {
    {"aoutput",  pyni_ao, METH_VARARGS,
     	"Send analog output. aoutput(monitor (list), samr (float), chanids (str), data (ndarray)). Monitor is a list [abort (int), written (int)]. The function will update written as it sends samples. If another thread sets abort to 1, the function will abort.  Sampr is a float specifying the sample rate of the data in Hz. chanids is a DAQmx Base channel name string (eg. Dev1/ao0,Dev1/ao1). Data is a 2D numpy array with one column for every channel specified in chanids and one row per output sample."},
    {"reset",  pyni_reset, METH_VARARGS,
     	"reset(dev (str)) resets the device identified by the string dev"},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};
		

PyMODINIT_FUNC
initpyni(void)
{
    import_array();
    (void) Py_InitModule("pyni", PyNiMethods);
}

		
