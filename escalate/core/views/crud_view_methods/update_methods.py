from django.urls import reverse_lazy

import core.models
import core.forms.models as forms

methods = {
    "Material": {
        "model": core.models.view_tables.Material,
        "context_object_name": "material",
        "form_class": forms.MaterialForm,
        "success_url": reverse_lazy("material_list"),
    },
    "Systemtool": {
        "model": core.models.view_tables.Systemtool,
        "context_object_name": "systemtool",
        "form_class": forms.LatestSystemtoolForm,
        "success_url": reverse_lazy("systemtool_list"),
    },
    "MaterialType": {
        "model": core.models.view_tables.MaterialType,
        "context_object_name": "material_type",
        "form_class": forms.MaterialTypeForm,
        "success_url": reverse_lazy("material_type_list"),
    },
    "MaterialIdentifier": {
        "model": core.models.view_tables.MaterialIdentifier,
        "context_object_name": "material_identifier",
        "form_class": forms.MaterialIdentifierForm,
        "success_url": reverse_lazy("material_identifier_list"),
    },
    "Organization": {
        "model": core.models.view_tables.Organization,
        "context_object_name": "organization",
        "form_class": forms.OrganizationForm,
        "success_url": reverse_lazy("organization_list"),
    },
    "Status": {
        "model": core.models.view_tables.Status,
        "context_object_name": "status",
        "form_class": forms.StatusForm,
        "success_url": reverse_lazy("status_list"),
    },
    "Tag": {
        "model": core.models.view_tables.Tag,
        "context_object_name": "tag",
        "form_class": forms.TagForm,
        "success_url": reverse_lazy("tag_list"),
    },
    "TagType": {
        "model": core.models.view_tables.TagType,
        "context_object_name": "tag_type",
        "form_class": forms.TagTypeForm,
        "success_url": reverse_lazy("tag_type_list"),
    },
    "InventoryMaterial": {
        "model": core.models.view_tables.InventoryMaterial,
        "context_object_name": "inventory_material",
        "form_class": forms.InventoryMaterialForm,
        "success_url": reverse_lazy("inventory_material_list"),
    },
    "Vessel": {
        "model": core.models.view_tables.Vessel,
        "context_object_name": "vessel",
        "form_class": forms.VesselForm,
        "success_url": reverse_lazy("vessel_list"),
    },
    "ActionDef": {
        "model": core.models.view_tables.ActionDef,
        "context_object_name": "action_def",
        "form_class": forms.ActionDefForm,
        "success_url": reverse_lazy("action_def_list"),
    },
    "ParameterDef": {
        "model": core.models.view_tables.ParameterDef,
        "context_object_name": "parameter_def",
        "form_class": forms.ParameterDefForm,
        "success_url": reverse_lazy("parameter_def_list"),
    },
    "PropertyTemplate": {
        "model": core.models.view_tables.PropertyTemplate,
        "context_object_name": "property_template",
        "form_class": forms.PropertyTemplateForm,
        "success_url": reverse_lazy("property_template_list"),
    },
    "ExperimentTemplate": {
        "model": core.models.view_tables.ExperimentTemplate,
        "context_object_name": "experiment_template",
        "form_class": forms.ExperimentTemplateForm,
        "success_url": reverse_lazy("experiment_template_list"),
    },
    "Outcome": {
        "model": core.models.view_tables.Outcome,
        "context_object_name": "outcome",
        "form_class": forms.OutcomeForm,
        "success_url": reverse_lazy("experiment_template_list"),
    },
    "Property": {
        "model": core.models.Property,
        "context_object_name": "property",
        "form_class": forms.PropertyForm,
        "success_url": reverse_lazy("main_menu"),
    },
    "ReagentTemplate": {
        "model": core.models.ReagentTemplate,
        "context_object_name": "reagent_template",
        "form_class": forms.ReagentTemplateForm,
        "success_url": reverse_lazy("experiment_template_list"),
    },
    "VesselTemplate": {
        "model": core.models.VesselTemplate,
        "context_object_name": "vessel_template",
        "form_class": forms.VesselTemplateForm,
        "success_form": reverse_lazy("experiment_template_list"),
    },
    "OutcomeTemplate": {
        "model": core.models.OutcomeTemplate,
        "context_object_name": "outcome_template",
        "form_class": forms.OutcomeTemplateForm,
        "success_form": reverse_lazy("experiment_template_list"),
    },
}
