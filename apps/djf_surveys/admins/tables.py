import apps.djf_surveys.models as models
import django_tables2 as tables
from django.utils.html import format_html
from django.urls import reverse, reverse_lazy


class SurveyTable(tables.Table):
    slug = tables.Column(verbose_name="")
    name = tables.Column()
    description = tables.Column()
    created_at = tables.Column(verbose_name="Created")
    active = tables.Column(verbose_name="Status")
    updated_at = tables.Column(verbose_name="Last Updated")

    def render_slug(self, record, value):
        usage_url = reverse("djf_surveys:admin_survey_details", args=[record.pk])
        edit_url = reverse("djf_surveys:admin_edit_survey", args=[record.slug])
        delete_url = reverse("djf_surveys:admin_delete_survey", args=[record.slug])
        version = ""
        if record.gracen_version or record.org_version:
            gracen_version = ""
            org_version = ""
            if record.gracen_version:
                gracen_version = "Gracen Version: " + str(record.gracen_version)
            if record.org_version:
                org_version = "Org Version: " + str(record.org_version)
            version = f"""<span class="tooltiptext" style="min-width: 160px;">{gracen_version} {org_version}</span>"""
        tiles = f"""
        <div style="width: 130px">
        <a  class="delete-btn tooltip-parent survey-tooltip1 mr-1" href="{usage_url}"><i class="material-icons" style="font-size: 18px; color: grey;">pie_chart_outline</i><span class="tooltiptext">View Usage</span></a>
        <a  class="delete-btn tooltip-parent survey-tooltip2" href="{edit_url}"><i class="material-icons" style="font-size: 13px; color: grey;">border_color</i><span class="tooltiptext">Edit Questionnaire</span></a>
        <a  class="delete-btn tooltip-parent survey-tooltip" data-toggle="modal" data-target="#deleteTask" onclick="deleteSurvey('{delete_url}')"><i class="material-symbols-outlined icon_alignment" style="font-size: 19px; color: grey;">delete</i><span class="tooltiptext" style="min-width: 160px;">Delete Questionnaire</span></a>
        <a class="tooltip-parent survey-parent mr-1" style='cursor:pointer;'><i class="material-symbols-outlined icon_alignment" style="font-size: 19px;">info</i>
        {version}
        </a>
        </div>
        """
        return format_html(tiles)

    def render_active(self, value):
        if value:
            return "Active"
        return format_html("{}", "Not Active")

    class Meta:
        attrs = {"class": "table table-hover table-sm"}
        template_name = "table/custome_table.html"
