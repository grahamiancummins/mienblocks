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


/* helper functions */

static double 
cmp(double v1, double v2, int mode)
{
	if (v1>v2)
	{
		if (mode<0) return v2;
		else return v1;
	} else {
		if (mode<0) return v1;
		else return v2;
	}
}	
	
static PyObject *
oe_findindex(PyObject *self, PyObject *args)

{
	PyArrayObject *els, *tab, *ind;
	long i, j, jin, v1, v2;
	int dims[1];
	if (!PyArg_ParseTuple(args, "OO", &els, &tab))
			return NULL;
	//this is required to avoid a segv on x86_32 linux
	els=PyArray_FROM_OTF(els, NPY_LONG, C_ARRAY);
	tab=PyArray_FROM_OTF(tab, NPY_LONG, C_ARRAY);	
	dims[0]=els->dimensions[0];
	ind=PyArray_SimpleNew(1, dims, PyArray_LONG);
	for (i=0;i<els->dimensions[0];i++)
	{
		v1= *((long *) PyArray_GETPTR1(els,i));
		jin=-1;
		for (j=0;j<tab->dimensions[0];j++)
		{
			v2=*((long *) PyArray_GETPTR1(tab,j));
			//printf("%i %i\n", v1, v2);
			if (v1==v2)
			{
				jin=j;
				break;
			}
		}
		//printf("%i %i\n", i, v1);
		*((long *) PyArray_GETPTR1(ind,i))=jin;
	}

 	Py_XDECREF(els);
	Py_XDECREF(tab);
	Py_INCREF(ind);
	return ind;
}

static PyObject *
oe_addcompress(PyObject *self, PyObject *args)
{
	PyArrayObject *ind, *val;
	long i, iv, lasti;
	float nv, cv;
	PyListObject *all;
	if (!PyArg_ParseTuple(args, "OO", &ind, &val))
			return NULL;
	//this is required to avoid a segv on x86_32 linux
	ind=PyArray_FROM_OTF(ind, NPY_LONG, C_ARRAY);
	val=PyArray_FROM_OTF(val, NPY_DOUBLE, C_ARRAY);
	lasti=*((long *) PyArray_GETPTR1(ind,0));
	cv=*((double *) PyArray_GETPTR1(val,0));
	all=PyList_New(0);
	for (i=1;i<ind->dimensions[0];i++)
	{
		iv= *((long *) PyArray_GETPTR1(ind,i));
		nv= *((double *) PyArray_GETPTR1(val,i));
		if (iv==lasti)
		{
			cv+=nv;
		} else {
			PyList_Append(all,Py_BuildValue("id", lasti, cv));
			cv=nv;
			lasti=iv;
		}
	}
	PyList_Append(all,Py_BuildValue("id", lasti, cv));
 	Py_XDECREF(ind);
	Py_XDECREF(val);
	Py_INCREF(all);
	return all;
}

static PyObject *
oe_pcompress(PyObject *self, PyObject *args)
{
	double*nv;
	double * cv;
	PyArrayObject *ind, *val, *rul;
	long i, iv, lasti, j, nj;
	PyListObject *all, *onev;
	if (!PyArg_ParseTuple(args, "OOO", &ind, &val, &rul))
			return NULL;
	//this is required to avoid a segv on x86_32 linux
	ind=PyArray_FROM_OTF(ind, NPY_LONG, C_ARRAY);
	val=PyArray_FROM_OTF(val, NPY_DOUBLE, C_ARRAY);
	rul=PyArray_FROM_OTF(rul, NPY_LONG, C_ARRAY);
	nj=rul->dimensions[0];
	nv=(double *)malloc((nj)*sizeof(double));
	cv=(double *)malloc((nj)*sizeof(double));
	lasti=*((long *) PyArray_GETPTR1(ind,0));
	for (j=0;j<nj;j++)
	{
		cv[j]=*((double *) PyArray_GETPTR2(val,0, j));
	}
	all=PyList_New(0);
	for (i=1;i<ind->dimensions[0];i++)
	{
		iv= *((long *) PyArray_GETPTR1(ind,i));
		for (j=0;j<nj;j++)
		{
			nv[j]=*((double *) PyArray_GETPTR2(val,i, j));
		}
		if (iv==lasti)
		{
			for (j=0;j<nj;j++)
			{
				switch (*((long *) PyArray_GETPTR1(rul,j))) 
				//Allowed rules are 0=add, 1=max, 2=min, 3=av
				{
				case 0:
					cv[j]=nv[j]+cv[j];
					break;
				case 1:
					cv[j]=cmp(cv[j], nv[j], 1.0);
					break;
				case 2:
					cv[j]=cmp(cv[j], nv[j], -1.0);
					break;
				case 3:
					cv[j]= (cv[j]*(cv[j-1]-nv[j-1])+nv[j]*nv[j-1])/cv[j-1];
					break;			
				}		
			}			
		} else {
			onev=PyList_New(0);
			PyList_Append(onev,Py_BuildValue("i", lasti));
			for (j=0;j<nj;j++)
			{
				PyList_Append(onev,Py_BuildValue("d", cv[j]));
				cv[j]=nv[j];
			}
			PyList_Append(all,onev);
			lasti=iv;
		}
	}
	onev=PyList_New(0);
	PyList_Append(onev,Py_BuildValue("i", lasti));
	for (j=0;j<nj;j++)
	{
		PyList_Append(onev,Py_BuildValue("d", cv[j]));
		cv[j]=nv[j];
	}
	PyList_Append(all,onev);
 	Py_XDECREF(ind);
	Py_XDECREF(val);
	Py_INCREF(all);
	return all;
}



/* module initialization */

static PyMethodDef OptExtMethods[] = {
    {"findindex",  oe_findindex, METH_VARARGS,
     "Take two 1D arrays of ints and return an array of ints with the same length as the first array, containing the indexes in the second array where elements of the first array are found. If there is more than one match, the first matching index is used. If there is no match for an element, a -1 is inserted in the return array."},
    {"addcompress",  oe_addcompress, METH_VARARGS,
     "Take two 1D arrays, int, float, and return a list of tuples (int, float) such that the ints in the first position are unique, and the floats in the second are the sum off all elements in the inputs that had the same index. The index array must be sorted."},
    {"pcompress",  oe_pcompress, METH_VARARGS,
     "Take a 1D array, a 2D array, and a 1D array , and return a list of tuples (int, float, float ...) such that the ints in the first position are unique, and the floats in the second and sebsequent are the values in the 2D input array combined according to rules specified by the final array. Allowed rules are 0=add, 1=max, 2=min, 3=av. The index array must be sorted."},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};
		

PyMODINIT_FUNC
initoptext(void)
{
    import_array();
    (void) Py_InitModule("optext", OptExtMethods);
}

		
