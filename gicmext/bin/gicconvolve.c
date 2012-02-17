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


static float min3(float x1, float x2, float x3)
{
    float least;
    least=x1;
    if (x2<least) least=x2;
    if (x3<least) least=x3;
    return least;
}


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



static float
conv_victorDist(long dl1, npy_float *d1, long dl2, npy_float *d2, float cost)
{
	float dist=0.0;

	float last=1.0;
	float *lasti;
	int i,j;
	lasti=(float *)malloc((dl2+1)*sizeof(float));
	for (i=0;i<dl2+1;i++) {
		lasti[i]=i;
	}
	for (i=1;i<dl1+1; i++) {
		if (i>1) lasti[dl2]=last;
		last=i;
		for (j=1;j<dl2+1;j++) {
			dist=min3(lasti[j]+1, last+1, lasti[j-1]+cost*abs(d1[i-1]-d2[j-1]));
			lasti[j-1]=last;
			last=dist;
		}
	}	
	free(lasti);
	return dist;
}

static float 
normprob(float val, float var)
{	
	float norm= (1/(var*sqrt(2*3.1415927)));
	float denom=-2*var*var;
	float prob=norm*exp(val*val/denom);
	return prob;
}

static float 
invar(float val, float mean, float var)
{
	float prob;
	float small=0.0000001;
	if (var<small) {
		var=small;
		}	
	prob=normprob(val-mean, var);
	//printf("%.3f - %.3f - %.3f -> %.3f\n", val, mean, var, prob);
	return prob; 
}

static void
conv_invar(long dlen, npy_float *data, long tlen, npy_float *template, npy_float *var, npy_float *match, int adjamp)
{
  long i=0, j=0;
  float accum=0.0, temp, tval, tvar, dmin=0.0, dmax=0.0;
  float tmin, tmax=0.0, tsize=0.0, offset=0.0, scale=0.0;
  if (adjamp==1) {
	tmin=tmax=template[0];
	dmin=dmax=data[0];
	for (i=i;i<tlen;i++) {
		if (template[i]<tmin)  
			tmin=template[i];
		else if (template[i]>tmax) 
			tmax=template[i];	
		}	
	tsize=tmax-tmin;
	}
	
  for (i=0;i<tlen;i++) {
	accum=0.0;
	for (j=0;j<tlen;j++) {
		if(i-tlen+j<-1) {
			temp=data[0];
			}
		else {
			temp=data[i-tlen+j+1];
			}
		tval=template[j];
		tvar=var[j];
		accum+=invar(temp, tval, tvar);
		}
	match[i]=accum;	
	}
  for(i=tlen; i<dlen; i++) {
	if (adjamp==1) {
		dmax=data[i-tlen+1];
		dmin=data[i-tlen+1];
		for (j=i-tlen+2;j<=i;j++) {
			if (data[j]>dmax) {
				dmax=data[j];
				}
			else if (data[j]<dmin)	{
				dmin=data[j];
				}
			}
		scale=(dmax-dmin)/tsize;
		offset=dmax-(tmax*scale);
		}
	accum=0.0;
	for (j=0;j<tlen;j++) {
		if 	(adjamp==1) {
			tval=template[j]*scale+offset;
			//tvar=var[j]*scale;
			}
		else {
			tval=template[j];
			}
		tvar=var[j];
		accum+=invar(data[i-tlen+j+1], tval, tvar);
		}
	//printf("%ld, %.3f, %.3f, %.3f,%.3f\n", i, scale, accum, dmax, dmin); 	
	match[i]=accum;	
	}
}

static void 
conv_residualvar(long dlen, npy_float *data, long tlen, long twidth, npy_float *template, npy_float *match)
{
	long i;
	long j; 
	long k; 
	long ind;
	float *resid;
	float proj=0;
	float temp=0;
	float mag=0;
	resid=(float *)malloc(tlen*sizeof(float));
	/*
	float t2[tlen][twidth];
  	for (i=0;i<tlen*twidth;i++) {
		j=i/twidth;
		k=i%twidth;
		printf("%ld, %ld, %.3f\n", j, k, template[i]);
		t2[j][k]=template[i];
		}
	*/
  for(i=0; i<dlen; i++) {
  		mag=0.0;
     	for (j=0;j<tlen;j++) {
			ind=i-tlen+j+1;
			if (ind<0) {ind=0;}
			resid[j]=data[ind]-template[j*twidth];
			//printf("%.3f, %.3f -> %.3f\n", template[j*twidth], data[i-tlen+j+1], resid[j]);
			mag+=resid[j]*resid[j];
			}
		proj=0.0;
		//printf("____%.3f\n", mag);
		for (k=1;k<twidth;k++) {
			temp=0.0;
			for (j=0;j<tlen;j++) {
				//printf("%.3f, %.3f\n", resid[j], template[j*twidth+k]);
				temp+=resid[j]*template[j*twidth+k];
				}
			//printf("%.3f\n", temp);
			proj+=temp*temp;
			}
		//printf("____%.3f\n",proj);
		match[i]=sqrt(mag-proj);
  }
	free(resid);	
}  
  

static void 
conv_projectvar(long dlen, npy_float *data, long tlen, long twidth, npy_float *template, npy_float *match)
{
	long i, j, k, ind;
	float proj=0;
	float temp=0;
	float *resid;
	resid=(float *)malloc(tlen*sizeof(float));
	
  for(i=0; i<dlen; i++) {
     	for (j=0;j<tlen;j++) {
			ind=i-tlen+j+1;
			if (ind<0) {ind=0;}
			resid[j]=data[ind]-template[j*twidth];
			}
		proj=0.0;
		for (k=1;k<twidth;k++) {
			temp=0.0;
			for (j=0;j<tlen;j++) {
				//printf("%.3f, %.3f\n", resid[j], template[j*twidth+k]);
				temp+=resid[j]*template[j*twidth+k];
				}
			//printf("%.3f\n", temp);
			proj+=temp*temp;
			}
		//printf("____%.3f\n",proj);
		match[i]=sqrt(proj);
  }
	free(resid);	
}	

static void
conv_2dkern(long dlen, npy_float *data, long tlen, npy_float *template, npy_float *match)
{
	long i, j, k, ind;
	float accum=0;
  	for(i=0; i<tlen; i++) {
		match[i]=0.0;
		}
	for(i=tlen;i<=dlen;i++) {	
		accum=0.0;
		ind=i-tlen;
		//printf("%.3f ------- \n", i);
     	for (j=0;j<tlen;j++) {
			for (k=1;k<tlen;k++) {
				accum+=data[ind+j]*data[ind+k]*template[j*tlen+k];
				}
			}
		match[i]=accum;
		}
}

/* python extension methods */

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
gicc_invar(PyObject *self, PyObject *args)
{
	PyObject *idata, *itemplate, *ivar, *omatch, *adjamp;
	PyArrayObject *data, *template, *var, *match;
	int ampadj;
	if (!PyArg_ParseTuple(args, "OOOOO", &idata, &itemplate, &ivar, &omatch, &adjamp))
			return NULL;
	data=PyArray_FROM_OTF(idata, NPY_FLOAT32 , C_ARRAY);
	template=PyArray_FROM_OTF(itemplate, NPY_FLOAT32, C_ARRAY);
	var=PyArray_FROM_OTF(ivar, NPY_FLOAT32, C_ARRAY);
	match=PyArray_FROM_OTF(omatch, NPY_FLOAT32, C_ARRAY);
	if (data == NULL || var== NULL || template== NULL || match== NULL) return NULL;
	if  (data->dimensions[0]!=match->dimensions[0])
		{
		return PyErr_Format(PyExc_StandardError,
        					"Conv invar: data and output arrays need identitcal shapes.");
		goto _fail;					
		}					
	if ((template->nd != 1) || (data->nd != 1) || (var->nd != 1))
		{
		return PyErr_Format(PyExc_StandardError,
				"Conv invar: arrays must have 1 dimension.");
		goto _fail;	
		}
	ampadj=PyObject_IsTrue(adjamp);	
	conv_invar(data->dimensions[0], PyArray_DATA(data),
			template->dimensions[0], PyArray_DATA(template),  
			PyArray_DATA(var), PyArray_DATA(match), ampadj);
	Py_XDECREF(data);
	Py_XDECREF(template);
	Py_XDECREF(var);			
	Py_XDECREF(match);			
	Py_INCREF(omatch);
	return omatch;
	
	_fail:
		Py_XDECREF(data);
		Py_XDECREF(template);			
		Py_XDECREF(var);			
		Py_XDECREF(match);			
		return NULL;
								
}

static PyObject *
gicc_pca(PyObject *self, PyObject *args)
{
	PyObject *idata, *itemplate, *omatch;
	PyArrayObject *data, *template, *match;
	if (!PyArg_ParseTuple(args, "OOO", &idata, &itemplate, &omatch))
			return NULL;
	data=PyArray_FROM_OTF(idata, NPY_FLOAT32, C_ARRAY);
	template=PyArray_FROM_OTF(itemplate, NPY_FLOAT32, C_ARRAY);
	match=PyArray_FROM_OTF(omatch, NPY_FLOAT32, C_ARRAY);
	if (data == NULL || template== NULL || match== NULL) return NULL;
	if (data->nd != 1)
		{
		return PyErr_Format(PyExc_StandardError,
				"Conv pca: input array must have 1 dimension.");
		goto _fail;	
		}
	conv_residualvar(data->dimensions[0], PyArray_DATA(data),
			template->dimensions[0],template->dimensions[1], PyArray_DATA(template), PyArray_DATA(match));
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
gicc_invpca(PyObject *self, PyObject *args)
{
	PyObject *idata, *itemplate, *omatch;
	PyArrayObject *data, *template, *match;
	if (!PyArg_ParseTuple(args, "OOO", &idata, &itemplate, &omatch))
			return NULL;
	data=PyArray_FROM_OTF(idata, NPY_FLOAT32, C_ARRAY);
	template=PyArray_FROM_OTF(itemplate, NPY_FLOAT32, C_ARRAY);
	match=PyArray_FROM_OTF(omatch, NPY_FLOAT32, C_ARRAY);
	if (data == NULL || template== NULL || match== NULL) return NULL;

	if (data->nd != 1)
		{
		return PyErr_Format(PyExc_StandardError,
				"Conv pca: input array must have 1 dimension.");
		goto _fail;	
		}
	conv_projectvar(data->dimensions[0], PyArray_DATA(data),
			template->dimensions[0],template->dimensions[1], PyArray_DATA(template), PyArray_DATA(match));
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
gicc_2dkern(PyObject *self, PyObject *args)
{
	PyObject *idata, *itemplate, *omatch;
	PyArrayObject *data, *template, *match;
	if (!PyArg_ParseTuple(args, "OOO", &idata, &itemplate, &omatch))
			return NULL;
	data=PyArray_FROM_OTF(idata, NPY_FLOAT32, C_ARRAY);
	template=PyArray_FROM_OTF(itemplate, NPY_FLOAT32, C_ARRAY);
	match=PyArray_FROM_OTF(omatch, NPY_FLOAT32, C_ARRAY);
	if (data == NULL ||  template== NULL || match== NULL) return NULL;

	if (data->nd != 1)
		{
		return PyErr_Format(PyExc_StandardError,
				"Conv 2dkern: input array must have 1 dimension.");
		goto _fail;	
		}
	if (template->dimensions[0] != template->dimensions[1])
		{
		return PyErr_Format(PyExc_StandardError,
				"Conv 2dkern: kernel must be a square matrix");
		goto _fail;	
		}
		
	conv_2dkern(data->dimensions[0], PyArray_DATA(data),
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
// new (better?) "python style" array element handling  
gicc_lif(PyObject *self, PyObject *args)

{
	PyArrayObject *data, *spikes;
	float refract, leak, thresh, v;
	int ind;
	PyListObject *buffer;
	if (!PyArg_ParseTuple(args, "Offf", &data, &refract, &leak, &thresh))
			return NULL;
	buffer=PyList_New(0);
	v=0;
	//this is required to avoid a segv on x86_32 linux
	data=PyArray_FROM_OTF(data, NPY_FLOAT32, C_ARRAY);
	for (ind=0;ind<data->dimensions[0];ind++)
	{
		v-=leak*v;
		v+=*((float *) PyArray_GETPTR1(data,ind));
		if (v>=thresh)
		{
			PyList_Append(buffer,Py_BuildValue("i", ind)); 
			v-=refract;
		}
		//printf("%.2f\n", v);
	}

 	Py_XDECREF(data);
	spikes=PyArray_FROM_OTF(buffer, NPY_INT64, C_ARRAY);
	Py_XDECREF(buffer);
	Py_INCREF(spikes);
	return spikes;
}

static PyObject *
gicc_spikeD(PyObject *self, PyObject *args)
{
	PyObject *idata, *idata2;
	PyArrayObject *data, *data2;
	float distance, cost;
	if (!PyArg_ParseTuple(args, "OOf", &idata, &idata2, &cost))
			return NULL;
	data=PyArray_FROM_OTF(idata, NPY_FLOAT32, C_ARRAY);
	data2=PyArray_FROM_OTF(idata2, NPY_FLOAT32, C_ARRAY);
	if (data == NULL ||  data2== NULL) return NULL;
	if (data->nd != 1)
		{
		return PyErr_Format(PyExc_StandardError,
				"Conv pca: input array must have 1 dimension.");
		goto _fail;	
		}
	distance=conv_victorDist(data->dimensions[0], PyArray_DATA(data),
			data2->dimensions[0],PyArray_DATA(data2), cost);
	Py_XDECREF(data);
	Py_XDECREF(data2);
	return Py_BuildValue("f", distance);
	_fail:
		Py_XDECREF(data);
		Py_XDECREF(data2);			
		return NULL;
}

static PyObject *
gicc_evttrans(PyObject *self, PyObject *args)
{
	PyObject *e1p, *e2p;
	PyArrayObject *e1, *e2;
	PyListObject *trans;
	float cost, ist, jst;
	int i,j, ni, nj;
	float *tmat;	
	if (!PyArg_ParseTuple(args, "OOf", &e1p, &e2p, &cost))
			return NULL;
	e1=PyArray_FROM_OTF(e1p, NPY_FLOAT32, C_ARRAY);
	e2=PyArray_FROM_OTF(e2p, NPY_FLOAT32, C_ARRAY);
	if (e1 == NULL ||  e2== NULL) return NULL;
	ni=e1->dimensions[0]+1;
	nj=e2->dimensions[0]+1;
	tmat=(float *)malloc((ni*nj)*sizeof(float));
	trans=PyList_New(0);
	for (i=0;i<ni;i++) {
		tmat[i]=i;
	}
	for (j=1;j<nj;j++) {
		tmat[j*ni]=j;
	}
	for (i=1;i<ni; i++) {
		for (j=1;j<nj;j++) {
			ist=*((float *) PyArray_GETPTR1(e1,i-1));
			jst=*((float *) PyArray_GETPTR1(e2,j-1));
			tmat[i+j*ni]=min3(tmat[i-1+j*ni]+1, tmat[i+(j-1)*ni]+1, tmat[i-1+(j-1)*ni]+cost*abs(ist-jst));
		}
	}
	i-=1;
	j-=1;
	PyList_Append(trans,Py_BuildValue("d", tmat[i+j*ni]));
	while (i>0 && j>0) {
		if (tmat[i+ni*j]==tmat[i-1+ni*j]+1) 
			i-=1;
		else if (tmat[i+ni*j]==tmat[i+ni*(j-1)]+1)
			j-=1;
		else {
			i-=1;
			j-=1;
			PyList_Append(trans,Py_BuildValue("ii", i, j));
		}
	}
	free(tmat);
	Py_XDECREF(e1);
	Py_XDECREF(e2);
	return trans;

}


static PyObject *
gicc_getindex(PyObject *self, PyObject *args)

{
	PyArrayObject *els, *tab, *ind;
	long i, j, jin, v1, v2;
	int dims[1];
	if (!PyArg_ParseTuple(args, "OO", &tab, &els))
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
gicc_getindex_s(PyObject *self, PyObject *args)

{
	PyArrayObject *els, *tab, *ind;
	long i, v1, v2, ci;
	int dims[1];
	if (!PyArg_ParseTuple(args, "OO", &tab, &els))
			return NULL;
	//this is required to avoid a segv on x86_32 linux
	els=PyArray_FROM_OTF(els, NPY_LONG, C_ARRAY);
	tab=PyArray_FROM_OTF(tab, NPY_LONG, C_ARRAY);	
	dims[0]=els->dimensions[0];
	ind=PyArray_SimpleNew(1, dims, PyArray_LONG);
	ci=0;
	v2=*((long *) PyArray_GETPTR1(tab,ci));
	for (i=0;i<els->dimensions[0];i++)
	{
		v1= *((long *) PyArray_GETPTR1(els,i));
		while (v2<v1 && ci< tab->dimensions[0]-1) {
			ci++;
			v2=*((long *) PyArray_GETPTR1(tab,ci));
		}
		if (v2==v1) {*((long *) PyArray_GETPTR1(ind,i))=ci;}
		else {*((long *) PyArray_GETPTR1(ind,i))=-1;}
	}	
 	Py_XDECREF(els);
	Py_XDECREF(tab);
	Py_INCREF(ind);
	return ind;
}



/* module initialization */

static PyMethodDef GicconvolveMethods[] = {
    {"match",  gicc_match, METH_VARARGS,
     "match a template"},
    {"getindex_full",  gicc_getindex, METH_VARARGS,
     "getindex_full(a, v) -> array of ints of len(v). if a and v are 1D arrays of ints, an array of ints R is returned such that the ith element of R is the index into a at which the ith value of v occurs. If the ith value of v is not in a, the ith value of R is -1, otherwise it is always a non-negative index. THis version of the function applies no requirements for the arrays to be unique or sorted. If a is non-unique, the indexes returned will always be for the first occurence of the target number."},
     {"getindex_set",  gicc_getindex_s, METH_VARARGS,
     "getindex_set(a, v) -> array of ints of len(v). Equivalent to getindex_full, but substantially faster, and only effective if a and v are both sorted, unique, and monotonically increasing. The return value will also be unique and increasing iff v is a subset of a (otherwise the return value will contain one or more -1 indexes"},
    {"mhnd",  gicc_mhnd, METH_VARARGS,
     "Calculate mahalanobis distance"},
 	{"invar",  gicc_invar, METH_VARARGS,
     "determine the probability that signal is within varriance of template"},
 	{"pcafilt",  gicc_pca, METH_VARARGS,
     "determine the magnitude of residual that is not explained by the PCs"},
 	{"pcaproj",  gicc_invpca, METH_VARARGS,
     "determine the magnitude of the residual that is explained by PCs"},
 	{"evttransform",  gicc_evttrans, METH_VARARGS,
     "convert one spike train to another using victor's distance."},
 	{"apply2dkern",  gicc_2dkern, METH_VARARGS,
     "apply the 2nd order wiener kernel in arg1 to the 1D array arg0, return in arg3"},
 	{"lif",  gicc_lif, METH_VARARGS,
     "Run a (deterministic) leaky integrate and fire model. Arg0 is the input signal (1D array), Arg1 is the refractory penalty (float), Arg2 is the leak, Arg3 is the threshold. The return is an array of ints"},
 	{"spikeDistance",  gicc_spikeD, METH_VARARGS,
     "Calculate the Victor/Purpura Metric Space spike distance"},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};
		

PyMODINIT_FUNC
initgicconvolve(void)
{
    import_array();
    (void) Py_InitModule("gicconvolve", GicconvolveMethods);
}

		
