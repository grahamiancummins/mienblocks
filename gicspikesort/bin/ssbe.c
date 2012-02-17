#include <Python.h>
#include <numpy/arrayobject.h>
#include <math.h>

#define C_ARRAY NPY_ALIGNED | NPY_CONTIGUOUS | NPY_FORCECAST
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


static void
conv_match(long dlen, npy_float *data, long tlen, npy_float *template, npy_float *match)
{
  long i, j;
  float accum, temp;
  for (i=0;i<tlen;i++) {
	accum=0.0;
	for (j=0;j<tlen;j++) {
		if(i-tlen+j<0) {
			temp=data[0]-template[j];
			}
		else {
			temp=data[i-tlen+j]-template[j];
			}	
		accum+=temp*temp;
		}
	match[i]=accum;	
	}
  for(i=tlen; i<dlen; i++) {
  		accum=0.0;
     	for (j=0;j<tlen;j++) {
			temp=data[i-tlen+j]-template[j];
			accum+=temp*temp;
			}
		match[i]=accum;	
  }
}

static void
conv_mhnd(long dlen, npy_float *data, long tlen, npy_float *template, 
	npy_float *var,npy_float *match)
{	
  long i, j;
  float accum, temp;
  for (i=0;i<tlen;i++) {
	accum=0.0;
	for (j=0;j<tlen;j++) {
		if(i-tlen+j<0) {
			temp=data[0]-template[j];
			}
		else {
			temp=data[i-tlen+j]-template[j];
			}	
		accum+=temp*temp/var[j];
		}
	match[i]=accum;	
	}
  for(i=tlen; i<dlen; i++) {
  		accum=0.0;
     	for (j=0;j<tlen;j++) {
			temp=data[i-tlen+j]-template[j];
			accum+=temp*temp/var[j];
			}
		match[i]=accum;	
  }
}


static PyObject *
gicc_match(PyObject *self, PyObject *args)
{
	PyObject *idata, *itemplate, *omatch;
	PyArrayObject *data, *template, *match;
	if (!PyArg_ParseTuple(args, "OOO", &idata, &itemplate, &omatch))
			return NULL;
	data=PyArray_FROM_OTF(idata,  NPY_FLOAT32 , C_ARRAY);
	template=PyArray_FROM_OTF(itemplate,  NPY_FLOAT32, C_ARRAY);
	match=PyArray_FROM_OTF(omatch,  NPY_FLOAT32,  C_ARRAY | NPY_UPDATEIFCOPY);
	if (data == NULL || match== NULL || template== NULL) return NULL;
	if (data->dimensions[0]!=match->dimensions[0])
		{
		return PyErr_Format(PyExc_StandardError,
        					"Conv match: data and output arrays need identitcal lengths.");
		goto _fail;					
		}					
	if ((template->nd != 1) || (data->nd != 1))
		{
		return PyErr_Format(PyExc_StandardError,
				"Conv match: arrays must have 1 dimension.");
		goto _fail;	
		}

	conv_match(data->dimensions[0], PyArray_DATA(data),
			template->dimensions[0], PyArray_DATA(template), PyArray_DATA(match));
	Py_XDECREF(data);
	Py_XDECREF(template);
	Py_XDECREF(match);		
	Py_INCREF(omatch);
	return omatch;
	
	_fail:
		Py_XDECREF(data);
		Py_XDECREF(template);			
		Py_XDECREF(match);			
		return NULL;
								
}

static PyObject *
gicc_mhnd(PyObject *self, PyObject *args)
{
	PyObject *idata, *itemplate, *ivar, *omatch;
	PyArrayObject *data, *template, *var, *match;
	if (!PyArg_ParseTuple(args, "OOOO", &idata, &itemplate, &ivar, &omatch))
			return NULL;
	data=PyArray_FROM_OTF(idata,  NPY_FLOAT32, C_ARRAY);
	template=PyArray_FROM_OTF(itemplate,  NPY_FLOAT32, C_ARRAY);
	var=PyArray_FROM_OTF(itemplate,  NPY_FLOAT32, C_ARRAY);
	match=PyArray_FROM_OTF(omatch,  NPY_FLOAT32,  C_ARRAY | NPY_UPDATEIFCOPY);
	if (data == NULL || var== NULL || template== NULL || match== NULL) return NULL;
	conv_mhnd(data->dimensions[0], PyArray_DATA(data),
			template->dimensions[0], PyArray_DATA(template), 
			PyArray_DATA(var), PyArray_DATA(match));
	Py_XDECREF(data);
	Py_XDECREF(template);
	Py_XDECREF(var);
	Py_XDECREF(match);		
	Py_INCREF(omatch);
	return omatch;
}



static PyObject *
ssbe_optmin(PyObject *self, PyObject *args)
{
	PyArrayObject *dat, *out;
	long length, lead;
	int dims[1];
	int i, j, ii;
	float min, sum, v;
	if (!PyArg_ParseTuple(args, "Oll", &dat, &lead, &length))
			return NULL;
	//this is required to avoid a segv on x86_32 linux
	dat=PyArray_FROM_OTF(dat, NPY_FLOAT, C_ARRAY);
	dims[0]=dat->dimensions[0];
	out=PyArray_SimpleNew(1, dims, PyArray_FLOAT);
	for (i=0;i<lead;i++) {
		*((float *) PyArray_GETPTR1(out,i))=0.0;
	}
	for (i=dat->dimensions[0]-length+lead;i<dat->dimensions[0];i++) {
		*((float *) PyArray_GETPTR1(out,i))=0.0;		
	}
	for (i=0;i<dat->dimensions[0]-length;i++) {
		sum=0.0;
		for (j=0;j<dat->dimensions[1];j++){
			min=0.0;
			for (ii=0;ii<length;ii++) {
				v= *((float *) PyArray_GETPTR2(dat,i+ii,j));
				if (v<min) {
					min=v;
				}				
			}
			sum+=min;		
		}
		*((float *) PyArray_GETPTR1(out,i+lead))=sum;
	}	
 	Py_XDECREF(dat);
	Py_INCREF(out);
	return out;
}

static PyObject *
ssbe_optmp(PyObject *self, PyObject *args)
{
	PyArrayObject *dat, *out;
	long length, lead;
	int dims[1];
	int i, j, ii;
	float min, sum, v;
	if (!PyArg_ParseTuple(args, "Oll", &dat, &lead, &length))
			return NULL;
	//this is required to avoid a segv on x86_32 linux
	dat=PyArray_FROM_OTF(dat, NPY_FLOAT, C_ARRAY);
	dims[0]=dat->dimensions[0];
	out=PyArray_SimpleNew(1, dims, PyArray_FLOAT);
	for (i=0;i<lead;i++) {
		*((float *) PyArray_GETPTR1(out,i))=0.0;
	}
	for (i=dat->dimensions[0]-length+lead;i<dat->dimensions[0];i++) {
		*((float *) PyArray_GETPTR1(out,i))=0.0;		
	}
	for (i=0;i<dat->dimensions[0]-length;i++) {
		sum=0.0;
		for (j=0;j<dat->dimensions[1];j++){
			min=0.0;
			for (ii=0;ii<length;ii++) {
				v= *((float *) PyArray_GETPTR2(dat,i+ii,j));
				if (v<min) {
					min=v;
				}				
			}
			sum+=min;		
		}
		*((float *) PyArray_GETPTR1(out,i+lead))=sum;
	}	
 	Py_XDECREF(dat);
	Py_INCREF(out);
	return out;
}


static PyMethodDef SSBEMethods[] = {
    {"match",  gicc_match, METH_VARARGS,
     "match a template"},
    {"optmin",  ssbe_optmin, METH_VARARGS,
     "Input is dat (2D float array), lead (int), length (int). Return is 1D float array. Calculate the best (smallest) possible summed minimum over channels, given any alignment constrained by the parameters lead and length, These specify a sliding window of length samples, offset by lead samples from the point of calculation."},
    {"mhnd",  gicc_mhnd, METH_VARARGS,
     "Calculate mahalanobis distance"},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};
		

PyMODINIT_FUNC
initssbe(void)
{
    import_array();
    (void) Py_InitModule("ssbe", SSBEMethods);
}

		
