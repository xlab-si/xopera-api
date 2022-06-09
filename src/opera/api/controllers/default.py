import tempfile
import traceback
from datetime import datetime
from pathlib import PurePath, Path

import pkg_resources
from opera.api.controllers.background_invocation import InvocationService
from opera.api.log import get_logger
from opera.api.openapi.models import ValidationInput, ValidationResult, OperationType, PackagingInput, UnpackagingInput, \
    PackagingResult, Info, DiffRequest, Diff, UpdateRequest
from opera.api.openapi.models.deployment_input import DeploymentInput
from opera.commands.diff import diff_instances as opera_diff_instances
from opera.commands.diff import diff_templates as opera_diff_templates
from opera.commands.info import info as opera_info
from opera.commands.outputs import outputs as opera_outputs
from opera.commands.package import package as opera_package
from opera.commands.unpackage import unpackage as opera_unpackage
from opera.commands.validate import validate as opera_validate
from opera.compare.instance_comparer import InstanceComparer
from opera.compare.template_comparer import TemplateComparer
from opera.storage import Storage

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
                    diff_result = opera_diff_templates(original_service_template, Path("."), original_inputs,
                                                       PurePath(new_service_template.name), Path("."),
                                                       diff_request.inputs, TemplateComparer(), True)
                else:
                    diff_result = opera_diff_instances(original_storage, Path("."), new_storage, Path("."),
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


def version():
    try:
        return pkg_resources.get_distribution("opera").version
    except pkg_resources.DistributionNotFound as e:
        return f"Error when retrieving current opera version: {e}"


def invocation_status(invocation_id):
    logger.debug("Entry: invocation_status")
    history = invocation_service.invocation_history()
    try:
        return next(inv for inv in history if inv.id == invocation_id), 200
    except StopIteration:
        return {"message": "No invocation with id {}".format(invocation_id)}, 404


def validate(body: dict = None):
    logger.debug("Entry: validate")
    logger.debug(body)

    validation_input = ValidationInput.from_dict(body)

    result = ValidationResult()
    try:
        opera_validate(PurePath(validation_input.service_template), validation_input.inputs, Storage, True, False)
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


def package(packaging_input: PackagingInput):
    logger.debug("Entry: package")

    try:
        path = opera_package(PurePath(packaging_input.service_template_folder), packaging_input.output,
                             PurePath(packaging_input.service_template), str(packaging_input.format))
        result = PackagingResult(path)
        return result, 200
    except Exception as e:
        return {"success": False, "message": "General error: {}".format(str(e))}, 500


def unpackage(unpackaging_input: UnpackagingInput):
    logger.debug("Entry: package")

    try:
        opera_unpackage(PurePath(unpackaging_input.csar), PurePath(unpackaging_input.destination))
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
