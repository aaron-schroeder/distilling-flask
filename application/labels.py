"""Custom pd column label class to handle fields and sources.

Originally implemented in hns, I am seeing if it makes sense to make
it into its owwwwwwwn thaaaaang.
"""

import inspect
import sys

import pandas as pd


def convert_stream_label(stream_label):
  """Attempt to convert string to StreamLabel.

  Args:
    stream_label (str): field name to be converted to StreamLabel class.
  Returns:
    A StreamLabel instance corresponding to the input object.

  """
  if stream_label is None or isinstance(stream_label, StreamLabel):
    # No need to convert.
    return stream_label

  # This will return a TypeError if passed other than a string.
  # (I previously was working with the exception within this method)
  return StreamLabel(field=stream_label, source='unknown')


class StreamLabel(object):

  def __init__(self, field=None, source=None, **kwargs):
    """
    Args:
      source_name (str): name of the source.
      method (str): the method that was used to produce the data
       from any number of other sources. Default `name`.
      units (str): (optional) string representing units of the data.
        Defaults to DEFAULT_UNITS, defined by subclasses.
      **kwargs: the remaining kwargs list functions as a dict of other
        sources used to produce data corresponding to this source. 
        This functionality is implemented in subclasses.
    """
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

    if field is None:
      raise(ValueError(
        f'`field` is a required kwarg'
      ))

    if source is None:
      raise(ValueError(
        f'`source` is a required kwarg'
      ))

    self.source_name = source.lower()
    self.field_name = field.lower()

    # Define units. 
    self.units = kwargs.pop('units', None)
    if isinstance(self.units, str):
      self.units = self.units.lower()

    # Set attributes dynamically based on kwargs.
    # eg `self.latlon = StreamLabel('src')
    # TODO: Figure out the new way I handle this. Wine.
    for fld_type, src in kwargs.items():
      if isinstance(src, str):
        src = StreamLabel(src)

      if not isinstance(src, StreamLabel):
        raise TypeError('All kwargs should be str or StreamLabel')
      
      setattr(self, fld_type, src)

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
    return self.__repr__() < other.__repr__()

  def __gt__(self, other):
    return self.__repr__() > other.__repr__()

  def __hash__(self):
    return hash(self.__repr__())

  def get_source_kwargs(self):
    return {key: self.__dict__[key] for key in sorted(self.__dict__)
            if key not in ['units', 'source_name', 'field_name']}


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
        
      # TODO: Once I find a way to convert `${field}_${src}` strings
      # to StreamLabels:
      #   raise AttributeError('Can only use .sl accessor with string '
      #                       'or StreamLabel values!')

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
  """Experimental class that piggybacks on the index accessor."""
  
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
  
  def set(self, field_source_str, series):
    self._obj[StreamLabel.from_str(field_source_str)] = series

  def get(self, *args):
    if len(args) == 1:
      return self._obj[StreamLabel.from_str(args)]
    else:
      return (self._obj[StreamLabel.from_str(arg)] for arg in args)

  # def loc(self, field_name, source_name):
  #   return self._obj[StreamLabel(field=field_name, source=source_name)]

  # @property
  # def oc(self):  #, field_source_str):
  #   """Idea: return the `.loc` indexer object, indexed w/ StreamLabel.

  #   Cheeky take on `df.loc` -> `df.sl.oc` ...get it??
    
  #   Tried to make setting work. It does not work right. Abandoned.

  #   This needs to return an object capable of getting and setting, not
  #   the result of that getting and setting.

  #   https://stackoverflow.com/questions/53268739/how-to-use-the-loc-method-from-pandas-on-a-custom-class-object
  #   https://github.com/pandas-dev/pandas/blob/d01561fb7b9ad337611fa38a3cfb7e8c2faec608/pandas/core/indexing.py#L264-L522
  #   https://github.com/pandas-dev/pandas/blob/d01561fb7b9ad337611fa38a3cfb7e8c2faec608/pandas/core/indexing.py#L951
    
  #   """
  #   # _obj_copy = self._obj.copy()
  #   # _obj_copy.columns = [col.to_str() if isinstance(col, StreamLabel) else col for col in _obj_copy.columns]
  #   # return pd.core.indexing._LocIndexer('oc', _obj_copy)(axis=1)

  #   self._obj.columns = [col.to_str() if isinstance(col, StreamLabel) else col for col in self._obj.columns]
  #   indexer = pd.core.indexing._LocIndexer('oc', self._obj)(axis=1)

  #   return indexer