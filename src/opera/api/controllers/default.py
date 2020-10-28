import traceback

from opera.commands.info import info as opera_info
from opera.commands.outputs import outputs as opera_outputs
from opera.commands.validate import validate as opera_validate
from opera.storage import Storage

from opera.api.controllers.background_invocation import InvocationService
from opera.api.log import get_logger
from opera.api.openapi.models import ValidationResult, OperationType
from opera.api.openapi.models.deployment_input import DeploymentInput

logger = get_logger(__name__)

invocation_service = InvocationService()


def deploy(body: DeploymentInput = None):
    logger.debug("Entry: deploy")
    logger.debug(body)

    deployment_input = DeploymentInput.from_dict(body)
    result = invocation_service.invoke(OperationType.DEPLOY, deployment_input.service_template, deployment_input.inputs)
    return result, 200


def undeploy():
    logger.debug("Entry: undeploy")

    result = invocation_service.invoke(OperationType.UNDEPLOY, None, None)
    return result, 200


def outputs():
    logger.debug("Entry: outputs")

    try:
        opera_storage = Storage.create()
        result = opera_outputs(opera_storage)
    except Exception as e:
        logger.error("Error getting outputs.", e)
        return {"message": str(e)}, 500

    if not result:
        return {"message": "No outputs exist for this deployment."}, 404
    return result, 200


def status():
    logger.debug("Entry: status")
    history = invocation_service.invocation_history()
    return history, 200


def invocation_status(invocation_id):
    logger.debug("Entry: invocation_status")
    history = invocation_service.invocation_history()
    try:
        return next(inv for inv in history if inv.id == invocation_id), 200
    except StopIteration:
        return {"message": "No invocation with id {}".format(invocation_id)}, 404


def validate(body: DeploymentInput = None):
    logger.debug("Entry: validate")
    logger.debug(body)

    deployment_input = DeploymentInput.from_dict(body)

    result = ValidationResult()
    try:
        opera_validate(deployment_input.service_template, deployment_input.inputs)
        result.success = True
    except Exception as e:
        result.success = False
        result.message = "{}: {}\n\n{}".format(e.__class__.__name__, str(e), traceback.format_exc())

    return result, 200


def info():
    logger.debug("Entry: info")

    try:
        opera_storage = Storage.create()
        result = opera_info(opera_storage)
    except Exception as e:
        return {"message": "General error: {}".format(str(e))}, 500

    return result, 200
