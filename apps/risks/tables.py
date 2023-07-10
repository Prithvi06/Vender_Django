from datetime import datetime, timezone
from sqlite3 import Date

import apps.risks.models as models
import django_tables2 as tables
from django.utils.html import format_html
from apps.risks.models import get_risk_rating


class RiskTable(tables.Table):
    title = tables.LinkColumn(viewname="risk-edit", args=[tables.A("pk")], attrs={"a": {"style": "font-weight: bold"}})
    category = tables.Column(attrs={"td": {"class": "hide_in_mobile_view"}, "th": {"class": "hide_in_mobile_view"}})
    likelihood = tables.Column()
    rating = tables.Column(attrs={"td": {"class": "hide_in_mobile_view"}, "th": {"class": "hide_in_mobile_view"}})
    mitigation = tables.Column(attrs={"td": {"class": "hide_in_mobile_view"}, "th": {"class": "hide_in_mobile_view"}})
    priority = tables.Column(attrs={"td": {"class": "hide_in_mobile_view"}, "th": {"class": "hide_in_mobile_view"}})
    owner = tables.Column()

    def render_owner(self, value):
        if value:
            if value.first_name and value.last_name:
                value = value.first_name + " " + value.last_name
            elif value.first_name:
                value = value.first_name
            else:
                return value
        return value

    def render_rating(self, value):
        return f"{get_risk_rating(value)} ({value})"

    class Meta:
        attrs = {"class": "table table-hover table-sm"}
        template_name = "table/custome_table.html"
