from typing import List, Dict, Any
from core.views.crud_views import LoginRequired
from django.shortcuts import render
from django.views import View
import json
import core.models.view_tables as vt

from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from django.http.response import JsonResponse
from pathlib import Path


class ActionTemplateView(LoginRequired, View):
    template_name = "core/action_template.html"

    def get_context_data(self, **kwargs):
        context = {}
        if "current_org_id" in self.request.session:
            org_id = self.request.session["current_org_id"]
            lab = vt.Actor.objects.get(organization=org_id, person__isnull=True)
            context["lab"] = lab
        return context

    # @method_decorator(login_required)
    def get(self, request, *args, **kwargs):

        context = self.get_context_data(**kwargs)

        if "current_org_id" in self.request.session:
            org_id = self.request.session["current_org_id"]

        else:
            return HttpResponseRedirect(reverse("main_menu"))

        base_path = Path("./core/static/json/")
        base_path2 = Path("./escalate/core/static/json/")

        path = base_path / Path("action_def_workflow.json")
        if not path.exists():
            path = base_path2 / Path("action_def_workflow.json")

        with path.open("r") as f:
            action_def_workflow = f.read()

        exp_template_uuid = kwargs["pk"]
        exp_template = vt.ExperimentTemplate.objects.get(uuid=kwargs["pk"])

        workflow = self._generate_existing_workflow(exp_template)

        action_defs = [a for a in vt.ActionDef.objects.all()]
        parameter_defs = [p for p in vt.ParameterDef.objects.all()]

        temp = self._generate_action_def_json(action_defs, exp_template)

        components = json.dumps(temp)

        context["components"] = components
        context["workflow"] = workflow
        context["exp_template"] = exp_template_uuid
        context["parameter_defs"] = parameter_defs
        context["dont_allow_save"] = (
            True
            if vt.ExperimentInstance.objects.filter(template=exp_template).exists()
            else False
        )

        return render(request, self.template_name, context=context)

    def _generate_existing_workflow(self, exp_template):
        """[summary]
        For the selected experiment template, this function obtains the action template and displays the information visually
        in the UI workflow designer

        Args:
            exp_template: Experiment Template database object

        Returns:
            json to render the workflow

        """
        parent_ats = vt.ActionTemplate.objects.filter(
            experiment_template=exp_template, parent=None
        )
        graph = {}
        queue = [at for at in parent_ats]
        visited = set()

        while len(queue) > 0:
            action_node = queue.pop(0)
            if action_node not in visited:
                graph[action_node] = action_node.children.all()
                visited.add(action_node)
                queue.extend([node for node in action_node.children.all()])

        return self._generate_workflow_json(graph, exp_template)

    def _generate_workflow_json(self, graph, exp_template):
        """Parses action template data to generate json in proper format to be rendered in workflow designer"""

        wf_coords: Dict[str, List[Dict[str, Any]]] = {}
        if exp_template.metadata is None:
            exp_template.metadata = {}

        if "workflow_coordinates" in exp_template.metadata:
            wf_coords = exp_template.metadata["workflow_coordinates"]
        else:
            wf_coords["activities"] = [
                {"id": "0", "top": 50, "left": 50, "type": "start", "state": {}}
            ]
            wf_coords["connections"] = []
            top = 50
            left = 350
            row = 0
            for i, node in enumerate(graph.keys()):
                activity = {
                    "id": str(node.uuid),
                    "top": top,
                    "left": left,
                    "type": node.action_def.description,
                    "state": {
                        "description": node.description,
                        "source": node.source_vessel_template.description
                        if node.source_vessel_template is not None
                        else " ",
                        "destination": node.dest_vessel_template.description
                        if node.dest_vessel_template is not None
                        else " ",
                        "destination_decomposable": "true"
                        if node.dest_vessel_decomposable
                        else "false",
                    },
                }
                i += 1
                if i % 2 == 0:
                    row += 1
                    top += 200
                    # left = 50
                else:
                    if row % 2 == 0:
                        left += 300
                    else:
                        left -= 300
                wf_coords["activities"].append(activity)
                # Connect start node with nodes without parents
                if not node.parent.all():
                    wf_coords["connections"].append(
                        {
                            "sourceActivityId": "0",
                            "destinationActivityId": str(node.uuid),
                            "outcome": "Done",
                        }
                    )

                # Connect child nodes
                for dest_node in graph[node]:
                    wf_coords["connections"].append(
                        {
                            "sourceActivityId": str(node.uuid),
                            "destinationActivityId": str(dest_node.uuid),
                            "outcome": "Done",
                        }
                    )

                # Connect end node with nodes without children
                if not node.children.all():
                    wf_coords["connections"].append(
                        {
                            "sourceActivityId": str(node.uuid),
                            "destinationActivityId": "1",
                            "outcome": "Done",
                        }
                    )
            # Add the end node
            wf_coords["activities"].append(
                {"id": "1", "top": top, "left": 50, "type": "end", "state": {}}
            )

        return json.dumps(wf_coords)

    def post(self, request, *args, **kwargs):
        #save action template and associate with experiment template
        #triggered upon clicking "save" button
        if "data" in request.POST: 
            data = json.loads(request.POST["data"])
            exp_template = vt.ExperimentTemplate.objects.get(uuid=data["exp_template"])
            at_url = reverse("action_template", args=[str(exp_template.uuid)])
            exp_template.action_templates = at_url
            return JsonResponse(
                data={"message": self._parse_activity_data(data, exp_template)}
            )

        #create new action definition
        #triggered upon clicking "create new action definition" button
        elif "actionDef_description" in request.POST: 
            actiondef_desc = request.POST["actionDef_description"]
            try:
                ad, created = vt.ActionDef.objects.get_or_create(
                    description=actiondef_desc
                ) #create action def

                for pdef_uuid in request.POST.getlist("parameterDefs"):
                    pdef = vt.ParameterDef.objects.get(uuid=pdef_uuid)
                    ad.parameter_def.add(pdef) #associate parameters
                ad.save()
            except Exception as e:
                print(e)
                return JsonResponse(
                    data={"message": f"Error could not create action definition. {e}"}
                )
            else:
                return JsonResponse(
                    data={"message": "Successfully created action definition"}
                )

    def _parse_activity_data(self, activity_data, exp_template):
        """[summary]
        This function parses a json of submitted data from the workflow designer and converts it into an action template, saving information
        for each action (description, action def, source vessel (and if it is decomposable), destination vessel (and if it is decomposable)).
        The information is used to create an action template that is then associated with the selected experiment template.

        Args:
            activity_data([dict]): json from workflow designer
            exp_template: Experiment Template database object

        Returns:
            ([str]) message to indicate success or failure saving the action template

        """
        if vt.ExperimentInstance.objects.filter(template=exp_template).exists():
            return "Cannot save changes to experiment template. Experiments using this template already exist"

        activity_dict = {}
        start_nodes = 0
        end_nodes = 0
        for a in activity_data["activities"]:
            if a["type"] == "start":
                start_nodes += 1
            elif a["type"] == "end":
                end_nodes += 1
            else:
                activity_dict[a["id"]] = a
        if not start_nodes == 1 or not end_nodes == 1:
            return "ERROR: Action template not saved. Start or End nodes not found"

        action_templates = {}

        for uid, a in activity_dict.items():
            # a["state"]
            adef_description = a["type"]
            at_description = a["state"].get("description", "")
            source = a["state"].get("source", None).strip()
            dest = a["state"].get("destination", None).strip()
            source_decomposable = a["state"].get("source_decomposable", False)
            dest_decomposable = a["state"].get("destination_decomposable", False)

            adef = vt.ActionDef.objects.get(description=adef_description)
            if source:
                source = vt.VesselTemplate.objects.get(description=source)
            if source_decomposable is None or source_decomposable == "false":
                source_decomposable = False
            elif source_decomposable == "true":
                source_decomposable = True
            if dest:
                dest = vt.VesselTemplate.objects.get(description=dest)
            if dest_decomposable is None or dest_decomposable == "false":
                dest_decomposable = False
            elif dest_decomposable == "true":
                dest_decomposable = True
            at, created = vt.ActionTemplate.objects.get_or_create(
                uuid=uid,
                description=at_description,
                experiment_template=exp_template,
            )
            at.action_def = adef
            at.source_vessel_template = source if source else None
            at.source_vessel_decomposable = source_decomposable
            at.dest_vessel_template = dest if dest else None
            at.dest_vessel_decomposable = dest_decomposable
            at.save()
            action_templates[str(at.uuid)] = at

        for conn in activity_data["connections"]:
            if (conn["destinationActivityId"] in action_templates) and (
                conn["sourceActivityId"] in action_templates
            ):
                action_templates[conn["destinationActivityId"]].parent.add(
                    action_templates[conn["sourceActivityId"]]
                )
                action_templates[conn["destinationActivityId"]].save()

        # Overwriting the saved workflow to experiment template
        if exp_template.metadata is None:
            exp_template.metadata = {}
        exp_template.metadata["workflow_coordinates"] = activity_data
        exp_template.save()

        return "SUCCESS: Workflow successfully saved"

    def _generate_action_def_json(self, action_defs, exp_template):
        """[summary]
        This function is used to populate the workflow designer tool with action definitions - each shows up as a "box"
        that can be added to a workflow design.

        Args:
            action_defs([list]): contains Action Def database objects
            exp_template: Experiment Template database object

        Returns:
            json data to render action definition "boxes" in workflow designer

        """

        vessel_choices = [
            (None, " ")
        ]  # add a "blank" option in case action has no source or no destination vessel

        for v_template in vt.VesselTemplate.objects.filter(
            experiment_template=exp_template
        ):
            vessel_choices.append(v_template.description)
            # dest_choices.append((v_template.description)

        json_data = [
            {
                "type": "start",
                "displayName": "Start",
                "runtimeDescription": " ",
                "description": "Start node",
                "category": "template",
                "outcomes": ["Done"],
                "properties": [],
            },
            {
                "type": "end",
                "displayName": "End",
                "runtimeDescription": " ",
                "description": "End node",
                "category": "template",
                "outcomes": ["Done"],
                "properties": [],
            },
        ]

        for i in range(len(action_defs)):

            json_data.append(
                {
                    "type": action_defs[i].description,
                    "displayName": action_defs[i].description,
                    "runtimeDescription": "x => `${ x.state.description }` ",
                    "description": action_defs[i].description,
                    "category": "template",
                    "outcomes": ["Done"],
                    "properties": [
                        {
                            "name": "description",
                            "type": "text",
                            "label": "Description",
                            "hint": "Name of action",
                            "options": {},
                        },
                        {
                            "name": "source",
                            "type": "select",
                            "label": "From:",
                            "hint": "source vessel",
                            "options": {"items": vessel_choices},
                        },
                        {
                            "name": "destination",
                            "type": "select",
                            "label": "To:",
                            "hint": "destination vessel",
                            "options": {"items": vessel_choices},
                        },
                        {
                            "name": "source_decomposable",
                            "type": "boolean",
                            "label": "Source vessel decomposable?",
                            "hint": "does the action apply to the entire source vessel, or to its components?",
                        },
                        {
                            "name": "destination_decomposable",
                            "type": "boolean",
                            "label": "Destination vessel decomposable?",
                            "hint": "does the action apply to the entire destination vessel, or to its components?",
                        },
                    ],
                }
            )
        return json_data
