from celery import shared_task
from django.core.mail import EmailMessage
from core.settings.base import FROM_EMAIL
import logging
from apps.administrator.models import ScheduledJobLogger
from apps.authentication.models import User
from django.utils.html import strip_tags
from apps.vendor.models import Contact


@shared_task
def email_service(to_email, payload, template_id, subject=None):
    try:
        msg = EmailMessage(
            from_email=FROM_EMAIL,
            to=[to_email],
        )
        if subject:
            msg.subject = subject
        msg.template_id = template_id
        msg.dynamic_template_data = payload
        msg.send(fail_silently=False)
        logger_object = ScheduledJobLogger.objects.create(
            api_url="SENDGRID_EMAIL_SERVICE", email=to_email, response_code="200", job_type="SENDGRID_EMAIL"
        )
        logger_object.save()
    except Exception as e:
        logging.warning(str(e))


def send_mention_email(users_list, mention_type, mention_by, mention_title, message):
    try:
        users = User.objects.filter(id__in=users_list)
        for user in users:
            msg = EmailMessage(
                from_email=FROM_EMAIL,
                to=[user.email],
            )
            msg.template_id = "d-aa060495d70b4224a882f28844a83a53"
            payload = {
                "firstName": (user.first_name).capitalize(),
                "senderName": mention_by.capitalize(),
                "objectType": mention_type,
                "objectName": (mention_title).capitalize(),
                "messageText": strip_tags(message).replace("&nbsp;", " "),
            }
            msg.dynamic_template_data = payload
            msg.send(fail_silently=False)
            logger_object = ScheduledJobLogger.objects.create(
                api_url="SENDGRID_EMAIL_SERVICE", email=user.email, response_code="200", job_type="SENDGRID_EMAIL"
            )
            logger_object.save()
    except Exception as e:
        logging.warning(str(e))


def send_survey_link(survey_name, sender_id, receiver_pk, org_name, url):
    try:
        sender = User.objects.filter(id=sender_id)
        reciever = Contact.objects.get(pk=receiver_pk)
        msg = EmailMessage(
            from_email=FROM_EMAIL,
            to=[reciever.email],
        )
        msg.template_id = "d-22d6509b9f004285bc197eb56e19b8cd"
        payload = {
            "firstName": reciever.first_name,
            "orgName": org_name,
            "orgFirstName": sender.first().first_name.capitalize(),
            "orgLastName": sender.first().last_name.capitalize(),
            "orgEmail": sender.first().email,
            "questionnaireName": survey_name,
            "url": url,
        }
        msg.dynamic_template_data = payload
        msg.send(fail_silently=False)
        logger_object = ScheduledJobLogger.objects.create(
            api_url="SENDGRID_EMAIL_SERVICE",
            email=sender.first().email,
            response_code="200",
            job_type="SENDGRID_EMAIL",
        )
        logger_object.save()
    except Exception as e:
        logging.warning(str(e))


def send_survey_password(survey_name, sender_id, receiver_pk, org_name, password):
    try:
        sender = User.objects.filter(id=sender_id)
        reciever = Contact.objects.get(pk=receiver_pk)
        msg = EmailMessage(
            from_email=FROM_EMAIL,
            to=[reciever.email],
        )
        msg.template_id = "d-f99f425e7b9c42ff8f9ff0c814ee2a98"
        payload = {
            "firstName": reciever.first_name,
            "orgName": org_name,
            "orgFirstName": sender.first().first_name.capitalize(),
            "orgLastName": sender.first().last_name.capitalize(),
            "orgEmail": sender.first().email,
            "questionnaireName": survey_name,
            "password": password,
        }
        msg.dynamic_template_data = payload
        msg.send(fail_silently=False)
        logger_object = ScheduledJobLogger.objects.create(
            api_url="SENDGRID_EMAIL_SERVICE",
            email=sender.first().email,
            response_code="200",
            job_type="SENDGRID_EMAIL",
        )
        logger_object.save()
    except Exception as e:
        logging.warning(str(e))
