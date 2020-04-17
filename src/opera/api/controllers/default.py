from opera.api.openapi.models import DeploymentStatus, ValidationResult, Invocation
# TODO: for both to work, delete .venv/lib/python3.7/site-packages/opera/__init__.py
#       implicit namespace packages (PEP420) need to be used in opera core for this to work
from opera.storage import Storage


def deploy(inputs=None):
    """
    :type inputs: dict
    :rtype: None
    """
    return 'wawawa!'


def outputs():
    """
    :rtype: dict
    """
    return 'wawawa!'


def status():
    """
    :rtype: DeploymentStatus
    """
    return 'wawawa!'


def undeploy():
    """
    :rtype: None
    """
    return 'wawawa!'


def validate():
    """
    :rtype: ValidationResult
    """
    return 'wawawa!'
