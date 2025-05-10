from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Next_App.settings')

app = Celery('Next_App')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related config keys should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Celery Beat schedule to run every 5 minutes
app.conf.beat_schedule = {
    'auto-cancel-bookings-every-5-minutes': {
        'task': 'authentication.tasks.auto_cancel_bookings',  # Path to your task
        'schedule': crontab(minute='*/1'),  # Every 5 minutes
    },
}


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
