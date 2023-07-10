import django_tables2 as tables


class EquipmentTable(tables.Table):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super(EquipmentTable, self).__init__(*args, **kwargs)

    name = tables.LinkColumn(
        viewname="equipment-edit", args=[tables.A("pk")], attrs={"a": {"style": "font-weight: bold"}}
    )
    equipment_type = tables.Column(
        verbose_name="Type",
        attrs={"td": {"class": "hide_in_mobile_view"}, "th": {"class": "hide_in_mobile_view"}},
    )
    asset_id = tables.Column(
        verbose_name="ID",
        attrs={"td": {"class": "hide_in_mobile_view"}, "th": {"class": "hide_in_mobile_view"}},
    )
    vendor = tables.Column()
    updated_at = tables.Column(verbose_name="Last Updated")


    class Meta:
        attrs = {"class": "table table-hover table-sm"}
        template_name = "table/custome_table.html"