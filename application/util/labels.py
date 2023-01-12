"""Custom pd column label class to handle fields and sources.

Originally implemented in hns, I am seeing if it makes sense to make
it into its owwwwwwwn thaaaaang.
"""

import inspect
import sys

import pandas as pd


class StreamLabel(object):

  def __init__(self, field=None, source=None, **kwargs):
    """Initialize a StreamLabel for use as a pd.DataFrame column label.
    
    Args:
      field (str): name of the field represented by the data stream
        in the column.
      source (str): source of the data stream in the column.

    """
    if field is None:
      raise(ValueError(
        f'`field` is a required kwarg'
      ))

    if source is None:
      raise(ValueError(
        f'`source` is a required kwarg'
      ))

    if not isinstance(field, str):
      raise(TypeError(
        f'`field` kwarg should be str, not '
        f'{type(field).__name__}'
      ))

    if not isinstance(source, str):
      raise(TypeError(
        f'`source` kwarg should be str, not '
        f'{type(source).__name__}'
      ))

    self.source_name = source.lower()
    self.field_name = field.lower()

  @classmethod
  def from_str(cls, field_src_str, delim='~'):
    field_name, source_name = field_src_str.split(delim, 1)
    
    return cls(field=field_name, source=source_name)

  def to_str(self, delim='~'):
    # Note: this won't necessarily round-trip with `from_str`.
    # If the delimiter appears in `field_name`, `from_str` will
    # infer that the field name ends at the delimiter.
    return f'{self.field_name}{delim}{self.source_name}'

  def __repr__(self):
    return f'{self.__class__.__name__}' +  \
           f'({self.field_name.__repr__()}, {self.source_name.__repr__()})'

  def __str__(self):
    return f'{self.field_name} ({self.source_name})'

  def __eq__(self, other):
    try:
      return self.__repr__() == other or self.__repr__() == other.__repr__()
    except AttributeError:
      return False

  def __lt__(self, other):
    # Might be useful to re-evaluate (+gt) for sorting.
    # eg alphabetize by field, then by source.
    return self.__repr__() < other.__repr__()

  def __gt__(self, other):
    return self.__repr__() > other.__repr__()

  def __hash__(self):
    return hash(self.__repr__())


@pd.api.extensions.register_index_accessor('sl')
class StreamIndexAccessor:
  """
  See also:
  https://github.com/pandas-dev/pandas/blob/2c80640ef79f6caa6d24234fd0ee419954b379ca/pandas/core/strings/accessor.py
  
  """

  def __init__(self, pandas_obj):
    self._validate(pandas_obj)    
    self._obj = pandas_obj

  @staticmethod
  def _validate(data):
    """Check the dtype of the index.
    As required by:
    https://pandas.pydata.org/docs/reference/api/pandas.api.extensions.register_index_accessor.html#pandas.api.extensions.register_index_accessor
    """
    # Consider adding this check:
    # raise AttributeError('Can only use .sl accessor with Index, '
    #                      'not MultiIndex')

    if data.dtype != 'object':
      raise AttributeError(
        'Can only use .sl accessor with dtype="object"!'
      )
        
      # TODO: Once (if) I find a way to convert `${field}_${src}` strings
      # to StreamLabels:
      #   raise AttributeError('Can only use .sl accessor with string '
      #                        'or StreamLabel values!')

    if not data.map(lambda x: isinstance(x, StreamLabel)).all():
      raise AttributeError(
        'Can only use .sl accessor with StreamLabel values!'
      )
      
  def field(self, field_name):
    """Return labels that match the given field name."""
    #series = self._obj.to_series().apply(lambda x: x.field_name == field_name)
    sub_index = self._obj[self._obj.map(lambda x: x.field_name == field_name)]
    
    return sub_index

  def source(self, source_name):
    """Return labels that match the given source name."""

    return self._obj[self._obj.map(lambda x: x.source_name == source_name)]

  @property
  def field_names(self):
    return self._obj.map(lambda x: x.field_name)

  @property
  def source_names(self):
    return self._obj.map(lambda x: x.source_name)


@pd.api.extensions.register_dataframe_accessor('sl')
class StreamDataFrameAccessor:
  """Mainly piggybacks on the corresponding Index accessor."""
  
  def __init__(self, pandas_obj):   
    self._obj = pandas_obj

  def field(self, field_name):
    return self._obj[self._obj.columns.sl.field(field_name)]

  def source(self, source_name):
    return self._obj[self._obj.columns.sl.source(source_name)]

  def has_source(self, source_name):
    return source_name in self._obj.columns.sl.source_names

  def has_field(self, field_name):
    return field_name in self._obj.columns.sl.field_names

  def has_fields(self, *args):
    return all(self.has_field(field_name) for field_name in args)


@pd.api.extensions.register_dataframe_accessor('fld')
class FieldDataFrameAccessor:
  """Convenience accessor to check for column labels in a DataFrame."""
  
  def __init__(self, pandas_obj):   
    self._obj = pandas_obj

  def has(self, *field_names):
    return all(field_name in self._obj.columns for field_name in field_names)
