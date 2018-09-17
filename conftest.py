import pytest
from messaging_abstract.component import Receiver, Sender

from instance import IQAInstance


# Default timeout settings
CLIENTS_TIMEOUT = 60


def pytest_addoption(parser):

    # Inventory selection
    parser.addoption("--inventory", action="store", required=True, help="Inventory file to use")


def pytest_configure(config):

    # Loading the inventory
    iqa = IQAInstance(config.getvalue('inventory'))

    # Adjusting clients timeout
    for client in iqa.clients:
        client.command.control.timeout = CLIENTS_TIMEOUT

    config.iqa = iqa


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
