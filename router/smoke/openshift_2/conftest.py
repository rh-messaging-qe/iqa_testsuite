import pytest
import itertools
from typing import Union

from messaging_components.clients import \
    ReceiverJava, SenderJava, \
    ReceiverPython, SenderPython, \
    ReceiverNodeJS, SenderNodeJS
from messaging_components.routers.dispatch.dispatch import Dispatch

from messaging_abstract.component import Receiver, Sender

clients = [
    "java",
    "python",
    "nodejs",
]


def pytest_addoption(parser):
    """
    This particular suite requires that the router1 ip address is informed,
    as it is used internally in the related inventory files.

    :param parser:
    :return:
    """

    parser.addoption("--cluster", action="append", required=True,
                     help="Openshift clusters IP where routers is deployed")


def pytest_generate_tests(metafunc):
    """
    Iterate through tests with length parameter and make
    sure tests will be executed with 1024 increment.
    """

    clusters = list(metafunc.config.option.cluster)
    clusters_count = len(clusters)
    
    if 'cluster' in metafunc.fixturenames:
        metafunc.parametrize('cluster', clusters, indirect=True)

    clients_cluster = [client + '_' + str(cluster) for client, cluster
                       in itertools.product(clients, range(0, clusters_count))]

    routers = ['router' + '_' + str(cluster) for cluster in range(0, clusters_count)]
    senders = ['sender' + '_' + client for client in clients_cluster]
    receivers = ['receiver' + '_' + client for client in clients_cluster]

    if 'msg_length' in metafunc.fixturenames:
        metafunc.parametrize("msg_length", [2 ** x for x in range(8, 15)])

    if 'sender' in metafunc.fixturenames:
        metafunc.parametrize('sender', senders)

    if 'receiver' in metafunc.fixturenames:
        metafunc.parametrize('receiver', receivers)

    if 'router_cluster' in metafunc.fixturenames:
        metafunc.parametrize('router_cluster', routers)


@pytest.fixture()
def router_cluster(request, iqa) -> Dispatch:
    """
    Fixture the first Router instance
    :param iqa:
    :param request:
    :return:
    """
    for param in request.param:
        if "router_" in param:
            router_number = int(param.split('_')[1])
            return iqa.get_routers()[router_number]


@pytest.fixture()
def receiver(request, iqa) -> Union[ReceiverJava, ReceiverPython, ReceiverNodeJS]:
    """
    Fixture the first Receiver instance
    :param request:
    :param iqa:
    :return: Returns first Receiver instance on 1 cluster instance
    """
    for param in request.param:
        if "receiver_" in param:
            s: str = param.split('_')
            receiver_implementation = s[1]
            receiver_number = int(s[2])
            return iqa.get_clients(Receiver, receiver_implementation)[receiver_number]


@pytest.fixture()
def sender(request, iqa) -> Union[SenderJava, SenderPython, SenderNodeJS]:
    """
    Fixture the first Sender instance
    :param request:
    :param iqa:
    :return: Returns first Sender instance on 1 cluster instance
    """
    for param in request.param:
        if "sender_" in param:
            s = param.split('_')
            sender_implementation = s[1]
            sender_number = int(s[2])
            return iqa.get_clients(Sender, sender_implementation)[sender_number]
