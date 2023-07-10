import django_tables2 as tables
from django.utils.html import format_html
from apps.tasks.models import get_task_circle


class TaskTable(tables.Table):
    title = tables.LinkColumn(viewname="task-edit", args=[tables.A("pk")], attrs={"a": {"style": "font-weight: bold"}})
    due_date = tables.Column(
        verbose_name="Due Date",
        empty_values=[],
        attrs={"td": {"class": "hide_in_mobile_view"}, "th": {"class": "hide_in_mobile_view"}},
    )
    priority = tables.Column(attrs={"td": {"class": "hide_in_mobile_view"}, "th": {"class": "hide_in_mobile_view"}})
    status = tables.Column()
    linked_resources = tables.Column(
        verbose_name="Resources",
        attrs={"td": {"class": "hide_in_mobile_view"}, "th": {"class": "hide_in_mobile_view"}},
    )
    owner = tables.Column()

    def render_due_date(self, record, value):
        if value:
            value = value.strftime("%b. %d, %Y")
            return format_html(
                f"<div style='display:flex'><div class='circle_div'>{get_task_circle(record)}</div> <span>{value}</span></div>"
            )
        return format_html(
            f"<div style='display:flex'><div class='circle_div'>{get_task_circle(record)}</div> <span></span></div>"
        )

    def render_linked_resources(self, value):
        if value:
            linked_resource = value.split("#")
            if len(linked_resource) == 3:
                value = linked_resource[2]
            return value
        return ""

    def render_owner(self, value):
        if value:
            if value.first_name and value.last_name:
                value = value.first_name + " " + value.last_name
            elif value.first_name:
                value = value.first_name
            else:
                return value
        return value

    class Meta:
        attrs = {"class": "table table-hover table-sm"}
        template_name = "table/custome_table.html"
