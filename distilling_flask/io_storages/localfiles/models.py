import os
from pathlib import Path
import re
import zlib

from distilling_flask import db
from distilling_flask.io_storages.models import (
  ImportStorage,
  ImportStorageEntity
)


class LocalFilesImportStorageMixin:
  path = db.Column(db.Text)
  # regex_filter = db.Column(db.Text)


class LocalFilesImportStorage(LocalFilesImportStorageMixin, ImportStorage):
  def validate_connection(self):
    path = Path(self.path)
    if not path.exists():
      # label-studio instead raises a Validation Error (from DRF).
      raise ValueError(f'Path {self.path} does not exist')
    # document_root = Path(settings.LOCAL_FILES_DOCUMENT_ROOT)
    # if document_root not in path.parents:
    #   raise ValidationError(f'Path {self.path} must start with '
    #                         f'LOCAL_FILES_DOCUMENT_ROOT={settings.LOCAL_FILES_DOCUMENT_ROOT} '
    #                         f'and must be a child, e.g.: {Path(settings.LOCAL_FILES_DOCUMENT_ROOT) / "abc"}')

  def iterkeys(self):
    path = Path(self.path)
    regex = re.compile(str(self.regex_filter)) if self.regex_filter else None
    # For better control of imported entities, file reading has been changed to ascending order of filenames.
    # In other words, the LocalFile IDs are sorted by filename order.
    for file in sorted(path.rglob('*'), key=os.path.basename):
      if file.is_file():
        key = file.name
        if regex and not regex.match(key):
          # logger.debug(
          print(key + ' is skipped by regex filter')
          continue
        yield str(file)

  def get_data(self, key):
    filepath = Path(key)
    with open(filepath, 'rb') as f:
      document = zlib.compress(f.read())
    return {'document': document}

  def scan_and_create_entities(self):
    return self._scan_and_create_entities(LocalFile)
  

class LocalFile(ImportStorageEntity):
  import_storage_id = db.Column(
    db.Integer,
    db.ForeignKey('local_files_import_storage.id'),
  )
  document = db.Column(db.BLOB)

  # @property
  # def format(self):
  #   file_format = None
  #   try:
  #     file_format = os.path.splitext(self.filepath)[-1]
  #   except:
  #     pass
  #   finally:
  #     # logger.debug(
  #     print('Get file format ' + str(file_format))
  #   return file_format

  # @property
  # def content(self):
  #   # cache file body
  #   if hasattr(self, '_file_body'):
  #     body = getattr(self, '_file_body')
  #   else:
  #     body = self.document  # TODO: Handle decompression
  #     setattr(self, '_file_body', body)
  #   return body