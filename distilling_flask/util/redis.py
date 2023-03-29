from flask import current_app
import redis


try:
  _redis = redis.Redis.from_url(current_app.config.REDIS_URL)
  _redis.ping()
  # logger.debug(
  print('=> Redis is connected successfully.')
except:
  # logger.debug(
  print('=> Redis is not connected.')
  _redis = None


def redis_healthcheck():
  if not _redis:
    return False
  try:
    _redis.ping()
  except redis.exceptions.ConnectionError as exc:
    # logger.error(f'Redis healthcheck failed with ConnectionError: {exc}', exc_info=True)
    print(f'Redis healthcheck failed with ConnectionError: {exc}')
    return False
  except redis.exceptions.TimeoutError as exc:
    # logger.error(f'Redis healthcheck failed with TimeoutError: {exc}', exc_info=True)
    print(f'Redis healthcheck failed with TimeoutError: {exc}')
    return False
  except redis.exceptions.RedisError as exc:
    # logger.error(f'Redis healthcheck failed: {exc}', exc_info=True)
    print(f'Redis healthcheck failed: {exc}')
    return False
  else:
    # logger.debug(
    print('Redis client is alive!')
    return True


def redis_connected():
  return redis_healthcheck()