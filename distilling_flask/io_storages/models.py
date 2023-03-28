import datetime
import os
from pathlib import Path
import re

from distilling_flask import db


class Storage(db.Model):
  """Abstract class"""
  id = db.Column(
    db.Integer,
    primary_key=True
  )
  # created_at = models.DateTimeField(_('created at'), auto_now_add=True, help_text='Creation time')
  # last_sync = models.DateTimeField(_('last sync'), null=True, blank=True, help_text='Last sync finished time')
  # last_sync_count = models.PositiveIntegerField(
  #     _('last sync count'), null=True, blank=True, help_text='Count of tasks synced last time'
  # )
  # last_sync_job = models.CharField(_('last_sync_job'), null=True, blank=True, max_length=256, help_text='Last sync job ID')

  def validate_connection(self, client=None):
    pass

  # @classmethod
  # def add_task(cls, data, project, maximum_annotations, max_inner_id, storage, key, link_class):


class ImportStorage(Storage):
  def iterkeys(self):
    raise NotImplementedError

  def get_data(self, key):
    raise NotImplementedError

  # def generate_http_url(self, url):
  #   raise NotImplementedError

  @classmethod
  def add_task(cls, data):
             # cls, data, project, maximum_annotations, max_inner_id, storage, key, link_class)
    raise NotImplementedError
  
  def scan_and_create_links(self):
    return self._scan_and_create_links(ImportStorageLink)
  
  def _scan_and_create_links(self, link_cls):
    # NOTE: In label-studio, seems to be called exclusively by
    # `ImportStorage.sync()`, which is called by
    # ImportStorageSyncAPI. Here is the other stuff the api does:
    # ```
    # storage = self.get_object()
    # # check connectivity & access, raise an exception if not satisfied
    # storage.validate_connection()
    # storage.sync()
    # storage.refresh_from_db()  # ???
    # ```

    tasks_created = 0
    # maximum_annotations = self.project.maximum_annotations
    # task = self.project.tasks.order_by('-inner_id').first()
    # max_inner_id = (task.inner_id + 1) if task else 1

    for key in self.iterkeys():
      # logger.debug(f'Scanning key {key}')

      # skip if task already exists
      if link_cls.exists(key, self):
        # logger.debug(f'{self.__class__.__name__} link {key} already exists')
        continue

      # logger.debug(f'{self}: found new key {key}')
      # try:
      data = self.get_data(key)
      # except (UnicodeDecodeError, json.decoder.JSONDecodeError) as exc:
      #     # logger.debug(exc, exc_info=True)
      #     raise ValueError(
      #         f'Error loading JSON from file "{key}".\nIf you\'re trying to import non-JSON data '
      #         f'(images, audio, text, etc.), edit storage settings and enable '
      #         f'"Treat every bucket object as a source file"'
      #     )

      self.add_task(data, self, key, ImportStorageLink)
      # max_inner_id += 1
      tasks_created += 1

    self.last_sync = datetime.datetime.now()  # timezone.now()
    self.last_sync_count = tasks_created
    self.save()

  def sync(self):
    # if redis_connected():
    #   queue = django_rq.get_queue('low')
    #   meta = {'project': self.project.id, 'storage': self.id}
    #   if not is_job_in_queue(queue, "sync_background", meta=meta) and \
    #           not is_job_on_worker(job_id=self.last_sync_job, queue_name='default'):
    #       job = queue.enqueue(sync_background, self.__class__, self.id,
    #                           meta=meta)
    #       self.last_sync_job = job.id
    #       self.save()
    #       # job_id = sync_background.delay()  # TODO: @niklub: check this fix
    #       logger.info(f'Storage sync background job {job.id} for storage {self} has been started')
    # else:
    #   logger.info(f'Start syncing storage {self}')
    #   self.scan_and_create_links()
    pass


class ImportStorageLink(db.Model):
  # storage = models.ForeignKey(ImportStorage, on_delete=models.CASCADE, related_name='links')

  # task = models.OneToOneField('tasks.Task', on_delete=models.CASCADE, related_name='%(app_label)s_%(class)s')
  # key = models.TextField(_('key'), null=False, help_text='External link key')
  # object_exists = models.BooleanField(
  #   _('object exists'), help_text='Whether object under external link still exists', default=True
  # )
  # created_at = models.DateTimeField(_('created at'), auto_now_add=True, help_text='Creation time')

  @classmethod
  def exists(cls, key, storage):
    # return cls.objects.filter(key=key, storage=storage.id).exists()
    # return bool(db.session.get(cls, key))
    return len(db.session.execute(db.select(cls).filter_by(key=key, storage_id=storage.id))) > 0

  # @classmethod
  # def create(cls, task, key, storage):
  #   link, created = cls.objects.get_or_create(task_id=task.id, key=key, storage=storage, object_exists=True)
  #   return link
