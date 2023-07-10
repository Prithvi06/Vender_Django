from datetime import datetime, timezone
from sqlite3 import Date

import apps.incidents.models as models
import django_tables2 as tables
from django.utils.html import format_html


class IncidentTable(tables.Table):
    title = tables.LinkColumn(
        viewname="incident-edit", args=[tables.A("pk")], attrs={"a": {"style": "font-weight: bold"}}
    )
    start_date = tables.Column(verbose_name="Started")
    end_date = tables.Column(
        verbose_name="Ended", attrs={"td": {"class": "hide_in_mobile_view"}, "th": {"class": "hide_in_mobile_view"}}
    )
    status = tables.Column()
    affected_resources = tables.Column(verbose_name="Resources")
    severity = tables.Column(attrs={"td": {"class": "hide_in_mobile_view"}, "th": {"class": "hide_in_mobile_view"}})

    def render_start_date(self, value):
        if value:
            value = value.date().strftime("%b. %d, %Y")
            return format_html("{}", value)
        return format_html("{}", value)

    def render_end_date(self, value):
        if value:
            value = value.date().strftime("%b. %d, %Y")
            return format_html("{}", value)
        return format_html("{}", value)

    class Meta:
        attrs = {"class": "table table-hover table-sm"}
        template_name = "table/custome_table.html"
