import datetime
import json
import multiprocessing
import os
import traceback
import typing
import uuid
from pathlib import Path
from typing import List, Optional

from opera.commands.deploy import deploy_service_template as opera_deploy
from opera.commands.notify import notify as opera_notify
from opera.commands.undeploy import undeploy as opera_undeploy
from opera.storage import Storage

from opera.api.log import get_logger
from opera.api.openapi.models import Invocation, InvocationState, OperationType

logger = get_logger(__name__)


class InvocationWorkerProcess(multiprocessing.Process):
    IN_PROGRESS_STDOUT_FILE = "/tmp/xopera-api-inprogress-stdout.txt"
    IN_PROGRESS_STDERR_FILE = "/tmp/xopera-api-inprogress-stderr.txt"

    def __init__(self, work_queue: multiprocessing.Queue):
        super(InvocationWorkerProcess, self).__init__(
            group=None, target=self._run_internal, name="Invocation-Worker", args=(),
            kwargs={
                "work_queue": work_queue,
            }, daemon=None)

    @staticmethod
    def _run_internal(work_queue: multiprocessing.Queue):
        file_stdout = open(InvocationWorkerProcess.IN_PROGRESS_STDOUT_FILE, "w")
        file_stderr = open(InvocationWorkerProcess.IN_PROGRESS_STDERR_FILE, "w")

        os.dup2(file_stdout.fileno(), 1)
        os.dup2(file_stderr.fileno(), 2)

        while True:
            inv: Invocation = work_queue.get(block=True)

            inv.state = InvocationState.IN_PROGRESS
            InvocationService.write_invocation(inv)

            try:
                if inv.operation == OperationType.DEPLOY:
                    InvocationWorkerProcess._deploy(inv.service_template, inv.inputs, num_workers=1,
                                                    clean_state=inv.clean_state)
                elif inv.operation == OperationType.UNDEPLOY:
                    InvocationWorkerProcess._undeploy(num_workers=1)
                elif inv.operation == OperationType.NOTIFY:
                    # we abuse service_template and inputs a bit, but they match
                    InvocationWorkerProcess._notify(inv.service_template, inv.inputs)
                else:
                    raise RuntimeError("Unknown operation type:" + str(inv.operation))

                inv.state = InvocationState.SUCCESS
            except BaseException as e:
                if isinstance(e, RuntimeError):
                    raise e
                inv.state = InvocationState.FAILED
                inv.exception = "{}: {}\n\n{}".format(e.__class__.__name__, str(e), traceback.format_exc())

            file_stdout.flush()
            os.fsync(file_stdout.fileno())
            file_stderr.flush()
            os.fsync(file_stderr.fileno())
            instance_state = InvocationService.get_instance_state()
            stdout = InvocationWorkerProcess.read_file(InvocationWorkerProcess.IN_PROGRESS_STDOUT_FILE)
            stderr = InvocationWorkerProcess.read_file(InvocationWorkerProcess.IN_PROGRESS_STDERR_FILE)
            file_stdout.truncate()
            file_stderr.truncate()

            inv.instance_state = instance_state
            inv.stdout = stdout
            inv.stderr = stderr
            InvocationService.write_invocation(inv)

    @staticmethod
    def _deploy(service_template: str, inputs: typing.Optional[dict], num_workers: int, clean_state: bool):
        opera_storage = Storage.create()
        opera_deploy(service_template, inputs, opera_storage,
                     verbose_mode=True, num_workers=num_workers, delete_existing_state=clean_state)

    @staticmethod
    def _undeploy(num_workers: int):
        opera_storage = Storage.create()
        opera_undeploy(opera_storage, verbose_mode=True, num_workers=num_workers)

    @staticmethod
    def _notify(event_name: str, notification_contents: Optional[str]):
        opera_storage = Storage.create()
        opera_notify(opera_storage, verbose_mode=True,
                     trigger_name_or_event=event_name, notification_file_contents=notification_contents)

    @staticmethod
    def read_file(filename):
        with open(filename, "r") as f:
            return f.read()


class InvocationService:
    def __init__(self):
        self.work_queue: multiprocessing.Queue = multiprocessing.Queue()
        self.worker = InvocationWorkerProcess(self.work_queue)
        self.worker.start()

    def invoke(self, operation_type: OperationType, service_template: Optional[str], inputs: Optional[any],
               clean_state: Optional[bool]) -> Invocation:
        invocation_uuid = str(uuid.uuid4())
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        logger.info("Invoking %s with ID %s at %s", operation_type, invocation_uuid, now.isoformat())

        inv = Invocation()
        inv.id = invocation_uuid
        inv.state = InvocationState.PENDING
        inv.operation = operation_type
        inv.timestamp = now.isoformat()
        inv.service_template = service_template
        inv.inputs = inputs
        inv.clean_state = clean_state or False
        inv.instance_state = None
        inv.exception = None
        inv.stdout = None
        inv.stderr = None
        self.write_invocation(inv)

        self.work_queue.put(inv)
        return inv

    @classmethod
    def invocation_history(cls) -> List[Invocation]:
        logger.info("Loading invocation history.")

        invocations = []
        for file_path in Path(".opera-api").glob('*.json'):
            logger.debug(file_path)
            invocation = Invocation.from_dict(json.load(open(file_path, 'r')))

            if invocation.state == InvocationState.IN_PROGRESS:
                invocation.stdout = InvocationWorkerProcess.read_file(InvocationWorkerProcess.IN_PROGRESS_STDOUT_FILE)
                invocation.stderr = InvocationWorkerProcess.read_file(InvocationWorkerProcess.IN_PROGRESS_STDERR_FILE)

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

    @classmethod
    def get_instance_state(cls):
        json_dict = {}
        for file_path in Path(os.path.join('.opera', 'instances')).glob("*"):
            parsed = json.load(open(file_path, 'r'))
            component_name = parsed['tosca_name']['data']
            json_dict[component_name] = parsed['state']['data']
        return json_dict
