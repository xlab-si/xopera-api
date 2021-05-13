import traceback
from pathlib import PurePath

from opera.commands.info import info as opera_info
from opera.commands.init import init_compressed_csar as opera_init_compressed_csar
from opera.commands.outputs import outputs as opera_outputs
from opera.commands.package import package as opera_package
from opera.commands.unpackage import unpackage as opera_unpackage
from opera.commands.validate import validate_service_template as opera_validate
from opera.storage import Storage

from opera.api.controllers.background_invocation import InvocationService
from opera.api.log import get_logger
from opera.api.openapi.models import ValidationResult, OperationType, CsarInitializationInput, PackagingInput, \
    UnpackagingInput, PackagingResult, Info
from opera.api.openapi.models.deployment_input import DeploymentInput

logger = get_logger(__name__)

invocation_service = InvocationService()


def deploy(body: DeploymentInput = None):
    logger.debug("Entry: deploy")
    logger.debug(body)

    deployment_input = DeploymentInput.from_dict(body)
    result = invocation_service.invoke(OperationType.DEPLOY, deployment_input.service_template,
                                       deployment_input.inputs, deployment_input.clean_state)
    return result, 200


def undeploy():
    logger.debug("Entry: undeploy")

    result = invocation_service.invoke(OperationType.UNDEPLOY, None, None, None)
    return result, 200


def notify(trigger_name: str, body: bytes = None):
    logger.debug("Entry: notify")
    logger.debug("Body: %s", body.decode("UTF-8"))

    result = invocation_service.invoke(OperationType.NOTIFY, trigger_name, body.decode("UTF-8"), None)
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
        result = opera_info(PurePath("."), opera_storage)
    except Exception as e:
        return {"message": "General error: {}".format(str(e))}, 500

    serialized = Info(
        service_template=str(result["service_template"]),
        content_root=str(result["content_root"]),
        inputs=result["inputs"],
        status=result["status"]
    )

    return serialized, 200


def init(csar_initialization_input: CsarInitializationInput):
    logger.debug("Entry: init")

    try:
        opera_storage = Storage.create()
        opera_init_compressed_csar(".", csar_initialization_input.inputs,
                                   opera_storage, csar_initialization_input.clean)
        return {"success": True, "message": ""}, 200
    except Exception as e:
        return {"success": False, "message": "General error: {}".format(str(e))}, 500


def package(packaging_input: PackagingInput):
    logger.debug("Entry: package")

    try:
        path = opera_package(packaging_input.service_template_folder, packaging_input.output,
                             packaging_input.service_template, str(packaging_input.format))
        result = PackagingResult(path)
        return result, 200
    except Exception as e:
        return {"success": False, "message": "General error: {}".format(str(e))}, 500


def unpackage(unpackaging_input: UnpackagingInput):
    logger.debug("Entry: package")

    try:
        opera_unpackage(unpackaging_input.csar, unpackaging_input.destination)
        return {"success": True, "message": ""}, 200
    except Exception as e:
        return {"success": False, "message": "General error: {}".format(str(e))}, 500
