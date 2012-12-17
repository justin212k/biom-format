#!/usr/bin/env python

"""Core BIOM objects for dense and sparse tables"""

from __future__ import division

from datetime import datetime
from json import dumps
from types import NoneType
from operator import itemgetter, xor, add
from itertools import izip
from collections import defaultdict, Hashable
from numpy import ndarray, asarray, array, newaxis, zeros

from biom import get_sparse_backend
from biom.exception import TableException, UnknownID
from biom.util import get_biom_format_version_string, \
    get_biom_format_url_string, unzip, flatten, _natsort_key, natsort, \
    prefer_self, index_list

SparseObj, to_sparse, dict_to_sparseobj, list_dict_to_sparseobj, \
        list_nparray_to_sparseobj, nparray_to_sparseobj, \
        list_list_to_sparseobj = get_sparse_backend()

__author__ = "Daniel McDonald"
__copyright__ = "Copyright 2012, BIOM-Format Project"
__credits__ = ["Daniel McDonald", "Jai Ram Rideout", "Greg Caporaso",
               "Jose Clemente", "Justin Kuczynski"]
__license__ = "GPL"
__url__ = "http://biom-format.org"
__version__ = "1.1.1"
__maintainer__ = "Daniel McDonald"
__email__ = "daniel.mcdonald@colorado.edu"   

class Table(object):
    """Abstract base class representing a Table.

    Once created, a Table object is immutable except for its sample/observation
    metadata, which can be modified in place via addSampleMetadata and
    addObservationMetadata.

    Code to simulate immutability taken from here:
        http://en.wikipedia.org/wiki/Immutable_object
    """
    _biom_type = None
    _biom_matrix_type = None

    def __setattr__(self, *args):
        raise TypeError("A Table object cannot be modified once created.")
    __delattr__ = __setattr__

    def __init__(self, Data, SampleIds, ObservationIds, SampleMetadata=None,
                 ObservationMetadata=None, TableId=None, **kwargs):
        super(Table, self).__setattr__('TableId', TableId)
        super(Table, self).__setattr__('_data', Data)
        super(Table, self).__setattr__('_dtype', Data.dtype)

        # Cast to tuple for immutability.
        super(Table, self).__setattr__('SampleIds', tuple(SampleIds))
        super(Table, self).__setattr__('ObservationIds', tuple(ObservationIds))

        if SampleMetadata is not None:
            super(Table, self).__setattr__('SampleMetadata',
                                           tuple(SampleMetadata))
        else:
            super(Table, self).__setattr__('SampleMetadata', None)

        if ObservationMetadata is not None:
            super(Table, self).__setattr__('ObservationMetadata',
                                           tuple(ObservationMetadata))
        else:
            super(Table, self).__setattr__('ObservationMetadata', None)

        # These will be set by _index_ids()
        super(Table, self).__setattr__('_sample_index', None)
        super(Table, self).__setattr__('_obs_index', None)

        self._verify_metadata()
        self._cast_metadata()
        self._index_ids()

    def _index_ids(self):
        """Sets lookups {id:index in _data}.
        
        Should only be called in constructor as this modifies state.
        """
        super(Table, self).__setattr__('_sample_index',
                                       index_list(self.SampleIds))
        super(Table, self).__setattr__('_obs_index',
                                       index_list(self.ObservationIds))

    def _conv_to_self_type(self, vals, transpose=False):
        """For converting vectors to a compatible self type"""
        raise NotImplementedError

    def _verify_metadata(self):
        """Obtain some notion of sanity on object construction with inputs"""
        try:
            n_obs, n_samp = self._data.shape
        except:
            n_obs = n_samp = 0

        if n_obs != len(self.ObservationIds):
            raise TableException, \
                    "Number of ObservationIds differs from matrix size!"

        if n_obs != len(set(self.ObservationIds)):
            raise TableException, "Duplicate ObservationIds"

        if n_samp != len(self.SampleIds):
            raise TableException, \
                    "Number of SampleIds differs from matrix size!"

        if n_samp != len(set(self.SampleIds)):
            raise TableException, "Duplicate SampleIds"

        if self.SampleMetadata is not None and \
           n_samp != len(self.SampleMetadata):
            raise TableException, "SampleMetadata not in a compatible shape \
                                   with data matrix!"

        if self.ObservationMetadata is not None and \
           n_obs != len(self.ObservationMetadata):
            raise TableException, "ObservationMetadata not in a compatible \
                                   shape with data matrix!"

    def _cast_metadata(self):
        """Casts all metadata to defaultdict to support default values.

        Should be called after any modifications to sample/observation
        metadata.
        """
        default_samp_md = []
        default_obs_md = []

        # if we have a list of [None], set to None
        if self.SampleMetadata is not None:
            if self.SampleMetadata.count(None) == len(self.SampleMetadata):
                super(Table, self).__setattr__('SampleMetadata', None)

        if self.SampleMetadata is not None:
            for samp_md in self.SampleMetadata:
                d = defaultdict(lambda: None)

                if isinstance(samp_md, dict):
                    d.update(samp_md)
                elif samp_md is None:
                    pass
                else:
                    raise TableException, "Unable to cast metadata: %s" % \
                            repr(samp_md)

                default_samp_md.append(d)
            super(Table, self).__setattr__('SampleMetadata',
                                           tuple(default_samp_md))

        # if we have a list of [None], set to None
        if self.ObservationMetadata is not None:
            none_count = self.ObservationMetadata.count(None)
            if none_count == len(self.ObservationMetadata):
                super(Table, self).__setattr__('ObservationMetadata', None)

        if self.ObservationMetadata is not None:
            for obs_md in self.ObservationMetadata:
                d = defaultdict(lambda: None)

                if isinstance(obs_md, dict):
                    d.update(obs_md)
                elif obs_md is None:
                    pass
                else:
                    raise TableException, "Unable to cast metadata: %s" % \
                            repr(obs_md)

                default_obs_md.append(d)
            super(Table, self).__setattr__('ObservationMetadata',
                                           tuple(default_obs_md))

    def addObservationMetadata(self, md):
        """Take a dict of metadata and add it to an observation.

        ``md`` should be of the form ``{observation_id:{dict_of_metadata}}``
        """
        if self.ObservationMetadata != None:
            for id_, md_entry in md.items():
                self.ObservationMetadata[self.getObservationIndex(id_)].update(md_entry)
        else:
            super(Table, self).__setattr__('ObservationMetadata',
                    tuple([md[id_] for id_ in self.ObservationIds]))
        self._cast_metadata()

    def addSampleMetadata(self, md):
        """Take a dict of metadata and add it to a sample.
    
        ``md`` should be of the form ``{sample_id:{dict_of_metadata}}``
        """
        if self.SampleMetadata != None:
            for id_, md_entry in md.items():
                self.SampleMetadata[self.getSampleIndex(id_)].update(md_entry)
        else:
            super(Table, self).__setattr__('SampleMetadata',
                    tuple([md[id_] for id_ in self.SampleIds]))
        self._cast_metadata()

    def __getitem__(self, args):
        """Passes through to internal matrix"""
        return self._data[args]

    def reduce(self, f, axis):
        """Reduce over axis with f

        ``axis`` can be either ``sample`` or ``observation``
        """
        if self.isEmpty():
            raise TableException, "Cannot reduce an empty table"

        # np.apply_along_axis might reduce type conversions here and improve
        # speed. am opting for reduce right now as I think its more readable
        if axis == 'sample':
            return asarray([reduce(f,v) for v in self.iterSampleData()])
        elif axis == 'observation':
            return asarray([reduce(f,v) for v in self.iterObservationData()])
        else:
            raise TableException, "Unknown reduction axis"

    def sum(self, axis='whole'):
        """Returns the sum by axis
        
        axis can be:

        ``whole``       : whole matrix sum
        
        ``sample``     : return a vector with a sum for each sample
        
        ``observation`` : return a vector with a sum for each observation
        """
        if axis == 'whole':
            return sum(self.reduce(add, 'sample'))
        elif axis == 'sample':
            return self.reduce(add, 'sample')
        elif axis == 'observation':
            return self.reduce(add, 'observation')
        else:
            raise TableException, "Unknown axis %s" % axis

    def getSampleIndex(self, samp_id):
        """Returns the sample index for sample ``samp_id``"""
        if samp_id not in self._sample_index:
            raise UnknownID, "SampleId %s not found!" % samp_id
        return self._sample_index[samp_id]

    def getObservationIndex(self, obs_id):
        """Returns the observation index for observation ``obs_id``"""
        if obs_id not in self._obs_index:
            raise UnknownID, "ObservationId %s not found!" % obs_id
        return self._obs_index[obs_id]

    def getValueByIds(self, obs_id, samp_id):
        """Return value in the matrix corresponding to ``(obs_id, samp_id)``
        """
        if obs_id not in self._obs_index:
            raise UnknownID, "ObservationId %s not found!" % obs_id
        if samp_id not in self._sample_index:
            raise UnknownID, "SampleId %s not found!" % samp_id

        return self._data[self._obs_index[obs_id], self._sample_index[samp_id]]

    def __str__(self):
        """Stringify self

        Default str output for a Table is just row/col ids and data values
        """
        return self.delimitedSelf()

    def sampleExists(self, id_):
        """Returns True if sample ``id_`` exists, False otherwise"""
        return id_ in self._sample_index

    def observationExists(self, id_):
        """Returns True if observation ``id_`` exists, False otherwise"""
        return id_ in self._obs_index

    def delimitedSelf(self, delim='\t', header_key=None, header_value=None, 
        metadata_formatter=str):
        """Return self as a string in a delimited form
        
        Default str output for the Table is just row/col ids and table data
        without any metadata

        Including observation metadata in output: If ``header_key`` is not 
        ``None``, the observation metadata with that name will be included 
        in the delimited output. If ``header_value`` is also not ``None``, the 
        observation metadata will use the provided ``header_value`` as the 
        observation metadata name (i.e., the column header) in the delimited 
        output. 
        
        ``metadata_formatter``: a function which takes a metadata entry and 
        returns a formatted version that should be written to file
        """
        if self.isEmpty():
            raise TableException, "Cannot delimit self if I don't have data..."

        samp_ids = delim.join(map(str, self.SampleIds))

        # 17 hrs of straight programming later...
        if header_key is not None:
            if header_value is None:
                raise TableException, "You need to specify both header_key and header_value"
        if header_value is not None:
            if header_key is None:
                raise TableException, "You need to specify both header_key and header_value"

        if header_value:
            output = ['# Constructed from biom file','#OTU ID%s%s\t%s' % (delim, 
                samp_ids,header_value)]
        else:
            output = ['# Constructed from biom file','#OTU ID%s%s' % (delim, 
                samp_ids)]

        for obs_id, obs_values in zip(self.ObservationIds, self._iter_obs()):
            str_obs_vals = delim.join(map(str, self._conv_to_np(obs_values)))

            if header_key and self.ObservationMetadata is not None:
                md = self.ObservationMetadata[self._obs_index[obs_id]]
                md_out = metadata_formatter(md.get(header_key,None))
                output.append('%s%s%s\t%s' % (obs_id, delim, str_obs_vals, md_out))
            else:
                output.append('%s%s%s' % (obs_id, delim, str_obs_vals))

        return '\n'.join(output)

    def isEmpty(self):
        """Returns ``True`` if the table is empty"""
        if not self.SampleIds or not self.ObservationIds:
            return True
        else:
            return False

    def getTableDensity(self):
        """Defined by subclass"""
        raise NotImplementedError

    def __iter__(self):
        """Defined by subclass"""
        raise NotImplementedError

    def _iter_obs(self):
        """Defined by subclass"""
        raise NotImplementedError

    def _iter_samp(self):
        """Defined by subclass"""
        raise NotImplementedError

    def __eq__(self, other):
        """Equality is determined by the data matrix, metadata, and IDs"""
        if self.ObservationIds != other.ObservationIds:
            return False
        if self.SampleIds != other.SampleIds:
            return False
        if self.ObservationMetadata != other.ObservationMetadata:
            return False
        if self.SampleMetadata != other.SampleMetadata:
            return False
        if not self._data_equality(other):
            return False

        return True

    def _data_equality(self,other):
        """Private method to determine equality of data"""
        raise NotImplementedError

    def __ne__(self,other):
        return not (self == other)

    def _conv_to_np(self, v):
        """Convert values of v to numpy arrays"""
        raise NotImplementedError

    # _index objs are in place, can now do sampleData(self, sample_id) and observationData(self, obs_id)
    def sampleData(self, id_):
        """Return observations associated with sample id ``id_``"""
        if id_ not in self._sample_index:
            raise UnknownID, "ID %s is not a known sample ID!" % id_
        return self._conv_to_np(self._data[:,self._sample_index[id_]])

    def observationData(self, id_):
        """Return samples associated with observation id ``id_``"""
        if id_ not in self._obs_index:
            raise UnknownID, "ID %s is not a known observation ID!" % id_
        return self._conv_to_np(self._data[self._obs_index[id_],:])

    def copy(self):
        """Returns a copy of the table"""
        #### NEEDS TO BE A DEEP COPY, MIGHT NOT GET METADATA! NEED TEST!
        return self.__class__(self._data.copy(), self.SampleIds[:], 
                self.ObservationIds[:], self.SampleMetadata, 
                self.ObservationMetadata, self.TableId)

    def iterSampleData(self):
        """Yields sample values"""
        for samp_v in self._iter_samp():
            yield self._conv_to_np(samp_v)

    def iterObservationData(self):
        """Yields observation values"""
        for obs_v in self._iter_obs():
            yield self._conv_to_np(obs_v)

    def iterSamples(self, conv_to_np=True):
        """Yields ``(sample_value, sample_id, sample_metadata)``

        NOTE: will return ``None`` in ``sample_metadata`` positions if 
        ``self.SampleMetadata`` is set to ``None``
        """
        if self.SampleMetadata is None:
            samp_metadata = (None,) * len(self.SampleIds)
        else:
            samp_metadata = self.SampleMetadata
        
        iterator = izip(self._iter_samp(), self.SampleIds, samp_metadata)
        for samp_v, samp_id, samp_md in iterator:
            if conv_to_np:
                yield (self._conv_to_np(samp_v), samp_id, samp_md)
            else:
                yield (samp_v, samp_id, samp_md)
        
    def iterObservations(self, conv_to_np=True):
        """Yields ``(observation_value, observation_id, observation_metadata)``

        NOTE: will return ``None`` in ``observation_metadata`` positions if 
        ``self.ObservationMetadata`` is set to ``None``
        """
        if self.ObservationMetadata is None:
            obs_metadata = (None,) * len(self.ObservationIds)
        else:
            obs_metadata = self.ObservationMetadata
        
        iterator = izip(self._iter_obs(), self.ObservationIds, obs_metadata)
        for obs_v, obs_id, obs_md in iterator:
            if conv_to_np:
                yield (self._conv_to_np(obs_v), obs_id, obs_md)
            else:
                yield (obs_v, obs_id, obs_md)
        
    def sortSampleOrder(self, sample_order):
        """Return a new table with samples in ``sample_order``"""
        samp_md = []
        vals = []

        for id_ in sample_order:
            cur_idx = self._sample_index[id_]
            vals.append(self._conv_to_np(self[:,cur_idx]))
            
            if self.SampleMetadata is not None:
                samp_md.append(self.SampleMetadata[cur_idx])

        if not samp_md:
            samp_md = None

        return self.__class__(self._conv_to_self_type(vals,transpose=True), 
                sample_order[:], self.ObservationIds[:], samp_md, 
                self.ObservationMetadata, self.TableId)

    def sortObservationOrder(self, obs_order):
        """Return a new table with observations in ``observation order``"""
        obs_md = []
        vals = []

        for id_ in obs_order:
            cur_idx = self._obs_index[id_]
            vals.append(self[cur_idx,:])

            if self.ObservationMetadata is not None:
                obs_md.append(self.ObservationMetadata[cur_idx])

        if not obs_md:
            obs_md = None

        return self.__class__(self._conv_to_self_type(vals),
                self.SampleIds[:], obs_order[:], self.SampleMetadata,
                obs_md, self.TableId)

    def sortBySampleId(self, sort_f=natsort):
        """Return a table where samples are sorted by ``sort_f``
        
            ``sort_f`` must take a single parameter: the list of sample ids
        """
        return self.sortSampleOrder(sort_f(self.SampleIds))

    def sortByObservationId(self, sort_f=natsort):
        """Return a table where observations are sorted by ``sort_f``
        
            ``sort_f`` must take a single parameter: the list of observation 
            ids
        """
        return self.sortObservationOrder(sort_f(self.ObservationIds))

    # a good refactor in the future is a general filter() method and then
    # specify the axis, like Table.reduce

    # take() is tempting here as well...
    def filterSamples(self, f, invert=False):
        """Filter samples from self based on ``f``
        
        ``f`` must accept three variables, the sample values, sample IDs and 
        sample metadata. The function must only return ``True`` or ``False``, 
        where ``True`` indicates that a sample should be retained.
        
        invert: if ``invert == True``, a return value of ``True`` from ``f`` 
        indicates that a sample should be discarded
        """
        samp_ids = []
        samp_vals = []
        samp_metadata = []

        # builtin filter puts all of this into memory and then return to the for
        # loop. This will impact memory substantially on large sparse matrices
        for s_val, s_id, s_md in self.iterSamples():
            if not xor(f(s_val, s_id, s_md), invert):
                continue

            # there is an implicit converstion to numpy types, want to make 
            # sure to convert back to underlying representation.
            samp_vals.append(self._conv_to_self_type(s_val))
            samp_metadata.append(s_md)
            samp_ids.append(s_id)
    
        # if we don't have any values to keep, throw an exception as we can 
        # create an inconsistancy in which there are observation ids but no
        # matrix data in the resulting table
        if not samp_ids:
            raise TableException, "All samples filtered out!"

        # the additional call to _conv_to_self_type is to convert a list of 
        # vectors to a matrix
        # transpose is necessary as the underlying storage is sample == col
        return self.__class__(self._conv_to_self_type(samp_vals,transpose=True),
                samp_ids[:], self.ObservationIds[:], samp_metadata, 
                self.ObservationMetadata, self.TableId)

    def filterObservations(self, f, invert=False):
        """Filter observations from self based on ``f``
        
        ``f`` must accept three variables, the observation values, observation
        IDs and observation metadata. The function must only return ``True`` or
        ``False``, where ``True`` indicates that an observation should be
        retained.
        
        invert: if ``invert == True``, a return value of ``True`` from ``f`` 
        indicates that an observation should be discarded
        """
        obs_ids = []
        obs_vals = []
        obs_metadata = []

        # builtin filter puts all of this into memory and then return to the for
        # loop. This will impact memory substantially on large sparse matrices
        for o_val, o_id, o_md in self.iterObservations():
            if not xor(f(o_val, o_id, o_md), invert):
                continue

            # there is an implicit converstion to numpy types, want to make 
            # sure to convert back to underlying representation.
            obs_vals.append(self._conv_to_self_type(o_val))
            obs_metadata.append(o_md)
            obs_ids.append(o_id)

        # if we don't have any values to keep, throw an exception as we can 
        # create an inconsistancy in which there are sample ids but no
        # matrix data in the resulting table
        if not obs_vals:
            raise TableException, "All obs filtered out!"

        return self.__class__(self._conv_to_self_type(obs_vals),self.SampleIds[:],
                obs_ids[:], self.SampleMetadata, obs_metadata, self.TableId)

    def binSamplesByMetadata(self, f):
        """Yields tables by metadata
        
        ``f`` is given the sample metadata by row and must return what "bin" 
        the sample is part of.
        """
        bins = {}
        # conversion of vector types is not necessary, vectors are not
        # being passed to an arbitrary function
        for samp_v, samp_id, samp_md in self.iterSamples(conv_to_np=False):
            bin = f(samp_md)

            # try to make it hashable...
            if not isinstance(bin, Hashable):
                bin = tuple(bin)

            if bin not in bins:
                bins[bin] = [[], [], []]

            bins[bin][0].append(samp_id)
            bins[bin][1].append(samp_v)
            bins[bin][2].append(samp_md)

        for bin, (samp_ids, samp_values, samp_md) in bins.iteritems():
            data = self._conv_to_self_type(samp_values, transpose=True)
            yield bin, self.__class__(data, samp_ids[:], self.ObservationIds[:], 
                    samp_md, self.ObservationMetadata, self.TableId)

    def binObservationsByMetadata(self, f):
        """Yields tables by metadata
        
        ``f`` is given the observation metadata by row and must return what 
        "bin" the observation is part of.
        """
        bins = {}
        # conversion of vector types is not necessary, vectors are not
        # being passed to an arbitrary function
        for obs_v, obs_id, obs_md in self.iterObservations(conv_to_np=False):
            bin = f(obs_md)

            # try to make it hashable...
            if not isinstance(bin, Hashable):
                bin = tuple(bin)

            if bin not in bins:
                bins[bin] = [[], [], []]

            bins[bin][0].append(obs_id)
            bins[bin][1].append(obs_v)
            bins[bin][2].append(obs_md)

        for bin, (obs_ids, obs_values, obs_md) in bins.iteritems():
            yield bin, self.__class__(self._conv_to_self_type(obs_values), 
                    self.SampleIds[:], obs_ids[:], self.SampleMetadata,
                    obs_md, self.TableId)

    def collapseSamplesByMetadata(self, metadata_f, reduce_f=add, norm=True, 
            min_group_size=2):
        """Collapse samples in a table by sample metadata
        
        Bin samples by metadata then collapse each bin into a single sample.
        
        Metadata for the collapsed samples are retained and can be referred to
        by the ``SampleId`` from each sample within the bin.
        """
        collapsed_data = []
        collapsed_sample_ids = []
        collapsed_sample_md = []

        for bin, table in self.binSamplesByMetadata(metadata_f):
            if len(table.SampleIds) < min_group_size:
                continue

            redux_data = table.reduce(reduce_f, 'observation')
            if norm:
                redux_data /= len(table.SampleIds)

            collapsed_data.append(self._conv_to_self_type(redux_data))
            collapsed_sample_ids.append(bin)
            
            # retain metadata but store by original sample id
            tmp_md = {}
            for id_, md in zip(table.SampleIds, table.SampleMetadata):
                tmp_md[id_] = md
            collapsed_sample_md.append(tmp_md)

        data = self._conv_to_self_type(collapsed_data, transpose=True)

        # if the table is empty
        if 0 in data.shape:
            raise TableException, "Collapsed table is empty!"

        return self.__class__(data, collapsed_sample_ids, self.ObservationIds[:],
                collapsed_sample_md, self.ObservationMetadata, self.TableId)

    def collapseObservationsByMetadata(self, metadata_f, reduce_f=add, 
            norm=True, min_group_size=2):
        """Collapse observations in a table by observation metadata
        
        Bin observations by metadata then collapse each bin into a single 
        observation. 
        
        Metadata for the collapsed observations are retained and 
        can be referred to by the ``ObservationId`` from each observation 
        within the bin.
        """
        collapsed_data = []
        collapsed_obs_ids = []
        collapsed_obs_md = []

        for bin, table in self.binObservationsByMetadata(metadata_f):
            if len(table.ObservationIds) < min_group_size:
                continue

            redux_data = table.reduce(reduce_f, 'sample')
            if norm:
                redux_data /= len(table.ObservationIds)

            collapsed_data.append(self._conv_to_self_type(redux_data))
            collapsed_obs_ids.append(bin)
   
            # retain metadata but store by original sample id
            tmp_md = {}
            for id_, md in zip(table.ObservationIds, table.ObservationMetadata):
                tmp_md[id_] = md
            collapsed_obs_md.append(tmp_md)

        data = self._conv_to_self_type(collapsed_data)

        # if the table is empty
        if 0 in data.shape:
            raise TableException, "Collapsed table is empty!"

        return self.__class__(data, self.SampleIds[:], collapsed_obs_ids,
                self.SampleMetadata, collapsed_obs_md, self.TableId)

    def transformSamples(self, f):
        """Iterate over samples, applying a function ``f`` to each value
        
        ``f`` must take three values: a sample value (int or float), a sample 
        id, and a sample metadata entry, and return a single value (int or 
        float) that replaces the provided sample value
        """
        dtype = float
        new_m = get_zerod_matrix(self._data, dtype)

        i = 0
        for s_v, s_id, s_md in self.iterSamples():
            s_v = f(s_v, s_id, s_md)
            
            for j,v in enumerate(s_v):
                if v:
                    # force transpose
                    new_m[j,i] = v
            i += 1

        return self.__class__(new_m, self.SampleIds[:], self.ObservationIds[:],
                self.SampleMetadata, self.ObservationMetadata, self.TableId)

    def transformObservations(self, f):
        """Iterate over observations, applying a function ``f`` to each value

        ``f`` must take three values: an observation value (int or float), an 
        observation id, and an observation metadata entry, and return a single
        value (int or float) that replaces the provided observation value

        """
        dtype = float
        new_obs_v = get_zerod_matrix(self._data, dtype)

        i = 0
        for obs_v, obs_id, obs_md in self.iterObservations():
            obs_v = f(obs_v, obs_id, obs_md)

            for j,v in enumerate(obs_v):
                if v:
                    new_obs_v[i,j] = v
            i += 1

        return self.__class__(new_obs_v, self.SampleIds[:], 
                self.ObservationIds[:], self.SampleMetadata, 
                self.ObservationMetadata, self.TableId)

    def normObservationBySample(self):
        """Return new table with vals as relative abundances within each sample
        """
        def f(samp_v, samp_id, samp_md):
            return samp_v / float(samp_v.sum())
        return self.transformSamples(f)

    def normSampleByObservation(self):
        """Return new table with vals as relative abundances within each obs
        """  
        def f(obs_v,obs_id,obs_md):
            return obs_v / float(obs_v.sum())
        #f = lambda x: x / float(x.sum())
        return self.transformObservations(f)
    
    def normObservationByMetadata(self,obs_metadata_id):
        """Return new table with vals divided by obs_metadata_id
        """
        def f(obs_v,obs_id,obs_md):
            return obs_v / obs_md[obs_metadata_id]
        return self.transformObservations(f)

    def nonzero(self):
        """Returns locations of nonzero elements within the data matrix

        The values returned are ``(observation_id, sample_id)``
        """
        # this is naively implemented. If performance is a concern, private
        # methods can be written to hit against the underlying types directly
        for o_idx, samp_vals in enumerate(self.iterObservationData()):
            for s_idx in samp_vals.nonzero()[0]:
                yield (self.ObservationIds[o_idx], self.SampleIds[s_idx])

    def _union_id_order(self, a, b):
        """Determines merge order for id lists A and B"""
        all_ids = list(a[:])
        all_ids.extend(b[:])
        new_order = {}
        idx = 0
        for id_ in all_ids:
            if id_ not in new_order:
                new_order[id_] = idx
                idx += 1
        return new_order
    
    def _intersect_id_order(self, a, b):
        """Determines the merge order for id lists A and B"""
        all_b = set(b[:])
        new_order = {}
        idx = 0
        for id_ in a:
            if id_ in all_b:
                new_order[id_] = idx
                idx += 1
        return new_order

    def merge(self, other, Sample='union', Observation='union',
            sample_metadata_f=prefer_self, observation_metadata_f=prefer_self):
        """Merge two tables together

        The axes, samples and observations, can be controlled independently. 
        Both can either work on ``union`` or ``intersection``. 

        ``sample_metadata_f`` and ``observation_metadata_f`` define how to 
        merge metadata between tables. The default is to just keep the metadata
        associated to self if self has metadata otherwise take metadata from
        other. These functions are given both metadata dictsand must return 
        a single metadata dict

        NOTE: There is an implicit type conversion to ``float``. Tables using
        strings as the type are not supported. No check is currently in
        place.

        NOTE: The return type is always that of ``self``
        """
        # determine the sample order in the resulting table
        if Sample is 'union':
            new_samp_order = self._union_id_order(self.SampleIds, 
                                                  other.SampleIds)         
        elif Sample is 'intersection':
            new_samp_order = self._intersect_id_order(self.SampleIds,
                                                      other.SampleIds)
        else:
            raise TableException, "Unknown Sample merge type: %s" % Sample
         
        # determine the observation order in the resulting table
        if Observation is 'union':
            new_obs_order = self._union_id_order(self.ObservationIds, 
                                                  other.ObservationIds) 
        elif Observation is 'intersection':
            new_obs_order = self._intersect_id_order(self.ObservationIds,
                                                      other.ObservationIds)
        else:
            raise TableException, "Unknown observation merge type: %s" % Observation

        # convert these to lists, no need to be dictionaries and reduces
        # calls to items() and allows for pre-caluculating insert order
        new_samp_order = sorted(new_samp_order.items(), key=itemgetter(1))
        new_obs_order = sorted(new_obs_order.items(), key=itemgetter(1))
       
        # if we don't have any samples, complain loudly. This is likely from 
        # performing an intersection without overlapping ids
        if not new_samp_order:
            raise TableException, "No samples in resulting table!"
        if not new_obs_order:
            raise TableException, "No observations in resulting table!"

        # helper index lookups
        other_obs_idx = other._obs_index
        self_obs_idx = self._obs_index
        other_samp_idx = other._sample_index
        self_samp_idx = self._sample_index

        # pre-calculate sample order from each table. We only need to do this 
        # once which dramatically reduces the number of dict lookups necessary
        # within the inner loop
        other_samp_order = []
        self_samp_order = []
        for samp_id, nsi in new_samp_order: # nsi -> new_sample_index
            other_samp_order.append((nsi, other_samp_idx.get(samp_id, None)))
            self_samp_order.append((nsi, self_samp_idx.get(samp_id,None)))

        # pre-allocate the a list for placing the resulting vectors as the 
        # placement id is not ordered
        vals = [None for i in range(len(new_obs_order))] 
       
        ### POSSIBLE DECOMPOSITION
        # resulting sample ids and sample metadata
        sample_ids = []
        sample_md = []
        for id_,idx in new_samp_order:
            sample_ids.append(id_)

            # if we have sample metadata, grab it
            if self.SampleMetadata is None or not self.sampleExists(id_):
                self_md = None
            else:
                self_md = self.SampleMetadata[self_samp_idx[id_]]
            
            # if we have sample metadata, grab it
            if other.SampleMetadata is None or not other.sampleExists(id_):
                other_md = None
            else:
                other_md = other.SampleMetadata[other_samp_idx[id_]]

            sample_md.append(sample_metadata_f(self_md, other_md))

        ### POSSIBLE DECOMPOSITION
        # resulting observation ids and sample metadata
        obs_ids = []
        obs_md = []
        for id_,idx in new_obs_order:
            obs_ids.append(id_)

            # if we have observation metadata, grab it
            if self.ObservationMetadata is None or \
               not self.observationExists(id_):
                self_md = None
            else:
                self_md = self.ObservationMetadata[self_obs_idx[id_]]

            # if we have observation metadata, grab it
            if other.ObservationMetadata is None or \
                not other.observationExists(id_):
                other_md = None
            else:
                other_md = other.ObservationMetadata[other_obs_idx[id_]]

            obs_md.append(observation_metadata_f(self_md, other_md))

        # length used for construction of new vectors
        vec_length = len(new_samp_order)
        
        # The following lines of code allow for removing type conversions,
        # however it should be noted that in testing as of 7.5.12, this 
        # degraded performance due to the vastly higher performing numpy
        # __setitem__ interface.
        #if self._biom_matrix_type is 'sparse':
        #    data_f = lambda: self._data.__class__(1, vec_length, dtype=float,\
        #                                    enable_indices=False)
        #else:
        #    data_f = lambda: zeros(vec_length, dtype=float) 

        # walk over observations in our new order
        for obs_id, new_obs_idx in new_obs_order:
            # create new vector for matrix values
            new_vec = zeros(vec_length, dtype='float')
            
            # This method allows for the creation of a matrix of self type. 
            # See note above
            #new_vec = data_f()
            
            # see if the observation exists in other, if so, pull it out.
            # if not, set to the placeholder missing
            if other.observationExists(obs_id):
                other_vec = other.observationData(obs_id)
            else:
                other_vec = None
                
            # see if the observation exists in self, if so, pull it out.
            # if not, set to the placeholder missing
            if self.observationExists(obs_id):
                self_vec = self.observationData(obs_id)
            else:
                self_vec = None

            # short circuit. If other doesn't have any values, then we can just
            # take all values from self
            if other_vec is None:
                for (n_idx, s_idx) in self_samp_order:
                    if s_idx is not None:
                        new_vec[n_idx] = self_vec[s_idx]
                                    
            # short circuit. If self doesn't have any values, then we can just
            # take all values from other
            elif self_vec is None:
                for (n_idx, o_idx) in other_samp_order:
                    if o_idx is not None:
                        new_vec[n_idx] = other_vec[o_idx]
                         
            else:
                # NOTE: DM 7.5.12, no observed improvement at the profile level
                # was made on this inner loop by using self_samp_order and 
                # other_samp_order lists.
                
                # walk over samples in our new order
                for samp_id, new_samp_idx in new_samp_order:
                    # pull out each individual sample value. This is expensive,
                    # but the vectors are in a different alignment. It is 
                    # possible that this could be improved with numpy take but 
                    # needs to handle missing values appropriately
                    if samp_id not in self_samp_idx:
                        self_vec_value = 0
                    else:
                        self_vec_value = self_vec[self_samp_idx[samp_id]]
            
                    if samp_id not in other_samp_idx:
                        other_vec_value = 0
                    else: 
                        other_vec_value = other_vec[other_samp_idx[samp_id]]
                        
                    new_vec[new_samp_idx] = self_vec_value + other_vec_value
                
            # convert our new vector to self type as to make sure we don't
            # accidently force a dense representation in memory
            vals[new_obs_idx] = self._conv_to_self_type(new_vec)

        return self.__class__(self._conv_to_self_type(vals), sample_ids[:], 
                obs_ids[:], sample_md, obs_md)

    def getBiomFormatObject(self, generated_by):
        """Returns a dictionary representing the table in BIOM format.

        This dictionary can then be easily converted into a JSON string for
        serialization.

        ``generated_by``: a string describing the software used to build the 
        table

        TODO: This method may be very inefficient in terms of memory usage, so
        it needs to be tested with several large tables to determine if
        optimizations are necessary or not (i.e. subclassing JSONEncoder, using
        generators, etc...).
        """
        if self._biom_type is None:
            raise TableException, "Unknown biom type"

        if (not isinstance(generated_by, str) and
            not isinstance(generated_by, unicode)):
            raise TableException, "Must specify a generated_by string"

        # Fill in top-level metadata.
        biom_format_obj = {}
        biom_format_obj["id"] = self.TableId
        biom_format_obj["format"] = get_biom_format_version_string()
        biom_format_obj["format_url"] =\
                get_biom_format_url_string()
        biom_format_obj["generated_by"] = generated_by
        biom_format_obj["date"] = "%s" % datetime.now().isoformat()
        
        # Determine if we have any data in the matrix, and what the shape of
        # the matrix is.
        try:
            num_rows, num_cols = self._data.shape
        except:
            num_rows = num_cols = 0
        hasData = True if num_rows > 0 and num_cols > 0 else False

        # Default the matrix element type to test to be an integer in case we
        # don't have any data in the matrix to test.
        test_element = 0
        if hasData:
            test_element = self[0,0]

        # Determine the type of elements the matrix is storing.
        if isinstance(test_element, int):
            dtype, matrix_element_type = int, "int"
        elif isinstance(test_element, float):
            dtype, matrix_element_type = float, "float"
        elif isinstance(test_element, unicode):
            dtype, matrix_element_type = unicode, "unicode"
        else:
            raise TableException("Unsupported matrix data type.")

        # Fill in details about the matrix.
        biom_format_obj["type"] = self._biom_type
        biom_format_obj["matrix_type"] = self._biom_matrix_type
        biom_format_obj["matrix_element_type"] = "%s" % matrix_element_type
        biom_format_obj["shape"] = [num_rows, num_cols]

        # Fill in details about the rows in the table and fill in the matrix's
        # data.
        biom_format_obj["rows"] = []
        biom_format_obj["data"] = []
        for obs_index, obs in enumerate(self.iterObservations()):
            biom_format_obj["rows"].append(
                    {"id" : "%s" % obs[1], "metadata" : obs[2]})
            # If the matrix is dense, simply convert the numpy array to a list
            # of data values. If the matrix is sparse, we need to store the
            # data in sparse format, as it is given to us in a numpy array in
            # dense format (i.e. includes zeroes) by iterObservations().
            if self._biom_matrix_type == "dense":
                # convert to python types, JSON doesn't like numpy types
                biom_format_obj["data"].append(map(dtype,obs[0]))
            elif self._biom_matrix_type == "sparse":
                dense_values = list(obs[0])
                sparse_values = []
                for col_index, val in enumerate(dense_values):
                    if float(val) != 0.0:
                        sparse_values.append([obs_index, col_index, \
                                    dtype(val)])
                biom_format_obj["data"].extend(sparse_values)

        # Fill in details about the columns in the table.
        biom_format_obj["columns"] = []
        for samp in self.iterSamples():
            biom_format_obj["columns"].append(
                    {"id" : "%s" % samp[1], "metadata" : samp[2]})
        
        return biom_format_obj

    def getBiomFormatJsonString(self,generated_by, direct_io=None):
        """Returns a JSON string representing the table in BIOM format.

        ``generated_by``: a string describing the software used to build the
        table

        If direct_io is not None, the final output is written directly to
        direct_io during processing.
        """
        if self._biom_type is None:
            raise TableException, "Unknown biom type"

        if (not isinstance(generated_by, str) and
            not isinstance(generated_by, unicode)):
            raise TableException, "Must specify a generated_by string"

        # Fill in top-level metadata.
        if direct_io:
            direct_io.write('{')
            direct_io.write('"id": "%s",' % str(self.TableId))
            direct_io.write('"format": "%s",' % get_biom_format_version_string())
            direct_io.write('"format_url": "%s",' % get_biom_format_url_string())
            direct_io.write('"generated_by": "%s",' % generated_by)
            direct_io.write('"date": "%s",' % datetime.now().isoformat())
        else:
            id_ = '"id": "%s",' % str(self.TableId)
            format_ = '"format": "%s",' % get_biom_format_version_string()
            format_url = '"format_url": "%s",' % get_biom_format_url_string()
            generated_by = '"generated_by": "%s",' % generated_by
            date = '"date": "%s",' % datetime.now().isoformat()
        
        # Determine if we have any data in the matrix, and what the shape of
        # the matrix is.
        try:
            num_rows, num_cols = self._data.shape
        except:
            num_rows = num_cols = 0
        hasData = True if num_rows > 0 and num_cols > 0 else False

        # Default the matrix element type to test to be an integer in case we
        # don't have any data in the matrix to test.
        test_element = 0
        if hasData:
            test_element = self[0,0]

        # Determine the type of elements the matrix is storing.
        if isinstance(test_element, int):
            dtype, matrix_element_type = int, "int"
        elif isinstance(test_element, float):
            dtype, matrix_element_type = float, "float"
        elif isinstance(test_element, unicode):
            dtype, matrix_element_type = unicode, "unicode"
        else:
            raise TableException("Unsupported matrix data type.")

        # Fill in details about the matrix.
        if direct_io:
            direct_io.write('"type": "%s",' % self._biom_type)
            direct_io.write('"matrix_type": "%s",' % self._biom_matrix_type)
            direct_io.write('"matrix_element_type": "%s",' % matrix_element_type)
            direct_io.write('"shape": [%d, %d],' % (num_rows, num_cols))
        else:
            type_ = '"type": "%s",' % self._biom_type
            matrix_type = '"matrix_type": "%s",' % self._biom_matrix_type
            matrix_element_type = '"matrix_element_type": "%s",' % matrix_element_type
            shape = '"shape": [%d, %d],' % (num_rows, num_cols)

        # Fill in details about the rows in the table and fill in the matrix's
        # data.
        if direct_io:
            direct_io.write('"data": [')
        else:
            data = '"data": ['

        max_row_idx = len(self.ObservationIds) - 1
        max_col_idx = len(self.SampleIds) - 1
        rows = '"rows": ['
        have_written = False
        for obs_index, obs in enumerate(self.iterObservations()):
            # i'm crying on the inside
            if obs_index != max_row_idx:
                rows += '{"id": "%s", "metadata": %s},' % (obs[1], 
                                                           dumps(obs[2]))
            else:
                rows += '{"id": "%s", "metadata": %s}],' % (obs[1], 
                                                           dumps(obs[2]))

            # If the matrix is dense, simply convert the numpy array to a list
            # of data values. If the matrix is sparse, we need to store the
            # data in sparse format, as it is given to us in a numpy array in
            # dense format (i.e. includes zeroes) by iterObservations().
            if self._biom_matrix_type == "dense":
                if direct_io:
                    # if we are not on the last row
                    if obs_index != max_row_idx:
                        direct_io.write("[%s]," % ','.join(map(repr, obs[0])))
                    else:
                        direct_io.write("[%s]]," % ','.join(map(repr, obs[0])))
                else:
                    # if we are not on the last row
                    if obs_index != max_row_idx:
                        data += "[%s]," % ','.join(map(repr, obs[0]))
                    else:
                        data += "[%s]]," % ','.join(map(repr, obs[0]))

            elif self._biom_matrix_type == "sparse":
                # turns out its a pain to figure out when to place commas. the
                # simple work around, at the expense of a little memory 
                # (bound by the number of samples) is to build of what will be
                # written, and then add in the commas where necessary.
                built_row = []
                for col_index, val in enumerate(obs[0]):
                    if float(val) != 0.0:
                        built_row.append("[%d,%d,%r]" % (obs_index, col_index,
                                                         val))
                if built_row:
                    # if we have written a row already, its safe to add a comma
                    if have_written:
                        if direct_io:
                            direct_io.write(',')
                        else:
                            data += ','
                    if direct_io:
                        direct_io.write(','.join(built_row))
                    else:
                        data += ','.join(built_row)

                    have_written = True

        # finalize the data block
        if self._biom_matrix_type == 'sparse':
            if direct_io:
                direct_io.write("],")
            else:
                data += "],"

        # Fill in details about the columns in the table.
        columns = '"columns": ['
        for samp_index, samp in enumerate(self.iterSamples()):
            if samp_index != max_col_idx:
                columns += '{"id": "%s", "metadata": %s},' % (samp[1], 
                                                                dumps(samp[2]))
            else:
                columns += '{"id": "%s", "metadata": %s}]' % (samp[1], 
                                                                dumps(samp[2]))

        if direct_io:
            direct_io.write(rows)
            direct_io.write(columns); 
            direct_io.write('}')
        else:
            return "{%s}" % ''.join([id_, format_, format_url, type_, 
                                      generated_by, date, 
                                      matrix_type, matrix_element_type, shape, 
                                      data, rows, columns])

    def getBiomFormatPrettyPrint(self,generated_by):
        """Returns a 'pretty print' format of a BIOM file

        ``generated_by``: a string describing the software used to build the
        table

        WARNING: This method displays data values in a columnar format and 
        can be misleading.
        """
        return dumps(self.getBiomFormatObject(generated_by), sort_keys=True,
                     indent=4)

class SparseTable(Table):
    _biom_matrix_type = "sparse"
    def __init__(self, *args, **kwargs):
        super(SparseTable, self).__init__(*args, **kwargs)
   
    def _data_equality(self, other):
        """Two SparseObj matrices are equal if the items are equal"""
        if isinstance(self, other.__class__):
            return sorted(self._data.items()) == sorted(other._data.items())
        
        for s_v, o_v in izip(self.iterSampleData(),other.iterSampleData()):
            if not (s_v == o_v).all():
                return False
    
        return True

    def _conv_to_np(self, v):
        """Converts a vector to a numpy array

        Always returns a row vector for consistancy with numpy iteration over
        arrays
        """
        vals = v.items()

        num_rows, num_cols = v.shape

        if num_rows > num_cols:
            new_v = zeros(num_rows, dtype=self._dtype)
            for (row,col),val in vals:
                new_v[row] = val
        else:
            new_v = zeros(num_cols, dtype=self._dtype)
            for (row,col),val in vals:
                new_v[col] = val
        return new_v

    def _conv_to_self_type(self, vals, transpose=False, dtype=None):
        """For converting vectors to a compatible self type"""
        if dtype is None:
            dtype = self._dtype
            
        if isinstance(vals, self._data.__class__):
            return vals
        else:
            return to_sparse(vals, transpose, dtype)

    def __iter__(self):
        """Defined by subclass"""
        return self.iterSamples()

    def _iter_samp(self):
        """Return sample vectors of data matrix vectors"""  
        rows, cols = self._data.shape
        for c in range(cols):
            # this pulls out col vectors but need to convert to the expected row
            # vector
            colvec = self._data.getCol(c)
            yield colvec.T

    def _iter_obs(self):
        """Return observation vectors of data matrix"""
        for r in range(self._data.shape[0]):
            #yield self._data[r,:]
            yield self._data.getRow(r)

    def getTableDensity(self):
        """Returns the fraction of nonzero elements in the table."""
        density = 0.0

        if not self.isEmpty():
            density = (self._data.size / (len(self.SampleIds) *
                                          len(self.ObservationIds)))

        return density


class DenseTable(Table):
    _biom_matrix_type = "dense"
    def __init__(self, *args, **kwargs):
        super(DenseTable, self).__init__(*args, **kwargs)

    def _data_equality(self, other):
        """Checks if the data matrices are equal"""
        if isinstance(self, other.__class__):
            return (self._data == other._data).all()
        
        for s_v, o_v in izip(self.iterSampleData(),other.iterSampleData()):
            if not (s_v == o_v).all():
                return False
    
        return True

    def _conv_to_np(self, v):
        """Converts a vector to a numpy array"""
        return asarray(v)

    def _conv_to_self_type(self, vals, transpose=False, dtype=None):
        """For converting vectors to a compatible self type"""
        # dtype call ignored, numpy will handle implicitly
        # expects row vector here...
        if transpose:
            return asarray(vals).T
        else:
            return asarray(vals)

    def __iter__(self):
        """Defined by subclass"""
        return self.iterSamples()

    def _iter_obs(self):
        """Return observations of data matrix"""
        for r in self._data:
            yield r

    def _iter_samp(self):
        """Return samples of data matrix in row vectors"""  
        for c in self._data.T:
            yield c

    def getTableDensity(self):
        """Returns the fraction of nonzero elements in the table."""
        density = 0.0

        if not self.isEmpty():
            density = (len(self._data.nonzero()[0]) /
                       (len(self.SampleIds) * len(self.ObservationIds)))

        return density


class OTUTable(object):
    """OTU table abstract class"""
    _biom_type = "OTU table"
    pass

class PathwayTable(object):
    """Pathway table abstract class"""
    _biom_type = "Pathway table"
    pass

class FunctionTable(object):
    """Function table abstract class"""
    _biom_type = "Function table"
    pass

class OrthologTable(object):
    """Ortholog table abstract class"""
    _biom_type = "Ortholog table"
    pass

class GeneTable(object):
    """Gene table abstract class"""
    _biom_type = "Gene table"
    pass

class MetaboliteTable(object):
    """Metabolite table abstract class"""
    _biom_type = "Metabolite table"
    pass

class TaxonTable(object):
    """Taxon table abstract class"""
    _biom_type = "Taxon table"
    pass

class DenseOTUTable(OTUTable, DenseTable):
    """Instantiatable dense OTU table"""
    pass

class SparseOTUTable(OTUTable, SparseTable):
    """Instantiatable sparse OTU table"""
    pass

class DensePathwayTable(PathwayTable, DenseTable):
    """Instantiatable dense pathway table"""
    pass

class SparsePathwayTable(PathwayTable, SparseTable):
    """Instantiatable sparse pathway table"""
    pass

class DenseFunctionTable(FunctionTable, DenseTable):
    """Instantiatable dense function table"""
    pass

class SparseFunctionTable(FunctionTable, SparseTable):
    """Instantiatable sparse function table"""
    pass

class DenseOrthologTable(OrthologTable, DenseTable):
    """Instantiatable dense ortholog table"""
    pass

class SparseOrthologTable(OrthologTable, SparseTable):
    """Instantiatable sparse ortholog table"""
    pass

class DenseGeneTable(GeneTable, DenseTable):
    """Instantiatable dense gene table"""
    pass

class SparseGeneTable(GeneTable, SparseTable):
    """Instantiatable sparse gene table"""
    pass

class DenseMetaboliteTable(MetaboliteTable, DenseTable):
    """Instantiatable dense metabolite table"""
    pass

class SparseMetaboliteTable(MetaboliteTable, SparseTable):
    """Instantiatable sparse metabolite table"""
    pass

class DenseTaxonTable(TaxonTable, DenseTable):
    """Instantiatable dense taxon table"""
    pass

class SparseTaxonTable(TaxonTable, SparseTable):
    """Instantiatable sparse taxon table"""
    pass

def list_list_to_nparray(data, dtype=float):
    """Convert a list of lists into a nparray

    [[value, value, ..., value], ...]
    """
    return asarray(data, dtype=dtype)

def dict_to_nparray(data, dtype=float):
    """Takes a dict {(row,col):val} and creates a numpy matrix"""
    rows, cols = zip(*data) # unzip
    mat = zeros((max(rows) + 1, max(cols) + 1), dtype=dtype)

    for (row,col),val in data.items():
        mat[row,col] = val

    return mat

def list_dict_to_nparray(data, dtype=float):
    """Takes a list of dicts {(0,col):val} and creates an numpy matrix

    Expects each dict to represent a row vector
    """
    n_rows = len(data)
    n_cols = max(flatten([d.keys() for d in data]), key=itemgetter(1))[1] + 1

    mat = zeros((n_rows, n_cols), dtype=dtype)
    
    for row_idx, row in enumerate(data):
        for (foo,col_idx),val in row.items():
            mat[row_idx, col_idx] = val

    return mat

def table_factory(data, sample_ids, observation_ids, sample_metadata=None, 
                  observation_metadata=None, table_id=None, 
                  constructor=SparseOTUTable, **kwargs):
    """Construct a table

    Attempts to make 'data' sane with respect to the constructor type through
    various means of juggling. Data can be: 
    
        - numpy.array       
        - list of numpy.array vectors 
        - SparseObj representation
        - dict representation
        - list of SparseObj representation vectors
        - list of lists of sparse values [[row, col, value], ...]
        - list of lists of dense values [[value, value, ...], ...]
    
    Example usage to create a SparseOTUTable object::
    
        from biom.table import table_factory, SparseOTUTable
        from numpy import array

        sample_ids = ['s1','s2','s3','s4']
        sample_md = [{'pH':4.2,'country':'Peru'},
                     {'pH':5.2,'country':'Peru'},
                     {'pH':5.0,'country':'Peru'},
                     {'pH':4.9,'country':'Peru'}]

        observation_ids = ['o1','o2','o3']
        observation_md = [{'domain':'Archaea'},
                          {'domain':'Bacteria'},
                          {'domain':'Bacteria'}]

        data = array([[1,2,3,4],
                      [-1,6,7,8],
                      [9,10,11,12]])

        t = table_factory(data,
                          sample_ids,
                          observation_ids,
                          sample_md,
                          observation_md,
                          constructor=SparseOTUTable)
    
    
    """
    if 'dtype' in kwargs:
        dtype = kwargs['dtype']
    else:
        dtype = float

    if 'shape' in kwargs:
        shape = kwargs['shape']
    else:
        shape = None

    if constructor._biom_matrix_type is 'sparse':
        # if we have a numpy array
        if isinstance(data, ndarray):
            data = nparray_to_sparseobj(data, dtype)

        # if we have a list of numpy vectors
        elif isinstance(data, list) and isinstance(data[0], ndarray):
            data = list_nparray_to_sparseobj(data, dtype)

        # if we have a dict representation
        elif isinstance(data, dict) and not isinstance(data, SparseObj):
            data = dict_to_sparseobj(data, dtype)

        elif isinstance(data, SparseObj):
            pass

        # if we have a list of dicts
        elif isinstance(data, list) and isinstance(data[0], dict):
            data = list_dict_to_sparseobj(data, dtype)

        # if we have a list of lists (like inputs from json biom)
        elif isinstance(data, list) and isinstance(data[0], list):
            data = list_list_to_sparseobj(data, dtype, shape=shape)
        else:
            raise TableException, "Cannot handle data!"
    
    elif constructor._biom_matrix_type is 'dense':
        # if we have a numpy array
        if isinstance(data, ndarray):
            pass

        # if we have a list of numpy vectors
        elif isinstance(data, list) and isinstance(data[0], ndarray):
            data = asarray(data, dtype)

        # if we have a dict representation
        elif isinstance(data, dict):
            data = dict_to_nparray(data, dtype)

        # if we have a list of dicts
        elif isinstance(data, list) and isinstance(data[0], dict):
            data = list_dict_to_nparray(data, dtype)

        # if we have a list of lists (ie input from json biom)
        elif isinstance(data, list) and isinstance(data[0], list):
            data = list_list_to_nparray(data, dtype)

        else:
            raise TableException, "Cannot handle data!"
    else:
        raise TableException, "Constructor type specifies an unknown matrix " +\
                              "type: %s" % constructor._biom_matrix_type

    return constructor(data, sample_ids, observation_ids, 
            SampleMetadata=sample_metadata,
            ObservationMetadata=observation_metadata,
            TableId=table_id, **kwargs)

def get_zerod_matrix(mat, dtype=float):
    """Returns a zerod matrix"""
    if isinstance(mat, ndarray):
        return zeros(mat.shape, dtype=float)
    elif isinstance(mat, SparseObj):
        return SparseObj(*mat.shape, dtype=float)
    else:
        raise TableException, "Unknown mat type"
