#!/usr/bin/env python3

# ----------------------------------------------------------------------------
# Copyright (c) 2020--, Qiyun Zhu.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

"""Functions for manipulating tables (profiles).
"""

from functools import reduce
from collections import defaultdict
from biom import Table, load_table

from .util import allkeys, update_dict
from .tree import lineage_str
from .file import openzip
from .biom import table_to_biom, biom_to_table, write_biom, filter_biom


def prep_table(profile, samples=None, tree=None, rankdic=None, namedic=None,
               name_as_id=False):
    """Convert a profile into data, features and samples, as well as metadata
    if applicable, which can be further converted into a TSV file, a BIOM table
    or a Pandas DataFrame.

    Parameters
    ----------
    profile : dict
        Profile data.
    samples : list, optional
        Ordered sample ID list.
    tree : dict, optional
        Taxonomic tree, to inform "Lineage" column.
    rankdic : dict, optional
        Rank dictionary, to inform "Rank" column.
    namedic : dict, optional
        Taxon name dictionary, to inform "Name" column.
    name_as_id : bool, optional
        Replace feature IDs with names. It applies to row headers and "Lineage"
        column, and removes "Name" column.

    Returns
    -------
    list of list
        Data (2D array of values).
    list
        Features (rows, Pandas index, or BIOM observation IDs).
    list
        Samples (columns, Pandas columns, or BIOM sample IDs).
    list of dict
        Metadata (extra columns, or BIOM observation metadata).

    Examples
    --------
    Convert output to a BIOM table:
    >>> import biom
    >>> args = profile, samples, tree, rankdic, namedic, name_as_id
    >>> table = biom.Table(prep_table(*args))

    Convert output to a Pandas DataFrame (data only):
    >>> import pandas as pd
    >>> data, features, samples, metadata = prep_table(*args)
    >>> df = pd.DataFrame(data, features, samples)

    Convert output to a Pandas DataFrame (data and metadata):
    >>> df = pd.concat([pd.DataFrame(data, features, samples),
                        pd.DataFrame.from_records(metadata, features)], axis=1)

    See Also
    --------
    write_tsv
    .biom.table_to_biom
    .workflow.write_profiles

    Notes
    -----
    Optionally, three metadata columns, "Name", "Rank" and "Lineage" will be
    appended to the table.

    A feature will be dropped if all its values are zero. However, samples will
    not be dropped even when empty.

    A stratified feature will be printed as "stratum|feature".
    """
    # determine range and order of samples
    samples = [x for x in samples if x in profile] if samples else sorted(
        profile)

    # determine metadata columns
    namecol = namedic and not name_as_id or None
    metacols = tuple(filter(None, (
        namecol and 'Name', rankdic and 'Rank', tree and 'Lineage')))

    notnone = None.__ne__
    features, data, metadata = [], [], []

    # sort features in alphabetical order
    for key in sorted(allkeys(profile)):

        # determine cell values (feature counts)
        datum = [profile[x][key] if key in profile[x] else 0 for x in samples]
        if not any(datum):
            continue
        data.append(datum)

        # determine feature Id
        stratum, taxon = key if isinstance(key, tuple) else (None, key)
        name = namedic[taxon] if namedic and taxon in namedic else None
        feature = name if name_as_id and name else taxon
        feature = f'{stratum}|{feature}' if stratum else feature
        features.append(feature)

        # determine metadata
        metadatum = dict(zip(metacols, filter(notnone, (
            namecol and (name or ''),
            rankdic and (rankdic[taxon] if taxon in rankdic else ''),
            tree and lineage_str(
                taxon, tree, namedic if name_as_id else None)))))
        metadata.append(metadatum)

    return data, features, samples, metadata


def read_table(fp):
    """Read a feature table (profile) from an input file, while automatically
    recognizing its format (BIOM or TSV).

    Parameters
    ----------
    fp : str
        Input filepath.

    Returns
    -------
    biom.Table or tuple
        Table that was read.
    str
        Format of table ('biom' or 'tsv)

    Raises
    ------
    ValueError
        Cannot read table.
    """
    with open(fp, 'r') as fh:
        try:
            table = read_tsv(fh)
        except UnicodeDecodeError:
            try:
                table = load_table(fp)
            except (TypeError, UnicodeDecodeError):
                raise ValueError(
                    'Input file cannot be parsed as BIOM or TSV format.')
            else:
                return table, 'biom'
        else:
            return table, 'tsv'


def write_table(table, fp, is_biom=None):
    """Write a feature table (profile) to an output file, while automatically
    matching format (BIOM or TSV).

    Parameters
    ----------
    table : biom.Table or tuple
        Table to be written.
    fp : str
        Output filepath.
    is_biom : bool, optional
        Output BIOM or TSV format. If not specified, will automatically
        determine based on output filename.
    """
    if is_biom is not False and fp.endswith('.biom'):
        if isinstance(table, tuple):
            table = table_to_biom(*table)
        write_biom(table, fp)
    else:
        if isinstance(table, Table):
            table = biom_to_table(table)
        with openzip(fp, 'wt') as fh:
            write_tsv(table, fh)


def read_tsv(fh):
    """Read a tab-delimited file into table components.

    Parameters
    ----------
    fh : file handle
        Output file.

    Returns
    -------
    list of list
        Profile data.
    list
        Feature IDs (row names).
    list
        Sample IDs (column names).
    list of dict
        Feature metadata (extra columns).

    Raises
    ------
    ValueError
        Input table file is empty.
    ValueError
        Input table file has no sample.
    """
    # get header (1st line)
    try:
        header = next(fh).rstrip('\r\n').split('\t')
    except StopIteration:
        raise ValueError('Input table file is empty.')

    # extract metadata columns
    header, metacols = strip_metacols(header)

    # extract sample Ids
    samples = header[1:]
    if not samples:
        raise ValueError('Input table file has no sample.')

    # parse table body
    data, features, metadata = [], [], []
    width = len(header)
    for line in fh:
        row = line.rstrip('\r\n').split('\t')
        feature = row[0]
        features.append(feature)
        data.append(list(map(int, row[1:width])))
        metadata.append(dict(zip(metacols, row[width:])))

    return data, features, samples, metadata


def write_tsv(table, fh):
    """Write table components to a tab-delimited file.

    Parameters
    ----------
    table : tuple
        Table components to write.
    fh : file handle
        Output file.

    Notes
    -----
    The output table will have columns as samples and rows as features.
    Optionally, three metadata columns, "Name", "Rank" and "Lineage" will be
    appended to the right of the table.
    """
    data, features, samples, metadata = table

    # metadata columns
    metacols = next(iter(metadata), {}).keys() if metadata else None

    # table header
    header = ['#FeatureID', '\t'.join(samples)]
    if metacols:
        header.append('\t'.join(metacols))
    print(*header, sep='\t', file=fh)

    # table body
    for i, feature in enumerate(features):
        row = [feature, '\t'.join(map(str, data[i]))]
        if metacols:
            row.append('\t'.join(metadata[i].values()))
        print(*row, sep='\t', file=fh)


def strip_metacols(header, cols=['Name', 'Rank', 'Lineage']):
    """Extract ordered metadata columns from the right end of a table header.

    Parameters
    ----------
    header : list
        Table header.
    cols : list, optional
        Candidate columns in order.

    Returns
    -------
    list
        Table header with metadata columns stripped.
    list
        Extracted metadata columns.

    Notes
    -----
    Metadata columns can be whole or a subset of the provided candidates, but
    they must appear in the given order at the right end of the table header.
    Unordered and duplicated columns as well as columns mixed within samples
    will not be extracted.
    """
    res = []
    for col in reversed(header):
        try:
            cols = cols[slice(cols.index(col))]
        except ValueError:
            break
        else:
            res.append(col)
    return header[:-len(res) or None], res[::-1]


def table_shape(table):
    """Get feature and sample counts of a table.

    Parameters
    ----------
    table : biom.Table, or tuple of (list, list, list, list)
        Table to count (data, features, samples, metadata).

    Returns
    -------
    int
        Number of features.
    int
        Number of samples.
    """
    if isinstance(table, Table):
        return table.shape
    return len(table[1]), len(table[2])


def filter_table(table, th):
    """Filter a table by per-sample count or percentage threshold.

    Parameters
    ----------
    table : biom.Table, or tuple of (list, list, list, list)
        Table to filter (data, features, samples, metadata).
    th : float
        Per-sample minimum abundance threshold. If >= 1, this value is an
        absolute count; if < 1, it is a fraction of sum of counts.

    Returns
    -------
    biom.Table, or tuple of (list, list, list, list)
        Filtered table (data, features, samples, metadata).
    """
    # redirect to BIOM module
    if isinstance(table, Table):
        return filter_biom(table, th)

    # filtering function to apply to each column
    def f(datum, th):
        bound = th if th >= 1 else sum(datum) * th
        return [0 if x < bound else x for x in datum]

    # transpose data array, apply function to each column (now row), then
    # transpose back
    res = ([], [], table[2], [])
    for i, datum in enumerate(zip(*(f(x, th) for x in zip(*table[0])))):
        if not any(datum):
            continue
        res[0].append(list(datum))
        res[1].append(table[1][i])
        res[3].append(table[3][i])

    return res


def merge_tables(tables):
    """Merge multiple tables into one.

    Parameters
    ----------
    tables : list
        Table to merge.

    Returns
    -------
    biom.Table, or tuple of (list, list, list, list)
        Merged table.
    """
    # merge BIOM tables using built-in method
    if all(isinstance(x, Table) for x in tables):
        return reduce(lambda a, b: a.merge(b), tables)

    data = defaultdict(lambda: defaultdict(int))
    metadata = {}
    for table in tables:
        if isinstance(table, Table):
            table = biom_to_table(table)

        # update metadata
        try:
            update_dict(metadata, dict(zip(table[1], table[3])))
        except AssertionError:
            raise ValueError('Conflicting metadata found in tables.')

        # update data
        for feature, datum in zip(table[1], table[0]):
            for sample, value in zip(table[2], datum):
                data[sample][feature] += value

    res = prep_table(data)
    return res[0], res[1], res[2], [metadata[x] for x in res[1]]
