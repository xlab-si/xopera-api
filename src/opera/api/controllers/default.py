import json

import connexion
from opera.commands import outputs as output_command
from opera.commands import validate as validate_command

from opera.api.controllers import utils
from opera.api.controllers.invocation_service import InvocationService
from opera.api.log import get_logger
from opera.api.openapi.models.deployment_input import DeploymentInput

logger = get_logger(__name__)
invocation_service = InvocationService()


def deploy(deployment_input=None):
    logger.debug("Entry: deploy")

    if connexion.request.is_json:
        jayson = connexion.request.get_json()
        logger.debug("Request has json: ", str(jayson))
        deployment_input = DeploymentInput.from_dict(jayson)

    args, invocation = invocation_service.prepare_deploy(deployment_input)
    invocation_service.background_function(invocation_service.run_deployment, args=args)

    return invocation, 200


def undeploy():
    logger.debug("Entry: undeploy")

    args, invocation = invocation_service.prepare_undeploy()
    invocation_service.background_function(invocation_service.run_undeployment, args=args)

    return invocation, 200


def outputs():
    logger.debug("Entry: outputs")

    args = invocation_service.prepare_outputs()
    try:
        with utils.CaptureString() as output:
            output_command.outputs(args)
        return json.loads(output.value), 200
    except Exception as e:
        logger.error("Error getting outputs.", e)
        return {"message": "No outputs exist for this deployment."}, 404


def status():
    logger.debug("Entry: outputs")

    return invocation_service.load_invocation_history(), 200


def invocation_status(invocation_id):
    logger.debug("Entry: invocation_status")

    service = InvocationService()
    response = service.load_invocation_status(invocation_id)
    if response:
        return response, 200
    else:
        return {"message": "No invocation with id {}".format(invocation_id)}, 404


def validate(deployment_input=None):
    logger.debug("Entry: validate")

    if connexion.request.is_json:
        jayson = connexion.request.get_json()
        logger.debug("Request has json: ", str(jayson))
        deployment_input = DeploymentInput.from_dict(jayson)

    args, invocation = invocation_service.prepare_deploy(deployment_input)

    try:
        with utils.CaptureString() as output:
            validate_command.validate(args)
        return utils.get_validation_result(output), 200
    except Exception as e:
        logger.error("Validation error.", e)
        return str(e), 500
