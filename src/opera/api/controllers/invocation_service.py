import os
import json
import threading
from datetime import datetime
from pathlib import Path
from opera.api.controllers import utils
from opera.api.openapi.models import \
        Invocation, \
        InvocationState
from opera.commands import \
    undeploy as undeploy_command, \
    deploy as deploy_command

# folder name to store invocation results
INVOCATION_STORAGE_FOLDER_NAME = '.opera-api'


class InvocationService(object):

    outputs = {}

    def background_function(self, func, args):
        invocation_thread = threading.Thread(target=func, args=[args])
        invocation_thread.start()

    def run_invocation(self, func, args, command_name):
        with utils.CaptureString() as output:
            try:
                self.outputs[args.uid] = output
                result = func(args)
                # if no exception save output as output
                # even if operation was not successful
                self.save_invocation(
                    args,
                    InvocationState.SUCCESS if result == 0
                    else InvocationState.FAILED,
                    command_name,
                    console_output=output.get_value(),
                    instance_state=utils.get_instance_state()
                )
            except Exception as e:
                self.save_invocation(
                    args, InvocationState.FAILED,
                    command_name,
                    console_output=output.get_value(),
                    error=str(e), instance_state=utils.get_instance_state()
                )
            finally:
                self.outputs.pop(args.uid)

    def run_deployment(self, args):
        self.run_invocation(deploy_command.deploy, args, 'deploy')

    def run_undeployment(self, args):
        self.run_invocation(undeploy_command.undeploy, args, 'undeploy')

    def prepare_deploy(self, deployment_input):
        # opera will save files to the current working directory
        utils.change_current_dir()
        command_args = utils.CommandArgs(deployment_input)
        invocation = self.save_invocation(
            command_args,
            InvocationState.IN_PROGRESS,
            'deploy',
            console_output=''
        )
        return command_args, invocation

    def prepare_undeploy(self):
        # opera gets saved files from current working directory
        utils.change_current_dir()
        args = utils.CommandArgs()
        invocation = self.save_invocation(
            args,
            InvocationState.IN_PROGRESS,
            'undeploy',
            console_output=''
        )
        return args, invocation

    def prepare_outputs(self):
        # opera gets saved files from current working directory
        utils.change_current_dir()
        args = utils.CommandArgs(output_format='json')
        return args

    def save_invocation(
            self, command_args, state,
            operation, console_output,
            instance_state=None, error=None):
        invocation = Invocation(
            command_args.uid, state, operation,
            command_args.timestamp, command_args.inputs,
            instance_state=instance_state,
            exception=error,
            console_output=console_output
        )
        utils.change_current_dir()
        Path(INVOCATION_STORAGE_FOLDER_NAME).mkdir(
            parents=True,
            exist_ok=True)
        filename = os.path.join(
            INVOCATION_STORAGE_FOLDER_NAME,
            '{0}_{1}.json'.format(operation, command_args.timestamp)
        )
        with open(filename, 'w') as outfile:
            json.dump(invocation.to_dict(), outfile)
        return invocation

    def load_invocation_history(self):
        invocations = []
        utils.change_current_dir()
        for file_path in Path(INVOCATION_STORAGE_FOLDER_NAME).glob('*.json'):
            invocation = Invocation.from_dict(json.load(open(file_path, 'r')))
            invocations.append(invocation)

        if invocations:
            invocations.sort(
                key=lambda x: datetime.strptime(
                    x.timestamp,
                    '%Y-%m-%dT%H:%M:%S.%f+00:00'
                ),
                reverse=True
            )

        for invocation in invocations:
            if invocation.state == InvocationState.IN_PROGRESS:
                invocation.instance_state = utils.get_instance_state()
                invocation.output = '' if invocation.id not in self.outputs \
                    else self.outputs[invocation.id].get_value()

        return invocations

    def load_invocation_status(self, uid):
        history = self.load_invocation_history()
        for invocation in history:
            if invocation.id == uid:
                return invocation
        return None
