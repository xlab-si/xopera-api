import json
import connexion
from opera.api.controllers import utils
from opera.commands import \
    validate as validate_command, \
    outputs as output_command
from opera.api.openapi.models.deployment_input import DeploymentInput
from opera.api.controllers.invocation_service import \
    InvocationService as invocation_service


def deploy(deployment_input=None):
    if connexion.request.is_json:
        deployment_input = DeploymentInput.from_dict(
            connexion.request.get_json()
        )
    service = invocation_service()
    args, invocation = service.prepare_deploy(deployment_input)
    service.background_function(service.run_deployment, args=args)

    return invocation, 200


def undeploy():
    service = invocation_service()
    args, invocation = service.prepare_undeploy()
    service.background_function(service.run_undeployment, args=args)

    return invocation, 200


def outputs():
    service = invocation_service()
    args = service.prepare_outputs()
    try:
        with utils.CaptureString() as output:
            output_command.outputs(args)
        return json.loads(output.value), 200
    except Exception:
        return 'No outputs exist for this deployment.', 404


def status():
    service = invocation_service()
    return service.load_invocation_history(), 200


def invocation_status(invocation_id):
    service = invocation_service()
    invocation_status = service.load_invocation_status(invocation_id)
    if invocation_status:
        return invocation_status, 200
    else:
        return "No invocation with id {}".format(invocation_id), 404


def validate(deployment_input=None):
    if connexion.request.is_json:
        deployment_input = DeploymentInput.from_dict(
            connexion.request.get_json()
        )
    service = invocation_service()
    args, invocation = service.prepare_deploy(deployment_input)
    try:
        with utils.CaptureString() as output:
            validate_command.validate(args)
        return utils.get_validation_result(output), 200
    except Exception as e:
        return str(e), 500
