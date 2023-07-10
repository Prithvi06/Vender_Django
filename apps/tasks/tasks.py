from celery import shared_task
from datetime import date
from django.utils import timezone
from core.celery import app
import logging
from apps.tasks.models import Task, TaskPriority, TaskStatus
from apps.authentication.models import User
from django.core.mail import EmailMessage
from core.settings.base import FROM_EMAIL
from apps.utility.EmailServices import email_service
from datetime import timedelta
from django.db.models import Q


@shared_task
def send_task_status(user_id):
    user = User.objects.filter(pk=user_id).first()
    today = timezone.now().date()
    next_60 = [today, today + timedelta(days=60)]
    status_list = [TaskStatus.NOT_STARTED, TaskStatus.ON_HOLD, TaskStatus.IN_PROCESS]
    task = Task.objects.filter(Q(owner=user, status__in=status_list), Q(due_date__isnull=True) | Q(due_date__range=next_60))
    total_li = ""
    for data in task:
        due_date = ""
        if data.due_date:
            due_date = f"- {data.due_date.strftime('%m/%d/%Y')}"
        new_li = f"<li>{data.title} - {data.get_status_display()} {due_date}</li>"
        total_li = total_li + new_li
    if task:
        template_id = "d-f0882272aeae4367a52a87b85e0c28fb"
        payload = {
            "firstName": user.first_name if user.first_name else user.email,
            "taskList": f"<ul>{total_li}</ul>"
        }
        email_service.delay(user.email, payload, template_id)


@shared_task(name="task_status_email")
def task_status_email():
    try:
        user_object = User.objects.all()
        for user in user_object:
            send_task_status.delay(user.id)
    except Exception as e:
        logging.warning(str(e))