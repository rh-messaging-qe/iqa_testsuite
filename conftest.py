import pytest
import os
import tempfile
import atexit
from messaging_abstract.component import Receiver, Sender
from jinja2 import Template
from instance import IQAInstance


"""
Defines mandatory options and configuration that can be applied to all test suites.
"""


# Default timeout settings
CLIENTS_TIMEOUT = 60
cleanup_file_list = []


def pytest_addoption(parser):
    """
    Mandatory options only for all distinct test suites.
    :param parser:
    :return:
    """

    # Inventory selection
    parser.addoption("--inventory", action="store", required=True, help="Inventory file to use")


def cleanup_files():
    """
    Remove temporary files.
    :return:
    """
    for f in cleanup_file_list:
        os.unlink(f)


def pytest_configure(config):
    """
    Parses the inventory file, treating it as a Jinja2 template, exposing
    two dictionaries that can be used internally:
    - 'environ': containing all environment variables
    - 'option': holds all options passed when executing pytest

    Once inventory is parsed, an instance of IQAInstance is created.
    :param config:
    :return:
    """

    # Reading inventory as a Jinja2 template
    inventory = open(config.getvalue('inventory'), 'r').read()
    template = Template(source=inventory)

    # Passing "environ" and "option" as dictionaries to the template
    parsed_inventory = template.render(environ=os.environ, option=config.option)
    temp_inventory = tempfile.NamedTemporaryFile(mode="w", prefix="inventory", delete=False)
    temp_inventory.write(parsed_inventory)
    temp_inventory.close()
    cleanup_file_list.append(temp_inventory.name)

    # Loading the inventory
    iqa = IQAInstance(temp_inventory.name)

    # Adjusting clients timeout
    for client in iqa.clients:
        client.command.control.timeout = CLIENTS_TIMEOUT

    config.iqa = iqa

    # Clean up temporary files at exit
    atexit.register(cleanup_files)

@pytest.fixture()
def iqa(request):
    return request.config.iqa


def first_or_none(components: list):
    """
    Returns first component provided or None
    :param components:
    :return:
    """
    if components:
        return components[0]
    return None


@pytest.fixture()
def router(iqa):
    """
    Returns the first Router instance or None
    :param iqa:
    :return:
    """
    assert iqa
    return first_or_none(iqa.get_routers())


@pytest.fixture()
def java_receiver(iqa):
    """
    Returns the first Java Receiver instance or None
    :param iqa:
    :return:
    """
    assert iqa
    return first_or_none(iqa.get_clients(Receiver, 'java'))


@pytest.fixture()
def java_sender(iqa):
    """
    Returns the first Java Sender instance or None
    :param iqa:
    :return:
    """
    assert iqa
    return first_or_none(iqa.get_clients(Sender, 'java'))


@pytest.fixture()
def python_receiver(iqa):
    """
    Returns the first Python Receiver instance or None
    :param iqa:
    :return:
    """
    assert iqa
    return first_or_none(iqa.get_clients(Receiver, 'python'))


@pytest.fixture()
def python_sender(iqa):
    """
    Returns the first Python Sender instance or None
    :param iqa:
    :return:
    """
    assert iqa
    return first_or_none(iqa.get_clients(Sender, 'python'))


@pytest.fixture()
def nodejs_receiver(iqa):
    """
    Returns the first NodeJS Receiver instance or None
    :param iqa:
    :return:
    """
    assert iqa
    return first_or_none(iqa.get_clients(Receiver, 'nodejs'))


@pytest.fixture()
def nodejs_sender(iqa):
    """
    Returns the first NodeJS Sender instance or None
    :param iqa:
    :return:
    """
    assert iqa
    return first_or_none(iqa.get_clients(Sender, 'nodejs'))
