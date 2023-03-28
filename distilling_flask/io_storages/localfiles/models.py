import os
from pathlib import Path
import re

from distilling_flask import db
from distilling_flask.io_storages.models import ImportStorage, ImportStorageLink


class LocalFilesImportStorage(ImportStorage):
  path = db.Column(db.Text)
  # regex_filter = db.Column(db.Text)

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
    # For better control of imported tasks, file reading has been changed to ascending order of filenames.
    # In other words, the task IDs are sorted by filename order.
    for file in sorted(path.rglob('*'), key=os.path.basename):
      if file.is_file():
        key = file.name
        if regex and not regex.match(key):
          # logger.debug(key + ' is skipped by regex filter')
          continue
        yield str(file)

  def get_data(self, key):
    raise NotImplementedError
    path = Path(key)
    # try:
    #     with open(path, encoding='utf8') as f:
    #         value = json.load(f)
    # except (UnicodeDecodeError, json.decoder.JSONDecodeError):
    #     raise ValueError(
    #         f"Can\'t import JSON-formatted tasks from {key}. If you're trying to import binary objects, "
    #         f"perhaps you've forgot to enable \"Treat every bucket object as a source file\" option?")

    # if not isinstance(value, dict):
    #     raise ValueError(f"Error on key {key}: For {self.__class__.__name__} your JSON file must be a dictionary with one task.")  # noqa
    # return value

  def scan_and_create_links(self):
    return self._scan_and_create_links(LocalFilesImportStorageLink)
  

class LocalFilesImportStorageLink(ImportStorageLink):
  pass