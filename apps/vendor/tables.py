from datetime import datetime, timezone, timedelta
from sqlite3 import Date
from django.utils import timezone as django_timezone
import apps.vendor.models as models
import django_tables2 as tables
from django.utils.html import format_html
from apps.vendor.models import Contact, Document, Contract
from apps.tasks.models import Task, TaskStatus


def get_task_color(tasks):
    color_code = "#ababab"
    for task in tasks:
        if task.status in [TaskStatus.IN_PROCESS, TaskStatus.NOT_STARTED]:
            if task.due_date:
                due_date = task.due_date  # datetime(2023, 1, 30).date()
                created_at = task.created_at  # datetime(2023, 1, 15)
                today = django_timezone.now().date()
                create_diff = (due_date - created_at.date()).days
                today_diff = (due_date - today).days
                if due_date < today:
                    color_code = "#f2726f"
                    break
                if ((create_diff > 7) and (today_diff < 7)) or (
                    (create_diff <= 7) and (today_diff < (0.5 * create_diff))
                ):
                    color_code = "#f8c533"

    return color_code


class VendorTable(tables.Table):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super(VendorTable, self).__init__(*args, **kwargs)

    name = tables.Column()
    owner = tables.Column(
        verbose_name="Relationship Owner",
        attrs={"td": {"class": "hide_in_mobile_view"}, "th": {"class": "hide_in_mobile_view"}},
    )
    status = tables.Column()
    residual_risk = tables.Column(
        verbose_name="Residual Risk",
        attrs={"td": {"class": "hide_in_mobile_view"}, "th": {"class": "hide_in_mobile_view"}},
    )
    time_for_renewal = tables.Column(verbose_name="Time for Renewal")

    def render_name(self, record, value):
        from apps.vendor.views import get_document_permission

        contact_count = Contact.objects.filter(vendor_id=record.pk).exclude(is_deleted=True).count()
        contracts = Contract.objects.filter(vendor_id=record.pk).exclude(is_deleted=True)
        contract_count = contracts.count()
        contract_document = Document.objects.filter(contract__in=contracts).exclude(is_deleted=True)
        document_count = (
            (Document.objects.filter(vendor_id=record.pk).exclude(is_deleted=True) | contract_document)
            .distinct()
            .count()
        )
        tasks = Task.objects.filter(vendor_id=record.pk)
        task_count = tasks.exclude(status__in=[TaskStatus.CANCELLED, TaskStatus.COMPLETED]).count()
        task_color = get_task_color(tasks)
        icon_style = ""
        btn_border = ""
        if record.time_for_renewal:
            diff = record.time_for_renewal - datetime.now(timezone.utc).date()
            if diff.days < 15:
                icon_style = "color:#f2726f;"
                btn_border = "border:1px solid #f2726f;"
        doc_pill = f"""<a href='/vendors/{record.pk}/?section=DOCUMENTS' class='btn vendor-tile tooltip-parent tooltip-parent2 tooltip-parent3'><i class='material-icons pr-1'>folder</i>{document_count}<span class="tooltiptext">{document_count} Documents</span></a>"""
        if not get_document_permission(self.user, record):
            doc_pill = f"""<a href='javascript:void(0)' class='disabled_btn btn vendor-tile tooltip-parent tooltip-parent2 tooltip-parent3 permission_tooltip'><i class='material-icons pr-1'>folder</i>{document_count}<span class="tooltiptext">You do not have permission to view documents</span></a>"""
        vendor_tile = f"""
            <a href="/vendors/{record.pk}" style="font-weight:bold; vertical-align: sub;">{record.name}</a>
            <span style="width: 180px" class="pull-right">
            <a href='/vendors/{record.pk}/?section=TASKS' class='btn vendor-tile tooltip-parent tooltip-parent2 tooltip-parent3' style="border:1px solid {task_color};"><i class='material-icons pr-1' style="color:{task_color};">task</i>{task_count}<span class="tooltiptext">{task_count} Tasks</span></a>
            <a href='/vendors/{record.pk}/?section=CONTRACTS' class='btn vendor-tile tooltip-parent tooltip-parent2 tooltip-parent3 ' style="{btn_border}"><i class='material-icons pr-1' style='font-size: 13px; padding-left:2px; {icon_style};'>border_color</i>{contract_count}<span class="tooltiptext">{contract_count} Contracts</span></a>
            {doc_pill}
            <a href='/vendors/{record.pk}/?section=CONTACTS' class='btn vendor-tile tooltip-parent tooltip-parent2 tooltip-parent3'><i class='material-icons pr-1'>contact_page</i>{contact_count}<span class="tooltiptext">{contact_count} Contacts</span></a>
            </span>
        """
        return format_html(vendor_tile)

    def render_owner(self, value):
        if value:
            return f"{value.first_name} {value.last_name}"
        return value

    def render_time_for_renewal(self, value):
        if value:
            diff = value - datetime.now(timezone.utc).date()
            if diff.days < 15:
                return format_html('<div class="expired">{}</div>', value.strftime("%b %d, %Y"))
            return format_html("{}", value.strftime("%b %d, %Y"))
        return format_html("{}", value)

    class Meta:
        attrs = {"class": "table table-hover table-sm vendor_table"}
        template_name = "table/custome_table.html"


class ContractTable(tables.Table):
    vendor__name = tables.Column(verbose_name="Third Party", empty_values=())
    title = tables.LinkColumn(
        viewname="contract-edit",
        args=[tables.A("vendor_id"), tables.A("pk")],
        attrs={"a": {"style": "font-weight: bold"}},
        verbose_name="Contract Name",
    )
    created_at = tables.Column(verbose_name="Created")
    effective_date = tables.Column(verbose_name="Effective")
    next_expiration = tables.Column(verbose_name="Ends")
    vendor__owner = tables.Column(
        verbose_name="Owner",
        attrs={"td": {"class": "hide_in_mobile_view"}, "th": {"class": "hide_in_mobile_view"}},
        empty_values=(),
    )

    def render_owner(self, record, value):
        if record.vendor.owner:
            return f"{record.vendor.owner.first_name} {record.vendor.owner.last_name}"
        return "_"

    def render_vendor__name(self, record, value):
        if record.vendor:
            return f"{record.vendor}"
        return value

    def render_created_at(self, value):
        if value:
            return value.date()
        return format_html("{}", value)

    class Meta:
        attrs = {"class": "table table-hover table-sm"}
        template_name = "table/custome_table.html"
