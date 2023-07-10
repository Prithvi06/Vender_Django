from datetime import datetime, timezone, timedelta
from sqlite3 import Date
from django.utils import timezone as django_timezone
import django_tables2 as tables
from django.utils.html import format_html
from apps.administrator.models import Location
from apps.tasks.models import Task, TaskStatus


class LocationTable(tables.Table):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super(LocationTable, self).__init__(*args, **kwargs)

    name = tables.LinkColumn(
        viewname="location-edit", args=[tables.A("org_id"), tables.A("pk")], attrs={"a": {"style": "font-weight: bold"}}
    )
    line_1 = tables.Column(
        verbose_name="Address",
        attrs={"td": {"class": "hide_in_mobile_view"}, "th": {"class": "hide_in_mobile_view"}},
    )
    city = tables.Column()
    location_type = tables.Column(
        verbose_name="Type",
        attrs={"td": {"class": "hide_in_mobile_view"}, "th": {"class": "hide_in_mobile_view"}},
    )
    updated_at = tables.Column(verbose_name="Last Updated")


    class Meta:
        attrs = {"class": "table table-hover table-sm"}
        template_name = "table/custome_table.html"