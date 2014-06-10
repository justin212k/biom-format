#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ----------------------------------------------------------------------------
# Copyright (c) 2011-2013, The BIOM Format Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
# ----------------------------------------------------------------------------

import os
from tempfile import mktemp
from unittest import TestCase, main
from StringIO import StringIO

import numpy.testing as npt
import numpy as np
from scipy.sparse import lil_matrix, csr_matrix

from biom.exception import UnknownAxisError, UnknownIDError, TableException
from biom.util import unzip, HAVE_H5PY
from biom.table import (Table, prefer_self, index_list, list_nparray_to_sparse,
                        list_dict_to_sparse, dict_to_sparse,
                        coo_arrays_to_sparse, list_list_to_sparse,
                        nparray_to_sparse, list_sparse_to_sparse)
from biom.parse import parse_biom_table

if HAVE_H5PY:
    import h5py

__author__ = "Daniel McDonald"
__copyright__ = "Copyright 2011-2013, The BIOM Format Development Team"
__credits__ = ["Daniel McDonald", "Jai Ram Rideout", "Justin Kuczynski",
               "Greg Caporaso", "Jose Clemente", "Adam Robbins-Pianka",
               "Joshua Shorenstein", "Jose Antonio Navas Molina",
               "Jorge Cañardo Alastuey"]
__license__ = "BSD"
__url__ = "http://biom-format.org"
__maintainer__ = "Daniel McDonald"
__email__ = "daniel.mcdonald@colorado.edu"


class SupportTests(TestCase):
    def test_table_sparse_nparray(self):
        """beat the table sparsely to death"""
        # nparray test
        samp_ids = ['1', '2', '3', '4']
        obs_ids = ['a', 'b', 'c']
        nparray = np.array([[1, 2, 3, 4], [-1, 6, 7, 8], [9, 10, 11, 12]])
        data = nparray_to_sparse(
            np.array([[1, 2, 3, 4], [-1, 6, 7, 8], [9, 10, 11, 12]]))
        exp = Table(data, obs_ids, samp_ids)
        obs = Table(nparray, obs_ids, samp_ids)
        self.assertEqual(obs, exp)

    def test_table_sparse_list_nparray(self):
        """beat the table sparsely to death"""
        # list of nparray test
        samp_ids = ['1', '2', '3', '4']
        obs_ids = ['a', 'b', 'c']
        list_np = [np.array([1, 2, 3, 4]), np.array([5, 6, 7, 8]),
                   np.array([9, 10, 11, 12])]
        data = list_nparray_to_sparse(list_np)
        exp = Table(data, obs_ids, samp_ids)
        obs = Table(list_np, obs_ids, samp_ids)
        self.assertEqual(obs, exp)

    def test_table_sparse_dict(self):
        """beat the table sparsely to death"""
        # dict test
        samp_ids = range(24)
        obs_ids = range(101)
        dict_input = {(0, 0): 1, (0, 10): 5, (100, 23): -3}
        d_input = np.zeros((101, 24), dtype=float)
        d_input[0, 0] = 1
        d_input[0, 10] = 5
        d_input[100, 23] = -3
        data = nparray_to_sparse(d_input)
        exp = Table(data, obs_ids, samp_ids)
        obs = Table(dict_input, obs_ids, samp_ids)
        self.assertEqual(obs, exp)

    def test_table_sparse_list_dict(self):
        """beat the table sparsely to death"""
        # list of dict test
        samp_ids = range(11)
        obs_ids = range(3)
        ld_input = np.zeros((3, 11), dtype=float)
        ld_input[0, 5] = 10
        ld_input[0, 10] = 2
        ld_input[1, 1] = 15
        ld_input[2, 3] = 7
        data = nparray_to_sparse(ld_input)
        exp = Table(data, obs_ids, samp_ids)
        list_dict = [{(0, 5): 10, (10, 10): 2}, {(0, 1): 15}, {(0, 3): 7}]
        obs = Table(list_dict, obs_ids, samp_ids)
        self.assertEqual(obs, exp)

    def test_table_sparse_list_list(self):
        """beat the table sparsely to death"""
        # list list test
        samp_ids = range(3)
        obs_ids = range(2)
        exp_data = lil_matrix((2, 3))
        exp_data[0, 1] = 5
        exp_data[1, 2] = 10
        exp = Table(exp_data, obs_ids, samp_ids)
        input_ = [[0, 1, 5], [1, 2, 10]]
        obs = Table(input_, obs_ids, samp_ids)
        self.assertEqual(obs, exp)

    def test_table_exception(self):
        """Make sure a TableException can be raised"""
        def f():
            raise TableException
        self.assertRaises(TableException, f)

    def test_prefer_self(self):
        """prefer x"""
        exp = 1
        obs = prefer_self(1, 2)
        self.assertEqual(obs, exp)

        exp = 2
        obs = prefer_self(None, 2)
        self.assertEqual(obs, exp)

        exp = None
        obs = prefer_self(None, None)
        self.assertEqual(obs, exp)

    def test_index_list(self):
        """returns a dict for list lookups"""
        exp = {'a': 2, 'b': 0, 'c': 1}
        obs = index_list(['b', 'c', 'a'])
        self.assertEqual(obs, exp)


class TableTests(TestCase):

    def setUp(self):
        self.simple_derived = Table(
            np.array([[5, 6], [7, 8]]), [3, 4], [1, 2])
        self.vals = {(0, 0): 5, (0, 1): 6, (1, 0): 7, (1, 1): 8}
        self.st1 = Table(self.vals, ['1', '2'], ['a', 'b'])
        self.st2 = Table(self.vals, ['1', '2'], ['a', 'b'])
        self.vals3 = {(0, 0): 1, (0, 1): 2, (1, 0): 3, (1, 1): 4}
        self.vals4 = {(0, 0): 1, (0, 1): 2, (1, 0): 3, (1, 1): 4}
        self.st3 = Table(self.vals3, ['2', '3'], ['b', 'c'])
        self.st4 = Table(self.vals4, ['3', '4'],  ['c', 'd'])
        self.st_rich = Table(self.vals,
                             ['1', '2'], ['a', 'b'],
                             [{'taxonomy': ['k__a', 'p__b']},
                              {'taxonomy': ['k__a', 'p__c']}],
                             [{'barcode': 'aatt'}, {'barcode': 'ttgg'}],
                             )

        self.empty_st = Table([], [], [])

        self.vals5 = {(0, 1): 2, (1, 1): 4}
        self.st5 = Table(self.vals5, ['5', '6'], ['a', 'b'])

        self.vals6 = {(0, 0): 0, (0, 1): 0, (1, 0): 0, (1, 1): 0}
        self.st6 = Table(self.vals6, ['5', '6'], ['a', 'b'])

        self.vals7 = {(0, 0): 5, (0, 1): 7, (1, 0): 8, (1, 1): 0}
        self.st7 = Table(self.vals7, ['5', '6'], ['a', 'b'])

        self.single_sample_st = Table(
            np.array([[2.0], [0.0], [1.0]]), ['O1', 'O2', 'O3'],
            ['S1'])
        self.single_obs_st = Table(np.array([[2.0, 0.0, 1.0]]),
                                   ['01'], ['S1', 'S2', 'S3'])

        self.to_remove = []

        # 1 0 2
        # 3 0 4
        self.mat1 = Table(np.array([[1, 0, 2], [3, 0, 4]]),
                          ['o1', 'o2'], ['s1', 's2', 's3'])

        # Empty/null cases (i.e., 0x0, 0xn, nx0).
        ids = lambda X: ['x%d' % e for e in range(0, X)]
        self.null1 = Table(np.zeros((0, 0)), [], [])
        self.null2 = Table(
            np.zeros((0, 42), dtype=float), [], ids(42))
        self.null3 = Table(
            np.zeros((42, 0), dtype=float), ids(42), [])
        self.nulls = [self.null1, self.null2, self.null3]

        # 0 0
        # 0 0
        self.empty = Table(np.zeros((2, 2)), ids(2), ids(2))

        # 1 0 3
        h = np.array([[1.0, 0.0, 3.0]])
        self.row_vec = Table(h, ids(1), ids(3))

        # 1
        # 0
        # 3
        h = np.array([[1], [0], [3]])
        self.col_vec = Table(h, ids(3), ids(1))

        # 1x1
        h = np.array([[42]])
        self.single_ele = Table(h, ['b'], ['a'])

        # Explicit zeros.
        self.explicit_zeros = Table(np.array([[0, 0, 1], [1, 0, 0],
                                              [1, 0, 2]]),
                                    ['a', 'b', 'c'], ['x', 'y', 'z'])

    def tearDown(self):
        if self.to_remove:
            for f in self.to_remove:
                os.remove(f)

    def test_repr(self):
        """__repr__ method of biom.table.Table"""
        # table
        data = np.asarray([[0, 0, 0], [0, 1, 0], [0, 0, 0]])
        t = Table(data, ['a', 'b', 'c'], ['x', 'y', 'z'])
        self.assertEqual("3 x 3 <class 'biom.table.Table'> with 1 nonzero "
                         "entries (11% dense)", repr(t))

        # empty table
        data = np.asarray([[]])
        t = Table(data, [], [])
        self.assertEqual("0 x 0 <class 'biom.table.Table'> with 0 nonzero "
                         "entries (0% dense)", repr(t))

    def test_init_with_nparray(self):
        """to_sparse in constructor should be triggered"""
        data = np.array([[1, 2], [3, 4]])
        samp_ids = ['a', 'b']
        obs_ids = ['1', '2']
        exp = Table(data, obs_ids, samp_ids)
        obs = Table(data, obs_ids, samp_ids)
        self.assertEqual(obs, exp)

    def test_min_observation(self):
        exp = np.array([5, 7])
        obs = self.simple_derived.min('observation')
        npt.assert_equal(obs, exp)

    def test_min_sample(self):
        exp = np.array([5, 6])
        obs = self.simple_derived.min('sample')
        npt.assert_equal(obs, exp)

    def test_min_whole(self):
        exp = 5
        obs = self.simple_derived.min('whole')
        npt.assert_equal(obs, exp)

    def test_max_observation(self):
        exp = np.array([6, 8])
        obs = self.simple_derived.max('observation')
        npt.assert_equal(obs, exp)

    def test_max_sample(self):
        exp = np.array([7, 8])
        obs = self.simple_derived.max('sample')
        npt.assert_equal(obs, exp)

    def test_max_whole(self):
        exp = 8
        obs = self.simple_derived.max('whole')
        npt.assert_equal(obs, exp)

    @npt.dec.skipif(HAVE_H5PY is False, msg='H5PY is not installed')
    def test_from_hdf5(self):
        """Parse a hdf5 formatted BIOM table"""
        cwd = os.getcwd()
        if '/' in __file__:
            os.chdir(__file__.rsplit('/', 1)[0])
        t = Table.from_hdf5(h5py.File('test_data/test.biom'))
        os.chdir(cwd)

        npt.assert_equal(t.sample_ids, ('Sample1', 'Sample2', 'Sample3',
                                        'Sample4', 'Sample5', 'Sample6'))
        npt.assert_equal(t.observation_ids, ('GG_OTU_1', 'GG_OTU_2',
                                             'GG_OTU_3', 'GG_OTU_4',
                                             'GG_OTU_5'))
        exp_obs_md = ({u'taxonomy': [u'k__Bacteria',
                                     u'p__Proteobacteria',
                                     u'c__Gammaproteobacteria',
                                     u'o__Enterobacteriales',
                                     u'f__Enterobacteriaceae',
                                     u'g__Escherichia',
                                     u's__']},
                      {u'taxonomy': [u'k__Bacteria',
                                     u'p__Cyanobacteria',
                                     u'c__Nostocophycideae',
                                     u'o__Nostocales',
                                     u'f__Nostocaceae',
                                     u'g__Dolichospermum',
                                     u's__']},
                      {u'taxonomy': [u'k__Archaea',
                                     u'p__Euryarchaeota',
                                     u'c__Methanomicrobia',
                                     u'o__Methanosarcinales',
                                     u'f__Methanosarcinaceae',
                                     u'g__Methanosarcina',
                                     u's__']},
                      {u'taxonomy': [u'k__Bacteria',
                                     u'p__Firmicutes',
                                     u'c__Clostridia',
                                     u'o__Halanaerobiales',
                                     u'f__Halanaerobiaceae',
                                     u'g__Halanaerobium',
                                     u's__Halanaerobiumsaccharolyticum']},
                      {u'taxonomy': [u'k__Bacteria',
                                     u'p__Proteobacteria',
                                     u'c__Gammaproteobacteria',
                                     u'o__Enterobacteriales',
                                     u'f__Enterobacteriaceae',
                                     u'g__Escherichia',
                                     u's__']})
        self.assertEqual(t.observation_metadata, exp_obs_md)

        exp_samp_md = ({u'LinkerPrimerSequence': u'CATGCTGCCTCCCGTAGGAGT',
                        u'BarcodeSequence': u'CGCTTATCGAGA',
                        u'Description': u'human gut',
                        u'BODY_SITE': u'gut'},
                       {u'LinkerPrimerSequence': u'CATGCTGCCTCCCGTAGGAGT',
                        u'BarcodeSequence': u'CATACCAGTAGC',
                        u'Description': u'human gut',
                        u'BODY_SITE': u'gut'},
                       {u'LinkerPrimerSequence': u'CATGCTGCCTCCCGTAGGAGT',
                        u'BarcodeSequence': u'CTCTCTACCTGT',
                        u'Description': u'human gut',
                        u'BODY_SITE': u'gut'},
                       {u'LinkerPrimerSequence': u'CATGCTGCCTCCCGTAGGAGT',
                        u'BarcodeSequence': u'CTCTCGGCCTGT',
                        u'Description': u'human skin',
                        u'BODY_SITE': u'skin'},
                       {u'LinkerPrimerSequence': u'CATGCTGCCTCCCGTAGGAGT',
                        u'BarcodeSequence': u'CTCTCTACCAAT',
                        u'Description': u'human skin',
                        u'BODY_SITE': u'skin'},
                       {u'LinkerPrimerSequence': u'CATGCTGCCTCCCGTAGGAGT',
                        u'BarcodeSequence': u'CTAACTACCAAT',
                        u'Description': u'human skin',
                        u'BODY_SITE': u'skin'})
        self.assertEqual(t.sample_metadata, exp_samp_md)

        exp = [np.array([0., 0., 1., 0., 0., 0.]),
               np.array([5., 1., 0., 2., 3., 1.]),
               np.array([0., 0., 1., 4., 0., 2.]),
               np.array([2., 1., 1., 0., 0., 1.]),
               np.array([0., 1., 1., 0., 0., 0.])]
        npt.assert_equal(list(t.iter_data(axis="observation")), exp)

    @npt.dec.skipif(HAVE_H5PY is False, msg='H5PY is not installed')
    def test_from_hdf5_sample_subset(self):
        """Parse a sample subset of a hdf5 formatted BIOM table"""
        samples = ['Sample2', 'Sample4', 'Sample6']

        cwd = os.getcwd()
        if '/' in __file__:
            os.chdir(__file__.rsplit('/', 1)[0])
        t = Table.from_hdf5(h5py.File('test_data/test.biom'), ids=samples)
        os.chdir(cwd)

        npt.assert_equal(t.sample_ids, ['Sample2', 'Sample4', 'Sample6'])
        npt.assert_equal(t.observation_ids, ['GG_OTU_2', 'GG_OTU_3',
                                             'GG_OTU_4', 'GG_OTU_5'])
        exp_obs_md = ({u'taxonomy': [u'k__Bacteria',
                                     u'p__Cyanobacteria',
                                     u'c__Nostocophycideae',
                                     u'o__Nostocales',
                                     u'f__Nostocaceae',
                                     u'g__Dolichospermum',
                                     u's__']},
                      {u'taxonomy': [u'k__Archaea',
                                     u'p__Euryarchaeota',
                                     u'c__Methanomicrobia',
                                     u'o__Methanosarcinales',
                                     u'f__Methanosarcinaceae',
                                     u'g__Methanosarcina',
                                     u's__']},
                      {u'taxonomy': [u'k__Bacteria',
                                     u'p__Firmicutes',
                                     u'c__Clostridia',
                                     u'o__Halanaerobiales',
                                     u'f__Halanaerobiaceae',
                                     u'g__Halanaerobium',
                                     u's__Halanaerobiumsaccharolyticum']},
                      {u'taxonomy': [u'k__Bacteria',
                                     u'p__Proteobacteria',
                                     u'c__Gammaproteobacteria',
                                     u'o__Enterobacteriales',
                                     u'f__Enterobacteriaceae',
                                     u'g__Escherichia',
                                     u's__']})
        self.assertEqual(t.observation_metadata, exp_obs_md)

        exp_samp_md = ({u'LinkerPrimerSequence': u'CATGCTGCCTCCCGTAGGAGT',
                        u'BarcodeSequence': u'CATACCAGTAGC',
                        u'Description': u'human gut',
                        u'BODY_SITE': u'gut'},
                       {u'LinkerPrimerSequence': u'CATGCTGCCTCCCGTAGGAGT',
                        u'BarcodeSequence': u'CTCTCGGCCTGT',
                        u'Description': u'human skin',
                        u'BODY_SITE': u'skin'},
                       {u'LinkerPrimerSequence': u'CATGCTGCCTCCCGTAGGAGT',
                        u'BarcodeSequence': u'CTAACTACCAAT',
                        u'Description': u'human skin',
                        u'BODY_SITE': u'skin'})
        self.assertEqual(t.sample_metadata, exp_samp_md)

        exp = [np.array([1., 2., 1.]),
               np.array([0., 4., 2.]),
               np.array([1., 0., 1.]),
               np.array([1., 0., 0.])]
        npt.assert_equal(list(t.iter_data(axis='observation')), exp)

    @npt.dec.skipif(HAVE_H5PY is False, msg='H5PY is not installed')
    def test_from_hdf5_observation_subset(self):
        """Parse a observation subset of a hdf5 formatted BIOM table"""
        observations = ['GG_OTU_1', 'GG_OTU_3', 'GG_OTU_5']

        cwd = os.getcwd()
        if '/' in __file__:
            os.chdir(__file__.rsplit('/', 1)[0])
        t = Table.from_hdf5(h5py.File('test_data/test.biom'),
                            ids=observations, axis='observation')
        os.chdir(cwd)

        npt.assert_equal(t.sample_ids, ['Sample2', 'Sample3',
                                        'Sample4', 'Sample6'])
        npt.assert_equal(t.observation_ids, ['GG_OTU_1', 'GG_OTU_3',
                                             'GG_OTU_5'])
        exp_obs_md = ({u'taxonomy': [u'k__Bacteria',
                                     u'p__Proteobacteria',
                                     u'c__Gammaproteobacteria',
                                     u'o__Enterobacteriales',
                                     u'f__Enterobacteriaceae',
                                     u'g__Escherichia',
                                     u's__']},
                      {u'taxonomy': [u'k__Archaea',
                                     u'p__Euryarchaeota',
                                     u'c__Methanomicrobia',
                                     u'o__Methanosarcinales',
                                     u'f__Methanosarcinaceae',
                                     u'g__Methanosarcina',
                                     u's__']},
                      {u'taxonomy': [u'k__Bacteria',
                                     u'p__Proteobacteria',
                                     u'c__Gammaproteobacteria',
                                     u'o__Enterobacteriales',
                                     u'f__Enterobacteriaceae',
                                     u'g__Escherichia',
                                     u's__']})
        self.assertEqual(t.observation_metadata, exp_obs_md)

        exp_samp_md = ({u'LinkerPrimerSequence': u'CATGCTGCCTCCCGTAGGAGT',
                        u'BarcodeSequence': u'CATACCAGTAGC',
                        u'Description': u'human gut',
                        u'BODY_SITE': u'gut'},
                       {u'LinkerPrimerSequence': u'CATGCTGCCTCCCGTAGGAGT',
                        u'BarcodeSequence': u'CTCTCTACCTGT',
                        u'Description': u'human gut',
                        u'BODY_SITE': u'gut'},
                       {u'LinkerPrimerSequence': u'CATGCTGCCTCCCGTAGGAGT',
                        u'BarcodeSequence': u'CTCTCGGCCTGT',
                        u'Description': u'human skin',
                        u'BODY_SITE': u'skin'},
                       {u'LinkerPrimerSequence': u'CATGCTGCCTCCCGTAGGAGT',
                        u'BarcodeSequence': u'CTAACTACCAAT',
                        u'Description': u'human skin',
                        u'BODY_SITE': u'skin'})
        self.assertEqual(t.sample_metadata, exp_samp_md)

        exp = [np.array([0., 1., 0., 0.]),
               np.array([0., 1., 4., 2.]),
               np.array([1., 1., 0., 0.])]
        npt.assert_equal(list(t.iter_data(axis='observation')), exp)

    @npt.dec.skipif(HAVE_H5PY is False, msg='H5PY is not installed')
    def test_from_hdf5_subset_error(self):
        """hdf5 biom table parse throws error with invalid parameters"""
        cwd = os.getcwd()
        if '/' in __file__:
            os.chdir(__file__.rsplit('/', 1)[0])

        # Raises an error if not all the given samples are in the OTU table
        with self.assertRaises(ValueError):
            Table.from_hdf5(h5py.File('test_data/test.biom'),
                            ids=['Sample2', 'DoesNotExist', 'Sample6'])

        # Raises an error if not all the given observation are in the OTU table
        with self.assertRaises(ValueError):
            Table.from_hdf5(h5py.File('test_data/test.biom'),
                            ids=['GG_OTU_1', 'DoesNotExist'],
                            axis='observation')
        os.chdir(cwd)

    @npt.dec.skipif(HAVE_H5PY is False, msg='H5PY is not installed')
    def test_to_hdf5(self):
        """Write a file"""
        fname = mktemp()
        self.to_remove.append(fname)
        h5 = h5py.File(fname, 'w')
        self.st_rich.to_hdf5(h5, 'tests')
        h5.close()

        h5 = h5py.File(fname, 'r')
        self.assertIn('observation', h5)
        self.assertIn('sample', h5)
        self.assertEqual(sorted(h5.attrs.keys()), sorted(['id', 'type',
                                                          'format-url',
                                                          'format-version',
                                                          'generated-by',
                                                          'creation-date',
                                                          'shape', 'nnz']))

        obs = Table.from_hdf5(h5)
        self.assertEqual(obs, self.st_rich)

    def test_from_tsv(self):
        tab1_fh = StringIO(otu_table1)
        sparse_rich = Table.from_tsv(tab1_fh, None, None,
                                     OBS_META_TYPES['naive'])
        self.assertEqual(sorted(sparse_rich.sample_ids),
                         sorted(['Fing', 'Key', 'NA']))
        self.assertEqual(sorted(sparse_rich.observation_ids),
                         map(str, [0, 1, 3, 4, 7]))
        for i, obs_id in enumerate(sparse_rich.observation_ids):
            if obs_id == '0':
                self.assertEqual(sparse_rich.observation_metadata[i],
                                 {'Consensus Lineage': 'Bacteria; '
                                  'Actinobacteria; Actinobacteridae; '
                                  'Propionibacterineae; '
                                  'Propionibacterium'})
            elif obs_id == '1':
                self.assertEqual(sparse_rich.observation_metadata[i],
                                 {'Consensus Lineage': 'Bacteria; Firmicutes; '
                                  'Alicyclobacillaceae; Bacilli; '
                                  'Lactobacillales; Lactobacillales; '
                                  'Streptococcaceae; '
                                  'Streptococcus'})
            elif obs_id == '7':
                self.assertEqual(sparse_rich.observation_metadata[i],
                                 {'Consensus Lineage': 'Bacteria; '
                                  'Actinobacteria; Actinobacteridae; '
                                  'Gordoniaceae; '
                                  'Corynebacteriaceae'})
            elif obs_id in ['3', '4']:
                pass  # got lazy
            else:
                raise RuntimeError('obs_id incorrect?')

        self.assertEquals(sparse_rich.sample_metadata, None)

        for i, obs_id in enumerate(sparse_rich.observation_ids):
            for j, sample_id in enumerate(sparse_rich.sample_ids):
                if obs_id == '1' and sample_id == 'Key':
                    # should test some abundance data
                    self.assertEqual(True, True)

    def test_from_tsv_dense(self):
        tab1_fh = StringIO(otu_table1)
        sparse_rich = Table.from_tsv(tab1_fh.readlines(), None, None,
                                     OBS_META_TYPES['naive'])
        self.assertEqual(sorted(sparse_rich.sample_ids),
                         sorted(['Fing', 'Key', 'NA']))
        self.assertEqual(sorted(sparse_rich.observation_ids),
                         map(str, [0, 1, 3, 4, 7]))
        for i, obs_id in enumerate(sparse_rich.observation_ids):
            if obs_id == '0':
                self.assertEqual(sparse_rich.observation_metadata[i],
                                 {'Consensus Lineage': 'Bacteria; '
                                  'Actinobacteria; Actinobacteridae; '
                                  'Propionibacterineae; '
                                  'Propionibacterium'})
            elif obs_id == '1':
                self.assertEqual(sparse_rich.observation_metadata[i],
                                 {'Consensus Lineage': 'Bacteria; Firmicutes; '
                                  'Alicyclobacillaceae; Bacilli; '
                                  'Lactobacillales; Lactobacillales; '
                                  'Streptococcaceae; '
                                  'Streptococcus'})
            elif obs_id == '7':
                self.assertEqual(sparse_rich.observation_metadata[i],
                                 {'Consensus Lineage': 'Bacteria; '
                                  'Actinobacteria; Actinobacteridae; '
                                  'Gordoniaceae; '
                                  'Corynebacteriaceae'})
            elif obs_id in ['3', '4']:
                pass  # got lazy
            else:
                raise RuntimeError('obs_id incorrect?')

        self.assertEquals(sparse_rich.sample_metadata, None)

        for i, obs_id in enumerate(sparse_rich.observation_ids):
            for j, sample_id in enumerate(sparse_rich.sample_ids):
                if obs_id == '1' and sample_id == 'Key':
                    self.assertEqual(True, True)
                    # should test some abundance data

    def test_to_tsv(self):
        """Print out self in a delimited form"""
        exp = '\n'.join(
            ["# Constructed from biom file",
             "#OTU ID\ta\tb",
             "1\t5.0\t6.0",
             "2\t7.0\t8.0"])
        obs = self.st1.delimited_self()
        self.assertEqual(obs, exp)

        # Test observation_column_name.
        exp = '\n'.join(
            ["# Constructed from biom file",
             "Taxon\ta\tb",
             "1\t5.0\t6.0",
             "2\t7.0\t8.0"])
        obs = self.st1.to_tsv(observation_column_name='Taxon')
        self.assertEqual(obs, exp)

    def test_metadata_invalid_input(self):
        """Correctly handles invalid input."""
        with self.assertRaises(UnknownAxisError):
            self.simple_derived.metadata(1, 'brofist')

    def test_metadata_sample(self):
        """returns the sample metadata"""
        self.assertEqual({'barcode': 'aatt'},
                         self.st_rich.metadata('a', 'sample'))
        self.assertEqual({'barcode': 'ttgg'},
                         self.st_rich.metadata('b', 'sample'))

        with self.assertRaises(UnknownIDError):
            self.st_rich.metadata(3, 'sample')

    def test_metadata_observation(self):
        """returns the observation metadata"""
        self.assertEqual({'taxonomy': ['k__a', 'p__b']},
                         self.st_rich.metadata('1', 'observation'))
        self.assertEqual({'taxonomy': ['k__a', 'p__c']},
                         self.st_rich.metadata('2', 'observation'))

        with self.assertRaises(UnknownIDError):
            self.simple_derived.metadata('3', 'observation')

    def test_index_invalid_input(self):
        """Correctly handles invalid input."""
        with self.assertRaises(UnknownAxisError):
            self.simple_derived.index(1, 'brofist')

    def test_index_sample(self):
        """returns the sample index"""
        self.assertEqual(0, self.simple_derived.index(1, 'sample'))
        self.assertEqual(1, self.simple_derived.index(2, 'sample'))

        with self.assertRaises(UnknownIDError):
            self.simple_derived.index(3, 'sample')

    def test_index_observation(self):
        """returns the observation index"""
        self.assertEqual(0, self.simple_derived.index(3, 'observation'))
        self.assertEqual(1, self.simple_derived.index(4, 'observation'))

        with self.assertRaises(UnknownIDError):
            self.simple_derived.index(5, 'observation')

    def test_index_ids(self):
        """Index all the ids!!!"""
        exp_samp = {1: 0, 2: 1}
        exp_obs = {3: 0, 4: 1}
        self.assertEqual(self.simple_derived._sample_index, exp_samp)
        self.assertEqual(self.simple_derived._obs_index, exp_obs)

    def test_sample_exists(self):
        """Verify samples exist!"""
        self.assertTrue(self.simple_derived.exists(1))
        self.assertTrue(self.simple_derived.exists(2))
        self.assertFalse(self.simple_derived.exists(3))

    def test_observation_exists(self):
        """Verify observation exist!"""
        self.assertTrue(self.simple_derived.exists(3, axis="observation"))
        self.assertTrue(self.simple_derived.exists(4, axis="observation"))
        self.assertFalse(self.simple_derived.exists(2, axis="observation"))

    def test_exists_invalid_axis(self):
        """Verify ValueError raised!"""
        with self.assertRaises(UnknownAxisError):
            self.simple_derived.exists(3, axis="fooz")

    def test_union_id_order(self):
        """Combine unique ids, union"""
        a = [1, 2, 3, 4]
        b = [3, 4, 5, 6, 0, 'a']
        exp = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 0: 6, 'a': 7}
        obs = self.st1._union_id_order(a, b)
        self.assertEqual(obs, exp)

    def test_intersect_id_order(self):
        """Combine ids, intersection"""
        a = [1, 2, 3, 4]
        b = [3, 4, 5, 6, 0, 'a']
        exp = {3: 0, 4: 1}
        obs = self.st1._intersect_id_order(a, b)
        self.assertEqual(obs, exp)

    def test_verify_metadata(self):
        """Make sure the metadata is sane (including obs/sample ids)"""
        obs_ids = [1, 2, 3]
        obs_md = [{'a': 0}, {'b': 0}, {'c': 0}]
        samp_ids = [4, 5, 6, 7]
        samp_md = [{'d': 0}, {'e': 0}, {'f': 0}, {'g': 0}]
        d = np.array([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]])
        Table(d, obs_ids, samp_ids, obs_md, samp_md)
        # test is that no exception is raised

        obs_ids = [1, 2]
        self.assertRaises(TableException, Table, d, samp_ids, obs_ids, samp_md,
                          obs_md)

        obs_ids = [1, 2, 3]
        samp_ids = [4, 5, 6]
        self.assertRaises(TableException, Table, d, samp_ids, obs_ids, samp_md,
                          obs_md)

        samp_ids = [4, 5, 6, 7]
        obs_md = ['a', 'b']
        self.assertRaises(TableException, Table, d, samp_ids, obs_ids, samp_md,
                          obs_md)

        obs_md = ['a', 'b', 'c']
        samp_md = ['d', 'e', 'f']
        self.assertRaises(TableException, Table, d, samp_ids, obs_ids, samp_md,
                          obs_md)

        obs_md = None
        samp_md = None

        # test is that no exception is raised
        Table(d, obs_ids, samp_ids, obs_md, samp_md)

        # do not allow duplicate ids
        obs_ids = [1, 1, 3]
        samp_ids = [4, 5, 6]
        self.assertRaises(TableException, Table, d, samp_ids, obs_ids, samp_md,
                          obs_md)

        obs_ids = [1, 2, 3]
        samp_ids = [4, 4, 6]
        self.assertRaises(TableException, Table, d, samp_ids, obs_ids, samp_md,
                          obs_md)

    def test_cast_metadata(self):
        """Cast metadata objects to defaultdict to support default values"""
        obs_ids = [1, 2, 3]
        obs_md = [{'a': 1}, {'b': 2}, {'c': 3}]
        samp_ids = [4, 5, 6, 7]
        samp_md = [{'d': 1}, None, {'f': 3}, {'g': 4}]
        d = np.array([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]])
        t = Table(d, obs_ids, samp_ids, obs_md, samp_md)

        self.assertEqual(t.sample_metadata[0]['non existent key'], None)
        self.assertEqual(t.sample_metadata[1]['non existent key'], None)
        self.assertEqual(t.sample_metadata[2]['non existent key'], None)
        self.assertEqual(t.sample_metadata[3]['non existent key'], None)
        self.assertEqual(t.observation_metadata[0]['non existent key'], None)
        self.assertEqual(t.observation_metadata[1]['non existent key'], None)
        self.assertEqual(t.observation_metadata[2]['non existent key'], None)

    def test_add_metadata_two_entries(self):
        """ add_metadata functions with more than one md entry """
        obs_ids = [1, 2, 3]
        obs_md = {1: {'taxonomy': ['A', 'B'], 'other': 'h1'},
                  2: {'taxonomy': ['B', 'C'], 'other': 'h2'},
                  3: {'taxonomy': ['E', 'D', 'F'], 'other': 'h3'}}
        samp_ids = [4, 5, 6, 7]
        samp_md = [{'d': 0}, {'e': 0}, {'f': 0}, {'g': 0}]
        d = np.array([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]])
        t = Table(d, obs_ids, samp_ids, observation_metadata=None,
                  sample_metadata=samp_md)
        t.add_metadata(obs_md, axis='observation')
        self.assertEqual(t.observation_metadata[0]['taxonomy'], ['A', 'B'])
        self.assertEqual(t.observation_metadata[1]['taxonomy'], ['B', 'C'])
        self.assertEqual(t.observation_metadata[2]['taxonomy'],
                         ['E', 'D', 'F'])
        self.assertEqual(t.observation_metadata[0]['other'], 'h1')
        self.assertEqual(t.observation_metadata[1]['other'], 'h2')
        self.assertEqual(t.observation_metadata[2]['other'], 'h3')

        samp_md = {4: {'x': 'y', 'foo': 'bar'}, 5: {'x': 'z'}}
        t.add_metadata(samp_md, axis='sample')
        self.assertEqual(t.sample_metadata[0]['x'], 'y')
        self.assertEqual(t.sample_metadata[0]['foo'], 'bar')
        self.assertEqual(t.sample_metadata[1]['x'], 'z')

    def test_add_metadata_one_w_existing_metadata(self):
        """ add_sample_metadata functions with existing metadata """
        obs_ids = [1, 2, 3]
        obs_md = [{'a': 0}, {'b': 0}, {'c': 0}]
        samp_ids = [4, 5, 6, 7]
        samp_md = [{'Treatment': 'Control'},
                   {'Treatment': 'Fasting'},
                   {'Treatment': 'Fasting'},
                   {'Treatment': 'Control'}]
        d = np.array([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]])
        t = Table(d, obs_ids, samp_ids, observation_metadata=obs_md,
                  sample_metadata=samp_md)
        self.assertEqual(t.sample_metadata[0]['Treatment'], 'Control')
        self.assertEqual(t.sample_metadata[1]['Treatment'], 'Fasting')
        self.assertEqual(t.sample_metadata[2]['Treatment'], 'Fasting')
        self.assertEqual(t.sample_metadata[3]['Treatment'], 'Control')

        samp_md = {4: {'barcode': 'TTTT'},
                   6: {'barcode': 'AAAA'},
                   5: {'barcode': 'GGGG'},
                   7: {'barcode': 'CCCC'},
                   10: {'ignore': 'me'}}
        t.add_metadata(samp_md, 'sample')
        self.assertEqual(t.sample_metadata[0]['Treatment'], 'Control')
        self.assertEqual(t.sample_metadata[1]['Treatment'], 'Fasting')
        self.assertEqual(t.sample_metadata[2]['Treatment'], 'Fasting')
        self.assertEqual(t.sample_metadata[3]['Treatment'], 'Control')
        self.assertEqual(t.sample_metadata[0]['barcode'], 'TTTT')
        self.assertEqual(t.sample_metadata[1]['barcode'], 'GGGG')
        self.assertEqual(t.sample_metadata[2]['barcode'], 'AAAA')
        self.assertEqual(t.sample_metadata[3]['barcode'], 'CCCC')

        obs_md = {1: {'foo': 'bar'}}
        t.add_metadata(obs_md, axis='observation')
        self.assertEqual(t.observation_metadata[0]['foo'], 'bar')
        self.assertEqual(t.observation_metadata[1]['foo'], None)
        self.assertEqual(t.observation_metadata[2]['foo'], None)

    def test_add_metadata_one_entry(self):
        """ add_sample_metadata functions with single md entry """
        obs_ids = [1, 2, 3]
        obs_md = [{'a': 0}, {'b': 0}, {'c': 0}]
        samp_ids = [4, 5, 6, 7]
        samp_md = {4: {'Treatment': 'Control'},
                   5: {'Treatment': 'Fasting'},
                   6: {'Treatment': 'Fasting'},
                   7: {'Treatment': 'Control'}}
        d = np.array([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]])
        t = Table(d, obs_ids, samp_ids, obs_md=obs_md, samp_md=None)
        t.add_metadata(samp_md, axis='sample')
        self.assertEqual(t.sample_metadata[0]['Treatment'], 'Control')
        self.assertEqual(t.sample_metadata[1]['Treatment'], 'Fasting')
        self.assertEqual(t.sample_metadata[2]['Treatment'], 'Fasting')
        self.assertEqual(t.sample_metadata[3]['Treatment'], 'Control')

    def test_add_sample_metadata_two_entries(self):
        """ add_sample_metadata functions with more than one md entry """
        obs_ids = [1, 2, 3]
        obs_md = [{'a': 0}, {'b': 0}, {'c': 0}]
        samp_ids = [4, 5, 6, 7]
        samp_md = {4: {'Treatment': 'Control', 'D': ['A', 'A']},
                   5: {'Treatment': 'Fasting', 'D': ['A', 'B']},
                   6: {'Treatment': 'Fasting', 'D': ['A', 'C']},
                   7: {'Treatment': 'Control', 'D': ['A', 'D']}}
        d = np.array([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]])
        t = Table(d, obs_ids, samp_ids, obs_md=obs_md, samp_md=None)
        t.add_metadata(samp_md, axis='sample')
        self.assertEqual(t.sample_metadata[0]['Treatment'], 'Control')
        self.assertEqual(t.sample_metadata[1]['Treatment'], 'Fasting')
        self.assertEqual(t.sample_metadata[2]['Treatment'], 'Fasting')
        self.assertEqual(t.sample_metadata[3]['Treatment'], 'Control')
        self.assertEqual(t.sample_metadata[0]['D'], ['A', 'A'])
        self.assertEqual(t.sample_metadata[1]['D'], ['A', 'B'])
        self.assertEqual(t.sample_metadata[2]['D'], ['A', 'C'])
        self.assertEqual(t.sample_metadata[3]['D'], ['A', 'D'])

    def test_get_value_by_ids(self):
        """Return the value located in the matrix by the ids"""
        t1 = Table(np.array([[5, 6], [7, 8]]), [3, 4], [1, 2])
        t2 = Table(np.array([[5, 6], [7, 8]]),
                   ['c', 'd'], ['a', 'b'])

        self.assertEqual(5, t1.get_value_by_ids(3, 1))
        self.assertEqual(6, t1.get_value_by_ids(3, 2))
        self.assertEqual(7, t1.get_value_by_ids(4, 1))
        self.assertEqual(8, t1.get_value_by_ids(4, 2))
        self.assertEqual(5, t2.get_value_by_ids('c', 'a'))
        self.assertEqual(6, t2.get_value_by_ids('c', 'b'))
        self.assertEqual(7, t2.get_value_by_ids('d', 'a'))
        self.assertEqual(8, t2.get_value_by_ids('d', 'b'))

        self.assertRaises(UnknownIDError, t1.get_value_by_ids, 'a', 1)
        self.assertRaises(UnknownIDError, t2.get_value_by_ids, 0, 0)

    def test_getitem(self):
        """getitem should work as expeceted"""
        self.assertEqual(self.simple_derived[0, 0], 5)
        self.assertEqual(self.simple_derived[1, 0], 7)
        self.assertEqual(self.simple_derived[0, 1], 6)
        self.assertEqual(self.simple_derived[1, 1], 8)
        self.assertRaises(IndexError, self.simple_derived.__getitem__, [1, 2])

    def test_is_empty(self):
        """returns true if empty"""
        self.assertTrue(Table(np.array([]), [], []).is_empty())
        self.assertFalse(self.simple_derived.is_empty())
        self.assertTrue(Table(np.array([[]]), [], []).is_empty())

    def test_convert_vector_to_dense(self):
        """Properly converts ScipySparseMat vectors to dense numpy repr."""
        input_row = lil_matrix((1, 3))
        input_row[(0, 0)] = 1
        input_row[(0, 2)] = 3
        exp = np.array([1, 0, 3])
        obs = self.row_vec._to_dense(input_row)
        npt.assert_array_equal(obs, exp)

        input_row = lil_matrix((3, 1))
        input_row[(0, 0)] = 1
        input_row[(2, 0)] = 3
        exp = np.array([1, 0, 3])
        obs = self.row_vec._to_dense(input_row)
        npt.assert_array_equal(obs, exp)

        input_row = lil_matrix((1, 1))
        input_row[(0, 0)] = 42
        exp = np.array([42])
        obs = self.single_ele._to_dense(input_row)
        npt.assert_array_equal(obs, exp)

    def test_shape(self):
        """What kind of shape are you in?"""
        npt.assert_array_equal(self.null1.shape, (0, 0))
        npt.assert_array_equal(self.null2.shape, (0, 42))
        npt.assert_array_equal(self.null3.shape, (42, 0))
        npt.assert_array_equal(self.mat1.shape, (2, 3))
        npt.assert_array_equal(self.empty.shape, (2, 2))
        npt.assert_array_equal(self.row_vec.shape, (1, 3))
        npt.assert_array_equal(self.col_vec.shape, (3, 1))
        npt.assert_array_equal(self.single_ele.shape, (1, 1))

    def test_dtype(self):
        """What's your type?"""
        for m in self.nulls:
            self.assertEqual(m.dtype, None)

        self.assertEqual(self.empty.dtype, float)
        self.assertEqual(self.row_vec.dtype, float)

    def test_nnz(self):
        """What is your NNZ?"""
        for m in self.nulls:
            self.assertEqual(m.nnz, 0)

        self.assertEqual(self.empty.nnz, 0)
        self.assertEqual(self.single_ele.nnz, 1)
        self.assertEqual(self.mat1.nnz, 4)
        self.assertEqual(self.explicit_zeros.nnz, 4)

    def test_get_row(self):
        """Test grabbing a row from the matrix."""
        # note that we only have to test the first two elements don't have that
        # row according to the underlying scipy sparse matrix
        for i in range(0, 2):
            with self.assertRaises(IndexError):
                self.nulls[i]._get_row(0)

        exp = lil_matrix((1, 3))
        exp[(0, 0)] = 1
        exp[(0, 2)] = 2

        obs = self.mat1._get_row(0)
        self.assertEqual((obs != exp).sum(), 0)

    def test_get_col(self):
        """Test grabbing a column from the matrix."""
        # note that we only have to test the first and last element, these
        # don't have that column according to the underlying scipy sparse
        # matrix
        for i in [0, 2]:
            with self.assertRaises(IndexError):
                self.nulls[i]._get_col(0)

        exp = lil_matrix((2, 1))
        exp[(0, 0)] = 1
        exp[(1, 0)] = 3

        obs = self.mat1._get_col(0)
        self.assertEqual((obs != exp).sum(), 0)

    def test_eq(self):
        """Test whether two matrices are equal."""
        # Empty/null cases (i.e., 0x0, 0xn, nx0).
        ids = lambda X: ['x%d' % e for e in range(0, X)]
        a = Table(np.zeros((0, 0)), [], [])
        b = Table(np.zeros((0, 42), dtype=float), [], ids(42))
        c = Table(np.zeros((42, 0), dtype=float), ids(42), [])
        d = Table(np.zeros((2, 2)), ids(2), ids(2))

        self.assertTrue(self.null1 == a)
        self.assertTrue(self.null2 == b)
        self.assertTrue(self.null3 == c)
        self.assertTrue(self.empty == d)

        mat2 = Table(np.array([[1, 0, 2], [3, 0, 4]]),
                     ['o1', 'o2'], ['s1', 's2', 's3'])
        self.assertTrue(self.mat1 == mat2)

        mat2._data = mat2._data.tolil()
        self.assertNotEqual(self.mat1._data.format, mat2._data.format)
        self.assertEqual(self.mat1, mat2)

        # Equality works in both directions.
        self.assertEqual(mat2, self.mat1)

    def test_ne(self):
        """Test whether two matrices are not equal."""
        # Wrong type.
        self.assertTrue(self.null1 != np.array([]))

        # Wrong shape.
        ids = lambda X: ['x%d' % e for e in range(0, X)]
        d = Table(np.ones((1, 1)), ids(1), ids(1))
        self.assertTrue(self.null2 != self.null3)
        self.assertTrue(self.empty != d)

        # Wrong dtype.
        d = Table(np.zeros((2, 2)), ids(2), ids(2), type=float)
        self.assertTrue(self.empty != d)

        # Wrong size.
        wrong_size = Table(np.zeros((2, 2)), ids(2), ids(2))
        self.assertTrue(self.empty == wrong_size)
        wrong_size = Table(np.ones((1, 1)), ['c'], ['a'])
        self.assertTrue(self.empty != wrong_size)

        # Wrong size.
        wrong_data = self.mat1.copy()
        self.assertTrue(self.mat1 == wrong_data)
        wrong_data = Table(np.array([[42, 0, 2], [3, 0, 4]]),
                           ['o1', 'o2'], ['s1', 's2', 's3'])
        self.assertTrue(self.mat1 != wrong_data)
        self.assertTrue(wrong_data != self.mat1)

    def test_getitem_2(self):
        """Test getting an element from the matrix."""
        for m in self.nulls:
            with self.assertRaises(IndexError):
                m[0, 0]

        with self.assertRaises(IndexError):
            self.empty[0]

        with self.assertRaises(IndexError):
            self.empty[:, :]

        with self.assertRaises(IndexError):
            self.empty[0:1, 0]

        with self.assertRaises(IndexError):
            self.empty[0, 0:1]

        exp = lil_matrix((2, 1))
        obs = self.empty[:, 0]
        self.assertEqual((obs != exp).sum(), 0)

        # Extracting a column.
        obs = self.mat1[:, 2]
        self.assertEqual((obs != self.mat1._get_col(2)).sum(), 0)

        # Extracting a row.
        obs = self.mat1[1, :]
        self.assertEqual((obs != self.mat1._get_row(1)).sum(), 0)

        # Extracting a single element.
        self.assertEqual(self.empty[1, 1], 0)
        self.assertEqual(self.mat1[1, 2], 4)

        with self.assertRaises(IndexError):
            self.mat1[1, 3]


class SparseTableTests(TestCase):

    def setUp(self):
        self.vals = {(0, 0): 5, (0, 1): 6, (1, 0): 7, (1, 1): 8}
        self.st1 = Table(self.vals,
                         ['1', '2'], ['a', 'b'])
        self.st2 = Table(self.vals,
                         ['1', '2'], ['a', 'b'])
        self.vals3 = {(0, 0): 1, (0, 1): 2, (1, 0): 3, (1, 1): 4}
        self.vals4 = {(0, 0): 1, (0, 1): 2, (1, 0): 3, (1, 1): 4}
        self.st3 = Table(self.vals3, ['2', '3'], ['b', 'c'])
        self.st4 = Table(self.vals4, ['3', '4'], ['c', 'd'])
        self._to_dict_f = lambda x: sorted(x.items())
        self.st_rich = Table(self.vals,
                             ['1', '2'], ['a', 'b'],
                             [{'taxonomy': ['k__a', 'p__b']},
                              {'taxonomy': ['k__a', 'p__c']}],
                             [{'barcode': 'aatt'}, {'barcode': 'ttgg'}])

        self.empty_st = Table([], [], [])

        self.vals5 = {(0, 1): 2, (1, 1): 4}
        self.st5 = Table(self.vals5, ['5', '6'], ['a', 'b'])

        self.vals6 = {(0, 0): 0, (0, 1): 0, (1, 0): 0, (1, 1): 0}
        self.st6 = Table(self.vals6, ['5', '6'], ['a', 'b'])

        self.vals7 = {(0, 0): 5, (0, 1): 7, (1, 0): 8, (1, 1): 0}
        self.st7 = Table(self.vals7, ['5', '6'], ['a', 'b'])

        self.single_sample_st = Table(
            np.array([[2.0], [0.0], [1.0]]),
            ['O1', 'O2', 'O3'], ['S1'])
        self.single_obs_st = Table(np.array([[2.0, 0.0, 1.0]]),
                                   ['01'], ['S1', 'S2', 'S3'])

    def test_sum(self):
        """Test of sum!"""
        self.assertEqual(self.st1.sum('whole'), 26)
        npt.assert_equal(self.st1.sum('sample'), np.array([12, 14]))
        npt.assert_equal(self.st1.sum('observation'), np.array([11, 15]))

        exp = np.array([3.0])
        obs = self.single_sample_st.sum('sample')
        self.assertEqual(obs, exp)

        exp = np.array([3.0])
        obs = self.single_obs_st.sum('observation')
        self.assertEqual(obs, exp)

    def test_reduce(self):
        """Reduce method"""
        f = lambda x, y: x * 2 + y
        npt.assert_equal(self.st1.reduce(f, 'sample'), np.array([17, 20]))
        npt.assert_equal(self.st1.reduce(f, 'observation'), np.array([16, 22]))

    def test_transpose(self):
        """Should transpose a sparse table"""
        obs = self.st1.transpose()

        npt.assert_equal(obs.sample_ids, self.st1.observation_ids)
        npt.assert_equal(obs.observation_ids, self.st1.sample_ids)
        npt.assert_equal(obs.data('1', 'sample'),
                         self.st1.data('1', 'observation'))
        npt.assert_equal(obs.data('2', 'sample'),
                         self.st1.data('2', 'observation'))
        self.assertEqual(obs.transpose(), self.st1)

        obs = self.st_rich.transpose()

        npt.assert_equal(obs.sample_ids, self.st_rich.observation_ids)
        npt.assert_equal(obs.observation_ids, self.st_rich.sample_ids)
        self.assertEqual(obs.sample_metadata,
                         self.st_rich.observation_metadata)
        self.assertEqual(obs.observation_metadata,
                         self.st_rich.sample_metadata)
        npt.assert_equal(obs.data('1', 'sample'),
                         self.st_rich.data('1', 'observation'))
        npt.assert_equal(obs.data('2', 'sample'),
                         self.st_rich.data('2', 'observation'))
        self.assertEqual(obs.transpose(), self.st_rich)

    def test_sort_order(self):
        """sorts tables by arbitrary order"""
        # sort by observations arbitrary order
        vals = {(0, 0): 7, (0, 1): 8, (1, 0): 5, (1, 1): 6}
        exp = Table(vals, ['2', '1'], ['a', 'b'])
        obs = self.st1.sort_order(['2', '1'], axis='observation')
        self.assertEqual(obs, exp)
        # sort by observations arbitrary order
        vals = {(0, 0): 6, (0, 1): 5,
                (1, 0): 8, (1, 1): 7}
        exp = Table(vals, ['1', '2'], ['b', 'a'])
        obs = self.st1.sort_order(['b', 'a'], axis='sample')
        self.assertEqual(obs, exp)
        # raises an error if a invalid axis is passed
        with self.assertRaises(UnknownAxisError):
            self.st1.sort_order(['b', 'a'], axis='foo')

    def test_sort(self):
        """table sorted by a function and provided axis"""
        # sort by samples by a function
        sort_f = sorted
        data_in = nparray_to_sparse(
            np.array([[1, 2, 3, 8], [4, 5, 6, 9], [7, 8, 9, 11]]))
        t = Table(data_in, [2, 1, 3], ['c', 'a', 'b', 'd'])
        exp_data = nparray_to_sparse(
            np.array([[2, 3, 1, 8], [5, 6, 4, 9], [8, 9, 7, 11]]))
        exp = Table(exp_data, [2, 1, 3], ['a', 'b', 'c', 'd'])
        obs = t.sort(sort_f=sort_f)
        self.assertEqual(obs, exp)
        # sort by observation ids by a function
        sort_f = sorted
        data_in = nparray_to_sparse(
            np.array([[1, 2, 3, 8], [4, 5, 6, 9], [7, 8, 9, 11]]), float)
        t = Table(data_in, [2, 1, 3], ['c', 'a', 'b', 'd'])
        exp_data = nparray_to_sparse(
            np.array([[4, 5, 6, 9], [1, 2, 3, 8], [7, 8, 9, 11]]), float)
        exp = Table(exp_data, [1, 2, 3], ['c', 'a', 'b', 'd'])
        obs = t.sort(sort_f=sort_f, axis='observation')
        self.assertEqual(obs, exp)
        # raises an error if a invalid axis is passed
        with self.assertRaises(UnknownAxisError):
            t.sort(axis='foo')

    def test_eq(self):
        """sparse equality"""
        self.assertTrue(self.st1 == self.st2)
        self.st1.observation_ids = np.array(["1", "2", "3"], dtype=object)
        self.assertFalse(self.st1 == self.st2)

        self.st1.observation_ids = self.st2.observation_ids
        self.st1._data = nparray_to_sparse(np.array([[1, 2], [10, 20]]))
        self.assertFalse(self.st1 == self.st2)

    def test_data_equality(self):
        """check equality between tables"""
        self.assertTrue(self.st1._data_equality(self.st2._data))
        self.assertTrue(self.st1._data_equality(self.st1._data))
        self.assertFalse(self.st1._data_equality(self.st3._data))

    def test_nonzero(self):
        """Return a list of nonzero positions"""
        data = {(0, 0): 5, (0, 1): 6, (0, 2): 0, (0, 3): 3,
                (1, 0): 0, (1, 1): 7, (1, 2): 0, (1, 3): 8,
                (2, 0): 1, (2, 1): -1, (2, 2): 0, (2, 3): 0}
        st = Table(data, ['1', '2', '3'], ['a', 'b', 'c', 'd'])
        exp = [('1', 'a'), ('1', 'b'), ('1', 'd'), ('2', 'b'), ('2', 'd'),
               ('3', 'a'), ('3', 'b')]
        obs = list(st.nonzero())
        self.assertEqual(obs, exp)

    def test_nonzero_counts(self):
        """Returns nonzero counts over an axis"""
        data = {(0, 0): 5, (0, 1): 6, (0, 2): 0, (0, 3): 3,
                (1, 0): 0, (1, 1): 7, (1, 2): 0, (1, 3): 8,
                (2, 0): 1, (2, 1): -1, (2, 2): 0, (2, 3): 0}
        st = Table(data, ['1', '2', '3'], ['a', 'b', 'c', 'd'])

        exp_samp = np.array([6, 12, 0, 11])
        exp_obs = np.array([14, 15, 0])
        exp_whole = np.array([29])

        obs_samp = st.nonzero_counts('sample')
        obs_obs = st.nonzero_counts('observation')
        obs_whole = st.nonzero_counts('whole')

        npt.assert_equal(obs_samp, exp_samp)
        npt.assert_equal(obs_obs, exp_obs)
        npt.assert_equal(obs_whole, exp_whole)

    def test_nonzero_counts_binary(self):
        """Returns nonzero counts over an axis"""
        data = {(0, 0): 5, (0, 1): 6, (0, 2): 0, (0, 3): 3,
                (1, 0): 0, (1, 1): 7, (1, 2): 0, (1, 3): 8,
                (2, 0): 1, (2, 1): -1, (2, 2): 0, (2, 3): 0}
        st = Table(data, ['1', '2', '3'], ['a', 'b', 'c', 'd'])

        exp_samp = np.array([2, 3, 0, 2])
        exp_obs = np.array([3, 2, 2])
        exp_whole = np.array([7])

        obs_samp = st.nonzero_counts('sample', binary=True)
        obs_obs = st.nonzero_counts('observation', binary=True)
        obs_whole = st.nonzero_counts('whole', binary=True)

        npt.assert_equal(obs_samp, exp_samp)
        npt.assert_equal(obs_obs, exp_obs)
        npt.assert_equal(obs_whole, exp_whole)

    def test_merge(self):
        """Merge two tables"""
        u = 'union'
        i = 'intersection'

        # test 1
        data = {(0, 0): 10, (0, 1): 12, (1, 0): 14, (1, 1): 16}
        exp = Table(data, ['1', '2'], ['a', 'b'])
        obs = self.st1.merge(self.st1, sample=u, observation=u)
        self.assertEqual(obs, exp)

        # test 2
        data = {(0, 0): 5, (0, 1): 6, (0, 2): 0, (1, 0): 7, (1, 1): 9,
                (1, 2): 2, (2, 0): 0, (2, 1): 3, (2, 2): 4}
        exp = Table(data, ['1', '2', '3'], ['a', 'b', 'c'])
        obs = self.st1.merge(self.st3, sample=u, observation=u)
        self.assertEqual(obs, exp)

        # test 3
        data = {(0, 0): 5, (0, 1): 6, (0, 2): 0, (0, 3): 0,
                (1, 0): 7, (1, 1): 8, (1, 2): 0, (1, 3): 0,
                (2, 0): 0, (2, 1): 0, (2, 2): 1, (2, 3): 2,
                (3, 0): 0, (3, 1): 0, (3, 2): 3, (3, 3): 4}
        exp = Table(data, ['1', '2', '3', '4'], ['a', 'b', 'c', 'd'])
        obs = self.st1.merge(self.st4, sample=u, observation=u)
        self.assertEqual(obs, exp)

        # test 4
        data = {(0, 0): 10, (0, 1): 12, (1, 0): 14, (1, 1): 16}
        exp = Table(data, ['1', '2'], ['a', 'b'])
        obs = self.st1.merge(self.st1, sample=i, observation=i)
        self.assertEqual(obs, exp)

        # test 5
        exp = Table({(0, 0): 9}, ['2'], ['b'])
        obs = self.st1.merge(self.st3, sample=i, observation=i)
        self.assertEqual(obs, exp)

        # test 6
        self.assertRaises(TableException, self.st1.merge, self.st4, i, i)

        # test 7
        data = {(0, 0): 10, (0, 1): 12, (1, 0): 14, (1, 1): 16}
        exp = Table(data, ['1', '2'], ['a', 'b'])
        obs = self.st1.merge(self.st1, sample=i, observation=u)
        self.assertEqual(obs, exp)

        # test 8
        data = {(0, 0): 6, (1, 0): 9, (2, 0): 3}
        exp = Table(data, ['1', '2', '3'], ['b'])
        obs = self.st1.merge(self.st3, sample=i, observation=u)
        self.assertEqual(obs, exp)

        # test 9
        self.assertRaises(TableException, self.st1.merge, self.st4, i, u)

        # test 10
        data = {(0, 0): 10, (0, 1): 12, (1, 0): 14, (1, 1): 16}
        exp = Table(data, ['1', '2'], ['a', 'b'])
        obs = self.st1.merge(self.st1, sample=u, observation=i)
        self.assertEqual(obs, exp)

        # test 11
        data = {(0, 0): 7, (0, 1): 9, (0, 2): 2}
        exp = Table(data, ['2'], ['a', 'b', 'c'])
        obs = self.st1.merge(self.st3, sample=u, observation=i)
        self.assertEqual(obs, exp)

        # test 12
        self.assertRaises(TableException, self.st1.merge, self.st4, u, i)

    def test_data(self):
        """"""
        # Returns observations for a given sample
        exp = np.array([5, 7])
        obs = self.st1.data('a', 'sample')
        npt.assert_equal(obs, exp)
        with self.assertRaises(UnknownIDError):
            self.st1.data('asdasd', 'sample')

        # Returns samples for a given observation
        exp = np.array([5, 6])
        obs = self.st1.data('1', 'observation')
        npt.assert_equal(obs, exp)
        with self.assertRaises(UnknownIDError):
            self.st1.data('asdsad', 'observation')

        # Raises an error with unknown axis
        with self.assertRaises(UnknownAxisError):
            obs = self.st1.data('a', axis='foo')

    def test_delimited_self(self):
        """Print out self in a delimited form"""
        exp = '\n'.join(
            ["# Constructed from biom file",
             "#OTU ID\ta\tb",
             "1\t5.0\t6.0",
             "2\t7.0\t8.0"])
        obs = self.st1.delimited_self()
        self.assertEqual(obs, exp)

        # Test observation_column_name.
        exp = '\n'.join(
            ["# Constructed from biom file",
             "Taxon\ta\tb",
             "1\t5.0\t6.0",
             "2\t7.0\t8.0"])
        obs = self.st1.delimited_self(observation_column_name='Taxon')
        self.assertEqual(obs, exp)

    def test_conv_to_self_type(self):
        """Should convert other to sparse type"""
        exp = lil_matrix((2, 2))
        exp[(0, 0)] = 5
        exp[(0, 1)] = 6
        exp[(1, 0)] = 7
        exp[(1, 1)] = 8
        obs = self.st1._conv_to_self_type(self.vals)
        self.assertEqual((obs != exp).sum(), 0)

        exp = lil_matrix((2, 2))
        exp[(0, 0)] = 5
        exp[(0, 1)] = 7
        exp[(1, 0)] = 6
        exp[(1, 1)] = 8
        obs = self.st1._conv_to_self_type(self.vals, transpose=True)
        self.assertEqual((obs != exp).sum(), 0)

        # passing a single vector
        exp = lil_matrix((1, 3))
        exp[(0, 0)] = 2
        exp[(0, 1)] = 0
        exp[(0, 2)] = 3
        obs = self.st1._conv_to_self_type(np.array([2, 0, 3]))
        self.assertEqual((obs != exp).sum(), 0)

        # passing a list of dicts
        exp = lil_matrix((2, 3))
        exp[(0, 0)] = 5
        exp[(0, 1)] = 6
        exp[(0, 2)] = 7
        exp[(1, 0)] = 8
        exp[(1, 1)] = 9
        exp[(1, 2)] = 10
        obs = self.st1._conv_to_self_type([{(0, 0): 5, (0, 1): 6, (0, 2): 7},
                                           {(1, 0): 8, (1, 1): 9, (1, 2): 10}])
        self.assertEqual((obs != exp).sum(), 0)

    def test_to_dense(self):
        """Should convert a self styled vector to numpy type"""
        input_row = lil_matrix((1, 3))
        input_row[(0, 0)] = 10
        exp = np.array([10.0, 0, 0])
        obs = self.st1._to_dense(input_row)
        npt.assert_equal(obs, exp)

        input_col = lil_matrix((3, 1))
        input_col[(0, 0)] = 12
        exp = np.array([12.0, 0, 0])
        obs = self.st1._to_dense(input_col)
        npt.assert_equal(obs, exp)

        # 1x1
        input_vec = lil_matrix((1, 1))
        input_vec[(0, 0)] = 42
        exp = np.array([42.0])
        obs = self.st1._to_dense(input_vec)
        npt.assert_equal(obs, exp)

    def test_iter(self):
        """Should iterate over samples"""
        exp = [(np.array([5, 7]), 'a', None), (np.array([6, 8]), 'b', None)]
        obs = list(self.st1)
        npt.assert_equal(obs, exp)

    def test_iter_obs(self):
        """Iterate over observations of sparse matrix"""
        r1 = lil_matrix((1, 2))
        r2 = lil_matrix((1, 2))
        r1[(0, 0)] = 5
        r1[(0, 1)] = 6
        r2[(0, 0)] = 7
        r2[(0, 1)] = 8

        exp = [r1.tocsr(), r2.tocsr()]
        obs = list(self.st1._iter_obs())

        for o, e in zip(obs, exp):
            self.assertEqual((o != e).sum(), 0)

    def test_iter_samp(self):
        """Iterate over samples of sparse matrix"""
        c1 = lil_matrix((1, 2))
        c2 = lil_matrix((1, 2))
        c1[(0, 0)] = 5
        c1[(0, 1)] = 7
        c2[(0, 0)] = 6
        c2[(0, 1)] = 8

        exp = [c1.tocsc(), c2.tocsc()]
        obs = list(self.st1._iter_samp())

        for o, e in zip(obs, exp):
            self.assertEqual((o != e).sum(), 0)

    def test_iter_samples(self):
        """Iterates samples"""
        gen = self.st1.iter()
        exp = [(np.array([5, 7]), 'a', None), (np.array([6, 8]), 'b', None)]
        obs = list(gen)
        npt.assert_equal(obs, exp)

        gen = self.st_rich.iter()
        exp = [(np.array([5, 7]), 'a', {'barcode': 'aatt'}),
               (np.array([6, 8]), 'b', {'barcode': 'ttgg'})]
        obs = list(gen)
        npt.assert_equal(obs, exp)

        # [[1,2,3],[1,0,2]] isn't yielding column 2 correctly
        vals = {(0, 0): 5, (0, 1): 6, (1, 1): 8}
        st = Table(vals, ['1', '2'], ['a', 'b'])
        gen = st.iter(axis='sample')
        exp = [(np.array([5, 0]), 'a', None), (np.array([6, 8]), 'b', None)]
        obs = list(gen)
        npt.assert_equal(obs, exp)

    def test_iter_observations(self):
        """Iterates observations"""
        gen = self.st1.iter(axis='observation')
        exp = [(np.array([5, 6]), '1', None), (np.array([7, 8]), '2', None)]
        obs = list(gen)
        npt.assert_equal(obs, exp)

        gen = self.st_rich.iter(axis='observation')
        exp = [(np.array([5, 6]), '1', {'taxonomy': ['k__a', 'p__b']}),
               (np.array([7, 8]), '2', {'taxonomy': ['k__a', 'p__c']})]
        obs = list(gen)
        npt.assert_equal(obs, exp)

    def test_iter_sample_data(self):
        """Iterates data by samples"""
        gen = self.st1.iter_data()
        exp = [np.array([5, 7]), np.array([6, 8])]
        obs = list(gen)
        npt.assert_equal(obs, exp)

        gen = self.st_rich.iter_data()
        exp = [np.array([5, 7]), np.array([6, 8])]
        obs = list(gen)
        npt.assert_equal(obs, exp)

        # [[1,2,3],[1,0,2]] isn't yielding column 2 correctly
        vals = {(0, 0): 5, (0, 1): 6, (1, 1): 8}
        st = Table(vals, ['1', '2'], ['a', 'b'])
        gen = st.iter_data()
        exp = [np.array([5, 0]), np.array([6, 8])]
        obs = list(gen)
        npt.assert_equal(obs, exp)

    def test_iter_sample_data_single_obs(self):
        """Iterates data by samples with a single observation."""
        exp = [np.array([2.0]), np.array([0.0]), np.array([1.0])]
        obs = list(self.single_obs_st.iter_data())
        # We test this way to make sure the observed value is a single element
        # array instead of a numpy scalar.
        for o, e in zip(obs, exp):
            self.assertEqual(o, e)

    def test_iter_observation_data(self):
        """Iterates data by observations"""
        gen = self.st1.iter_data(axis="observation")
        exp = [np.array([5, 6]), np.array([7, 8])]
        obs = list(gen)
        npt.assert_equal(obs, exp)

        gen = self.st_rich.iter_data(axis="observation")
        exp = [np.array([5, 6]), np.array([7, 8])]
        obs = list(gen)
        npt.assert_equal(obs, exp)

    def test_iter_observation_data_single_sample(self):
        """Iterates data by observations from a single sample."""
        exp = [np.array([2.0]), np.array([0.0]), np.array([1.0])]
        obs = list(self.single_sample_st.iter_data(axis="observation"))
        for o, e in zip(obs, exp):
            self.assertEqual(o, e)

    def test_copy_metadata(self):
        self.st_rich.sample_metadata[0]['foo'] = ['bar']
        copied_table = self.st_rich.copy()
        copied_table.sample_metadata[0]['foo'].append('bar2')
        self.assertNotEqual(copied_table, self.st_rich)
        self.st_rich.observation_metadata[0]['foo'] = ['bar']
        copied_table = self.st_rich.copy()
        copied_table.observation_metadata[0]['foo'].append('bar2')
        self.assertNotEqual(copied_table, self.st_rich)

    def test_copy_ids(self):
        copied_table = self.st_rich.copy()
        self.st_rich.sample_ids[0] = 'a different id'
        self.assertNotEqual(copied_table, self.st_rich)
        copied_table = self.st_rich.copy()
        self.st_rich.observation_ids[0] = 'a different id'
        self.assertNotEqual(copied_table, self.st_rich)

    def test_copy_data(self):
        copied_table = self.st_rich.copy()
        self.st_rich._data *= 2
        self.assertNotEqual(copied_table, self.st_rich)

    def test_filter_id_state(self):
        f = lambda vals, id_, md: id_[0] == 'b'
        filtered_table = self.st3.filter(f, inplace=False)
        filtered_table_2 = self.st3.filter(f, inplace=True)
        self.assertEqual(filtered_table._sample_index, {'b': 0})
        self.assertEqual(filtered_table._obs_index, {'2': 0, '3': 1})
        self.assertEqual(filtered_table_2._sample_index, {'b': 0})
        self.assertEqual(filtered_table_2._obs_index, {'2': 0, '3': 1})

    def test_filter_return_type(self):
        f = lambda vals, id_, md: id_[0] == 'b'
        filtered_table = self.st3.filter(f, inplace=False)
        filtered_table_2 = self.st3.filter(f, inplace=True)
        self.assertEqual(filtered_table, filtered_table_2)
        self.assertTrue(filtered_table_2 is self.st3)

    def test_filter_general_sample(self):
        f = lambda vals, id_, md: id_ == 'a'

        values = csr_matrix(np.array([[5.],
                                      [7.]]))
        exp_table = Table(values, ['1', '2'], ['a'],
                          [{'taxonomy': ['k__a', 'p__b']},
                           {'taxonomy': ['k__a', 'p__c']}],
                          [{'barcode': 'aatt'}])

        table = self.st_rich
        obs_table = table.filter(f, 'sample', inplace=False)
        self.assertEqual(obs_table, exp_table)

        f_2 = lambda vals, id_, md: np.all(vals == np.array([5, 7]))
        obs_table_2 = table.filter(f_2, 'sample', inplace=False)
        self.assertEqual(obs_table_2, exp_table)

    def test_filter_general_observation(self):
        f = lambda vals, id_, md: md['taxonomy'][1] == 'p__c'
        values = csr_matrix(np.array([[7., 8.]]))
        exp_table = Table(values, ['2'], ['a', 'b'],
                          [{'taxonomy': ['k__a', 'p__c']}],
                          [{'barcode': 'aatt'}, {'barcode': 'ttgg'}])
        table = self.st_rich
        obs_table = table.filter(f, 'observation', inplace=False)
        self.assertEqual(obs_table, exp_table)

        f_2 = lambda vals, id_, md: np.all(vals == np.array([7, 8]))
        obs_table_2 = table.filter(f_2, 'observation', inplace=False)
        self.assertEqual(obs_table_2, exp_table)

    def test_filter_sample_id(self):
        f = lambda vals, id_, md: id_ == 'a'

        values = csr_matrix(np.array([[5.],
                                      [7.]]))
        exp_table = Table(values, ['1', '2'], ['a'],
                          [{'taxonomy': ['k__a', 'p__b']},
                           {'taxonomy': ['k__a', 'p__c']}],
                          [{'barcode': 'aatt'}])

        table = self.st_rich
        table.filter(f, 'sample')
        self.assertEqual(table, exp_table)

    def test_filter_sample_metadata(self):
        f = lambda vals, id_, md: md['barcode'] == 'ttgg'
        values = csr_matrix(np.array([[6.],
                                      [8.]]))
        exp_table = Table(values, ['1', '2'], ['b'],
                          [{'taxonomy': ['k__a', 'p__b']},
                           {'taxonomy': ['k__a', 'p__c']}],
                          [{'barcode': 'ttgg'}])
        table = self.st_rich
        table.filter(f, 'sample')
        self.assertEqual(table, exp_table)

    def test_filter_sample_invert(self):
        f = lambda vals, id_, md: md['barcode'] == 'aatt'
        values = csr_matrix(np.array([[6.],
                                      [8.]]))
        exp_table = Table(values, ['1', '2'], ['b'],
                          [{'taxonomy': ['k__a', 'p__b']},
                           {'taxonomy': ['k__a', 'p__c']}],
                          [{'barcode': 'ttgg'}])
        table = self.st_rich
        table.filter(f, 'sample', invert=True)
        self.assertEqual(table, exp_table)

    def test_filter_sample_remove_everything(self):
        with self.assertRaises(TableException):
            self.st_rich.filter(lambda vals, id_, md: False, 'sample')

    def test_filter_observations_id(self):
        f = lambda vals, id_, md: id_ == '1'
        values = csr_matrix(np.array([[5., 6.]]))
        exp_table = Table(values, ['1'], ['a', 'b'],
                          [{'taxonomy': ['k__a', 'p__b']}],
                          [{'barcode': 'aatt'}, {'barcode': 'ttgg'}])
        table = self.st_rich
        table.filter(f, 'observation')
        self.assertEqual(table, exp_table)

    def test_filter_observations_metadata(self):
        f = lambda vals, id_, md: md['taxonomy'][1] == 'p__c'
        values = csr_matrix(np.array([[7., 8.]]))
        exp_table = Table(values, ['2'], ['a', 'b'],
                          [{'taxonomy': ['k__a', 'p__c']}],
                          [{'barcode': 'aatt'}, {'barcode': 'ttgg'}])
        table = self.st_rich
        table.filter(f, 'observation')
        self.assertEqual(table, exp_table)

    def test_filter_observations_invert(self):
        f = lambda vals, id_, md: md['taxonomy'][1] == 'p__c'
        values = csr_matrix(np.array([[5., 6.]]))
        exp_table = Table(values, ['1'], ['a', 'b'],
                          [{'taxonomy': ['k__a', 'p__b']}],
                          [{'barcode': 'aatt'}, {'barcode': 'ttgg'}])
        table = self.st_rich
        table.filter(f, 'observation', invert=True)
        self.assertEqual(table, exp_table)

    def test_filter_observations_remove_everything(self):
        with self.assertRaises(TableException):
            self.st_rich.filter(lambda vals, id_, md: False, 'observation')

    def test_subsample(self):
        table = Table(np.array([[0, 5, 0]]), ['O1'], ['S1', 'S2', 'S3'])

        obs = table.subsample(5, axis='observation')
        npt.assert_equal(obs.data('O1', 'observation'), np.array([5]))
        self.assertEqual(obs.sample_ids, ['S2'])

        table = Table(np.array([[3, 1, 1], [0, 3, 3]]), ['O1', 'O2'],
                      ['S1', 'S2', 'S3'])
        actual_o1 = set()
        actual_o2 = set()
        for i in range(100):
            obs = table.subsample(3)
            actual_o1.add(tuple(obs.data('O1', 'observation')))
            actual_o2.add(tuple(obs.data('O2', 'observation')))
        self.assertEqual(actual_o1, {(3, 0, 0), (3, 1, 0), (3, 0, 1),
                                     (3, 1, 1)})
        self.assertEqual(actual_o2, {(0, 3, 3), (0, 2, 3), (0, 3, 2),
                                     (0, 2, 2)})

    def test_subsample_md_copy_bug(self):
        """subsample would except when if metadata were present"""
        table = Table(np.array([[5, 5, 5]]), ['O1'], ['S1', 'S2', 'S3'],
                      [{'foo': 'bar'}], [{1: 2}, {3: 4}, {5: 6}])
        exp = table.copy()
        obs = table.subsample(5)
        self.assertEqual(obs, exp)

    def test_pa(self):
        exp = Table(np.array([[1, 1], [1, 0]]), ['5', '6'], ['a', 'b'])
        self.st7.pa()
        self.assertEqual(self.st7, exp)

    def test_pa_works_if_something_has_been_zeroed(self):
        exp = Table(np.array([[0, 1], [1, 0]]), ['5', '6'], ['a', 'b'])
        self.st7._data[0, 0] = 0
        self.st7.pa()
        self.assertEqual(self.st7, exp)


    def test_transform_return_type(self):
        f = lambda data, id_, md: data / 2.
        filtered_table = self.st3.transform(f, inplace=False)
        filtered_table_2 = self.st3.transform(f, inplace=True)
        self.assertEqual(filtered_table, filtered_table_2)
        self.assertTrue(filtered_table_2 is self.st3)

    def test_transform_observation(self):
        """Transform axis by arbitrary function"""
        # Transform observations by arbitrary function
        def obs_transform_f(v, id, md):
            return np.where(v >= 7, 1, 0)
        sp_sd = {(0, 0): 0, (0, 1): 0, (1, 0): 1, (1, 1): 1}
        exp = Table(sp_sd, ['1', '2'], ['a', 'b'])
        self.st1.transform(obs_transform_f, axis='observation')
        self.assertEqual(self.st1, exp)

    def test_transform_sample(self):
        # """Transform samples by arbitrary function"""
        def sample_transform_f(v, id, md):
            return np.where(v >= 6, 1, 0)

        sp_sd = {(0, 0): 0, (0, 1): 1, (1, 0): 1, (1, 1): 1}
        exp = Table(sp_sd, ['1', '2'], ['a', 'b'])
        self.st1.transform(sample_transform_f)
        self.assertEqual(self.st1, exp)

        # Raises UnknownAxisError if a invalid axis is passed
        with self.assertRaises(UnknownAxisError):
            self.st1.transform(sample_transform_f, axis='foo')

    def test_norm_observation_by_sample(self):
        """normalize observations by sample"""
        data = {(0, 0): 2, (0, 1): 0, (1, 0): 6, (1, 1): 1}
        data_exp = {(0, 0): 0.25, (0, 1): 0.0, (1, 0): 0.75, (1, 1): 1.0}

        st = Table(data, ['1', '2'], ['a', 'b'])
        exp = Table(data_exp, ['1', '2'], ['a', 'b'])
        st.norm()
        self.assertEqual(st, exp)

    def test_norm_sample_by_observation(self):
        """normalize sample by observation"""
        data = {(0, 0): 0, (0, 1): 2, (1, 0): 2, (1, 1): 6}
        data_exp = {(0, 0): 0.0, (0, 1): 1.0, (1, 0): 0.25, (1, 1): 0.75}
        st = Table(data, ['1', '2'], ['a', 'b'])
        exp = Table(data_exp, ['1', '2'], ['a', 'b'])
        st.norm(axis='observation')
        self.assertEqual(st, exp)

    def test_collapse_observations_by_metadata_one_to_many_strict(self):
        """Collapse observations by arbitary metadata"""
        dt_rich = Table(np.array([[5, 6, 7], [8, 9, 10], [11, 12, 13]]),
                        ['1', '2', '3'], ['a', 'b', 'c'],
                        [{'pathways': [['a', 'bx'], ['a', 'd']]},
                         {'pathways': [['a', 'bx'], ['a', 'c']]},
                         {'pathways': [['a']]}],
                        [{'barcode': 'aatt'},
                         {'barcode': 'ttgg'},
                         {'barcode': 'aatt'}])
        exp_cat2 = Table(np.array([[13, 15, 17], [8, 9, 10], [5, 6, 7]]),
                         ['bx', 'c', 'd'], ['a', 'b', 'c'],
                         [{'Path': ['a', 'bx']},
                          {'Path': ['a', 'c']},
                          {'Path': ['a', 'd']}],
                         [{'barcode': 'aatt'},
                          {'barcode': 'ttgg'},
                          {'barcode': 'aatt'}])

        def bin_f(id_, x):
            for foo in x['pathways']:
                yield (foo, foo[1])

        obs_cat2 = dt_rich.collapse(
            bin_f, norm=False, min_group_size=1, one_to_many=True,
            strict=False, axis='observation').sort(axis='observation')
        self.assertEqual(obs_cat2, exp_cat2)

        with self.assertRaises(IndexError):
            dt_rich.collapse(
                bin_f, norm=False, min_group_size=1, one_to_many=True,
                strict=True, axis='observation')

    def test_collapse_observations_by_metadata_one_to_many(self):
        """Collapse observations by arbitary metadata"""
        dt_rich = Table(np.array([[5, 6, 7], [8, 9, 10], [11, 12, 13]]),
            ['1', '2', '3'], ['a', 'b', 'c'],
            [{'pathways': [['a', 'bx'], ['a', 'd']]},
             {'pathways': [['a', 'bx'], ['a', 'c']]},
             {'pathways': [['a', 'c']]}],
            [{'barcode': 'aatt'},
             {'barcode': 'ttgg'},
             {'barcode': 'aatt'}])
        exp_cat2 = Table(np.array([[13, 15, 17], [19, 21, 23], [5, 6, 7]]),
                         ['bx', 'c', 'd'], ['a', 'b', 'c'],
                         [{'Path': ['a', 'bx']},
                          {'Path': ['a', 'c']},
                          {'Path': ['a', 'd']}],
                         [{'barcode': 'aatt'},
                          {'barcode': 'ttgg'},
                          {'barcode': 'aatt'}])

        def bin_f(id_, x):
            for foo in x['pathways']:
                yield (foo, foo[-1])

        obs_cat2 = dt_rich.collapse(
            bin_f, norm=False, min_group_size=1,
            one_to_many=True, axis='observation').sort(axis='observation')
        self.assertEqual(obs_cat2, exp_cat2)

        dt_rich = Table(np.array([[5, 6, 7], [8, 9, 10], [11, 12, 13]]),
            ['1', '2', '3'], ['a', 'b', 'c'],
            [{'pathways': [['a', 'b'], ['a', 'd']]},
             {'pathways': [['a', 'b'], ['a', 'c']]},
             {'pathways': [['a', 'c']]}],
            [{'barcode': 'aatt'},
             {'barcode': 'ttgg'},
             {'barcode': 'aatt'}])
        exp_cat1 = Table(np.array([[37, 42, 47]]),
                         ['a'], ['a', 'b', 'c'],
                         [{'Path': ['a']}],
                         [{'barcode': 'aatt'},
                          {'barcode': 'ttgg'},
                          {'barcode': 'aatt'}])

        def bin_f(id_, x):
            for foo in x['pathways']:
                yield (foo[:1], foo[0])

        obs_cat1 = dt_rich.collapse(
            bin_f, norm=False, min_group_size=1,
            one_to_many=True, axis='observation').sort(axis='observation')
        self.assertEqual(obs_cat1, exp_cat1)

        # Test out include_collapsed_metadata=False.
        exp = Table(np.array([[37, 42, 47]]),
                    ['a'], ['a', 'b', 'c'], None,
                    [{'barcode': 'aatt'},
                     {'barcode': 'ttgg'},
                     {'barcode': 'aatt'}])
        obs = dt_rich.collapse(
            bin_f, norm=False, min_group_size=1, one_to_many=True,
            include_collapsed_metadata=False,
            axis='observation').sort(axis='observation')
        self.assertEqual(obs, exp)

        # Test out constructor.
        obs = dt_rich.collapse(
            bin_f, norm=False, min_group_size=1, one_to_many=True,
            include_collapsed_metadata=False,
            axis='observation').sort(axis='observation')
        self.assertEqual(obs, exp)
        self.assertEqual(type(obs), Table)

    def test_collapse_observations_by_metadata_one_to_many_divide(self):
        """Collapse observations by 1-M metadata using divide mode"""
        dt_rich = Table(np.array([[1, 6, 7], [8, 0, 10], [11, 12, 13]]),
                        ['1', '2', '3'],
                        ['a', 'b', 'c'],
                        [{'pathways': [['a', 'bx'], ['a', 'd']]},
                         {'pathways': [['a', 'bx'], ['a', 'c']]},
                         {'pathways': [['a', 'c']]}],
                        [{'barcode': 'aatt'},
                         {'barcode': 'ttgg'},
                         {'barcode': 'aatt'}])
        exp = Table(np.array([[4.5, 3, 8.5], [15, 12, 18], [0.5, 3, 3.5]]),
                    ['bx', 'c', 'd'],
                    ['a', 'b', 'c'],
                    [{'Path': ['a', 'bx']},
                     {'Path': ['a', 'c']},
                     {'Path': ['a', 'd']}],
                    [{'barcode': 'aatt'},
                     {'barcode': 'ttgg'},
                     {'barcode': 'aatt'}])

        def bin_f(id_, x):
            for foo in x['pathways']:
                yield (foo, foo[-1])

        obs = dt_rich.collapse(
            bin_f, norm=False, one_to_many=True,
            one_to_many_mode='divide',
            axis='observation').sort(axis='observation')
        self.assertEqual(obs, exp)

        # Test skipping some observation metadata (strict=False).
        dt_rich = Table(
            np.array([[5.0, 6.0, 7], [8, 9, 10], [11, 12, 13.0]]),
            ['1', '2', '3'], ['a', 'b', 'c'],
            [{'pathways': [['a', 'bx'], ['a', 'd']]},
             {'pathways': [['a', 'bx'], ['a', 'c'], ['z']]},
             {'pathways': [['a']]}],
            [{'barcode': 'aatt'},
             {'barcode': 'ttgg'},
             {'barcode': 'aatt'}])
        exp = Table(np.array([[6.5, 7.5, 8.5], [4, 4.5, 5], [2.5, 3, 3.5]]),
                    ['bx', 'c', 'd'], ['a', 'b', 'c'],
                    [{'Path': ['a', 'bx']},
                     {'Path': ['a', 'c']},
                     {'Path': ['a', 'd']}],
                    [{'barcode': 'aatt'},
                     {'barcode': 'ttgg'},
                     {'barcode': 'aatt'}])

        def bin_f(id_, x):
            for foo in x['pathways']:
                yield (foo, foo[1])

        obs = dt_rich.collapse(
            bin_f, norm=False, one_to_many=True, one_to_many_mode='divide',
            strict=False, axis='observation').sort(axis='observation')

        self.assertEqual(obs, exp)

        with self.assertRaises(IndexError):
            dt_rich.collapse(
                bin_f, norm=False, one_to_many=True, one_to_many_mode='divide',
                strict=True, axis='observation')

        # Invalid one_to_many_mode.
        with self.assertRaises(ValueError):
            dt_rich.collapse(
                bin_f, norm=False, one_to_many=True, one_to_many_mode='foo',
                axis='observation')

    def test_collapse_observations_by_metadata(self):
        """Collapse observations by arbitrary metadata"""
        dt_rich = Table(
            np.array([[5, 6, 7], [8, 9, 10], [11, 12, 13]]),
            ['1', '2', '3'], ['a', 'b', 'c'],
            [{'taxonomy': ['k__a', 'p__b']},
             {'taxonomy': ['k__a', 'p__c']},
             {'taxonomy': ['k__a', 'p__c']}],
            [{'barcode': 'aatt'},
             {'barcode': 'ttgg'},
             {'barcode': 'aatt'}])
        exp_phy = Table(np.array([[5, 6, 7], [19, 21, 23]]),
                        ['p__b', 'p__c'], ['a', 'b', 'c'],
                        [{'1': {'taxonomy': ['k__a', 'p__b']}},
                         {'2': {'taxonomy': ['k__a', 'p__c']},
                          '3':{'taxonomy': ['k__a', 'p__c']}}],
                        [{'barcode': 'aatt'},
                         {'barcode': 'ttgg'},
                         {'barcode': 'aatt'}])
        bin_f = lambda id_, x: x['taxonomy'][1]
        obs_phy = dt_rich.collapse(
            bin_f, norm=False, min_group_size=1,
            axis='observation').sort(axis='observation')
        self.assertEqual(obs_phy, exp_phy)

        exp_king = Table(np.array([[24, 27, 30]]),
                         ['k__a'], ['a', 'b', 'c'],
                         [{'1': {'taxonomy': ['k__a', 'p__b']},
                           '2':{'taxonomy': ['k__a', 'p__c']},
                           '3':{'taxonomy': ['k__a', 'p__c']}}],
                         [{'barcode': 'aatt'},
                          {'barcode': 'ttgg'},
                          {'barcode': 'aatt'}])
        bin_f = lambda id_, x: x['taxonomy'][0]
        obs_king = dt_rich.collapse(bin_f, norm=False, axis='observation')
        self.assertEqual(obs_king, exp_king)

        self.assertRaises(
            TableException, dt_rich.collapse, bin_f, min_group_size=10,
            axis='observation')

        # Test out include_collapsed_metadata=False.
        exp = Table(np.array([[24, 27, 30]]),
                    ['k__a'],
                    ['a', 'b', 'c'], None,
                    [{'barcode': 'aatt'},
                     {'barcode': 'ttgg'},
                     {'barcode': 'aatt'}])
        obs = dt_rich.collapse(bin_f, norm=False,
                               include_collapsed_metadata=False,
                               axis='observation')
        self.assertEqual(obs, exp)

        # Test out constructor.
        obs = dt_rich.collapse(bin_f, norm=False,
                               include_collapsed_metadata=False,
                               axis='observation')
        self.assertEqual(obs, exp)
        self.assertEqual(type(obs), Table)

    def test_collapse_samples_by_metadata(self):
        """Collapse samples by arbitrary metadata"""
        dt_rich = Table(
            np.array([[5, 6, 7], [8, 9, 10], [11, 12, 13]]),
            ['1', '2', '3'], ['a', 'b', 'c'],
            [{'taxonomy': ['k__a', 'p__b']},
             {'taxonomy': ['k__a', 'p__c']},
             {'taxonomy': ['k__a', 'p__c']}],
            [{'barcode': 'aatt'},
             {'barcode': 'ttgg'},
             {'barcode': 'aatt'}])
        exp_bc = Table(
            np.array([[12, 6], [18, 9], [24, 12]]),
            ['1', '2', '3'], ['aatt', 'ttgg'],
            [{'taxonomy': ['k__a', 'p__b']},
             {'taxonomy': ['k__a', 'p__c']},
             {'taxonomy': ['k__a', 'p__c']}],
            [{'a': {'barcode': 'aatt'},
              'c': {'barcode': 'aatt'}},
             {'b': {'barcode': 'ttgg'}}])
        bin_f = lambda id_, x: x['barcode']
        obs_bc = dt_rich.collapse(
            bin_f, norm=False, min_group_size=1,
            axis='sample').sort(axis='sample')
        self.assertEqual(obs_bc, exp_bc)

        self.assertRaises(TableException, dt_rich.collapse,
                          bin_f, min_group_size=10)
        # Test out include_collapsed_metadata=False.
        exp = Table(np.array([[12, 6], [18, 9], [24, 12]]),
                    ['1', '2', '3'],
                    ['aatt', 'ttgg'],
                    [{'taxonomy': ['k__a', 'p__b']},
                     {'taxonomy': ['k__a', 'p__c']},
                     {'taxonomy': ['k__a', 'p__c']}],
                    None)

        obs = dt_rich.collapse(
            bin_f, norm=False, min_group_size=1,
            include_collapsed_metadata=False).sort(axis='sample')
        self.assertEqual(obs, exp)

        # Test out constructor.
        obs = dt_rich.collapse(
            bin_f, norm=False, min_group_size=1,
            include_collapsed_metadata=False).sort(axis='sample')
        self.assertEqual(obs, exp)
        self.assertEqual(type(obs), Table)

    def test_collapse_samples_by_metadata_one_to_many_strict(self):
        """Collapse samples by arbitary metadata"""
        dt_rich = Table(np.array([[5, 6, 7], [8, 9, 10], [11, 12, 13]]),
                        ['1', '2', '3'],
                        ['XXa', 'XXb', 'XXc'],
                        [{'other': 'aatt'},
                         {'other': 'ttgg'},
                         {'other': 'aatt'}],
                        [{'foo': [['a', 'b'], ['a', 'd']]},
                         {'foo': [['a', 'b'], ['a', 'c']]},
                         {'foo': [['a']]}])
        exp_cat2 = Table(np.array([[11, 17, 23], [6, 9, 12], [5, 8, 11]]).T,
                         ['1', '2', '3'],
                         ['b', 'c', 'd'],
                         [{'other': 'aatt'},
                          {'other': 'ttgg'},
                          {'other': 'aatt'}],
                         [{'Path': ['a', 'b']},
                          {'Path': ['a', 'c']},
                          {'Path': ['a', 'd']}])

        def bin_f(id_, x):
            for foo in x['foo']:
                yield (foo, foo[1])

        obs_cat2 = dt_rich.collapse(
            bin_f, norm=False, min_group_size=1, one_to_many=True,
            strict=False).sort(axis='observation')
        self.assertEqual(obs_cat2, exp_cat2)

        self.assertRaises(IndexError, dt_rich.collapse, bin_f,
                          norm=False, min_group_size=1, one_to_many=True,
                          strict=True)

    def test_collapse_samples_by_metadata_one_to_many_divide(self):
        """Collapse samples by 1-M metadata using divide mode"""
        dt_rich = Table(np.array([[1, 8, 11], [6, 0, 12], [7, 10, 13]]),
                        ['a', 'b', 'c'],
                        ['1', '2', '3'],
                        [{'barcode': 'aatt'},
                         {'barcode': 'ttgg'},
                         {'barcode': 'aatt'}],
                        [{'pathways': [['a', 'bx'], ['a', 'd']]},
                         {'pathways': [['a', 'bx'], ['a', 'c']]},
                         {'pathways': [['a', 'c']]}])
        exp = Table(np.array([[4.5, 15, 0.5], [3, 12, 3], [8.5, 18, 3.5]]),
                    ['a', 'b', 'c'],
                    ['bx', 'c', 'd'],
                    [{'barcode': 'aatt'},
                     {'barcode': 'ttgg'},
                     {'barcode': 'aatt'}],
                    [{'Path': ['a', 'bx']},
                     {'Path': ['a', 'c']},
                     {'Path': ['a', 'd']}])

        def bin_f(id_, x):
            for foo in x['pathways']:
                yield (foo, foo[-1])

        obs = dt_rich.collapse(
            bin_f, norm=False, one_to_many=True,
            one_to_many_mode='divide').sort(axis='sample')
        self.assertEqual(obs, exp)

        # Test skipping some sample metadata (strict=False).
        dt_rich = Table(np.array([[5.0, 8, 11], [6.0, 9, 12], [7, 10, 13.0]]),
            ['a', 'b', 'c'],
            ['1', '2', '3'],
            [{'barcode': 'aatt'},
             {'barcode': 'ttgg'},
             {'barcode': 'aatt'}],
            [{'pathways': [['a', 'bx'], ['a', 'd']]},
             {'pathways': [['a', 'bx'], ['a', 'c'], ['z']]},
             {'pathways': [['a']]}])
        exp = Table(np.array([[6.5, 4, 2.5], [7.5, 4.5, 3], [8.5, 5, 3.5]]),
                    ['a', 'b', 'c'],
                    ['bx', 'c', 'd'],
                    [{'barcode': 'aatt'},
                     {'barcode': 'ttgg'},
                     {'barcode': 'aatt'}],
                    [{'Path': ['a', 'bx']},
                     {'Path': ['a', 'c']},
                     {'Path': ['a', 'd']}])

        def bin_f(id_, x):
            for foo in x['pathways']:
                yield (foo, foo[1])

        obs = dt_rich.collapse(
            bin_f, norm=False, one_to_many=True, one_to_many_mode='divide',
            strict=False).sort(axis='sample')

        self.assertEqual(obs, exp)

        with self.assertRaises(IndexError):
            dt_rich.collapse(bin_f, norm=False,
                             one_to_many=True,
                             one_to_many_mode='divide',
                             strict=True)

        # Invalid one_to_many_mode.
        with self.assertRaises(ValueError):
            dt_rich.collapse(bin_f, norm=False,
                             one_to_many=True,
                             one_to_many_mode='foo')

    def test_collapse_samples_by_metadata_one_to_many(self):
        """Collapse samples by arbitary metadata"""
        dt_rich = Table(np.array([[5, 6, 7],
                                  [8, 9, 10],
                                  [11, 12, 13]]),
                        ['1', '2', '3'],
                        ['XXa', 'XXb', 'XXc'],
                        [{'other': 'aatt'},
                         {'other': 'ttgg'},
                         {'other': 'aatt'}],
                        [{'foo': [['a', 'b'], ['a', 'd']]},
                         {'foo': [['a', 'b'], ['a', 'c']]},
                         {'foo': [['a', 'c']]}])
        exp_cat2 = Table(
            np.array([[11, 17, 23], [13, 19, 25], [5, 8, 11]]).T,
            ['1', '2', '3'],
            ['b', 'c', 'd'],
            [{'other': 'aatt'},
             {'other': 'ttgg'},
             {'other': 'aatt'}],
            [{'Path': ['a', 'b']},
             {'Path': ['a', 'c']},
             {'Path': ['a', 'd']}])

        def bin_f(id_, x):
            for foo in x['foo']:
                yield (foo, foo[-1])

        obs_cat2 = dt_rich.collapse(
            bin_f, norm=False, min_group_size=1,
            one_to_many=True, axis='sample').sort(axis='observation')

        self.assertEqual(obs_cat2, exp_cat2)

        dt_rich = Table(
            np.array([[5, 6, 7], [8, 9, 10], [11, 12, 13]]),
            ['1', '2', '3'], ['a', 'b', 'c'],
            [{'other': 'aatt'},
             {'other': 'ttgg'},
             {'other': 'aatt'}],
            [{'foo': [['a', 'b'], ['a', 'd']]},
             {'foo': [['a', 'b'], ['a', 'c']]},
             {'foo': [['a', 'c']]}])
        exp_cat1 = Table(np.array([[29, 44, 59]]).T,
                         ['1', '2', '3'], ['a'],
                         [{'other': 'aatt'},
                          {'other': 'ttgg'},
                          {'other': 'aatt'}],
                         [{'Path': ['a']}])

        def bin_f(id_, x):
            for foo in x['foo']:
                yield (foo[:1], foo[0])

        obs_cat1 = dt_rich.collapse(
            bin_f, norm=False, min_group_size=1,
            one_to_many=True, axis='sample').sort(axis='observation')
        self.assertEqual(obs_cat1, exp_cat1)

        # Test out include_collapsed_metadata=False.
        exp = Table(np.array([[29, 44, 59]]).T,
                    ['1', '2', '3'],
                    ['a'],
                    [{'other': 'aatt'},
                     {'other': 'ttgg'},
                     {'other': 'aatt'}],
                    None)
        obs = dt_rich.collapse(
            bin_f, norm=False, min_group_size=1, one_to_many=True,
            include_collapsed_metadata=False,
            axis='sample').sort(axis='observation')
        self.assertEqual(obs, exp)

        # Test out constructor.
        obs = dt_rich.collapse(bin_f, norm=False, min_group_size=1,
                               one_to_many=True,
                               include_collapsed_metadata=False,
                               axis='sample').sort(axis='observation')
        self.assertEqual(obs, exp)
        self.assertEqual(type(obs), Table)

    def test_to_json_dense_int(self):
        """Get a BIOM format string for a dense table of integers"""
        # check by round trip
        obs_ids = map(str, range(5))
        samp_ids = map(str, range(10))
        obs_md = [{'foo': i} for i in range(5)]
        samp_md = [{'bar': i} for i in range(10)]
        data = np.reshape(np.arange(50), (5, 10))

        # using Table type to support parsing round trip
        t = Table(data, obs_ids, samp_ids, obs_md, samp_md)

        # verify that we can parse still
        t2 = parse_biom_table(StringIO(t.to_json('asd')))

        # verify that the tables are the same
        self.assertEqual(t, t2)

    def test_to_json_dense_float(self):
        """Get a BIOM format string for a dense table of floats"""
        # check by round trip
        obs_ids = ['a', 'b']
        samp_ids = ['c', 'd']
        obs_md = [{'foo': i} for i in range(2)]
        samp_md = [{'bar': i} for i in range(2)]
        data = np.array([[0.01, 1.5], [0.0, 0.79]])

        # using OTUTable type to support parsing round trip
        t = Table(data, obs_ids, samp_ids, obs_md, samp_md)

        # verify that we can parse still
        t2 = parse_biom_table(StringIO(t.to_json('asd')))

        # verify that the tables are the same
        self.assertEqual(t, t2)

    def test_to_json_dense_int_directio(self):
        """Get a BIOM format string for a dense table of integers"""
        # check by round trip
        obs_ids = map(str, range(5))
        samp_ids = map(str, range(10))
        obs_md = [{'foo': i} for i in range(5)]
        samp_md = [{'bar': i} for i in range(10)]
        data = np.reshape(np.arange(50), (5, 10))

        # using OTUTable type to support parsing round trip
        t = Table(data, obs_ids, samp_ids, obs_md, samp_md)

        # verify that we can parse still
        io = StringIO()
        t.to_json('asd', direct_io=io)
        io.seek(0)
        t2 = parse_biom_table(io)

        # verify that the tables are the same
        self.assertEqual(t, t2)

    def test_to_json_dense_float_directio(self):
        """Get a BIOM format string for a dense table of floats"""
        # check by round trip
        obs_ids = ['a', 'b']
        samp_ids = ['c', 'd']
        obs_md = [{'foo': i} for i in range(2)]
        samp_md = [{'bar': i} for i in range(2)]
        data = np.array([[0.01, 1.5], [0.0, 0.79]])

        # using OTUTable type to support parsing round trip
        t = Table(data, obs_ids, samp_ids, obs_md, samp_md)

        # verify that we can parse still
        io = StringIO()
        t.to_json('asd', direct_io=io)
        io.seek(0)
        t2 = parse_biom_table(io)

        # verify that the tables are the same
        self.assertEqual(t, t2)

    def test_to_json_sparse_int(self):
        """Get a BIOM format string for a sparse table of integers"""
        # check by round trip
        obs_ids = map(str, range(5))
        samp_ids = map(str, range(10))
        obs_md = [{'foo': i} for i in range(5)]
        samp_md = [{'bar': i} for i in range(10)]
        data = [[0, 0, 10], [1, 1, 11], [2, 2, 12], [3, 3, 13], [4, 4, 14],
                [3, 5, 15], [2, 6, 16], [1, 7, 18], [0, 8, 19], [1, 9, 20]]

        # using OTUTable type to support parsing round trip
        t = Table(data, obs_ids, samp_ids, obs_md, samp_md, obs_md)

        # verify that we can parse still
        t2 = parse_biom_table(StringIO(t.to_json('asd')))

        # verify that the tables are the same
        self.assertEqual(t, t2)

    def test_to_json_sparse_float(self):
        """Get a BIOM format string for a sparse table of floats"""
        # check by round trip
        obs_ids = ['a', 'b']
        samp_ids = ['c', 'd']
        obs_md = [{'foo': i} for i in range(2)]
        samp_md = [{'bar': i} for i in range(2)]
        data = [[0, 0, 0.01], [0, 1, 1.5], [1, 0, 0.0], [1, 1, 0.79]]

        # using OTUTable type to support parsing round trip
        t = Table(data, obs_ids, samp_ids, obs_md, samp_md, obs_md)

        # verify that we can parse still
        t2 = parse_biom_table(StringIO(t.to_json('asd')))

        # verify that the tables are the same
        self.assertEqual(t, t2)

    def test_to_json_sparse_int_directio(self):
        """Get a BIOM format string for a sparse table of integers"""
        # check by round trip
        obs_ids = map(str, range(5))
        samp_ids = map(str, range(10))
        obs_md = [{'foo': i} for i in range(5)]
        samp_md = [{'bar': i} for i in range(10)]
        data = [[0, 0, 10], [1, 1, 11], [2, 2, 12], [3, 3, 13], [4, 4, 14],
                [3, 5, 15], [2, 6, 16], [1, 7, 18], [0, 8, 19], [1, 9, 20]]

        # using OTUTable type to support parsing round trip
        t = Table(data, obs_ids, samp_ids, obs_md, samp_md, obs_md)

        # verify that we can parse still
        io = StringIO()
        t.to_json('asd', direct_io=io)
        io.seek(0)
        t2 = parse_biom_table(io)

        # verify that the tables are the same
        self.assertEqual(t, t2)

    def test_to_json_sparse_float_directio(self):
        """Get a BIOM format string for a sparse table of floats"""
        # check by round trip
        obs_ids = ['a', 'b']
        samp_ids = ['c', 'd']
        obs_md = [{'foo': i} for i in range(2)]
        samp_md = [{'bar': i} for i in range(2)]
        data = [[0, 0, 0.01], [0, 1, 1.5], [1, 0, 0.0], [1, 1, 0.79]]

        # using OTUTable type to support parsing round trip
        t = Table(data, obs_ids, samp_ids, obs_md, samp_md)

        # verify that we can parse still
        io = StringIO()
        t.to_json('asd', direct_io=io)
        io.seek(0)
        t2 = parse_biom_table(io)

        # verify that the tables are the same
        self.assertEqual(t, t2)

    def test_extract_data_from_tsv(self):
        """Parses a classic table

        This method is ported from QIIME (http://www.qiime.org). QIIME is a GPL
        project, but we obtained permission from the authors of this method to
        port it to the BIOM Format project (and keep it under BIOM's BSD
        license).
        """
        input = legacy_otu_table1.splitlines()
        samp_ids = ['Fing', 'Key', 'NA']
        obs_ids = ['0', '1', '7', '3', '4']
        metadata = [
            'Bacteria; Actinobacteria; Actinobacteridae; Propionibacterineae; '
            'Propionibacterium',
            'Bacteria; Firmicutes; Alicyclobacillaceae; Bacilli; Lactobacillal'
            'es; Lactobacillales; Streptococcaceae; Streptococcus',
            'Bacteria; Actinobacteria; Actinobacteridae; Gordoniaceae; Coryneb'
            'acteriaceae',
            'Bacteria; Firmicutes; Alicyclobacillaceae; Bacilli; Staphylococca'
            'ceae',
            'Bacteria; Cyanobacteria; Chloroplasts; vectors']
        md_name = 'Consensus Lineage'
        data = np.array([[19111, 44536, 42],
                        [1216, 3500, 6],
                        [1803, 1184, 2],
                        [1722, 4903, 17],
                        [589, 2074, 34]])

        exp = (samp_ids, obs_ids, data, metadata, md_name)
        obs = Table._extract_data_from_tsv(input, dtype=int)
        npt.assert_equal(obs, exp)

    def test_bin_samples_by_metadata(self):
        """Yield tables binned by sample metadata"""
        f = lambda id_, md: md['age']
        obs_ids = ['a', 'b', 'c', 'd']
        samp_ids = ['1', '2', '3', '4']
        data = {(0, 0): 1, (0, 1): 2, (0, 2): 3, (0, 3): 4,
                (1, 0): 5, (1, 1): 6, (1, 2): 7, (1, 3): 8,
                (2, 0): 8, (2, 1): 9, (2, 2): 10, (2, 3): 11,
                (3, 0): 12, (3, 1): 13, (3, 2): 14, (3, 3): 15}
        obs_md = [{}, {}, {}, {}]
        samp_md = [{'age': 2, 'foo': 10}, {'age': 4}, {'age': 2, 'bar': 5}, {}]
        t = Table(data, obs_ids, samp_ids, obs_md, samp_md)
        obs_bins, obs_tables = unzip(t.partition(f))

        exp_bins = (2, 4, None)
        exp1_data = {(0, 0): 1, (0, 1): 3, (1, 0): 5, (1, 1): 7, (2, 0): 8,
                     (2, 1): 10, (3, 0): 12, (3, 1): 14}
        exp1_obs_ids = ['a', 'b', 'c', 'd']
        exp1_samp_ids = ['1', '3']
        exp1_obs_md = [{}, {}, {}, {}]
        exp1_samp_md = [{'age': 2, 'foo': 10}, {'age': 2, 'bar': 5}]
        exp1 = Table(exp1_data, exp1_obs_ids, exp1_samp_ids, exp1_obs_md,
                     exp1_samp_md)
        exp2_data = {(0, 0): 2, (1, 0): 6, (2, 0): 9, (3, 0): 13}
        exp2_obs_ids = ['a', 'b', 'c', 'd']
        exp2_samp_ids = ['2']
        exp2_obs_md = [{}, {}, {}, {}]
        exp2_samp_md = [{'age': 4}]
        exp2 = Table(exp2_data, exp2_obs_ids, exp2_samp_ids, exp2_obs_md,
                     exp2_samp_md)
        exp3_data = {(0, 0): 4, (1, 0): 8, (2, 0): 11, (3, 0): 15}
        exp3_obs_ids = ['a', 'b', 'c', 'd']
        exp3_samp_ids = ['4']
        exp3_obs_md = [{}, {}, {}, {}]
        exp3_samp_md = [{'age': None}]
        exp3 = Table(exp3_data, exp3_obs_ids, exp3_samp_ids, exp3_obs_md,
                     exp3_samp_md)
        exp_tables = (exp1, exp2, exp3)

        exp1_idx = obs_bins.index(exp_bins[0])
        exp2_idx = obs_bins.index(exp_bins[1])
        exp3_idx = obs_bins.index(exp_bins[2])
        obs_sort = (obs_bins[exp1_idx], obs_bins[exp2_idx], obs_bins[exp3_idx])
        self.assertEqual(obs_sort, exp_bins)
        obs_sort = (obs_tables[exp1_idx], obs_tables[exp2_idx],
                    obs_tables[exp3_idx])

        self.assertEqual(obs_sort, exp_tables)

        # We should get the same table type back.
        exp_types = (Table, Table, Table)
        obs_sort = (type(obs_tables[exp1_idx]), type(obs_tables[exp2_idx]),
                    type(obs_tables[exp3_idx]))
        self.assertEqual(obs_sort, exp_types)

        # Test passing a different constructor. We should get the same data
        # equality, but different table types.
        obs_bins, obs_tables = unzip(t.partition(f))

        obs_sort = (obs_bins[exp1_idx], obs_bins[exp2_idx], obs_bins[exp3_idx])
        self.assertEqual(obs_sort, exp_bins)
        obs_sort = (obs_tables[exp1_idx], obs_tables[exp2_idx],
                    obs_tables[exp3_idx])
        self.assertEqual(obs_sort, exp_tables)
        exp_types = (Table, Table, Table)
        obs_sort = (type(obs_tables[exp1_idx]), type(obs_tables[exp2_idx]),
                    type(obs_tables[exp3_idx]))
        self.assertEqual(obs_sort, exp_types)

    def test_bin_observations_by_metadata(self):
        """Yield tables binned by observation metadata"""
        def make_level_f(level):
            def f(id_, metadata):
                return metadata['taxonomy'][:level]
            return f

        func_king = make_level_f(1)
        func_phy = make_level_f(2)

        obs_ids = ['a', 'b', 'c']
        samp_ids = [1, 2, 3]
        data = {(0, 0): 1, (0, 1): 2, (0, 2): 3,
                (1, 0): 4, (1, 1): 5, (1, 2): 6,
                (2, 0): 7, (2, 1): 8, (2, 2): 9}
        obs_md = [{"taxonomy": ['k__a', 'p__b', 'c__c']},
                  {"taxonomy": ['k__a', 'p__b', 'c__d']},
                  {"taxonomy": ['k__a', 'p__c', 'c__e']}]
        t = Table(data, obs_ids, samp_ids, observation_metadata=obs_md)

        exp_king_obs_ids = ['a', 'b', 'c']
        exp_king_samp_ids = [1, 2, 3]
        exp_king_obs_md = [{"taxonomy": ['k__a', 'p__b', 'c__c']},
                           {"taxonomy": ['k__a', 'p__b', 'c__d']},
                           {"taxonomy": ['k__a', 'p__c', 'c__e']}]
        exp_king = Table(data, exp_king_obs_ids, exp_king_samp_ids,
                         observation_metadata=exp_king_obs_md)
        obs_bins, obs_king = unzip(t.partition(func_king, axis='observation'))

        self.assertEqual(obs_king, [exp_king])
        self.assertEqual(obs_bins, [tuple(['k__a'])])
        self.assertEqual(type(obs_king[0]), type(exp_king))

        obs_bins, obs_king = unzip(t.partition(func_king, axis='observation'))
        self.assertEqual(obs_king, [exp_king])
        self.assertEqual(obs_bins, [tuple(['k__a'])])
        self.assertEqual(type(obs_king[0]), Table)

        exp_phy1_obs_ids = ['a', 'b']
        exp_phy1_samp_ids = [1, 2, 3]
        exp_phy1_data = np.array([[1, 2, 3], [4, 5, 6]])
        exp_phy1_data = {(0, 0): 1, (0, 1): 2, (0, 2): 3,
                         (1, 0): 4, (1, 1): 5, (1, 2): 6}
        exp_phy1_obs_md = [{"taxonomy": ['k__a', 'p__b', 'c__c']},
                           {"taxonomy": ['k__a', 'p__b', 'c__d']}]
        exp_phy1 = Table(exp_phy1_data, exp_phy1_obs_ids, exp_phy1_samp_ids,
                         observation_metadata=exp_phy1_obs_md)
        exp_phy2_obs_ids = ['c']
        exp_phy2_samp_ids = [1, 2, 3]
        exp_phy2_data = {(0, 0): 7, (0, 1): 8, (0, 2): 9}
        exp_phy2_obs_md = [{"taxonomy": ['k__a', 'p__c', 'c__e']}]
        exp_phy2 = Table(exp_phy2_data, exp_phy2_obs_ids, exp_phy2_samp_ids,
                         observation_metadata=exp_phy2_obs_md)
        obs_bins, obs_phy = unzip(t.partition(func_phy, axis='observation'))
        self.assertEqual(obs_phy, [exp_phy1, exp_phy2])
        self.assertEqual(obs_bins, [('k__a', 'p__b'), ('k__a', 'p__c')])

    def test_get_table_density(self):
        """Test correctly computes density of table."""
        # Perfectly dense tables.
        npt.assert_almost_equal(self.st1.get_table_density(), 1.0)
        npt.assert_almost_equal(self.st3.get_table_density(), 1.0)
        npt.assert_almost_equal(self.st_rich.get_table_density(), 1.0)

        # Empty table (no dimensions).
        npt.assert_almost_equal(self.empty_st.get_table_density(), 0.0)

        # Tables with some zeros.
        npt.assert_almost_equal(self.st5.get_table_density(), 0.5)

        # Tables with all zeros (with dimensions).
        npt.assert_almost_equal(self.st6.get_table_density(), 0.0)

        # Tables with some zeros explicitly defined.
        npt.assert_almost_equal(self.st7.get_table_density(), 0.75)


class SupportTests2(TestCase):

    def test_coo_arrays_to_sparse(self):
        """convert (values, (row, col)) to scipy"""
        n_rows, n_cols = 3, 4
        exp_d = lil_matrix((n_rows, n_cols))
        exp_d[(0, 0)] = 10
        exp_d[(1, 3)] = 5
        exp_d[(2, 1)] = 2
        exp_d = exp_d.tocoo()
        exp = lil_matrix((n_rows, n_cols))
        exp[(0, 0)] = 10
        exp[(1, 3)] = 5
        exp[(2, 1)] = 2
        data = (np.array([5.0, 2.0, 10.0]),
                (np.array([1, 2, 0]),
                 np.array([3, 1, 0])))
        obs = coo_arrays_to_sparse(data, shape=(n_rows, n_cols))
        self.assertEqual((obs != exp).sum(), 0)

    def test_list_list_to_sparse(self):
        """convert [[row,col,value], ...] to scipy"""
        input = [[0, 0, 1], [1, 1, 5.0], [0, 2, 6]]
        exp = lil_matrix((2, 3))
        exp[(0, 0)] = 1.0
        exp[(1, 1)] = 5.0
        exp[(0, 2)] = 6
        obs = list_list_to_sparse(input)
        self.assertEqual((obs != exp).sum(), 0)

    def test_nparray_to_sparse(self):
        """Convert nparray to sparse"""
        input = np.array([[1, 2, 3, 4], [-1, 6, 7, 8], [9, 10, 11, 12]])
        exp = lil_matrix((3, 4))
        exp[(0, 0)] = 1
        exp[(0, 1)] = 2
        exp[(0, 2)] = 3
        exp[(0, 3)] = 4
        exp[(1, 0)] = -1
        exp[(1, 1)] = 6
        exp[(1, 2)] = 7
        exp[(1, 3)] = 8
        exp[(2, 0)] = 9
        exp[(2, 1)] = 10
        exp[(2, 2)] = 11
        exp[(2, 3)] = 12
        obs = nparray_to_sparse(input)
        self.assertEqual((obs != exp).sum(), 0)

    def test_list_dict_to_sparse(self):
        """Take a list of dicts and condense down to a single dict"""
        input = [{(0, 0): 10, (0, 1): 2}, {(1, 2): 15}, {(0, 3): 7}]
        exp = lil_matrix((3, 4))
        exp[(0, 0)] = 10
        exp[(0, 1)] = 2
        exp[(1, 2)] = 15
        exp[(2, 3)] = 7
        obs = list_dict_to_sparse(input)
        self.assertEqual((obs != exp).sum(), 0)

    def test_dict_to_sparse(self):
        """Take a dict and convert to sparse"""
        input = {(0, 1): 5, (1, 0): 2, (2, 1): 6}
        exp = lil_matrix((3, 2))
        exp[(0, 1)] = 5
        exp[(1, 0)] = 2
        exp[(2, 1)] = 6
        obs = dict_to_sparse(input)
        self.assertEqual((obs != exp).sum(), 0)

    def test_to_sparse(self):
        """Convert to expected sparse types"""
        vals = {(0, 0): 5, (0, 1): 6, (1, 0): 7, (1, 1): 8}
        obs = Table._to_sparse(vals)
        exp = lil_matrix((2, 2))
        exp[(0, 0)] = 5
        exp[(0, 1)] = 6
        exp[(1, 0)] = 7
        exp[(1, 1)] = 8
        self.assertEqual((obs != exp).sum(), 0)

        input = {(0, 1): 5, (10, 8): -1.23}
        input_transpose = {(1, 0): 5, (8, 10): -1.23}

        exp = lil_matrix((11, 9))
        exp[(0, 1)] = 5
        exp[(10, 8)] = -1.23
        obs = Table._to_sparse(input)
        self.assertEqual((obs != exp).sum(), 0)

        # test transpose
        exp = lil_matrix((9, 11))
        exp[(1, 0)] = 5
        exp[(8, 10)] = -1.23
        obs = Table._to_sparse(input_transpose)
        self.assertEqual((obs != exp).sum(), 0)

        # passing a list of dicts, transpose
        exp = lil_matrix((3, 2))
        exp[(0, 0)] = 5.0
        exp[(1, 0)] = 6.0
        exp[(2, 0)] = 7.0
        exp[(0, 1)] = 8.0
        exp[(1, 1)] = 9.0
        exp[(2, 1)] = 10.0
        obs = Table._to_sparse([{(0, 0): 5, (1, 0): 6, (2, 0): 7},
                                {(0, 1): 8, (1, 1): 9, (2, 1): 10}])
        self.assertEqual((obs != exp).sum(), 0)

        # passing a list of lil_matrix
        exp = lil_matrix((2, 3))
        exp[(0, 0)] = 5
        exp[(0, 1)] = 6
        exp[(0, 2)] = 7
        exp[(1, 0)] = 8
        exp[(1, 1)] = 9
        exp[(1, 2)] = 10
        row1 = lil_matrix((1, 3))
        row1[(0, 0)] = 5
        row1[(0, 1)] = 6
        row1[(0, 2)] = 7
        row2 = lil_matrix((1, 3))
        row2[(0, 0)] = 8
        row2[(0, 1)] = 9
        row2[(0, 2)] = 10
        obs = Table._to_sparse([row1, row2])
        self.assertEqual((obs != exp).sum(), 0)

        # test empty set
        exp = lil_matrix((0, 0))
        obs = Table._to_sparse([])
        self.assertEqual((obs != exp).sum(), 0)

    def test_list_nparray_to_sparse(self):
        """lists of nparrays to sparse"""
        ins = [np.array([0, 2, 1, 0]), np.array([1, 0, 0, 1])]
        exp = lil_matrix((2, 4))
        exp[(0, 1)] = 2
        exp[(0, 2)] = 1
        exp[(1, 0)] = 1
        exp[(1, 3)] = 1
        obs = list_nparray_to_sparse(ins)
        self.assertEqual((obs != exp).sum(), 0)

    def test_list_sparse_to_sparse(self):
        """list of lil_matrix to sparse"""
        ins = [lil_matrix((1, 4)), lil_matrix((1, 4))]
        ins[0][0, 0] = 5
        ins[0][0, 1] = 10
        ins[1][0, 2] = 1
        ins[1][0, 3] = 2
        exp = lil_matrix((2, 4))
        exp[0, 0] = 5
        exp[0, 1] = 10
        exp[1, 2] = 1
        exp[1, 3] = 2
        obs = list_sparse_to_sparse(ins)
        self.assertEqual((obs != exp).sum(), 0)

legacy_otu_table1 = """# some comment goes here
#OTU id\tFing\tKey\tNA\tConsensus Lineage
0\t19111\t44536\t42 \tBacteria; Actinobacteria; Actinobacteridae; Propioniba\
cterineae; Propionibacterium

1\t1216\t3500\t6\tBacteria; Firmicutes; Alicyclobacillaceae; Bacilli; La\
ctobacillales; Lactobacillales; Streptococcaceae; Streptococcus
7\t1803\t1184\t2\tBacteria; Actinobacteria; Actinobacteridae; Gordoniace\
ae; Corynebacteriaceae
3\t1722\t4903\t17\tBacteria; Firmicutes; Alicyclobacillaceae; Bacilli; St\
aphylococcaceae
4\t589\t2074\t34\tBacteria; Cyanobacteria; Chloroplasts; vectors
"""
otu_table1 = """# Some comment
#OTU ID\tFing\tKey\tNA\tConsensus Lineage
0\t19111\t44536\t42\tBacteria; Actinobacteria; Actinobacteridae; \
Propionibacterineae; Propionibacterium
# some other comment
1\t1216\t3500\t6\tBacteria; Firmicutes; Alicyclobacillaceae; Bacilli; \
Lactobacillales; Lactobacillales; Streptococcaceae; Streptococcus
7\t1803\t1184\t2\tBacteria; Actinobacteria; Actinobacteridae; Gordoniaceae; \
Corynebacteriaceae
# comments
#    everywhere!
3\t1722\t4903\t17\tBacteria; Firmicutes; Alicyclobacillaceae; \
Bacilli; Staphylococcaceae
4\t589\t2074\t34\tBacteria; Cyanobacteria; Chloroplasts; vectors
"""

OBS_META_TYPES = {'sc_separated': lambda x: [e.strip() for e in x.split(';')],
                  'naive': lambda x: x
                  }
OBS_META_TYPES['taxonomy'] = OBS_META_TYPES['sc_separated']

if __name__ == '__main__':
    main()
