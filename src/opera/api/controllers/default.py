import tempfile
import traceback
from datetime import datetime
from pathlib import PurePath

from opera.commands.diff import diff_instances as opera_diff_instances
from opera.commands.diff import diff_templates as opera_diff_templates
from opera.commands.info import info as opera_info
from opera.commands.init import init_compressed_csar as opera_init_compressed_csar
from opera.commands.outputs import outputs as opera_outputs
from opera.commands.package import package as opera_package
from opera.commands.unpackage import unpackage as opera_unpackage
from opera.commands.validate import validate_csar as opera_validate_csar
from opera.commands.validate import validate_service_template as opera_validate_service_template
from opera.compare.instance_comparer import InstanceComparer
from opera.compare.template_comparer import TemplateComparer
from opera.storage import Storage

from opera.api.controllers.background_invocation import InvocationService
from opera.api.log import get_logger
from opera.api.openapi.models import ValidationResult, OperationType, CsarInitializationInput, PackagingInput, \
    UnpackagingInput, PackagingResult, Info, CsarValidationInput, DiffRequest, Diff, UpdateRequest
from opera.api.openapi.models.deployment_input import DeploymentInput

logger = get_logger(__name__)

invocation_service = InvocationService()


def deploy(body: DeploymentInput = None):
    logger.debug("Entry: deploy")
    logger.debug(body)

    deployment_input = DeploymentInput.from_dict(body)
    result = invocation_service.invoke(OperationType.DEPLOY, deployment_input.service_template,
                                       deployment_input.inputs, deployment_input.clean_state)
    return result, 202


def diff(body: dict = None):
    logger.debug("Entry: diff")
    diff_request = DiffRequest.from_dict(body)

    try:
        original_storage = Storage.create()
        original_service_template = original_storage.read("root_file")
        original_inputs = original_storage.read_json("inputs")

        with tempfile.TemporaryDirectory(prefix=".opera-api-diff", dir=".") as new_storage_root:
            new_storage = Storage.create(instance_path=new_storage_root)
            with tempfile.NamedTemporaryFile(prefix="diff-service-template", dir=".") as new_service_template:
                new_service_template.write(diff_request.new_service_template_contents)
                new_service_template.flush()

                if diff_request.template_only:
                    diff_result = opera_diff_templates(original_service_template, ".", original_inputs,
                                                       new_service_template.name, ".", diff_request.inputs,
                                                       TemplateComparer(), True)
                else:
                    diff_result = opera_diff_instances(original_storage, ".", new_storage, ".",
                                                       TemplateComparer(), InstanceComparer(), True)

        result = Diff(
            added=diff_result.added,
            changed=diff_result.changed,
            deleted=diff_result.deleted
        )
    except Exception as e:
        logger.error("Error performing diff.", e)
        return {"message": str(e)}, 500

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
    logger.debug("Entry: validate (proxying to validate_service_template)")
    return validate_service_template(body)


def validate_service_template(body: dict = None):
    logger.debug("Entry: validate_service_template")
    logger.debug(body)

    deployment_input = DeploymentInput.from_dict(body)

    result = ValidationResult()
    try:
        opera_validate_service_template(PurePath(deployment_input.service_template), deployment_input.inputs)
        result.success = True
    except Exception as e:
        result.success = False
        result.message = "{}: {}\n\n{}".format(e.__class__.__name__, str(e), traceback.format_exc())

    return result, 200


def validate_csar(body: dict = None):
    logger.debug("Entry: validate_csar")
    logger.debug(body)

    path = "."
    inputs = None
    if body:
        csar_validation_input = CsarValidationInput.from_dict(body)
        if csar_validation_input.csar_path:
            # don't override with None
            path = csar_validation_input.csar_path
        inputs = csar_validation_input.inputs

    result = ValidationResult()
    try:
        opera_validate_csar(PurePath(path), inputs)
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

    serialized = Info(**result)

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


def update(body: dict = None):  # noqa: E501
    logger.debug("Entry: update")
    update_request = UpdateRequest.from_dict(body)

    posixnow = int(datetime.utcnow().timestamp())
    with open("st-operaapi-update-{}.yml".format(posixnow)) as new_st_file:
        new_st_file.write(update_request.new_service_template_contents)
        new_st_filename = new_st_file.name

    result = invocation_service.invoke(OperationType.UPDATE, new_st_filename, update_request.inputs, False)

    return result, 202
