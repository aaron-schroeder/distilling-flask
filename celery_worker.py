import os

from application import celery, create_app


app = create_app(config=os.getenv('FLASK_CONFIG', 'dev'))
app.app_context().push()