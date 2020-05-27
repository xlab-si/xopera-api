import os
import json
import sys
import uuid
from datetime import datetime, timezone
from io import StringIO
from opera.api.openapi.models import \
        ValidationResult
from pathlib import Path


DEFAULT_TEMPLATE_LOCATION_PATH = ''

class CommandArgs(object):
    def __init__(self, command_inputs=None, output_format=None):
        self.format = output_format
        self.uid = str(uuid.uuid4())
        self.timestamp = datetime.now(tz=timezone.utc).isoformat()
        self.inputs = ''
        if not command_inputs:
            return
        if not command_inputs.service_template:
            raise ValueError('No service template is specified.')
        else:
            self.csar = Csar(command_inputs.service_template)

        if command_inputs.inputs:
            self.inputs = str(command_inputs.inputs)


class Csar(object):
    def __init__(self, name):
        self.name = name


class CaptureString(object):
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self

    def __exit__(self, *args):
        self.value = self._stringio.getvalue()
        del self._stringio    # free up some memory
        sys.stdout = self._stdout

    def get_value(self):
        return self._stringio.getvalue()


def change_current_dir():
    if DEFAULT_TEMPLATE_LOCATION_PATH != '':
        os.chdir(DEFAULT_TEMPLATE_LOCATION_PATH)


def get_validation_result(output):
    output_list = output.value.splitlines()
    if output_list[1] != 'Done.':
        return ValidationResult(False, output_list[1])
    else:
        return ValidationResult(True)


def get_instance_state():
    json_dict = {}
    change_current_dir()
    for file_path in Path(os.path.join('.opera', 'instances')).glob("*"):
        parsed = json.load(open(file_path, 'r'))
        component_name = parsed['tosca_name']['data']
        json_dict[component_name] = parsed['state']['data']
    return json_dict
