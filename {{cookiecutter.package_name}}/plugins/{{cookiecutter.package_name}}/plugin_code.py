# when renaming this module also change the import in __init__.py

from http import HTTPStatus
from json import dumps, loads
from tempfile import SpooledTemporaryFile
from datetime import datetime
from typing import Any, Mapping, Optional, List, Dict, Tuple

from celery.canvas import chain
from celery.utils.log import get_task_logger
from flask import redirect
from flask.helpers import url_for
from flask.views import MethodView
from marshmallow import EXCLUDE

from qhana_plugin_runner.celery import CELERY
from qhana_plugin_runner.db.models.tasks import ProcessingTask
from qhana_plugin_runner.storage import STORE
from qhana_plugin_runner.tasks import save_task_error, save_task_result

################################################################################
# import plugin specific requirements in this module
# the get_requirements method of the plugin class must be defined and functional
# before any of the requirements specified in the method are imported!
################################################################################

from .api import PLUGIN_BLP, {{cookiecutter.base_classname}}ParametersSchema
from .plugin import {{cookiecutter.base_classname}}


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
