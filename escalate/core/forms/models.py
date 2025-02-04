import django
from core.models.view_tables import (
    ActionDef,
    DefaultValues,
    ExperimentTemplate,
    InventoryMaterial,
    Material,
    MaterialIdentifier,
    MaterialIdentifierDef,
    MaterialType,
    Organization,
    Outcome,
    OutcomeTemplate,
    ParameterDef,
    Property,
    ReagentTemplate,
    Status,
    Systemtool,
    Tag,
    TagType,
    Vessel,
    VesselTemplate,
)
from core.widgets import RelatedFieldWidgetCanAdd, ValFormField, ValWidget
from django import forms
from django.contrib.admin import widgets
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from packaging import version

if version.parse(django.__version__) < version.parse("3.1"):
    from django.contrib.postgres.forms import JSONField
else:
    from django.forms import JSONField


dropdown_attrs = {
    "class": "selectpicker",
    "data-style": "btn-outline-primary",
    "data-live-search": "true",
}


class VesselTemplateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        related_uuid = kwargs.pop("related_uuid", None)
        super().__init__(*args, **kwargs)
        if related_uuid:
            self.fields["experiment_template"].initial = ExperimentTemplate.objects.get(
                uuid=related_uuid
            )

    class Meta:
        model = VesselTemplate
        fields = [
            "description",
            "experiment_template",
            "outcome_vessel",
            "default_vessel",
        ]
        widgets = {
            "experiment_template": forms.HiddenInput(),
        }


class OutcomeTemplateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        related_uuid = kwargs.pop("related_uuid", None)
        super().__init__(*args, **kwargs)
        if related_uuid:
            self.fields["experiment_template"].initial = ExperimentTemplate.objects.get(
                uuid=related_uuid
            )

    class Meta:
        model = OutcomeTemplate
        fields = ["description", "experiment_template", "default_value"]
        widgets = {
            "experiment_template": forms.HiddenInput(),
            "default_value": forms.Select(attrs=dropdown_attrs),
        }


class ReagentTemplateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        related_uuid = kwargs.pop("related_uuid", None)
        super().__init__(*args, **kwargs)
        if related_uuid:
            self.fields["experiment_template"].initial = ExperimentTemplate.objects.get(
                uuid=related_uuid
            )

    class Meta:
        model = ReagentTemplate
        fields = ["description", "experiment_template", "properties"]
        widgets = {
            "experiment_template": forms.HiddenInput(),
            # "properties": forms.Select(
            #    attrs=dropdown_attrs,
            # ),
        }


class PropertyForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        related_uuid = kwargs.pop("related_uuid", None)
        super().__init__(*args, **kwargs)
        if related_uuid:
            self.fields["material"].initial = Material.objects.get(uuid=related_uuid)

    class Meta:
        model = Property
        fields = ["template", "value", "material"]
        labels = {}
        widgets = {
            "template": forms.Select(
                attrs=dropdown_attrs,
            ),
            "value": ValWidget(),
            "material": forms.HiddenInput(),
        }


class MaterialForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # pk of model that is passed in to filter for tags belonging to the model
        material_instance: Material = kwargs.get("instance", None)

        current_material_identifiers = (
            [
                (item.uuid, item.description)
                for item in material_instance.identifier.all()
            ]
            if material_instance
            else list()
        )
        current_material_types = (
            material_instance.material_type.all()
            if material_instance
            else MaterialType.objects.none()
        )

        current_material_properties = (
            [
                (item.uuid, item.template.description)
                for item in material_instance.property_m.all()
            ]
            if material_instance
            else list()
        )

        self.fields["identifier"] = forms.ChoiceField(
            choices=current_material_identifiers,
            required=False,
            label="Identifiers",
            # queryset=current_material_identifiers,
            widget=RelatedFieldWidgetCanAdd(
                MaterialIdentifier,
                related_url="material_identifier_add",
                related_instance=material_instance,
                attrs={"size": 5},
            ),
        )

        self.fields["property_m"] = forms.ChoiceField(
            choices=current_material_properties,
            required=False,
            label="Properties",
            widget=RelatedFieldWidgetCanAdd(
                Property,
                related_url="property_add",
                related_instance=material_instance,
                attrs={"size": 5},
            ),
        )
        # self.fields["description"].initial = material_instance.description

        # self.fields["material_type"] = forms.ModelMultipleChoiceField(
        #    initial=current_material_types,
        #    required=False,
        #    queryset=MaterialType.objects.all(),
        # )
        # self.fields["material_type"].widget.attrs.update(dropdown_attrs)

    class Meta:
        model = Material
        fields = ["description", "material_type"]
        # fields = "__all__"
        labels = {"property_m": "Properties"}


class MaterialTypeForm(forms.ModelForm):
    class Meta:
        model = MaterialType
        fields = ["description"]
        field_classes = {"description": forms.CharField}
        labels = {"description": "Description"}
        widgets = {
            "description": forms.Textarea(
                attrs={
                    "cols": "10",
                    "rows": "3",
                    "placeholder": "Your material type description",
                }
            )
        }


class InventoryMaterialForm(forms.ModelForm):
    class Meta:
        model = InventoryMaterial
        fields = [
            "description",
            "inventory",
            "material",
            #'material_consumable', 'material_composite_flg',
            "part_no",
            "phase",
            "onhand_amt",
            "expiration_date",
            "location",
            "status",
        ]

        field_classes = {
            "description": forms.CharField,
            "part_no": forms.CharField,
            "onhand_amt": ValFormField,
            # "onhand_amt": JSONField,
            "expiration_date": forms.SplitDateTimeField,
            "location": forms.CharField,
        }
        labels = {
            "description": "Description",
            "material": "Material",
            "actor": "Actor",
            "part_no": "Part Number",
            "phase": "Phase",
            "onhand_amt": "Amount on hand",
            "expiration_date": "Expiration date",
            "location": "Inventory location",
            #'material_consumable': 'Consumable',
            #'material_composite_flg': 'Composite Material'
        }
        widgets = {
            "material": forms.Select(attrs=dropdown_attrs),
            "actor": forms.Select(attrs=dropdown_attrs),
            "inventory": forms.Select(attrs=dropdown_attrs),
            "description": forms.Textarea(
                attrs={"rows": "3", "cols": "10", "placeholder": "Description"}
            ),
            # "onhand_amt": forms.TextInput(attrs={"placeholder": "On hand amount"}),
            "phase": forms.Select(attrs=dropdown_attrs),
            "onhand_amt": ValWidget(),
            "part_no": forms.TextInput(attrs={"placeholder": "Part number"}),
            "expiration_date": widgets.AdminSplitDateTime(),
            "location": forms.TextInput(attrs={"placeholder": "Location"}),
            "status": forms.Select(attrs=dropdown_attrs),
        }


class VesselForm(forms.ModelForm):
    class Meta:
        model = Vessel
        fields = [
            "description",
            "parent",
            "total_volume",
            "well_number",
            "column_order",
        ]
        field_classes = {
            "description": forms.CharField,
            "total_volume": ValFormField,
            "well_number": forms.IntegerField,
            "column_order": forms.CharField,
        }
        labels = {
            "description": "Description",
            "parent": "Parent",
            "total_volume": "Total Volume",
            "well_number": "Well Count",
            "column_order": "Column Order",
        }
        widgets = {
            "description": forms.TextInput(
                attrs={"placeholder": "Vessel description..."}
            ),
            # "total_volume": forms.TextInput(attrs={"placeholder": "Total Volume..."}),
            "total_volume": ValWidget(),
            "column_order": forms.TextInput(
                attrs={"placeholder": "Order of columns for robot dispensing..."}
            ),
            "parent": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        related_uuid = kwargs.pop("related_uuid", None)
        super().__init__(*args, **kwargs)
        vessel_instance: Vessel = kwargs.pop("instance", None)

        if related_uuid:
            self.fields["parent"].initial = Vessel.objects.get(uuid=related_uuid)

        self.fields["parent"].widget.attrs.update(dropdown_attrs)

        current_children = []
        if vessel_instance:
            current_children = [
                (child.uuid, child.description)
                for child in vessel_instance.children.all()
            ]

        if vessel_instance:
            self.fields["children"] = forms.ChoiceField(
                choices=current_children,
                required=False,
                label=mark_safe("Vials/Wells/Child vessels"),
                widget=RelatedFieldWidgetCanAdd(
                    Vessel,
                    related_url="vessel_add",
                    related_instance=vessel_instance,
                    attrs={
                        "size": 5,
                        "class": "selectpicker",
                        "data-live-search": "true",
                    },
                ),
            )


class ActionDefForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        action_def = kwargs.get("instance", None)

        current_parameter_defs = (
            action_def.parameter_def.all()
            if action_def
            else ParameterDef.objects.none()
        )

        super(ActionDefForm, self).__init__(*args, **kwargs)

        self.fields["parameter_def"] = forms.MultipleChoiceField(
            initial=current_parameter_defs,
            required=False,
            choices=[(pd.uuid, pd.description) for pd in ParameterDef.objects.all()],
        )

        self.fields["parameter_def"].widget.attrs.update(dropdown_attrs)

    class Meta:
        model = ActionDef
        fields = ["description", "parameter_def"]
        labels = {"description": "Description"}
        widgets = {
            "description": forms.Textarea(
                attrs={
                    "cols": "10",
                    "rows": "3",
                    "placeholder": "Your action def description",
                },
            ),
        }


class ParameterDefForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        parameter_def = kwargs.get("instance", None)

        """current_parameter_defs = (
            action_def.parameter_def.all()
            if action_def
            else ParameterDef.objects.none()
        )"""

        current_default_val = (
            parameter_def.default_val.all()
            if parameter_def
            else DefaultValues.objects.none()
        )

        super(ParameterDefForm, self).__init__(*args, **kwargs)

        self.fields["default_val"] = ValFormField(
            initial=current_default_val,
            required=False,
            label="Default value",
            # choices=[(pd.uuid, pd.description) for pd in ParameterDef.objects.all()],
        )

        self.fields["default_val"].widget.attrs.update(dropdown_attrs)

    class Meta:
        model = ParameterDef
        fields = ["description", "unit_type"]
        labels = {"description": "Description"}
        widgets = {
            "description": forms.Textarea(
                attrs={
                    "cols": "10",
                    "rows": "3",
                    "placeholder": "Your parameter def description",
                },
            ),
        }


class PropertyTemplateForm(forms.ModelForm):
    class Meta:
        model = Status
        fields = ["description"]
        labels = {"description": "Property Description"}
        widgets = {
            "description": forms.Textarea(
                attrs={
                    "cols": "10",
                    "rows": "3",
                    "placeholder": "Your property description",
                }
            )
        }


class MaterialIdentifierForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        related_uuid = kwargs.pop("related_uuid", None)
        super(MaterialIdentifierForm, self).__init__(*args, **kwargs)

        if related_uuid:
            self.fields["material"].initial = Material.objects.get(uuid=related_uuid)

        """
        self.fields["material_identifier_def"] = forms.MultipleChoiceField(
            # initial=current_material_identifiers,
            required=False,
            choices=[
                (mi.uuid, mi.description) for mi in MaterialIdentifierDef.objects.all()
            ],
        )
        """

        # self.fields["material_identifier_def"].widget.attrs.update(dropdown_attrs)

    class Meta:
        model = MaterialIdentifier
        fields = ["description", "material_identifier_def", "material"]
        field_classes = {
            "description": forms.CharField,
        }
        labels = {"description": "Description"}
        widgets = {
            "material_identifier_def": forms.Select(attrs=dropdown_attrs),
            "material": forms.HiddenInput(),
        }


class ExperimentTemplateForm(forms.ModelForm):
    class Meta:
        model = ExperimentTemplate
        fields = [
            "description",
        ]  # "reagent_templates", "outcome_templates", "vessel_templates"]
        labels = {"description": "Experiment Template Name"}

    def __init__(self, *args, **kwargs):

        template = kwargs.get("instance", None)

        current_reagent_templates = (
            [(item.uuid, item.description) for item in template.reagent_templates.all()]
            if template
            else list()
        )
        current_vessel_templates = (
            [(item.uuid, item.description) for item in template.vessel_templates.all()]
            if template
            else list()
        )
        current_outcome_templates = (
            [(item.uuid, item.description) for item in template.outcome_templates.all()]
            if template
            else list()
        )
        super((ExperimentTemplateForm), self).__init__(*args, **kwargs)

        """
        forms.ModelMultipleChoiceField(
            initial=current_reagent_templates,
            required=False,
            # choices=[(r.uuid, r.description) for r in ReagentTemplate.objects.all()],
            queryset=ReagentTemplate.objects.all(),
        )
        """
        self.fields["reagent_templates"] = forms.ChoiceField(
            choices=current_reagent_templates,
            required=False,
            label="Reagent Templates",
            widget=RelatedFieldWidgetCanAdd(
                ReagentTemplate,
                related_url="reagent_template_add",
                related_instance=template,
                attrs={"size": 5},
            ),
        )

        self.fields["vessel_templates"] = forms.ChoiceField(
            choices=current_vessel_templates,
            required=False,
            label="Vessel Templates",
            widget=RelatedFieldWidgetCanAdd(
                VesselTemplate,
                related_url="vessel_template_add",
                related_instance=template,
                attrs={"size": 5},
            ),
        )

        self.fields["outcome_templates"] = forms.ChoiceField(
            choices=current_outcome_templates,
            required=False,
            label="Outcome Templates",
            widget=RelatedFieldWidgetCanAdd(
                OutcomeTemplate,
                related_url="outcome_template_add",
                related_instance=template,
                attrs={"size": 5},
            ),
        )

        # self.fields['description'].disabled = True


class OutcomeForm(forms.ModelForm):
    class Meta:
        model = Outcome
        fields = ["description", "nominal_value", "actual_value"]
        widgets = {
            "nominal_value": ValWidget,
            "actual_value": ValWidget,
        }


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = [
            "full_name",
            "short_name",
            "description",
            "address1",
            "address2",
            "city",
            "state_province",
            "zip",
            "country",
            "website_url",
            "phone",
            "parent",
        ]
        field_classes = {
            "full_name": forms.CharField,
            "short_name": forms.CharField,
            "description": forms.CharField,
            "address1": forms.CharField,
            "address2": forms.CharField,
            "city": forms.CharField,
            "state_province": forms.CharField,
            "zip": forms.CharField,
            "country": forms.CharField,
            "website_url": forms.URLField,
            "phone": forms.CharField,
        }
        labels = {
            "full_name": "Full name",
            "short_name": "Short name",
            "description": "Description",
            "address1": "Address Line 1",
            "address2": "Address Line 2",
            "city": "City",
            "state_province": "State/Province",
            "zip": "Zip",
            "country": "Country",
            "website_url": "Website URL",
            "phone": "Phone",
            "parent": "Parent Organization",
            "parent_org_full_name": "Parent Organization full name",
        }
        help_texts = {
            "website_url": "Make sure to include https:// or http:// or www(1-9)"
        }
        widgets = {
            "full_name": forms.TextInput(
                attrs={"placeholder": "Ex: Some Full Organization Name"}
            ),
            "short_name": forms.TextInput(attrs={"placeholder": "Ex: S.F.O.N"}),
            "description": forms.Textarea(
                attrs={
                    "cols": "10",
                    "rows": "3",
                    "placeholder": "Your organization description",
                }
            ),
            "address1": forms.TextInput(attrs={"placeholder": "Ex: 123 Smith Street"}),
            "address2": forms.TextInput(attrs={"placeholder": "Ex: Apt. 2c"}),
            "city": forms.TextInput(attrs={"placeholder": "Ex: San Francisco"}),
            "state_province": forms.TextInput(
                attrs={"cols": 3, "placeholder": "Ex: CA"}
            ),
            "zip": forms.TextInput(attrs={"placeholder": "Ex: 12345/12345-6789"}),
            "country": forms.TextInput(
                attrs={"placeholder": "Ex: United States of America"}
            ),
            "website_url": forms.URLInput(
                attrs={"placeholder": "Ex: https://example.com"}
            ),
            "phone": forms.TextInput(
                attrs={"placeholder": "Ex: 1-234-567-8900/12345678900"}
            ),
            "parent": forms.Select(attrs=dropdown_attrs),
        }


class StatusForm(forms.ModelForm):
    class Meta:
        model = Status
        fields = ["description"]
        labels = {"description": "Status Description"}
        widgets = {
            "description": forms.Textarea(
                attrs={
                    "cols": "10",
                    "rows": "3",
                    "placeholder": "Your status description",
                }
            )
        }


class TagTypeForm(forms.ModelForm):
    class Meta:
        model = TagType
        fields = ["type"]


class TagForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[
            "tag_type"
        ].help_text = f'To create a new tag type, <a href="{reverse_lazy("tag_type_add")}">click here</a>'

    class Meta:
        model = Tag
        fields = ["display_text", "description", "tag_type"]
        labels = {
            "display_text": "Tag Name",
            "description": "Tag Description",
            "actor": "Actor",
            "tag_type": "Tag Type",
        }
        widgets = {
            "display_text": forms.TextInput(
                attrs={"placeholder": "Enter your name of the tag Ex: acid"}
            ),
            "description": forms.Textarea(
                attrs={
                    "cols": "10",
                    "rows": "3",
                    "placeholder": "Detailed description for your tag",
                }
            ),
        }


class LatestSystemtoolForm(forms.ModelForm):
    class Meta:
        model = Systemtool
        fields = [
            "systemtool_name",
            "description",
            "systemtool_type",
            "vendor_organization",
            "model",
            "serial",
            "ver",
        ]
        field_classes = {
            "systemtool_name": forms.CharField,
            "description": forms.CharField,
            "model": forms.CharField,
            "serial": forms.CharField,
            "ver": forms.CharField,
        }
        labels = {
            "systemtool_name": "System tool name",
            "description": "Description",
            "model": "Model",
            "serial": "Serial number",
            "ver": "Version",
            "systemtool_type": "System tool type",
            "vendor_organization": "Vendor Organization",
        }
        # help_texts = {
        #  }
        widgets = {
            "systemtool_name": forms.TextInput(
                attrs={"placeholder": "Ex: Command Line"}
            ),
            "description": forms.Textarea(
                attrs={
                    "cols": "10",
                    "rows": "3",
                    "placeholder": "Your system tool description",
                }
            ),
            "model": forms.TextInput(attrs={"placeholder": "Ex: left to be done"}),
            "serial": forms.TextInput(
                attrs={"placeholder": "Your system tool serial number Ex:Y291325"}
            ),
            "ver": forms.TextInput(
                attrs={"placeholder": "Your system tool current version Ex: 1.06"}
            ),
            "systemtool_type": forms.Select(attrs=dropdown_attrs),
        }
