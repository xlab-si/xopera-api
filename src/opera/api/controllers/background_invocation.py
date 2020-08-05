import datetime
import json
import multiprocessing
import os
import sys
import typing
import uuid
from io import StringIO
from pathlib import Path
from typing import List, Callable, Optional

from opera.commands.deploy import deploy as opera_deploy
from opera.commands.undeploy import undeploy as opera_undeploy
from opera.storage import Storage

from opera.api.log import get_logger
from opera.api.openapi.models import Invocation, InvocationState

logger = get_logger(__name__)


def get_instance_state():
    json_dict = {}
    for file_path in Path(os.path.join('.opera', 'instances')).glob("*"):
        parsed = json.load(open(file_path, 'r'))
        component_name = parsed['tosca_name']['data']
        json_dict[component_name] = parsed['state']['data']
    return json_dict


class StdoutCapture(object):
    def __enter__(self):
        self._stdout_backup = sys.stdout
        self._stringio = StringIO()
        sys.stdout = self._stringio
        return self

    def __exit__(self, *args):
        self.value = self._stringio.getvalue()
        del self._stringio  # free up some memory
        sys.stdout = self._stdout_backup

    def get_value(self):
        return self._stringio.getvalue()


class WrapperException(BaseException):
    def __init__(self, invocation_uuid, wrapped_exception):
        self.invocation_uuid = invocation_uuid
        self.wrapped_exception = wrapped_exception


def wrapper_start(function, function_args, invocation_uuid):
    logger.debug("Starting %s", invocation_uuid)

    local_inv = InvocationService.load_invocation(invocation_uuid)
    local_inv.state = InvocationState.IN_PROGRESS
    InvocationService.write_invocation(local_inv)

    with StdoutCapture() as capture:
        try:
            function(*function_args)
        # we want the console output no matter what
        except BaseException as e:
            wrapped_exc = WrapperException(invocation_uuid, e)
            raise wrapped_exc
        finally:
            local_inv = InvocationService.load_invocation(invocation_uuid)
            local_inv.console_output = capture.get_value()
            InvocationService.write_invocation(local_inv)

    return invocation_uuid


def wrapper_error(error: WrapperException):
    if not isinstance(error, WrapperException):
        logger.error("Unexpected out-of-band error.")
        raise error

    logger.error("Error in %s", error.invocation_uuid, exc_info=error.wrapped_exception)

    local_inv = InvocationService.load_invocation(error.invocation_uuid)
    local_inv.state = InvocationState.FAILED
    local_inv.exception = str(error)
    InvocationService.write_invocation(local_inv)


# gets param as the result of wrapper_start
def wrapper_done(invocation_uuid):
    logger.debug("Done with %s", invocation_uuid)

    local_inv = InvocationService.load_invocation(invocation_uuid)
    local_inv.state = InvocationState.SUCCESS
    local_inv.instance_state = get_instance_state()
    InvocationService.write_invocation(local_inv)


# necessary because we can't pickle the storage object and therefore can't submit upstream deploy to the pool
def opera_deploy_storage_proxy(service_template: str, inputs: typing.Optional[dict], num_workers: int):
    opera_storage = Storage.create()
    return opera_deploy(service_template, inputs, opera_storage, num_workers)


def opera_undeploy_storage_proxy(num_workers: int):
    opera_storage = Storage.create()
    opera_undeploy(opera_storage, num_workers)


class InvocationService:
    def __init__(self):
        # FIXME: should really be closed or used as a context manager
        self.pool = multiprocessing.Pool(1)  # one thing at a time

    def invoke(self, function: Callable, function_args: list,
               operation_type: str, inputs: Optional[dict]) -> Invocation:
        invocation_uuid = str(uuid.uuid4())
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        logger.info("Invoking %s with ID %s at %s", operation_type, invocation_uuid, now.isoformat())

        inv = Invocation()
        inv.id = invocation_uuid
        inv.state = InvocationState.PENDING
        inv.operation = operation_type
        inv.timestamp = now.isoformat()
        inv.inputs = inputs
        inv.instance_state = None
        inv.exception = None
        inv.console_output = None
        self.write_invocation(inv)

        wrapper_kwargs = dict(
            function=function,
            function_args=function_args,
            invocation_uuid=invocation_uuid
        )

        # the error callback is runtime correct, as we only throw one type of exception
        # noinspection PyTypeChecker
        self.pool.apply_async(wrapper_start, kwds=wrapper_kwargs, callback=wrapper_done, error_callback=wrapper_error)
        return inv

    @classmethod
    def invocation_history(cls) -> List[Invocation]:
        logger.info("Loading invocation history.")

        invocations = []
        for file_path in Path(".opera-api").glob('*.json'):
            logger.debug(file_path)
            invocation = Invocation.from_dict(json.load(open(file_path, 'r')))
            invocations.append(invocation)

        if invocations:
            invocations.sort(
                key=lambda x: datetime.datetime.strptime(
                    x.timestamp,
                    '%Y-%m-%dT%H:%M:%S.%f+00:00'
                ),
                reverse=True
            )

        return invocations

    @classmethod
    def latest_invocation(cls) -> Optional[Invocation]:
        all_invocations = cls.invocation_history()
        try:
            return next(all_invocations)
        except StopIteration:
            return None

    @classmethod
    def load_invocation(cls, eye_dee: str) -> Optional[Invocation]:
        all_invocations = cls.invocation_history()
        try:
            return next(inv for inv in all_invocations if inv.id == eye_dee)
        except StopIteration:
            return None

    @classmethod
    def write_invocation(cls, inv: Invocation):
        storage = Storage.create(".opera-api")
        filename = "invocation-{}.json".format(inv.id)
        dump = json.dumps(inv.to_dict())
        storage.write(dump, filename)
