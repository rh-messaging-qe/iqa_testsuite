import pytest
import os
import tempfile
import atexit
from messaging_abstract.component import Receiver, Sender
from jinja2 import Template
from instance import IQAInstance


# Default timeout settings
CLIENTS_TIMEOUT = 60
cleanup_file_list = []


def pytest_addoption(parser):

    # Inventory selection
    parser.addoption("--inventory", action="store", required=True, help="Inventory file to use")


def cleanup_files():
    for f in cleanup_file_list:
        os.unlink(f)


def pytest_configure(config):

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


@pytest.fixture()
def router(iqa):
    return iqa.get_routers()[0]


@pytest.fixture()
def java_receiver(iqa):
    return iqa.get_clients(Receiver, 'java')[0]


@pytest.fixture()
def java_sender(iqa):
    return iqa.get_clients(Sender, 'java')[0]


@pytest.fixture()
def python_receiver(iqa):
    return iqa.get_clients(Receiver, 'python')[0]


@pytest.fixture()
def python_sender(iqa):
    return iqa.get_clients(Sender, 'python')[0]


@pytest.fixture()
def nodejs_receiver(iqa):
    return iqa.get_clients(Receiver, 'nodejs')[0]


@pytest.fixture()
def nodejs_sender(iqa):
    return iqa.get_clients(Sender, 'nodejs')[0]
