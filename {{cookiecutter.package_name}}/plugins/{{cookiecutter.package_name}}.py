from http import HTTPStatus
from json import dumps, loads
from tempfile import SpooledTemporaryFile
from textwrap import dedent
from datetime import datetime
from typing import Any, Mapping, Optional, List, Dict, Tuple

import marshmallow as ma
from celery.canvas import chain
from celery.utils.log import get_task_logger
from flask import redirect, abort
from flask.wrappers import Response
from flask.app import Flask
from flask.globals import request
from flask.helpers import url_for
from flask.templating import render_template
from flask.views import MethodView
from marshmallow import EXCLUDE

from qhana_plugin_runner.api.plugin_schemas import (
    DataMetadata,
    PluginMetadataSchema,
    PluginMetadata,
    PluginType,
    EntryPoint,
)
from qhana_plugin_runner.api.util import FrontendFormBaseSchema, SecurityBlueprint
from qhana_plugin_runner.celery import CELERY
from qhana_plugin_runner.db.models.tasks import ProcessingTask
from qhana_plugin_runner.storage import STORE
from qhana_plugin_runner.tasks import save_task_error, save_task_result
from qhana_plugin_runner.util.plugins import QHAnaPluginBase, plugin_identifier


# plugin identifying constants
_plugin_name = "{{cookiecutter.plugin_identifier}}"
__version__ = "{{cookiecutter.plugin_version}}"
_identifier = plugin_identifier(_plugin_name, __version__) # full identifier including version


# Blueprint to register API endpoints with
PLUGIN_BLP = SecurityBlueprint( #SecurityBlueprint for eventual JWT support
    _identifier,  # blueprint name
    __name__,  # module import name!
    description="{{cookiecutter.description}}",
)

# Input parameters of the plugin
class {{cookiecutter.base_classname}}ParametersSchema(FrontendFormBaseSchema):
    example_value = ma.fields.String(
        required=True,
        allow_none=False,
        metadata={ # metadata holds extra information that is used for example in the form generator
            "label": "Example Value",
            "description": "A simple string example value.",
        },
    )


@PLUGIN_BLP.route("/")
class PluginView(MethodView):
    """Root resource of this plugin."""

    @PLUGIN_BLP.response(HTTPStatus.OK, PluginMetadataSchema())
    @PLUGIN_BLP.require_jwt("jwt", optional=True)
    def get(self):
        """Endpoint returning the plugin metadata."""
        plugin = {{cookiecutter.base_classname}}.instance
        if plugin is None:
            abort(HTTPStatus.INTERNAL_SERVER_ERROR)
        return PluginMetadata(
            # human readable title and description
            title=plugin.name,
            description=PLUGIN_BLP.description,
            # machine readable identifying name and version
            name=plugin.identifier,
            version=plugin.version,
            # pluin type: "processing"|"visualizing"|"conversion" (actual values still WIP!! confirm with current documentation)
            type=PluginType.processing,
            # tags describing the plugin, e.g. ml:autoencoder, ml:svm
            tags=[],
            # the main plugin entry point
            entry_point=EntryPoint(
                # entry point for headless (non-gui) applications
                href=url_for(f"{PLUGIN_BLP.name}.ProcessView"),
                # micro frontend entry point
                ui_href=url_for(f"{PLUGIN_BLP.name}.MicroFrontend"),
                # definition of (required) input data
                data_input=[],
                # definition of output data
                data_output=[
                    DataMetadata(
                        data_type="txt",
                        content_type=["text/plain"],
                        required=True,
                    )
                ],
            ),
        )


@PLUGIN_BLP.route("/ui/")
class MicroFrontend(MethodView):
    """Micro frontend for {{cookiecutter.plugin_name}}."""

    @PLUGIN_BLP.html_response(
        HTTPStatus.OK, description="Micro frontend of {{cookiecutter.plugin_name}}."
    )
    @PLUGIN_BLP.arguments(
        {{cookiecutter.base_classname}}ParametersSchema(
            # partial to allow partial inputs, validate as errors to get all validation errors
            # data is still stored in request.args
            partial=True, unknown=EXCLUDE, validate_errors_as_result=True
        ),
        location="query", # allow get submit via query parameters
        required=False, # micro frontend should just ignore most errors (but return error messages!)
    )
    @PLUGIN_BLP.require_jwt("jwt", optional=True)
    def get(self, errors):
        """Return the micro frontend."""
        return self.render(request.args, errors)

    @PLUGIN_BLP.html_response(
        HTTPStatus.OK, description="Micro frontend of the hello world plugin."
    )
    @PLUGIN_BLP.arguments(
        {{cookiecutter.base_classname}}ParametersSchema(
            # partial to allow partial inputs, validate as errors to get all validation errors
            # data is still stored in request.form
            partial=True, unknown=EXCLUDE, validate_errors_as_result=True
        ),
        location="form", # allow post submit of html form
        required=False, # micro frontend should just ignore most errors (but return error messages!)
    )
    @PLUGIN_BLP.require_jwt("jwt", optional=True)
    def post(self, errors):
        """Return the micro frontend with prerendered inputs."""
        return self.render(request.form, errors)

    def render(self, data: Mapping, errors: dict):
        """Render the micro frontend from the html template.

        Args:
            data (Mapping): The submitted data (may be incomplete!)
            errors (dict): Validation errors with the current submitted data

        Returns:
            Response: the rendered template with the submitted data prefilled and errors
        """
        plugin = {{cookiecutter.base_classname}}.instance
        if plugin is None:
            abort(HTTPStatus.INTERNAL_SERVER_ERROR)
        schema = {{cookiecutter.base_classname}}ParametersSchema()
        return Response(
            render_template(
                "simple_template.html",
                name=plugin.name,
                version=plugin.version,
                schema=schema, #schema is used to create the html form
                values=data, # data is used to prefill values in the form
                errors=errors, # errors is used to show error texts in the form
                process=url_for(f"{PLUGIN_BLP.name}.ProcessView"), # the endpoint starting the background task
            )
        )


@PLUGIN_BLP.route("/process/")
class ProcessView(MethodView):
    """Start a long running processing task."""

    @PLUGIN_BLP.arguments({{cookiecutter.base_classname}}ParametersSchema(unknown=EXCLUDE), location="form")
    @PLUGIN_BLP.response(HTTPStatus.SEE_OTHER)
    @PLUGIN_BLP.require_jwt("jwt", optional=True)
    def post(self, arguments):
        """Start the background task."""
        # create a new task instance in DB with the relevant parameters
        db_task = ProcessingTask(task_name=background_task.name, parameters=dumps(arguments))
        db_task.save(commit=True)

        # all tasks need to know about db id to load the db entry
        task: chain = background_task.s(db_id=db_task.id) | save_task_result.s(
            db_id=db_task.id
        )
        # save errors appearing somewhere in task chain to db
        task.link_error(save_task_error.s(db_id=db_task.id))

        try:
            # start the task chain as a background task
            task.apply_async()
        except Exception as e:
            # save error in DB if task could not be scheduled!
            db_task.task_status = "FAILURE"
            db_task.finished_at = datetime.utcnow()
            db_task.add_task_log_entry(f"Error scheduling task: {e!r}")

            db_task.save(commit=True)
            raise e # and raise exception again

        # redirect to the created task resource (constructed from the ProcessingTask saved in the DB)
        return redirect(
            url_for("tasks-api.TaskView", task_id=str(db_task.id)), HTTPStatus.SEE_OTHER
        )


class {{cookiecutter.base_classname}}(QHAnaPluginBase):
    """{{cookiecutter.description}}"""

    name = _plugin_name
    version = __version__

    def __init__(self, app: Optional[Flask]) -> None:
        super().__init__(app)

    def get_api_blueprint(self):
        return PLUGIN_BLP

    def get_requirements(self):
        return dedent("""# place your plugin requirements in here
        """)

################################################################################
# import plugin specific requirements below this line
# the get_requirements method of the plugin class must be defined and functional
# before any of the requirements specified in the method are imported!
################################################################################


TASK_LOGGER = get_task_logger(__name__)


# task names must be globally unique => use full versioned plugin identifier to scope name
@CELERY.task(name=f"{{'{'}}{{cookiecutter.base_classname}}.instance.identifier{{'}'}}.demo_task", bind=True)
def background_task(self, db_id: int) -> str:
    """The main background task of the plugin {{cookiecutter.plugin_name}}."""
    TASK_LOGGER.info(f"Starting new background task for plugin {{cookiecutter.plugin_name}} with db id '{db_id}'")

    # load task data based on given DB id
    task_data: Optional[ProcessingTask] = ProcessingTask.get_by_id(id_=db_id)

    if task_data is None:
        msg = f"Could not load task data with id {db_id} to read parameters!"
        TASK_LOGGER.error(msg)
        raise KeyError(msg)

    # deserialize task parameters
    task_parameters: Dict[str, Any] = loads(task_data.parameters or "{}")

    ############################################################################
    # TODO implement your background task
    ############################################################################
    
    # write output
    with SpooledTemporaryFile(mode="w") as output:
        output.write("TODO")
        STORE.persist_task_result(
            db_id, output, "{{cookiecutter.plugin_identifier}}.txt", "text", "text/plain"
        )
