#!/usr/bin/env python
# encoding: utf-8

import h5py
import numpy as np


def read(f, **kwargs):
    raise NotImplementedError()


def write(fileobj, doc, **kwargs):
    """

    :param fileobj: filelike object to write to
    :type fileobj: file
    :param doc: mien document
    :type doc: mien.nmpml.basic_tools.NmpmlObject
    :param kwargs:
    :return:
    """
    fn = fileobj.name
    fileobj.close()
    h5 = h5py.File(fn, "w")
    data = doc.getElements("Data", heads=False)
    for d in data:
        grp = h5.require_group(d.dpath())
        for k in d.attributes:
            grp.attrs[k] = d.attributes[k]
        dat = d.getData()
        grp.create_dataset("data", data=dat)
    h5.close()


ftype = {
    'notes': 'Read and Write Data blocks in HDF5 files.',
    'read': read,
    'write': write,
    'data type': 'Numerical',
    'elements': ['Data'],
    'extensions': ['.h5', '.hdf', '.hdf5']
}
