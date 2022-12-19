from functools import wraps
import uuid

from dash import dcc
from flask_login import current_user


def layout_login_required(f):
  @wraps(f)
  def decorated_function(*args, **kwargs):
    if current_user.is_authenticated:
        return f(*args, **kwargs)
    return dcc.Location(pathname='/login', id=str(uuid.uuid4()))
  return decorated_function