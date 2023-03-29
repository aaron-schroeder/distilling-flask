import datetime
import os
from pathlib import Path
import warnings

from sqlalchemy.sql import func
from sqlalchemy.orm import declared_attr

from distilling_flask import celery, db
from distilling_flask.util.redis import redis_connected


class Storage(db.Model):
  __abstract__ = True
  
  if os.getenv('ff_rename'):
    id = db.Column(
      db.Integer,
      primary_key=True
    )
    @property
    def strava_id(self):
      # warnings.warn(
      print('The use of `strava_id` for StravaImportStorage is '
                    'deprecated in favor of `id`.')
      return self.id
  else:
    strava_id = db.Column(
      db.Integer,
      primary_key=True
    )

  @declared_attr
  def entities(self):
    return db.relationship('ImportStorageEntity', backref='import_storage', lazy='dynamic')
  # created_at = models.DateTimeField(_('created at'), auto_now_add=True, help_text='Creation time')
  # last_sync = models.DateTimeField(_('last sync'), null=True, blank=True, help_text='Last sync finished time')
  # last_sync_count = models.PositiveIntegerField(
  #     _('last sync count'), null=True, blank=True, help_text='Count of tasks synced last time'
  # )
  # last_sync_job = models.CharField(_('last_sync_job'), null=True, blank=True, max_length=256, help_text='Last sync job ID')

  def validate_connection(self, client=None):
    pass

class ImportStorage(Storage):
  __abstract__ = True
  
  def iterkeys(self):
    raise NotImplementedError

  def get_data(self, key):
    raise NotImplementedError

  def scan_and_create_entities(self):
    return self._scan_and_create_entities(ImportStorageEntity)
  
  def _scan_and_create_entities(self, entity_cls):
    # NOTE: In label-studio, seems to be called exclusively by
    # `ImportStorage.sync()`, which is called by
    # ImportStorageSyncAPI. Here is the other stuff the api does:
    # ```
    # storage = self.get_object()
    # # check connectivity & access, raise an exception if not satisfied
    # storage.validate_connection()
    # storage.sync()
    # storage.refresh_from_db()  # django model method
    # ```

    entities_created = 0
    # maximum_annotations = self.project.maximum_annotations
    # task = self.project.tasks.order_by('-inner_id').first()
    # max_inner_id = (task.inner_id + 1) if task else 1

    for key in self.iterkeys():
      # logger.debug(
      print(f'Scanning key {key}')

      # skip if task already exists
      if entity_cls.exists(key, self):
        # logger.debug(
        print(f'{self.__class__.__name__} entity {key} already exists')
        continue

      # logger.debug(
      print(f'{self}: found new key {key}')

      # try:
      data = self.get_data(key)
      # except (UnicodeDecodeError, json.decoder.JSONDecodeError) as exc:
      #     # logger.debug(exc, exc_info=True)
      #     raise ValueError(
      #         f'Error loading JSON from file "{key}".\nIf you\'re trying to import non-JSON data '
      #         f'(images, audio, text, etc.), edit storage settings and enable '
      #         f'"Treat every bucket object as a source file"'
      #     )

      # self.add_task(data, self, key, entity_cls)
      # activity = Activity(data=data)
      # db.session.add(activity)
      db.session.add(entity_cls(key, self, **data))
      # logger.debug(
      print(f'Create {self.__class__.__name__} entity with key={key}')

      # max_inner_id += 1
      entities_created += 1

    self.last_sync = datetime.datetime.now()  # timezone.now()
    self.last_sync_count = entities_created
    # self.save()
    # db.session.

  def sync(self):
    if redis_connected():
      job_id = sync_background.delay(self.__class__, self.id)
      print(f'Storage sync background job {job_id} for storage {self} has been started')
      
      # queue = django_rq.get_queue('low')
      # meta = {'project': self.project.id, 'storage': self.id}
      # if not is_job_in_queue(queue, "sync_background", meta=meta) and \
      #         not is_job_on_worker(job_id=self.last_sync_job, queue_name='default'):
      #     job = queue.enqueue(sync_background, self.__class__, self.id,
      #                         meta=meta)
      #     self.last_sync_job = job.id
      #     self.save()
      #     # job_id = sync_background.delay()  # TODO: @niklub: check this fix
      #     logger.info(f'Storage sync background job {job.id} for storage {self} has been started')
    else:
      # logger.info(
      print(f'Start syncing storage {self}')
      self.scan_and_create_entities()


@celery.task()
def sync_background(storage_class, storage_id, **kwargs):
  storage = db.session.get(storage_class, storage_id)
  storage.scan_and_create_entities()


class ImportStorageEntity(db.Model):
  __abstract__ = True

  id = db.Column(db.Integer, primary_key=True)
  if os.getenv('ff_rename'):
    key = db.Column(db.String, nullable=False, unique=True, doc='External entity key')
    @property
    def strava_id(self):
      # warnings.warn(
      print('The use of `strava_id` for StravaApiActivity is '
                    'deprecated in favor of `key`.')
      return self.key
  else:
    strava_id = db.Column(db.String, nullable=False, doc='External entity key')
  object_exists = db.Column(db.Boolean, default=True,
    doc='Whether object under external entity still exists')
  created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(),
                         doc='Creation time')
  # updated_at = db.Column(db.DateTime(timezone=True), onupdate=func.now(),
  #                        doc='Last updated time')
  
  @declared_attr
  def strava_acct_id(self):
    return db.Column(db.Integer, db.ForeignKey('import_storage.id'))

  # @declared_attr
  # def import_storage_id(self):
  #   return db.Column(db.Integer, db.ForeignKey('import_storage.id'))

  @classmethod
  def exists(cls, key, storage):
    return len(db.session.execute(db.select(cls).filter_by(key=key, storage_id=storage.id))) > 0
