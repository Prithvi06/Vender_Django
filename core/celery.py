from celery import Celery
from celery.schedules import crontab

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.local")

app = Celery("core")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
app.conf.update(timezone="US/Pacific", enable_utc=True)


@app.task(bind=True)
def debug_task(self):
    print("Request: {0!r}".format(self.request))


app.conf.beat_schedule = {
    "run-every-day-morning": {
        "task": "contract_renewal",
        "schedule": crontab(minute=0, hour=0),
    },
    "run-every-day-morning-user-cleanup": {
        "task": "user_cleanup",
        "schedule": crontab(minute=0, hour=0),
    },
    "search-ofac-list-weekly": {
        "task": "contact_report",
        "schedule": crontab(minute=0, hour=2, day_of_week="Monday"),
        "args": (),
    },
    "contract-status-email": {
        "task": "contract_status_email",
        "schedule": crontab(minute=0, hour=2, day_of_week="Tuesday"),
        "args": (),
    },
    "task-status-email": {
        "task": "task_status_email",
        "schedule": crontab(minute=0, hour=2, day_of_week="Tuesday"),
        "args": (),
    },
    "fetch-ofac-list-weekly": {
        "task": "fetch_weekly_ofac_list",
        "schedule": crontab(minute=0, hour=4, day_of_week="Monday"),
        "args": (),
    },
}
