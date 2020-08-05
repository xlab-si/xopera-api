from opera.commands.outputs import outputs as opera_outputs
from opera.commands.validate import validate as opera_validate
from opera.storage import Storage

from opera.api.controllers.background_invocation import InvocationService, opera_deploy_storage_proxy, \
    opera_undeploy_storage_proxy
from opera.api.log import get_logger
from opera.api.openapi.models import ValidationResult, OperationType
from opera.api.openapi.models.deployment_input import DeploymentInput

logger = get_logger(__name__)

# must be created (pool) _after_ any functions are referenced, otherwise AttributeError: can't get attribute
invocation_service = InvocationService()


def deploy(body: DeploymentInput = None):
    logger.debug("Entry: deploy")
    logger.debug(body)

    deployment_input = DeploymentInput.from_dict(body)
    result = invocation_service.invoke(
        opera_deploy_storage_proxy, [deployment_input.service_template, deployment_input.inputs, 1],
        OperationType.DEPLOY, deployment_input.inputs
    )

    return result, 200


def undeploy():
    logger.debug("Entry: undeploy")

    result = invocation_service.invoke(
        opera_undeploy_storage_proxy, [1],
        OperationType.UNDEPLOY, None
    )

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
        result.message = str(e)

    return result, 200
