from sqlalchemy.sql import func
from sqlalchemy.orm import declared_attr

from distilling_flask import celery, db
from distilling_flask.util.feature_flags import flag_set


class Storage(db.Model):
  __abstract__ = True
  
  if flag_set('ff_rename'):
    id = db.Column(
      db.Integer,
      primary_key=True
    )
    @property
    def strava_id(self):
      # warnings.warn(
      print('The use of `strava_id` for ImportStorage is deprecated '
            'in favor of `id`.')
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
    """
    NOTE: In label-studio, seems to be called exclusively by
    `ImportStorage.sync()`, which is called by ImportStorageSyncAPI. 
    Here is the other stuff the sync api does:
    ```
    storage = self.get_object()
    # check connectivity & access, raise an exception if not satisfied
    storage.validate_connection()
    storage.sync()
    storage.refresh_from_db()  # django model method
    ```
    """
    entities_created = 0
    for key in self.iterkeys():
      # logger.debug(
      print(f'Scanning key {key}')

      # skip if entity already exists
      if entity_cls.exists(key, self):
        # logger.debug(
        print(f'{self.__class__.__name__} entity {key} already exists')
        continue

      # logger.debug(
      print(f'{self}: found new key {key}')

      data = self.get_data(key)
      db.session.add(entity_cls(import_storage_id=self.id, **data))
      db.session.commit()  # check if intermediate commits could slow stuff down

      # logger.debug(
      print(f'Create {entity_cls.__name__} ({self.__class__.__name__} entity) with key={key}')

      # max_inner_id += 1
      entities_created += 1

    # self.last_sync = datetime.datetime.now()  # timezone.now()
    # self.last_sync_count = entities_created
    # db.session.commit()
    # # self.save()

  def sync(self):
    from distilling_flask.util.redis import redis_connected
    if redis_connected():
      # job_id = sync_background.delay(self.__class__, self.id)

      # Alt implementation (original for strava):
      # call a master task that gathers all the strava activity ids
      # then dispatches a new task for each ID.
      from distilling_flask.io_storages.strava.models import sync_strava_background
      job_id = sync_strava_background(
        # self.__class__,
        self.id,
        # handle_overlap=overlap_choice
      )

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

  if flag_set('ff_rename'):
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
  
  # created_at?                  )
  created = db.Column(
    db.DateTime,
    # db.DateTime(timezone=True)
    unique=False,
    nullable=False,
    # server_default=func.now(),
    # doc='Creation time',
  )

  # updated_at = db.Column(db.DateTime(timezone=True), onupdate=func.now(),
  #                        doc='Last updated time')
  
  if flag_set('ff_rename'):
    @declared_attr
    def import_storage_id(self):
      return db.Column(db.Integer, db.ForeignKey('import_storage.id'))
  else:
    @declared_attr
    def strava_acct_id(self):
      return db.Column(db.Integer, db.ForeignKey('import_storage.id'))

  @classmethod
  def exists(cls, key, storage):
    """
    cls is an ImportStorageEntity class
    key is an ImportStorageEntity instance's key
    storage is an ImportStorage instance
    
    """ 
    # subq = storage.entities.subquery()
    # result = db.session.scalars(db.select(subq).filter_by(key=key)).all()
    # return len(result) > 0

    return len(db.session.scalars(db.select(cls).filter_by(key=key, import_storage_id=storage.id)).all()) > 0
