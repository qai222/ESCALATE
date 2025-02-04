from distutils import command
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from core.models import (
    Actor,
    Action,
    ActionDef,
    ActionUnit,
    BaseBomMaterial,
    BomMaterial,
    BillOfMaterials,
    DefaultValues,
    ExperimentTemplate,
    Type,
    Inventory,
    InventoryMaterial,
    Material,
    MaterialType,
    MaterialIdentifier,
    MaterialIdentifierDef,
    ParameterDef,
    PropertyTemplate,
    Property,
    Status,
    Systemtool,
    TypeDef,
    Vessel,
    ReagentTemplate,
    ReagentMaterialTemplate,
    # ReagentMaterialValueTemplate,
    OutcomeTemplate,
    Parameter,
    DescriptorTemplate,
    VesselType,
    ActionTemplate,
    VesselTemplate,
)
from core.custom_types import Val
import csv
import os
import json
import math

import pandas as pd

from core.utilities.utils import make_well_labels_list


class Command(BaseCommand):
    help = "Loads initial data from load tables after a datebase refresh"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Loading load tables"))
        self._load_material_identifier()
        self._load_material()
        self._load_chem_inventory()
        self._load_inventory_material()
        self._load_vessels()
        self._load_experiment_related_def()
        # self._load_experiment_and_action_sequence()
        # self._load_mixture()
        # self._load_base_bom_material()
        # self._load_action()
        # self._load_action_unit()
        # self._load_reagents_and_outcomes()
        self._create_wf1()
        self._create_wf3()

        self._create_wf3new()

        self._load_descriptors()
        self.stdout.write(self.style.NOTICE("Finished loading load tables"))
        return

    def _load_descriptors(self):
        filename = "type_command.csv"
        DESCRIPTORS = path_to_file(filename)
        type_commands = pd.read_csv(DESCRIPTORS)
        for i, row in type_commands.iterrows():
            command = row["calc_definition"]
            description = row["short_name"]
            human_description = row["human readable description"]
            material_type, created = MaterialType.objects.get_or_create(
                description=row["input"]
            )
            systemtool, created = Systemtool.objects.get_or_create(
                description=row["actor_systemtool_name"]
            )
            template = DescriptorTemplate.objects.create(
                description=description,
                command=command,
                human_description=human_description,
                material_type=material_type,
                systemtool=systemtool,
            )

    def _create_wf1(self):
        # Get the lab related to this template
        lab = Actor.objects.get(
            description="Haverford College",
            person__isnull=True,
            systemtool__isnull=True,
        )

        # Create the experiment
        exp_template, created = ExperimentTemplate.objects.get_or_create(
            description="Workflow 1",
            ref_uid="workflow_1",
            lab=lab,
        )

        reagents = {
            "Reagent 2 - Stock A": ["organic", "solvent"],
            "Reagent 7 - Acid": ["acid"],
            "Reagent 3 - Stock B": ["inorganic", "organic", "solvent"],
            "Reagent 1 - Solvent": ["solvent"],
        }

        # Vals for each default value
        volume_val = {"value": 0, "unit": "ml", "type": "num"}
        dead_vol_val = {"value": 4000, "unit": "uL", "type": "num"}
        amount_val = {"value": 0, "unit": "g", "type": "num"}
        conc_val = {"value": 0, "unit": "M", "type": "num"}
        crystal_score_val = {"value": 0, "unit": "", "type": "int"}

        # Create default values
        default_volume, created = DefaultValues.objects.get_or_create(
            **{
                "description": "Zero ml",
                "nominal_value": volume_val,
                "actual_value": volume_val,
            }
        )
        default_dead_volume, created = DefaultValues.objects.get_or_create(
            **{
                "description": "4000 uL",
                "nominal_value": dead_vol_val,
                "actual_value": dead_vol_val,
            }
        )
        default_amount, created = DefaultValues.objects.get_or_create(
            **{
                "description": "Zero g",
                "nominal_value": amount_val,
                "actual_value": amount_val,
            }
        )
        default_conc, created = DefaultValues.objects.get_or_create(
            **{
                "description": "Zero M",
                "nominal_value": conc_val,
                "actual_value": conc_val,
            }
        )
        default_crystal_score, created = DefaultValues.objects.get_or_create(
            **{
                "description": "Zero Crystal score",
                "nominal_value": crystal_score_val,
                "actual_value": crystal_score_val,
            }
        )

        # Concentration and amount data to be stored for each reagent material
        reagent_values = {"concentration": default_conc, "amount": default_amount}

        # Create total volume and dead volume property templates for each reagent
        total_volume_prop, created = PropertyTemplate.objects.get_or_create(
            **{
                "description": "total volume",
                "property_def_class": "extrinsic",
                "short_description": "volume",
                "default_value": default_volume,
            }
        )
        dead_volume_prop, created = PropertyTemplate.objects.get_or_create(
            **{
                "description": "dead volume",
                "property_def_class": "extrinsic",
                "short_description": "dead volume",
                "default_value": default_dead_volume,
            }
        )

        # Loop through each reagent in reagents dict and create ReagentTemplates,
        # corresponding ReagentMaterialTemplates and their Value Templates (ReagentMaterialValueTemplate)
        for r, rms in reagents.items():
            reagent_template, created = ReagentTemplate.objects.get_or_create(
                description=r, experiment_template=exp_template
            )
            reagent_template.properties.add(total_volume_prop)
            reagent_template.properties.add(dead_volume_prop)
            # exp_template.reagent_templates.add(reagent_template)
            for rm in rms:
                self.stdout.write(self.style.NOTICE(f"{rm}"))
                material_type = MaterialType.objects.get(description=rm)
                (
                    reagent_material_template,
                    created,
                ) = ReagentMaterialTemplate.objects.get_or_create(
                    **{
                        "description": f"{r}: {rm}",
                        "reagent_template": reagent_template,
                        "material_type": material_type,
                    }
                )

                for rv, default in reagent_values.items():
                    (rmv_template, created,) = PropertyTemplate.objects.get_or_create(
                        # ReagentMaterialValueTemplate.objects.get_or_create(
                        **{
                            "description": rv,
                            # "reagent_material_template": reagent_material_template,
                            "default_value": default,
                        }
                    )
                    reagent_material_template.properties.add(rmv_template)

        # VESSEL data

        vessel_types = ["plate", "well", "beaker", "tube", "wells"]
        for vt in vessel_types:
            VesselType.objects.get_or_create(description=vt)

        column_order = "ACEGBDFH"
        rows = 12
        well_list = [
            f"{col}{row}" for row in range(1, rows + 1) for col in column_order
        ]
        plate = Vessel.objects.get(description="96 Well Plate well")
        plate.vessel_type.add(VesselType.objects.get(description="plate"))
        plate.column_order = column_order
        plate.well_number = 96
        plate.save()
        # Dictionary of plate wells so that we don't keep accessing the database
        # multiple times
        plate_wells = {}
        vial_type = VesselType.objects.get(description="well")
        for well in well_list:
            plate_wells[well] = Vessel.objects.get(parent=plate, description=well)
            plate_wells[well].vessel_type.add(vial_type)
            plate_wells[well].save()

        # Create outcome templates, Currently hard coded to capture 96 values

        ot, created = OutcomeTemplate.objects.get_or_create(
            description="Crystal score",
            experiment_template=exp_template,
            # instance_labels=well_list,
            default_value=default_crystal_score,
        )
        ot.save()
        # exp_template.outcome_templates.add(ot)

        # heat_stir and heat causes duplicates, not sure why
        action_parameter_def = {
            "dispense": (("volume", "uL"),),
            "bring_to_temperature": (("temperature", "degC"),),
            "stir": (("duration", "s"), ("speed", "rpm")),
            "heat_stir": (("duration", "s"), ("speed", "rpm"), ("temperature", "degC")),
        }
        # Action defs it is assumed that action defs are already inserted
        actions = [  # List of tuples (Description, Action def description, source_bommaterial, destination_bommaterial)
            # ('Preheat Plate', 'bring_to_temperature', (None, None), ('vessel', '96 Well Plate well'), 'Preheat Plate'),
            (
                "Preheat Plate",
                "bring_to_temperature",
                (None, None),
                ("vessel", "96 Well Plate well"),
                "Preheat Plate",
            ),
            (
                "Dispense Reagent 1 - Solvent",
                "dispense",
                (None, "Reagent 1 - Solvent"),
                ("vessel", plate_wells),
                "Dispense Reagent 1 - Solvent",
            ),
            # Dispense Stock A to vials
            (
                "Dispense Reagent 2 - Stock A",
                "dispense",
                (None, "Reagent 2 - Stock A"),
                ("vessel", plate_wells),
                "Dispense Reagent 2 - Stock A",
            ),
            # Dispense Stock B to vials
            (
                "Dispense Reagent 3 - Stock B",
                "dispense",
                (None, "Reagent 3 - Stock B"),
                ("vessel", plate_wells),
                "Dispense Reagent 3 - Stock B",
            ),
            # Dispense Acid Vol 1
            (
                "Dispense Reagent 7 - Acid Volume 1",
                "dispense",
                (None, "Reagent 7 - Acid"),
                ("vessel", plate_wells),
                "Dispense Reagent 7 - Acid Volume 1",
            ),
            # Heat stir 1
            # ('Heat stir 1', 'heat_stir', (None, None), ('vessel', '96 Well Plate well'), 'Heat stir 1'),
            (
                "Heat-Stir 1",
                "heat_stir",
                (None, None),
                ("vessel", "96 Well Plate well"),
                "Heat-Stir 1",
            ),
            # Dispense Acid Vol 2
            (
                "Dispense Reagent 7 - Acid Volume 2",
                "dispense",
                (None, "Reagent 7 - Acid"),
                ("vessel", plate_wells),
                "Dispense Reagent 7 - Acid Volume 2",
            ),
            # Heat stir 2
            # ('Heat stir 2', 'heat_stir', (None, None), ('vessel', '96 Well Plate well'), 'Heat stir 2'),
            (
                "Heat-Stir 2",
                "heat_stir",
                (None, None),
                ("vessel", "96 Well Plate well"),
                "Heat-Stir 2",
            ),
            # Heat
            # ('Heat', 'heat', (None, None), ('vessel', '96 Well Plate well'), 'Heat'),
        ]
        # Saving prev_action here so that we can save it as a parent for the next action_template
        prev_action_template = None
        for action_tuple in actions:
            (
                action_desc,
                action_def_desc,
                (source_col, source_desc),
                (dest_col, dest_desc),
                action_seq,
            ) = action_tuple
            action_def, created = ActionDef.objects.get_or_create(
                description=action_def_desc
            )
            # action_sequences[action_seq].action_def.add(action_def)
            source_vessel_template = None
            source_vessel_decomposable = False
            if source_desc:
                default_vessel, created = Vessel.objects.get_or_create(
                    description="Generic Vessel"
                )
                source_vessel_template, created = VesselTemplate.objects.get_or_create(
                    experiment_template=exp_template,
                    description=source_desc,
                    outcome_vessel=False,
                    # decomposable=False,
                    default_vessel=default_vessel,
                )

                # if created:
                #    exp_template.vessel_templates.add(source_vessel_template)

            dest_vessel_template = None
            dest_vessel_decomposable = False
            if dest_desc:
                default_vessel = Vessel.objects.get(description="96 Well Plate well")

                if isinstance(dest_desc, str):
                    dest_vessel_decomposable = False
                elif isinstance(dest_desc, dict):
                    dest_vessel_decomposable = True

                (dest_vessel_template, created,) = VesselTemplate.objects.get_or_create(
                    experiment_template=exp_template,
                    description="Outcome vessel",
                    outcome_vessel=True,
                    default_vessel=default_vessel,
                )

                # if created:
                #    exp_template.vessel_templates.add(dest_vessel_template)

            at, created = ActionTemplate.objects.get_or_create(
                # action_sequence=action_sequences[action_seq],
                description=action_desc,
                experiment_template=exp_template,
                action_def=action_def,
                source_vessel_template=source_vessel_template,
                source_vessel_decomposable=source_vessel_decomposable,
                dest_vessel_template=dest_vessel_template,
                dest_vessel_decomposable=dest_vessel_decomposable,
            )
            if prev_action_template is not None:
                at.parent.add(prev_action_template)
            prev_action_template = at

            for param_def_desc, unit in action_parameter_def[action_def_desc]:
                param, created = ParameterDef.objects.get_or_create(
                    description=param_def_desc,
                )
                param.default_val = Val.from_dict(
                    {"value": 0, "unit": unit, "type": "num"}
                )
                param.save()
                action_def.parameter_def.add(param)

    def _create_wf3new(self):
        # 2023/01 wf3 for copper without acid, template creation is buggy so im using this quick dirty fix
        plate = Vessel.objects.create(
            description="48 well plate - WF3",
            well_number=48,
            parent=None,
            metadata={'well_order':
                          ['A1', 'C1', 'E1', 'G1', 'B2', 'D2', 'F2', 'H2', 'A3', 'C3', 'E3', 'G3',
                           'B4', 'D4', 'F4', 'H4', 'A5', 'C5', 'E5', 'G5', 'B6', 'D6', 'F6', 'H6',
                           'A7', 'C7', 'E7', 'G7', 'B8', 'D8', 'F8', 'H8', 'A9', 'C9', 'E9', 'G9',
                           'B10', 'D10', 'F10', 'H10', 'A11', 'C11', 'E11', 'G11', 'B12', 'D12', 'F12', 'H12']})

        plate.vessel_type.add(VesselType.objects.get(description="plate"))
        plate.save()
        plate_wells = {}
        vial_type = VesselType.objects.get(description="well")

        column_order = "ACEGBDFH"
        rows = 12
        a_well_list = []
        b_well_list = []
        well_list = []
        for row in range(rows):
            if (row + 1) % 2 != 0:
                for col in column_order[0:4]:
                    a_well_list.append("{}{}".format(col, row + 1))
                    well_list.append("{}{}".format(col, row + 1))
            else:
                for col in column_order[4:]:
                    b_well_list.append("{}{}".format(col, row + 1))
                    well_list.append("{}{}".format(col, row + 1))
        for well in well_list:
            plate_wells[well] = Vessel(parent=plate, description=well)

        Vessel.objects.bulk_create(plate_wells.values())
        for well in well_list:
            plate_wells[well].vessel_type.add(vial_type)
            plate_wells[well].save()

        # Get the lab related to this template
        lab = Actor.objects.get(
            description="Haverford College",
            person__isnull=True,
            systemtool__isnull=True,
        )

        # Create the experiment
        exp_template, created = ExperimentTemplate.objects.get_or_create(
            description="Workflow 3 noacid",
            ref_uid="workflow_3_noacid",
            lab=lab,
        )
        # exp_template.save()

        reagents = {
            "Reagent 2 - Stock A": ["inorganic", "organic", "solvent"],
            "Reagent 3 - Stock B": ["inorganic", "organic", "solvent"],
            "Reagent 1 - Solvent": ["solvent"],
            "Reagent 9 - Antisolvent": ["solvent"],
        }

        # Vals for each default value
        volume_val = {"value": 0, "unit": "ml", "type": "num"}
        dead_vol_val = {"value": 4000, "unit": "uL", "type": "num"}
        amount_val = {"value": 0, "unit": "g", "type": "num"}
        conc_val = {"value": 0, "unit": "M", "type": "num"}
        crystal_score_val = {"value": 0, "unit": "", "type": "int"}

        # Create default values
        default_volume, created = DefaultValues.objects.get_or_create(
            **{
                "description": "Zero ml",
                "nominal_value": volume_val,
                "actual_value": volume_val,
            }
        )
        default_dead_volume, created = DefaultValues.objects.get_or_create(
            **{
                "description": "4000 uL",
                "nominal_value": dead_vol_val,
                "actual_value": dead_vol_val,
            }
        )
        default_amount, created = DefaultValues.objects.get_or_create(
            **{
                "description": "Zero g",
                "nominal_value": amount_val,
                "actual_value": amount_val,
            }
        )
        default_conc, created = DefaultValues.objects.get_or_create(
            **{
                "description": "Zero M",
                "nominal_value": conc_val,
                "actual_value": conc_val,
            }
        )
        default_crystal_score, created = DefaultValues.objects.get_or_create(
            **{
                "description": "Zero Crystal score",
                "nominal_value": crystal_score_val,
                "actual_value": crystal_score_val,
            }
        )

        # Concentration and amount data to be stored for each reagent material
        reagent_values = {"concentration": default_conc, "amount": default_amount}

        # Create total volume and dead volume property templates for each reagent
        total_volume_prop, created = PropertyTemplate.objects.get_or_create(
            **{
                "description": "total volume",
                "property_def_class": "extrinsic",
                "short_description": "volume",
                "default_value": default_volume,
            }
        )
        dead_volume_prop, created = PropertyTemplate.objects.get_or_create(
            **{
                "description": "dead volume",
                "property_def_class": "extrinsic",
                "short_description": "dead volume",
                "default_value": default_dead_volume,
            }
        )

        # Loop through each reagent in reagents dict and create ReagentTemplates,
        # corresponding ReagentMaterialTemplates and their Property Templates
        for r, rms in reagents.items():
            reagent_template, created = ReagentTemplate.objects.get_or_create(
                experiment_template=exp_template,
                description=r,
            )
            reagent_template.properties.add(total_volume_prop)
            reagent_template.properties.add(dead_volume_prop)
            # exp_template.reagent_templates.add(reagent_template)
            for rm in rms:
                self.stdout.write(self.style.NOTICE(f"{rm}"))
                material_type = MaterialType.objects.get(description=rm)
                (
                    reagent_material_template,
                    created,
                ) = ReagentMaterialTemplate.objects.get_or_create(
                    **{
                        "description": f"{r}: {rm}",
                        "reagent_template": reagent_template,
                        "material_type": material_type,
                    }
                )

                for rv, default in reagent_values.items():
                    (rmv_template, created,) = PropertyTemplate.objects.get_or_create(
                        # ReagentMaterialValueTemplate.objects.get_or_create(
                        **{
                            "description": rv,
                            # "reagent_material_template": reagent_material_template,
                            "default_value": default,
                        }
                    )
                    reagent_material_template.properties.add(rmv_template)

        # Dictionary of plate wells so that we don't keep accessing the database
        # multiple times
        a_wells = {}
        b_wells = {}
        for well in a_well_list:
            a_wells[well] = Vessel.objects.get(parent=plate, description=well)
        for well in b_well_list:
            b_wells[well] = Vessel.objects.get(parent=plate, description=well)

        # Create outcome templates, Currently hard coded to capture 96 values
        ot, created = OutcomeTemplate.objects.get_or_create(
            description="Crystal score",
            experiment_template=exp_template,
            # instance_labels=well_list,
            default_value=default_crystal_score,
        )
        ot.save()
        # exp_template.outcome_templates.add(ot)

        action_parameter_def = {
            "dispense": (("volume", "uL"),),
            "bring_to_temperature": (("temperature", "degC"),),
            "stir": (("duration", "s"), ("speed", "rpm")),
            "heat": (("temperature", "degC"), ("duration", "s")),
            "heat_stir": (("duration", "s"), ("speed", "rpm"), ("temperature", "degC")),
            "dwell": (("duration", "s"),),
        }
        # Action defs it is assumed that action defs are already inserted
        actions = [  # List of tuples (Description, Action def description, source_bommaterial, destination_bommaterial)
            # Preheat plate
            (
                "Preheat Plate",
                "bring_to_temperature",
                (None, None),
                ("vessel", "48 well plate - WF3"),
                "Preheat Plate",
            ),
            # Dispense Solvent to vials
            (
                "Dispense Reagent 1 - Solvent",
                "dispense",
                (None, "Reagent 1 - Solvent"),
                ("vessel", a_wells),
                "Dispense Reagent 1 - Solvent",
            ),
            # Dispense Stock A to vials
            (
                "Dispense Reagent 2 - Stock A",
                "dispense",
                (None, "Reagent 2 - Stock A"),
                ("vessel", a_wells),
                "Dispense Reagent 2 - Stock A",
            ),
            # Dispense Stock B to vials
            (
                "Dispense Reagent 3 - Stock B",
                "dispense",
                (None, "Reagent 3 - Stock B"),
                ("vessel", a_wells),
                "Dispense Reagent 3 - Stock B",
            ),
            # Mix
            (
                "Heat-Stir",
                "heat_stir",
                (None, None),
                ("vessel", "48 well plate - WF3"),
                "Heat-Stir",
            ),
            # Dispense antisolvent
            (
                "Dispense Reagent 9 - Antisolvent",
                "dispense",
                (None, "Reagent 9 - Antisolvent"),
                ("vessel", b_wells),
                "Dispense Reagent 9 - Antisolvent",
            ),
            # Store to wait for crystal growth
            (
                "Store",
                "dwell",
                (None, None),
                ("vessel", "48 well plate - WF3"),
                "Store",
            ),
        ]

        prev_action_template = None
        for action_tuple in actions:
            (
                action_desc,
                action_def_desc,
                (source_col, source_desc),
                (dest_col, dest_desc),
                action_seq,
            ) = action_tuple
            action_def, created = ActionDef.objects.get_or_create(
                description=action_def_desc
            )
            # action_sequences[action_seq].action_def.add(action_def)

            """
            action = Action(
                description=action_desc,
                action_def=action_def,
                action_sequence=action_sequences[action_seq],
            )
            action.save()
            """
            source_vessel_template = None
            source_vessel_decomposable = False
            if source_desc:
                default_vessel, created = Vessel.objects.get_or_create(
                    description="Generic Vessel"
                )
                source_vessel_template, created = VesselTemplate.objects.get_or_create(
                    experiment_template=exp_template,
                    description=source_desc,
                    outcome_vessel=False,
                    # decomposable=False,
                    default_vessel=default_vessel,
                )
                # exp_template.vessel_templates.add(source_vessel_template)

            dest_vessel_template = None
            dest_vessel_decomposable = False
            if dest_desc:
                # default_vessel = Vessel.objects.get(description="96 Well Plate well")
                default_vessel = plate
                (dest_vessel_template, created,) = VesselTemplate.objects.get_or_create(
                    experiment_template=exp_template,
                    description="Outcome vessel",
                    outcome_vessel=True,
                    default_vessel=default_vessel,
                )
                if isinstance(dest_desc, str):
                    dest_vessel_decomposable = False
                elif isinstance(dest_desc, dict):
                    dest_vessel_decomposable = True

            at, created = ActionTemplate.objects.get_or_create(
                description=action_desc,
                experiment_template=exp_template,
                action_def=action_def,
                source_vessel_template=source_vessel_template,
                source_vessel_decomposable=source_vessel_decomposable,
                dest_vessel_template=dest_vessel_template,
                dest_vessel_decomposable=dest_vessel_decomposable,
            )

            if prev_action_template is not None:
                at.parent.add(prev_action_template)
            prev_action_template = at

            for param_def_desc, unit in action_parameter_def[action_def_desc]:
                param, created = ParameterDef.objects.get_or_create(
                    description=param_def_desc,
                )
                param.default_val = Val.from_dict(
                    {"value": 0, "unit": unit, "type": "num"}
                )
                param.save()
                # action.parameter_def.add(param)
                action_def.parameter_def.add(param)

            """
            if source_desc is not None:
                rt = ReagentTemplate.objects.get(description=source_desc)
                source_bbm = BaseBomMaterial.objects.create(
                    description=source_desc, reagent=rt
                )
            else:
                source_bbm = None

            if dest_col == "vessel":
                if isinstance(dest_desc, dict):
                    for well in dest_desc.values():
                        dest_bbm = BaseBomMaterial.objects.create(
                            description=f"{plate.description} : {well.description}",
                            vessel=well,
                        )
                        if source_bbm:
                            description = f"{action.description} : {source_bbm.description} -> {dest_bbm.description}"
                        else:
                            description = (
                                f"{action.description} : {dest_bbm.description}"
                            )
                        ActionUnit.objects.create(
                            action=action,
                            source_material=source_bbm,
                            destination_material=dest_bbm,
                            description=description,
                        )
                else:
                    dest_bbm = BaseBomMaterial.objects.create(
                        description=plate.description, vessel=plate
                    )
                    if source_bbm:
                        description = f"{action.description} : {source_bbm.description} -> {dest_bbm.description}"
                    else:
                        description = f"{action.description} : {dest_bbm.description}"
                    ActionUnit.objects.create(
                        action=action,
                        source_material=source_bbm,
                        description=description,
                        destination_material=dest_bbm,
                    )

            elif dest_col is None:
                dest_bbm = BaseBomMaterial.objects.create(description=dest_desc)
                if source_bbm:
                    description = f"{action.description} : {source_bbm.description} -> {dest_bbm.description}"
                else:
                    description = f"{action.description} : {dest_bbm.description}"
                au = ActionUnit(
                    action=action,
                    source_material=source_bbm,
                    description=description,
                    destination_material=dest_bbm,
                )
                au.save()
            """

    def _create_wf3(self):
        # Creating the 48 well plate used for WF3 experiments
        plate = Vessel.objects.create(
            description="48 well plate - WF3",
            well_number=48,
            parent=None,
            metadata={'well_order': 
                ['A1','C1','E1','G1', 'B2','D2','F2','H2','A3','C3','E3','G3',
                'B4','D4','F4','H4','A5','C5','E5','G5', 'B6', 'D6', 'F6','H6',
                'A7','C7','E7','G7', 'B8','D8','F8','H8','A9', 'C9','E9','G9',
                'B10','D10','F10','H10','A11','C11','E11','G11', 'B12','D12','F12','H12']})
                
        plate.vessel_type.add(VesselType.objects.get(description="plate"))
        plate.save()
        plate_wells = {}
        vial_type = VesselType.objects.get(description="well")

        column_order = "ACEGBDFH"
        rows = 12
        a_well_list = []
        b_well_list = []
        well_list = []
        for row in range(rows):
            if (row + 1) % 2 != 0:
                for col in column_order[0:4]:
                    a_well_list.append("{}{}".format(col, row + 1))
                    well_list.append("{}{}".format(col, row + 1))
            else:
                for col in column_order[4:]:
                    b_well_list.append("{}{}".format(col, row + 1))
                    well_list.append("{}{}".format(col, row + 1))
        for well in well_list:
            plate_wells[well] = Vessel(parent=plate, description=well)

        Vessel.objects.bulk_create(plate_wells.values())
        for well in well_list:
            plate_wells[well].vessel_type.add(vial_type)
            plate_wells[well].save()

        # Get the lab related to this template
        lab = Actor.objects.get(
            description="Haverford College",
            person__isnull=True,
            systemtool__isnull=True,
        )

        # Create the experiment
        exp_template, created = ExperimentTemplate.objects.get_or_create(
            description="Workflow 3",
            ref_uid="workflow_3",
            lab=lab,
        )
        # exp_template.save()

        reagents = {
            "Reagent 2 - Stock A": ["inorganic", "organic", "solvent"],
            "Reagent 7 - Acid": ["acid"],
            "Reagent 3 - Stock B": ["inorganic", "organic", "solvent"],
            "Reagent 1 - Solvent": ["solvent"],
            "Reagent 9 - Antisolvent": ["solvent"],
        }

        # Vals for each default value
        volume_val = {"value": 0, "unit": "ml", "type": "num"}
        dead_vol_val = {"value": 4000, "unit": "uL", "type": "num"}
        amount_val = {"value": 0, "unit": "g", "type": "num"}
        conc_val = {"value": 0, "unit": "M", "type": "num"}
        crystal_score_val = {"value": 0, "unit": "", "type": "int"}

        # Create default values
        default_volume, created = DefaultValues.objects.get_or_create(
            **{
                "description": "Zero ml",
                "nominal_value": volume_val,
                "actual_value": volume_val,
            }
        )
        default_dead_volume, created = DefaultValues.objects.get_or_create(
            **{
                "description": "4000 uL",
                "nominal_value": dead_vol_val,
                "actual_value": dead_vol_val,
            }
        )
        default_amount, created = DefaultValues.objects.get_or_create(
            **{
                "description": "Zero g",
                "nominal_value": amount_val,
                "actual_value": amount_val,
            }
        )
        default_conc, created = DefaultValues.objects.get_or_create(
            **{
                "description": "Zero M",
                "nominal_value": conc_val,
                "actual_value": conc_val,
            }
        )
        default_crystal_score, created = DefaultValues.objects.get_or_create(
            **{
                "description": "Zero Crystal score",
                "nominal_value": crystal_score_val,
                "actual_value": crystal_score_val,
            }
        )

        # Concentration and amount data to be stored for each reagent material
        reagent_values = {"concentration": default_conc, "amount": default_amount}

        # Create total volume and dead volume property templates for each reagent
        total_volume_prop, created = PropertyTemplate.objects.get_or_create(
            **{
                "description": "total volume",
                "property_def_class": "extrinsic",
                "short_description": "volume",
                "default_value": default_volume,
            }
        )
        dead_volume_prop, created = PropertyTemplate.objects.get_or_create(
            **{
                "description": "dead volume",
                "property_def_class": "extrinsic",
                "short_description": "dead volume",
                "default_value": default_dead_volume,
            }
        )

        # Loop through each reagent in reagents dict and create ReagentTemplates,
        # corresponding ReagentMaterialTemplates and their Property Templates
        for r, rms in reagents.items():
            reagent_template, created = ReagentTemplate.objects.get_or_create(
                experiment_template=exp_template,
                description=r,
            )
            reagent_template.properties.add(total_volume_prop)
            reagent_template.properties.add(dead_volume_prop)
            # exp_template.reagent_templates.add(reagent_template)
            for rm in rms:
                self.stdout.write(self.style.NOTICE(f"{rm}"))
                material_type = MaterialType.objects.get(description=rm)
                (
                    reagent_material_template,
                    created,
                ) = ReagentMaterialTemplate.objects.get_or_create(
                    **{
                        "description": f"{r}: {rm}",
                        "reagent_template": reagent_template,
                        "material_type": material_type,
                    }
                )

                for rv, default in reagent_values.items():
                    (rmv_template, created,) = PropertyTemplate.objects.get_or_create(
                        # ReagentMaterialValueTemplate.objects.get_or_create(
                        **{
                            "description": rv,
                            # "reagent_material_template": reagent_material_template,
                            "default_value": default,
                        }
                    )
                    reagent_material_template.properties.add(rmv_template)

        # Dictionary of plate wells so that we don't keep accessing the database
        # multiple times
        a_wells = {}
        b_wells = {}
        for well in a_well_list:
            a_wells[well] = Vessel.objects.get(parent=plate, description=well)
        for well in b_well_list:
            b_wells[well] = Vessel.objects.get(parent=plate, description=well)

        # Create outcome templates, Currently hard coded to capture 96 values
        ot, created = OutcomeTemplate.objects.get_or_create(
            description="Crystal score",
            experiment_template=exp_template,
            # instance_labels=well_list,
            default_value=default_crystal_score,
        )
        ot.save()
        # exp_template.outcome_templates.add(ot)

        action_parameter_def = {
            "dispense": (("volume", "uL"),),
            "bring_to_temperature": (("temperature", "degC"),),
            "stir": (("duration", "s"), ("speed", "rpm")),
            "heat": (("temperature", "degC"), ("duration", "s")),
            "heat_stir": (("duration", "s"), ("speed", "rpm"), ("temperature", "degC")),
            "dwell": (("duration", "s"),),
        }
        # Action defs it is assumed that action defs are already inserted
        actions = [  # List of tuples (Description, Action def description, source_bommaterial, destination_bommaterial)
            # Preheat plate
            (
                "Preheat Plate",
                "bring_to_temperature",
                (None, None),
                ("vessel", "48 well plate - WF3"),
                "Preheat Plate",
            ),
            # Dispense Solvent to vials
            (
                "Dispense Reagent 1 - Solvent",
                "dispense",
                (None, "Reagent 1 - Solvent"),
                ("vessel", a_wells),
                "Dispense Reagent 1 - Solvent",
            ),
            # Dispense Stock A to vials
            (
                "Dispense Reagent 2 - Stock A",
                "dispense",
                (None, "Reagent 2 - Stock A"),
                ("vessel", a_wells),
                "Dispense Reagent 2 - Stock A",
            ),
            # Dispense Stock B to vials
            (
                "Dispense Reagent 3 - Stock B",
                "dispense",
                (None, "Reagent 3 - Stock B"),
                ("vessel", a_wells),
                "Dispense Reagent 3 - Stock B",
            ),
            # Dispense Acid
            (
                "Dispense Reagent 7 - Acid",
                "dispense",
                (None, "Reagent 7 - Acid"),
                ("vessel", a_wells),
                "Dispense Reagent 7 - Acid",
            ),
            # Mix
            (
                "Heat-Stir",
                "heat_stir",
                (None, None),
                ("vessel", "48 well plate - WF3"),
                "Heat-Stir",
            ),
            # Dispense antisolvent
            (
                "Dispense Reagent 9 - Antisolvent",
                "dispense",
                (None, "Reagent 9 - Antisolvent"),
                ("vessel", b_wells),
                "Dispense Reagent 9 - Antisolvent",
            ),
            # Store to wait for crystal growth
            (
                "Store",
                "dwell",
                (None, None),
                ("vessel", "48 well plate - WF3"),
                "Store",
            ),
        ]

        prev_action_template = None
        for action_tuple in actions:
            (
                action_desc,
                action_def_desc,
                (source_col, source_desc),
                (dest_col, dest_desc),
                action_seq,
            ) = action_tuple
            action_def, created = ActionDef.objects.get_or_create(
                description=action_def_desc
            )
            # action_sequences[action_seq].action_def.add(action_def)

            """
            action = Action(
                description=action_desc,
                action_def=action_def,
                action_sequence=action_sequences[action_seq],
            )
            action.save()
            """
            source_vessel_template = None
            source_vessel_decomposable = False
            if source_desc:
                default_vessel, created = Vessel.objects.get_or_create(
                    description="Generic Vessel"
                )
                source_vessel_template, created = VesselTemplate.objects.get_or_create(
                    experiment_template=exp_template,
                    description=source_desc,
                    outcome_vessel=False,
                    # decomposable=False,
                    default_vessel=default_vessel,
                )
                # exp_template.vessel_templates.add(source_vessel_template)

            dest_vessel_template = None
            dest_vessel_decomposable = False
            if dest_desc:
                # default_vessel = Vessel.objects.get(description="96 Well Plate well")
                default_vessel = plate
                (dest_vessel_template, created,) = VesselTemplate.objects.get_or_create(
                    experiment_template=exp_template,
                    description="Outcome vessel",
                    outcome_vessel=True,
                    default_vessel=default_vessel,
                )
                if isinstance(dest_desc, str):
                    dest_vessel_decomposable = False
                elif isinstance(dest_desc, dict):
                    dest_vessel_decomposable = True

            at, created = ActionTemplate.objects.get_or_create(
                description=action_desc,
                experiment_template=exp_template,
                action_def=action_def,
                source_vessel_template=source_vessel_template,
                source_vessel_decomposable=source_vessel_decomposable,
                dest_vessel_template=dest_vessel_template,
                dest_vessel_decomposable=dest_vessel_decomposable,
            )

            if prev_action_template is not None:
                at.parent.add(prev_action_template)
            prev_action_template = at

            for param_def_desc, unit in action_parameter_def[action_def_desc]:
                param, created = ParameterDef.objects.get_or_create(
                    description=param_def_desc,
                )
                param.default_val = Val.from_dict(
                    {"value": 0, "unit": unit, "type": "num"}
                )
                param.save()
                # action.parameter_def.add(param)
                action_def.parameter_def.add(param)

            """
            if source_desc is not None:
                rt = ReagentTemplate.objects.get(description=source_desc)
                source_bbm = BaseBomMaterial.objects.create(
                    description=source_desc, reagent=rt
                )
            else:
                source_bbm = None

            if dest_col == "vessel":
                if isinstance(dest_desc, dict):
                    for well in dest_desc.values():
                        dest_bbm = BaseBomMaterial.objects.create(
                            description=f"{plate.description} : {well.description}",
                            vessel=well,
                        )
                        if source_bbm:
                            description = f"{action.description} : {source_bbm.description} -> {dest_bbm.description}"
                        else:
                            description = (
                                f"{action.description} : {dest_bbm.description}"
                            )
                        ActionUnit.objects.create(
                            action=action,
                            source_material=source_bbm,
                            destination_material=dest_bbm,
                            description=description,
                        )
                else:
                    dest_bbm = BaseBomMaterial.objects.create(
                        description=plate.description, vessel=plate
                    )
                    if source_bbm:
                        description = f"{action.description} : {source_bbm.description} -> {dest_bbm.description}"
                    else:
                        description = f"{action.description} : {dest_bbm.description}"
                    ActionUnit.objects.create(
                        action=action,
                        source_material=source_bbm,
                        description=description,
                        destination_material=dest_bbm,
                    )

            elif dest_col is None:
                dest_bbm = BaseBomMaterial.objects.create(description=dest_desc)
                if source_bbm:
                    description = f"{action.description} : {source_bbm.description} -> {dest_bbm.description}"
                else:
                    description = f"{action.description} : {dest_bbm.description}"
                au = ActionUnit(
                    action=action,
                    source_material=source_bbm,
                    description=description,
                    destination_material=dest_bbm,
                )
                au.save()
            """

    def _load_reagents_and_outcomes(self):
        exp_template = ExperimentTemplate.objects.get(description="perovskite_demo")

        reagents = {
            "Reagent 3 - Stock B": ["organic", "solvent"],
            "Reagent 7 - Acid": ["acid"],
            "Reagent 2 - Stock A": ["inorganic", "organic", "solvent"],
            "Reagent 1 - Solvent": ["solvent"],
        }

        # Vals for each default value
        volume_val = {"value": 0, "unit": "ml", "type": "num"}
        dead_vol_val = {"value": 4000, "unit": "uL", "type": "num"}
        amount_val = {"value": 0, "unit": "g", "type": "num"}
        conc_val = {"value": 0, "unit": "M", "type": "num"}
        crystal_score_val = {"value": 0, "unit": "", "type": "int"}

        # Create default values
        default_volume, created = DefaultValues.objects.get_or_create(
            **{
                "description": "Zero ml",
                "nominal_value": volume_val,
                "actual_value": volume_val,
            }
        )
        default_dead_volume, created = DefaultValues.objects.get_or_create(
            **{
                "description": "WF1 dead volume",
                "nominal_value": dead_vol_val,
                "actual_value": dead_vol_val,
            }
        )
        default_amount, created = DefaultValues.objects.get_or_create(
            **{
                "description": "Zero g",
                "nominal_value": amount_val,
                "actual_value": amount_val,
            }
        )
        default_conc, created = DefaultValues.objects.get_or_create(
            **{
                "description": "Zero M",
                "nominal_value": conc_val,
                "actual_value": conc_val,
            }
        )
        default_crystal_score, created = DefaultValues.objects.get_or_create(
            **{
                "description": "Zero Crystal score",
                "nominal_value": crystal_score_val,
                "actual_value": crystal_score_val,
            }
        )

        # Concentration and amount data to be stored for each reagent material
        reagent_values = {"concentration": default_conc, "amount": default_amount}

        # Create total volume and dead volume property templates for each reagent
        total_volume_prop, created = PropertyTemplate.objects.get_or_create(
            **{
                "description": "total volume",
                "property_def_class": "extrinsic",
                "short_description": "volume",
                "default_value": default_volume,
            }
        )
        dead_volume_prop, created = PropertyTemplate.objects.get_or_create(
            **{
                "description": "dead volume",
                "property_def_class": "extrinsic",
                "short_description": "dead volume",
                "default_value": default_dead_volume,
            }
        )

        # Loop through each reagent in reagents dict and create ReagentTemplates,
        # corresponding ReagentMaterialTemplates and their PropertyTemplates
        for r, rms in reagents.items():
            reagent_template, created = ReagentTemplate.objects.get_or_create(
                description=r,
            )
            reagent_template.properties.add(total_volume_prop)
            reagent_template.properties.add(dead_volume_prop)
            exp_template.reagent_templates.add(reagent_template)
            for rm in rms:
                self.stdout.write(self.style.NOTICE(f"{rm}"))
                material_type = MaterialType.objects.get(description=rm)
                (
                    reagent_material_template,
                    created,
                ) = ReagentMaterialTemplate.objects.get_or_create(
                    **{
                        "description": f"{r}: {rm}",
                        "reagent_template": reagent_template,
                        "material_type": material_type,
                    }
                )

                for rv, default in reagent_values.items():
                    (rmv_template, created,) = PropertyTemplate(
                        # ReagentMaterialValueTemplate.objects.get_or_create(
                        **{
                            "description": rv,
                            # "reagent_material_template": reagent_material_template,
                            "default_value": default,
                        }
                    )
                    reagent_material_template.properties.add(rmv_template)
        # Create outcome templates, Currently hard coded to capture 96 values
        column_order = ["A", "C", "E", "G", "B", "D", "F", "H"]
        total_columns = 8
        well_count = 96
        row_limit = math.ceil(well_count / total_columns)
        well_names = [
            f"{col}{row}" for row in range(1, row_limit + 1) for col in column_order
        ]
        OutcomeTemplate.objects.get_or_create(
            description="Crystal score",
            experiment=exp_template,
            # instance_labels=well_names,
            default_value=default_crystal_score,
        )

    def _load_chem_inventory(self):
        self.stdout.write(self.style.NOTICE("Beginning loading chem"))

        # query for status
        active_status = Status.objects.get(description="active")
        # create default values
        DefaultValues.objects.get_or_create(
            description="g/ml",
            actual_value={
                "value": "0.0",
                "unit": "g/ml",
                "type": "num",
            },
        )
        gml_dv = DefaultValues.objects.get(description="g/ml")

        DefaultValues.objects.get_or_create(
            description="g/mol",
            actual_value={
                "value": "0.0",
                "unit": "g/mol",
                "type": "num",
            },
        )
        gmol_dv = DefaultValues.objects.get(description="g/mol")

        # create property templates
        PropertyTemplate.objects.get_or_create(
            description="MolecularWeight",
            property_def_class="intrinsic",
            status=active_status,
            default_value=gml_dv,
        )
        mw = PropertyTemplate.objects.get(description="MolecularWeight")

        PropertyTemplate.objects.get_or_create(
            description="Density",
            property_def_class="intrinsic",
            status=active_status,
            default_value=gmol_dv,
        )
        density = PropertyTemplate.objects.get(description="Density")

        filename = "load_chem_inventory.txt"
        LOAD_CHEM_INVENTORY = path_to_file(filename)
        with open(LOAD_CHEM_INVENTORY, newline="") as f:
            reader = csv.reader(f, delimiter="\t")

            # first row should be header
            column_names = next(reader)

            # {'col_0': 0, 'col_1': 1, ...}
            column_names_to_index = list_data_to_index(column_names)

            # this block of code loads new material types not in db
            material_types = set()
            for row in reader:
                # material_type
                material_types_this_row = [
                    x.strip()
                    for x in row[column_names_to_index["ChemicalCategory"]].split(",")
                ]
                for mat_type_description in material_types_this_row:
                    if mat_type_description != "":
                        material_types.add(mat_type_description)
            new_mat_types_counter = 0
            for mat_type_description in material_types:
                new_mat_type, created = MaterialType.objects.get_or_create(
                    description=mat_type_description
                )
                if created:
                    new_mat_types_counter += 1
            self.stdout.write(
                self.style.SUCCESS(f"Added {new_mat_types_counter} new material types")
            )

            # jump to top of csv
            f.seek(0)
            # skip initial header row
            next(reader)

            # query it once
            active_status = Status.objects.get(description="active")

            # this block of code loads new materials not in db
            new_mat_counter = 0
            for row in reader:
                mat_description = row[column_names_to_index["ChemicalName"]]
                if mat_description == "":
                    continue
                material, created = Material.objects.get_or_create(
                    description=mat_description, status=active_status
                )
                if created:
                    new_mat_counter += 1
            self.stdout.write(
                self.style.SUCCESS(f"Added {new_mat_counter} new materials")
            )

            # jump to top of csv
            f.seek(0)
            # skip initial header row
            next(reader)

            # this block of code matches each material to its material types(s)
            for row in reader:
                row_desc = row[column_names_to_index["ChemicalName"]]
                if string_is_null(row[column_names_to_index["ChemicalCategory"]]):
                    continue
                row_material_types_raw = [
                    x.strip()
                    for x in row[column_names_to_index["ChemicalCategory"]].split(",")
                ]
                row_material_types = [
                    MaterialType.objects.get(description=y)
                    for y in row_material_types_raw
                ]
                row_material = Material.objects.get(description=row_desc)
                row_material.material_type.add(*row_material_types)
            self.stdout.write(
                self.style.SUCCESS(f"Updated material types of materials")
            )

            # jump to top of csv
            f.seek(0)
            # skip initial header row
            next(reader)

            # this block of code loads the chemical reference (MaterialIdentifier) names not in db
            ref_name_cols = [
                "ChemicalName",
                "ChemicalAbbreviation",
                "InChI",
                "InChIKey",
                "CanonicalSMILES",
                "MolecularFormula",
            ]
            col_name_to_material_identifier_def = {
                "ChemicalName": MaterialIdentifierDef.objects.get(
                    description="Chemical_Name"
                ),
                "ChemicalAbbreviation": MaterialIdentifierDef.objects.get(
                    description="Abbreviation"
                ),
                "InChI": MaterialIdentifierDef.objects.get(description="InChI"),
                "InChIKey": MaterialIdentifierDef.objects.get(description="InChIKey"),
                "CanonicalSMILES": MaterialIdentifierDef.objects.get(
                    description="SMILES"
                ),
                "MolecularFormula": MaterialIdentifierDef.objects.get(
                    description="Molecular_Formula"
                ),
            }
            new_refname_counter = 0
            for row in reader:
                for col_name in ref_name_cols:
                    ref_name = row[column_names_to_index[col_name]]
                    if ref_name == "":
                        continue
                    (
                        new_material_identifier,
                        created,
                    ) = MaterialIdentifier.objects.get_or_create(
                        description=ref_name,
                        material_identifier_def=col_name_to_material_identifier_def[
                            col_name
                        ],
                        status=active_status,
                    )
                    if created:
                        new_refname_counter += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"Added {new_refname_counter} new material identifiers"
                )
            )

            # jump to top of csv
            f.seek(0)
            # skip initial header row
            next(reader)

            # this block of code matches each material to its material identifier(s)
            for row in reader:
                row_desc = row[column_names_to_index["ChemicalName"]]
                some_material = Material.objects.get(description=row_desc)
                for col_name in ref_name_cols:
                    ref_name = row[column_names_to_index[col_name]]
                    if ref_name == "":
                        continue
                    material_identifier = MaterialIdentifier.objects.get(
                        description=ref_name,
                        material_identifier_def=col_name_to_material_identifier_def[
                            col_name
                        ],
                        status=active_status,
                    )
                    if material_identifier != None:
                        some_material.identifier.add(material_identifier)
            self.stdout.write(
                self.style.SUCCESS(f"Updated material identifier for materials")
            )

            # jump to top of csv
            f.seek(0)
            # skip initial header row
            next(reader)
            # update molecular weight and density
            for row in reader:
                row_desc = row[column_names_to_index["ChemicalName"]]
                some_material, created = Material.objects.get_or_create(
                    **{"description": row_desc, "status": active_status}
                )

                # create property instances
                # not currently working, error occurs when passing material object in to property
                mw_val = row[column_names_to_index["MolecularWeight"]]
                den_val = row[column_names_to_index["Density"]]
                mw_value = {
                    "value": float(mw_val) if mw_val else None,
                    "unit": "g/mol",
                    "type": "num",
                }
                density_value = {
                    "value": float(den_val) if den_val else None,
                    "unit": "g/mL",
                    "type": "num",
                }
                Property.objects.create(
                    material=some_material, template=mw, value=mw_value
                )
                Property.objects.create(
                    material=some_material,
                    template=density,
                    value=density_value,
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Updated molecular weight and density for materials"
                )
            )

            self.stdout.write(self.style.NOTICE("Finished loading chem"))

    def _load_material_identifier(self):
        self.stdout.write(self.style.NOTICE("Beginning loading material identifier"))
        filename = "load_material_identifier.csv"
        MATERIAL_IDENTIFIERS = path_to_file(filename)

        df = pd.read_csv(MATERIAL_IDENTIFIERS, sep="\t", index_col=False, header=0)

        active_status = Status.objects.get(description="active")
        material_identifier_defs = {
            x.description: x for x in MaterialIdentifierDef.objects.all()
        }

        new_material_identifier = 0
        for _, row in df.iterrows():
            description = clean_string(row["description"])
            material_identifier_def__description = clean_string(
                row["material_identifier_def__description"]
            )
            material_identifier_def = (
                material_identifier_defs[y]
                if not string_is_null(y := material_identifier_def__description)
                else None
            )
            fields = {
                "description": description,
                "material_identifier_def": material_identifier_def,
                "status": active_status,
            }
            (
                material_identifier_instance,
                created,
            ) = MaterialIdentifier.objects.get_or_create(**fields)
            if created:
                new_material_identifier += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Added {new_material_identifier} new material identifiers"
            )
        )
        self.stdout.write(self.style.NOTICE("Finished loading material identifier"))

    def _load_material(self):
        self.stdout.write(self.style.NOTICE("Beginning loading material"))

        filenames = ["load_material.txt"]
        for filename in filenames:
            MATERIAL = path_to_file(filename)

            df = pd.read_csv(
                MATERIAL, sep="\t", index_col=False, header=0, na_filter=False
            )

            material_identifier_defs = {
                x.description: x for x in MaterialIdentifierDef.objects.all()
            }

            active_status = Status.objects.get(description="active")
            new_material = 0

            for _idx, row in df.iterrows():
                description = clean_string(row["description"])
                material_class = clean_string(row["material_class"])
                consumable = row["consumable"]

                material_identifier_descs_joined = clean_string(
                    row["material_identifier__description"]
                )
                material_identifier_def_descs_joined = clean_string(
                    row["material_identifier_def__description"]
                )
                material_type_descs_joined = clean_string(
                    row["material_type__description"]
                )

                # update phase, model update to include phase into materials and foreign key material from inventory material
                y: str
                material_identifier__description = (
                    [x.strip() for x in y.split("|")]
                    if not string_is_null(y := material_identifier_descs_joined)
                    else []
                )
                material_identifier_def__description = (
                    [x.strip() for x in y.split("|")]
                    if not string_is_null(y := material_identifier_def_descs_joined)
                    else []
                )
                material_type__description = (
                    [x.strip() for x in z.split("|")]
                    if not string_is_null(z := material_type_descs_joined)
                    else []
                )

                fields = {
                    "description": description,
                    "material_class": material_class,
                    "consumable": consumable,
                    "status": active_status,
                }
                material_instance, created = Material.objects.get_or_create(**fields)
                if created:
                    new_material += 1

                material_instance.identifier.add(
                    *[
                        MaterialIdentifier.objects.get(
                            description=descr,
                            material_identifier_def=material_identifier_defs[def_descr],
                        )
                        for descr, def_descr in zip(
                            material_identifier__description,
                            material_identifier_def__description,
                        )
                    ]
                )
                material_instance.material_type.add(
                    *[
                        MaterialType.objects.get(description=d)
                        for d in material_type__description
                    ]
                )

            self.stdout.write(self.style.SUCCESS(f"Added {new_material} new materials"))
        self.stdout.write(self.style.NOTICE("Finished loading material"))

    def _load_inventory_material(self):
        self.stdout.write(self.style.NOTICE("Beginning loading inventory material"))
        filename = "load_inventory_material.txt"
        INVENTORY_MATERIALS = path_to_file(filename)

        df = pd.read_csv(
            INVENTORY_MATERIALS, sep="\t", index_col=False, header=0, na_filter=False
        )

        active_status = Status.objects.get(description="active")

        new_inventory_material = 0
        for _idx, row in df.iterrows():
            description = clean_string(row["description"])
            inventory_description = clean_string(row["inventory_description"])
            material_description = clean_string(row["material_description"])
            part_no = clean_string(row["part_no"])

            onhand_amt_type = clean_string(row["onhand_amt_type"])
            onhand_amt_unit = clean_string(row["onhand_amt_unit"])
            onhand_amt_value = clean_string(row["onhand_amt_value"])

            expiration_date = clean_string(row["expiration_date"])
            location = clean_string(row["location"])

            try:
                material = (
                    Material.objects.get(description=material_description)
                    if not string_is_null(material_description)
                    else None
                )
                phase = None
                if material is not None:
                    if material.material_type.filter(
                        Q(description="acid")
                        | Q(description="solvent")
                        | Q(description="antisolvent")
                    ).exists():
                        phase = "liquid"
                    elif material.material_type.filter(
                        Q(description="organic")
                    ).exists():
                        phase = "solid"
                    elif material.material_type.filter(
                        Q(description="inorganic")
                    ).exists():
                        phase = "solid"
                fields = {
                    "description": description,
                    "inventory": Inventory.objects.get(
                        description=inventory_description
                    )
                    if not string_is_null(inventory_description)
                    else None,
                    "material": material,
                    "part_no": part_no,
                    "onhand_amt": get_val_field_dict(
                        onhand_amt_type, onhand_amt_unit, onhand_amt_value
                    ),
                    # 'expiration_date': expiration_date if not string_is_null(expiration_date) else None,
                    "phase": phase,
                    "location": location,
                    "status": active_status,
                }
                (
                    inventory_material_instance,
                    created,
                ) = InventoryMaterial.objects.get_or_create(**fields)
                if created:
                    new_inventory_material += 1
                material_object = Material.objects.get(description=material_description)
                inventory_material_instance.material = material_object
            except Material.DoesNotExist:
                inventory_material_instance.material = None
            except Exception as e:
                print(e)
                print(material_description)

        self.stdout.write(
            self.style.SUCCESS(
                f"Added {new_inventory_material} new inventory materials"
            )
        )
        self.stdout.write(self.style.NOTICE("Finished loading inventory material"))

    def _load_vessels(self):
        self.stdout.write(self.style.NOTICE("Beginning loading vessels"))
        # filename = 'old_dev_schema_materials.csv'
        # filename = "load_vessel.csv"
        filename = "load_opentrons_vessels.csv"
        OLD_DEV_SCHEMA_MATERIALS = path_to_file(filename)

        df = pd.read_csv(
            OLD_DEV_SCHEMA_MATERIALS,
            sep=",",
            index_col=False,
            header=0,
            na_filter=False,
        )

        active_status = Status.objects.get(description="active")

        new_vessels = 0
        # new_plates = 0
        for _, row in df.iterrows():
            description = clean_string(row["description"])
            vol = clean_string(row["total_volume"])
            if len(vol.split()) > 1:
                val = vol.split()[0]
                unit = vol.split()[1]
                total_volume = Val.from_dict(
                    {"value": val, "unit": unit, "type": "num"}
                )
            else:
                total_volume = None

            if string_is_null(row["column_order"]):
                column_order = None
            else:
                column_order = clean_string(row["column_order"])

            well_number = row["well_number"]

            vessel, created = Vessel.objects.get_or_create(
                description=description,
                total_volume=total_volume,
                well_number=well_number,
                column_order=column_order,
                status=active_status,
            )
            if created:
                new_vessels += 1

            if well_number > 1:
                wells = make_well_labels_list(
                    well_count=well_number, column_order=column_order, robot="False"
                )
                for well in wells:
                    well_instance, created = Vessel.objects.get_or_create(
                        description=well, parent=vessel, status=active_status
                    )

            """parts = description.split("#:")
            assert 1 <= len(parts) <= 2
            plate_name = parts[0].strip() if len(parts) >= 1 else None
            well_number = parts[1].strip() if len(parts) > 1 else None
            plate_instance, created = Vessel.objects.get_or_create(
                description=plate_name, status=active_status
            )
            if well_number is not None:
                well_instance, created = Vessel.objects.get_or_create(
                    description=well_number, parent=plate_instance, status=active_status
                )
                if created:
                    new_plates += 1"""
        self.stdout.write(self.style.SUCCESS(f"Added {new_vessels} new vessels"))
        # self.stdout.write(self.style.SUCCESS(f"Added {new_plates} new plates"))

        self.stdout.write(self.style.NOTICE("Finished loading vessels"))

    # ---------------EXPERIMENT--------------

    def _load_experiment_related_def(self):
        self.stdout.write(self.style.NOTICE("Beginning experiment related def"))
        self._load_parameter_def()
        self._load_action_def()
        # self._load_calculation_def()
        self.stdout.write(self.style.NOTICE("Finished loading experiment related def"))

    def _load_parameter_def(self):
        self.stdout.write(self.style.NOTICE("Beginning loading parameter def"))
        filename = "load_parameter_def.csv"
        PARAMETER_DEF = path_to_file(filename)

        df = pd.read_csv(
            PARAMETER_DEF, sep="\t", index_col=False, header=0, na_filter=False
        )

        active_status = Status.objects.get(description="active")

        new_parameter_def = 0
        for _, row in df.iterrows():
            description = clean_string(row["description"])
            type_ = clean_string(row["type"])
            value_from_csv = clean_string(str(row["value"]))
            unit = clean_string(row["unit"])
            required = to_bool(row["required"])
            unit_type = clean_string(row["unit_type"])
            fields = {
                "description": description,
                "default_val": get_val_field_dict(type_, unit, value_from_csv),
                "unit_type": unit_type,
                "required": required,
                "status": active_status,
            }
            row_parameter_def_instance, created = ParameterDef.objects.get_or_create(
                **fields
            )
            if created:
                new_parameter_def += 1
        self.stdout.write(
            self.style.SUCCESS(f"Added {new_parameter_def} new parameter def")
        )
        self.stdout.write(self.style.NOTICE("Finished loading parameter def"))

    def _load_action_def(self):
        self.stdout.write(self.style.NOTICE("Beginning loading action def"))
        filename = "load_action_def.csv"
        ACTION_DEF = path_to_file(filename)

        df = pd.read_csv(
            ACTION_DEF, sep="\t", index_col=False, header=0, na_filter=False
        )
        active_status = Status.objects.get(description="active")

        new_action_def = 0
        for _, row in df.iterrows():
            description = clean_string(row["description"])
            parameter_def_descriptions = (
                [x.strip() for x in y.split(",")]
                if not string_is_null(y := row["parameter_def_descriptions"])
                else []
            )
            synonym = clean_string(row["synonym"])

            action_def_instance, created = ActionDef.objects.get_or_create(
                description=description, synonym=synonym, status=active_status
            )
            if created:
                new_action_def += 1
            action_def_instance.parameter_def.add(
                *[
                    ParameterDef.objects.filter(description=x).first()
                    for x in parameter_def_descriptions
                ]
            )
        self.stdout.write(self.style.SUCCESS(f"Added {new_action_def} new action def"))
        self.stdout.write(self.style.NOTICE("Finished loading action def"))

    def _load_calculation_def(self):
        self.stdout.write(self.style.NOTICE("Beginning loading calculation def"))
        filename = "load_calculation_def.csv"
        CALCULATION_DEF = path_to_file(filename)

        df = pd.read_csv(
            CALCULATION_DEF, sep="\t", index_col=False, header=0, na_filter=False
        )
        active_status = Status.objects.get(description="active")
        new_calculation_def = 0

        # create calculation def
        for _, row in df.iterrows():
            description = clean_string(row["description"])
            short_name = clean_string(row["short_name"])
            calc_definition = clean_string(row["calc_definition"])
            in_type__description = clean_string(row["in_type__description"])
            in_opt_type__description = clean_string(row["in_opt_type__description"])
            out_type__description = clean_string(row["out_type__description"])
            systemtool_name = clean_string(row["systemtool_name"])
            fields = {
                "description": description,
                "short_name": short_name,
                "calc_definition": calc_definition,
                "in_type": TypeDef.objects.get(
                    description=in_type__description, category="data"
                )
                if not string_is_null(in_type__description)
                else None,
                "in_opt_type": TypeDef.objects.get(
                    description=in_opt_type__description, category="data"
                )
                if not string_is_null(in_opt_type__description)
                else None,
                "out_type": TypeDef.objects.get(
                    description=out_type__description, category="data"
                )
                if not string_is_null(out_type__description)
                else None,
                "systemtool": Systemtool.objects.get(systemtool_name=systemtool_name)
                if not string_is_null(systemtool_name)
                else None,
                "status": active_status,
            }
            """
            calculation_def_instance, created = CalculationDef.objects.get_or_create(
                **fields)
            if created:
                new_calculation_def += 1
            parameter_def_descriptions = [x.strip() for x in y.split(',')] if not string_is_null(
                y := row[column_names_to_index['parameter_def_descriptions']]) else []
            calculation_def_instance.parameter_def.add(
                *[ParameterDef.objects.get(description=d) for d in parameter_def_descriptions])
            """

        # go back and save self foreign keys
        for _, row in df.iterrows():
            short_name = row["short_name"]
            row_calculation_def_instance = CalculationDef.objects.get(
                short_name=short_name
            )

            in_source__short_name = clean_string(row["in_source__short_name"])
            in_opt_source__short_name = clean_string(row["in_opt_source__short_name"])

            fields = {
                "in_source": CalculationDef.objects.get(
                    short_name=in_source__short_name
                )
                if not string_is_null(in_source__short_name)
                else None,
                "in_opt_source": CalculationDef.objects.get(
                    short_name=in_opt_source__short_name
                )
                if not string_is_null(in_opt_source__short_name)
                else None,
            }
            for field, value in fields.items():
                setattr(row_calculation_def_instance, field, value)
            row_calculation_def_instance.save(
                update_fields=["in_source", "in_opt_source"]
            )
        self.stdout.write(
            self.style.SUCCESS(f"Added {new_calculation_def} new calculation def")
        )
        self.stdout.write(self.style.NOTICE("Finished loading calculation def"))

    '''def _load_mixture(self):
        self.stdout.write(self.style.NOTICE("Beginning loading mixture"))
        filename = "load_mixture.csv"
        MIXTURE = path_to_file(filename)

        df = pd.read_csv(MIXTURE, sep="\t", index_col=False, header=0, na_filter=False)
        active_status = Status.objects.get(description="active")

        new_mixture = 0
        for _, row in df.iterrows():
            material_composite_description = clean_string(
                row["material_composite_description"]
            )
            material_component_description = clean_string(
                row["material_component_description"]
            )
            addressable = clean_string(row["addressable"])
            fields = {
                "composite": Material.objects.get(description=y)
                if not string_is_null(y := material_composite_description)
                else None,
                "component": Material.objects.get(description=y)
                if not string_is_null(y := material_component_description)
                else None,
                "addressable": to_bool(addressable),
                "status": active_status,
            }
            mixture_instance, created = Mixture.objects.get_or_create(**fields)
            if created:
                new_mixture += 1
        self.stdout.write(self.style.SUCCESS(f"Added {new_mixture} new mixture"))
        self.stdout.write(self.style.NOTICE("Finished loading mixture"))'''

    def _load_base_bom_material(self):
        self.stdout.write(self.style.NOTICE("Beginning loading base bom material"))

        filename = "load_base_bom_material.csv"
        BASE_BOM_MATERIAL = path_to_file(filename)

        df = pd.read_csv(
            BASE_BOM_MATERIAL, sep="\t", index_col=False, header=0, na_filter=False
        )
        active_status = Status.objects.get(description="active")

        new_base_bom_material = 0
        new_bom_material = 0
        new_bom_composite_material = 0
        for _, row in df.iterrows():
            description = clean_string(row["description"])
            bom_description = clean_string(row["bom_description"])
            inventory_material_description = clean_string(
                row["inventory_material_description"]
            )
            alloc_amt_val_type = clean_string(row["alloc_amt_val_type"])
            alloc_amt_val_unit = clean_string(row["alloc_amt_val_unit"])
            alloc_amt_val_value = clean_string(row["alloc_amt_val_value"])
            used_amt_val_type = clean_string(row["used_amt_val_type"])
            used_amt_val_unit = clean_string(row["used_amt_val_unit"])
            used_amt_val_value = clean_string(row["used_amt_val_value"])
            putback_amt_val_type = clean_string(row["putback_amt_val_type"])
            putback_amt_val_unit = clean_string(row["putback_amt_val_unit"])
            putback_amt_val_value = clean_string(row["putback_amt_val_value"])
            mixture_composite_description = clean_string(
                row["mixture_composite_description"]
            )
            mixture_component_description = clean_string(
                row["mixture_component_description"]
            )

            # mixture_composite = Material.objects.get(description=mixture_composite_description) \
            #    if not string_is_null(mixture_composite_description) else None
            # mixture_component = Material.objects.get(description=mixture_component_description) \
            #    if not string_is_null(mixture_component_description) else None

            fields = {
                "description": description,
                "bom": BillOfMaterials.objects.get(description=bom_description)
                if not string_is_null(bom_description)
                else None,
                # 'inventory_material': InventoryMaterial.objects.get(description=y) if not string_is_null(y := inventory_material_description) else None,
                "alloc_amt_val": get_val_field_dict(
                    alloc_amt_val_type, alloc_amt_val_unit, alloc_amt_val_value
                ),
                "used_amt_val": get_val_field_dict(
                    used_amt_val_type, used_amt_val_unit, used_amt_val_value
                ),
                "putback_amt_val": get_val_field_dict(
                    putback_amt_val_type,
                    putback_amt_val_unit,
                    putback_amt_val_value,
                ),
                # 'mixture': Mixture.objects.get(composite=mixture_composite,
                #                               component=mixture_component
                #                               ) if mixture_composite != None or mixture_component != None else None,
                "status": active_status,
            }

            (
                base_bom_material_instance,
                created,
            ) = BaseBomMaterial.objects.get_or_create(**fields)

            try:
                inventory_material_object = InventoryMaterial.objects.get(
                    description=inventory_material_description
                )
                base_bom_material_instance.inventory_material = (
                    inventory_material_object
                )
                new_bom_material += 1
            except InventoryMaterial.DoesNotExist:
                base_bom_material_instance.inventory_material = None

            if created:
                new_base_bom_material += 1

        # go back and save self bom_material fk
        for _, row in df.iterrows():
            description = clean_string(row["description"])
            bom_description = clean_string(row["bom_description"])
            inventory_material_description = clean_string(
                row["inventory_material_description"]
            )
            mixture_composite_description = clean_string(
                row["mixture_composite_description"]
            )
            mixture_component_description = clean_string(
                row["mixture_component_description"]
            )

            # mixture_composite = Material.objects.get(description=mixture_composite_description) \
            #    if not string_is_null(mixture_composite_description) else None
            # mixture_component = Material.objects.get(description=mixture_component_description) \
            #    if not string_is_null(mixture_component_description) else None

            fields = {
                "description": description,
                "bom": BillOfMaterials.objects.get(description=bom_description)
                if not string_is_null(bom_description)
                else None,
                # 'inventory_material': InventoryMaterial.objects.get(description=y) if not string_is_null(y := inventory_material_description) else None
                # 'mixture': Mixture.objects.get(composite=mixture_composite,
                #                               component=mixture_component
                #                               ) if mixture_composite != None or mixture_component != None else None
            }

            bom_material_description = clean_string(row["bom_material_description"])
            bom_material_bom_description = clean_string(
                row["bom_material_bom_description"]
            )
            bom_material_bom = (
                BillOfMaterials.objects.get(description=y)
                if not string_is_null(y := bom_material_bom_description)
                else None
            )

            row_base_bom_material_instance = BaseBomMaterial.objects.get(**fields)

            try:
                inventory_material_object = InventoryMaterial.objects.get(
                    description=inventory_material_description
                )
                row_base_bom_material_instance.inventory_material = (
                    inventory_material_object
                )
            except InventoryMaterial.DoesNotExist:
                row_base_bom_material_instance.inventory_material = None

            try:
                row_base_bom_material_instance.bom_material = BomMaterial.objects.get(
                    description=bom_material_description, bom=bom_material_bom
                )
            except BomMaterial.DoesNotExist:
                row_base_bom_material_instance.bom_material = None

            row_base_bom_material_instance.save(update_fields=["bom_material"])
        self.stdout.write(
            self.style.SUCCESS(f"Added {new_base_bom_material} new base bom materials")
        )
        self.stdout.write(
            self.style.SUCCESS(f"Added {new_bom_material} new bom materials")
        )

    def _load_action(self):
        self.stdout.write(self.style.NOTICE("Beginning loading action"))
        filename = "load_action.csv"
        ACTION = path_to_file(filename)

        df = pd.read_csv(ACTION, sep="\t", index_col=False, header=0, na_filter=False)
        active_status = Status.objects.get(description="active")

        new_action = 0
        for _, row in df.iterrows():
            description = clean_string(row["description"])
            action_def_description = clean_string(row["action_def_description"])
            action_sequence_description = clean_string(row["workflow_description"])
            start_date = clean_string(row["start_date"])
            end_date = clean_string(row["end_date"])
            duration = clean_string(row["duration"])
            repeating = clean_string(row["repeating"])
            calculation_def_short_name = clean_string(row["calculation_def_short_name"])

            fields = {
                "description": description,
                "action_def": ActionDef.objects.get(description=y)
                if not string_is_null(y := action_def_description)
                else None,
                "start_date": start_date if not string_is_null(start_date) else None,
                "end_date": end_date if not string_is_null(end_date) else None,
                "duration": int(duration) if not string_is_null(duration) else None,
                "repeating": int(repeating) if not string_is_null(repeating) else None,
                # 'calculation_def': CalculationDef.objects.get(short_name=y) if not string_is_null(y := calculation_def_short_name) else None,
                "status": active_status,
            }

            action_instance, created = Action.objects.get_or_create(**fields)

            if created:
                new_action += 1

            parameter_def_description = (
                [x.strip() for x in y.split(",")]
                if not string_is_null(y := row["parameter_def_description"])
                else []
            )
            # action_instance.parameter_def.add(
            #    *[
            #        ParameterDef.objects.get(description=d)
            #        for d in parameter_def_description
            #    ]
            # )

        self.stdout.write(self.style.SUCCESS(f"Added {new_action} new action"))
        self.stdout.write(self.style.NOTICE("Finished loading action"))

    def _load_action_unit(self):
        self.stdout.write(self.style.NOTICE("Beginning loading action unit"))
        filename = "load_action_unit.csv"
        ACTION_UNIT = path_to_file(filename)

        df = pd.read_csv(
            ACTION_UNIT, sep="\t", index_col=False, header=0, na_filter=False
        )
        active_status = Status.objects.get(description="active")

        new_action_unit = 0
        for _, row in df.iterrows():
            action_description = clean_string(row["action_description"])
            action_action_sequence_description = clean_string(
                row["action_workflow_description"]
            )

            source_material_description = clean_string(
                row["source_material_description"]
            )
            source_material_bom_description = clean_string(
                row["source_material_bom_description"]
            )

            destination_material_description = clean_string(
                row["destination_material_description"]
            )
            destination_material_bom_description = clean_string(
                row["destination_material_bom_description"]
            )

            source_material_bom = (
                BillOfMaterials.objects.get(description=source_material_bom_description)
                if not string_is_null(source_material_bom_description)
                else None
            )

            destination_material_bom = (
                BillOfMaterials.objects.get(
                    description=destination_material_bom_description
                )
                if not string_is_null(destination_material_bom_description)
                else None
            )

            fields = {
                "action": Action.objects.get(
                    description=action_description,
                    action_sequence__description=action_action_sequence_description,
                )
                if not string_is_null(action_description)
                else None,
                "source_material": BaseBomMaterial.objects.get(
                    description=source_material_description, bom=source_material_bom
                )
                if not string_is_null(source_material_description)
                else None,
                "destination_material": BaseBomMaterial.objects.get(
                    description=destination_material_description,
                    bom=destination_material_bom,
                )
                if not string_is_null(destination_material_description)
                else None,
            }

            action_unit_instance = ActionUnit.objects.create(**fields)

            new_action_unit += 1
        self.stdout.write(
            self.style.SUCCESS(f"Added {new_action_unit} new action units")
        )
        self.stdout.write(self.style.NOTICE("Finished loading action unit"))


def path_to_file(filename):
    script_dir = os.path.dirname(__file__)
    csv_dir = "../../../../data_model/dataload_csv"
    return os.path.join(script_dir, f"{csv_dir}/{filename}")


def list_data_to_index(list_data):
    # hopefully list has hashable elements
    return {list_data[i]: i for i in range(len(list_data))}


def string_is_null(s):
    return s == None or s.strip() == "" or s.lower() == "null"


def clean_string(s):
    if s != None:
        return s.strip()
    return None


def to_bool(s):
    if s == "t" or s.lower() == "true" or s:
        return True
    else:
        return False


def get_val_field_dict(type_, unit, value_from_csv):
    if string_is_null(type_):
        return None
    if type_ == "text":
        value = value_from_csv
    elif type_ == "num":
        value = float(value_from_csv) if not string_is_null(value_from_csv) else 0.0
    elif type_ == "int":
        value = int(value_from_csv) if not string_is_null(value_from_csv) else 0
    elif type_ == "array_int":
        value = (
            [int(x.strip()) for x in value_from_csv.split(",")]
            if not string_is_null(value_from_csv)
            else []
        )
    elif type_ == "array_num":
        value = (
            [float(x.strip()) for x in value_from_csv.split(",")]
            if not string_is_null(value_from_csv)
            else []
        )
    elif type_ == "bool":
        value = to_bool(value_from_csv) if not string_is_null(value_from_csv) else False
    elif type_ == "array_bool":
        value = (
            [to_bool(x.strip()) for x in value_from_csv.split(",")]
            if not string_is_null(value_from_csv)
            else []
        )
    elif type_ == "array_text":
        value = (
            [x.strip() for x in value_from_csv.split(",")]
            if not string_is_null(value_from_csv)
            else []
        )
    elif type_ == "blob":
        value = value_from_csv
    else:
        assert False, f"{type_} is an invalid type"
    return {"type": type_, "unit": unit, "value": value}


def get_or_none(model_cls, fields):
    try:
        obj = model_cls.objects.get(**fields)
        return obj
    except:
        return None
