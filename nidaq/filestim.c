#include "NIDAQmxBase.h"
#include <stdio.h>
#include <math.h>
#include <time.h>
#include <unistd.h>
#include <stdlib.h>


#define DAQmxErrChk(functionCall) { if( DAQmxFailed(error=(functionCall)) ) { goto Error; } }

static int gRunning=0;

int main(int argc, char *argv[])
{
    // Task parameters
	FILE		*stimfile;
	int32       error = 0;
    TaskHandle  taskHandle = 0;
    int32       i = 0;
    char        errBuff[2048]={'\0'};
    time_t      startTime;
    bool32      done=0;

    // Channel parameters
    char        chan[10] = "Dev1/ao0";
    float64     min = -10.0;
    float64     max = 10.0;

    // Data write parameters
    int32       pointsWritten;
    float64     timeout = 10.0;
	
	float32		header[2];
	float32		datval;
	float64		*data;
	int			off=0;
	long		fsize;
	long		sampPerChan;

	stimfile=fopen(argv[1],"r");
	if (stimfile==NULL) {
		printf("Unable to open file %s \n", argv[1]);
		exit (8);
	}

	fread( (char *)header, 4, 2, stimfile);

	fseek(stimfile, 0, SEEK_END);
	fsize=ftell(stimfile)-8;
	fsize=fsize/4;
	fseek(stimfile, 8, SEEK_SET);
	
	sampPerChan=fsize/header[0];
	printf("Playing file %s: %i channels with %i samples at %.2f Hz ...\n", argv[1], (int)header[0], sampPerChan, header[1]);

	data=(float64 *) calloc(fsize, 8);
	for (i=0;i<fsize;i++) {
		fread( (char *)&datval, 4, 1, stimfile);
		data[i] = (float64)datval;
	}

	if ((int)header[0] > 1) {
		sprintf(chan, "Dev1/ao0:%i", (int) header[0]-1);
	}
	printf("Using device %s \n", chan);


    DAQmxErrChk (DAQmxBaseCreateTask("",&taskHandle));	
    DAQmxErrChk (DAQmxBaseCreateAOVoltageChan(taskHandle,chan,"",min,max,DAQmx_Val_Volts,NULL));
    DAQmxErrChk (DAQmxBaseCfgSampClkTiming(taskHandle,"",(float64) header[1], DAQmx_Val_Rising, DAQmx_Val_FiniteSamps, sampPerChan));
    DAQmxErrChk (DAQmxBaseWriteAnalogF64(taskHandle,512, FALSE,timeout,DAQmx_Val_GroupByScanNumber, data ,&pointsWritten,NULL));
	off+=1024;

    DAQmxErrChk (DAQmxBaseStartTask(taskHandle));
    gRunning = 1;
    // The loop will quit after 10 seconds
    startTime = time(NULL);
    while( gRunning && !done && time(NULL)<startTime+10 ) {
    	DAQmxErrChk (DAQmxBaseWriteAnalogF64(taskHandle,512, FALSE,timeout,DAQmx_Val_GroupByScanNumber, data+off ,&pointsWritten,NULL));
		if (off>= fsize - 1024) {
			done=1;
		} else {
			off+=1024;
			
        DAQmxErrChk (DAQmxBaseIsTaskDone(taskHandle,&done));
		}	

    }
	
	printf("Done. Sent %i samples in %.2f seconds \n", pointsWritten, (float) time(NULL)-startTime);

	if (!done) {
        DAQmxBaseStopTask(taskHandle);
        DAQmxBaseClearTask(taskHandle);
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


