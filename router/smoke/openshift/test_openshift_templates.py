from iqa_common.executor import Command, Execution
from messaging_abstract.component import Receiver, Sender
from messaging_abstract.message import Message
from messaging_components.clients import ReceiverJava, SenderJava, ReceiverPython, SenderPython, ReceiverNodeJS, \
    SenderNodeJS

# Initial static configuration
from messaging_components.routers import Dispatch
from messaging_components.routers.dispatch.management import RouterQuery
import time

from instance import IQAInstance
from pytest import mark


# TODO Java sender is working very slowly (need to discuss with clients team)
MESSAGE_COUNT = {'java': 10, 'python': 100, 'nodejs': 100}
MESH_SIZE = 3


def test_scale_up_router(router: Dispatch):
    """
    Executes "oc" command to scale up the number of PODs according to value defined in MESH_SIZE constant.
    It also uses 'amq-interconnect' as the deployment config name (standard in official templates).

    Test passes if command is executed without errors.
    Note: the oc command expects that current session is logged to Openshift cluster (you can do it manually,
          but it will be also done through the CI job).
    :param router:
    :return:
    """
    cmd_scale_up = Command(args=['oc', 'scale', '--replicas=%d' % MESH_SIZE, 'dc', 'amq-interconnect'], timeout=30,
                           stderr=True, stdout=True)
    execution: Execution = router.execute(cmd_scale_up)
    execution.wait()

    assert execution.completed_successfully()


def test_router_mesh_after_scale_up(router: Dispatch):
    """
    Queries Router for all Node Entities available in the topology.
    It expects the number of nodes matches number of PODs (mesh is correctly formed).
    :param router:
    :return:
    """
    assert router
    validate_mesh_size(router, MESH_SIZE)


def test_basic_messaging_with_java(java_receiver: ReceiverJava, java_sender: SenderJava, length):
    """
    Exchange messages through the router using a pair of Java Sender and Receiver.
    Expects that all messages are exchanged and external clients complete successfully.
    :param java_receiver:
    :param java_sender:
    :param length:
    :return:
    """
    exchange_messages(java_receiver, java_sender, length)
    validate_client_results(java_receiver, java_sender)


def test_basic_messaging_with_python(python_receiver: ReceiverPython, python_sender: SenderPython, length):
    """
    Exchange messages through the router using a pair of Python Sender and Receiver.
    Expects that all messages are exchanged and external clients complete successfully.
    :param python_receiver:
    :param python_sender:
    :param length:
    :return:
    """
    exchange_messages(python_receiver, python_sender, length)
    validate_client_results(python_receiver, python_sender)


def test_basic_messaging_with_nodejs(nodejs_receiver: ReceiverNodeJS, nodejs_sender: SenderNodeJS, length):
    """
    Exchange messages through the router using a pair of NodeJS Sender and Receiver.
    Expects that all messages are exchanged and external clients complete successfully.
    :param nodejs_receiver:
    :param nodejs_sender:
    :param length:
    :return:
    """
    exchange_messages(nodejs_receiver, nodejs_sender, length)
    validate_client_results(nodejs_receiver, nodejs_sender)


def test_basic_messaging_with_all_clients_concurrently(iqa: IQAInstance, length):
    """
    Exchange messages through the router using three pairs of:
    - Java Sender and Receiver
    - Python Sender and Receiver, and
    - NodeJS Sender and Receiver.
    Expects that all messages are exchanged and all external clients complete successfully.
    :param iqa:
    :param length:
    :return:
    """

    receivers = iqa.get_clients(client_type=Receiver)
    senders = iqa.get_clients(client_type=Sender)

    # Run all available clients in parallel
    for receiver in receivers:
        start_receiver(receiver)
    for sender in senders:
        start_sender(sender, length)

    # Validate all results
    for receiver, sender in zip(receivers, senders):
        validate_client_results(receiver, sender)


def test_scale_down_router(router: Dispatch):
    """
    Scale down the number of PODs to 1.
    Expects that the scale down command completes successfully.
    :param router:
    :return:
    """
    cmd_scale_up = Command(args=['oc', 'scale', '--replicas=1', 'dc', 'amq-interconnect'], timeout=30)
    execution: Execution = router.execute(cmd_scale_up)
    execution.wait()
    assert execution.completed_successfully()


def test_router_mesh_after_scale_down(router: Dispatch):
    """
    Queries the router to validate that the number of Nodes in the topology is 1.
    :param router:
    :return:
    """
    assert router
    validate_mesh_size(router, 1)


def validate_mesh_size(router, new_size):
    """
    Asserts that router topology size matches "new_size" value.
    :param router:
    :param new_size:
    :return:
    """
    time.sleep(60)
    query = RouterQuery(host=router.node.ip, port=router.port, router=router)
    node_list = query.node()
    assert node_list
    assert len(node_list) == new_size


def start_receiver(receiver):
    """
    Starts the provided receiver instance using pre-defined message count (per implementation)
    and sets it to log received messages as a dictionary (one message per line).
    :param receiver:
    :return:
    """
    assert receiver

    # Defining number of messages to exchange
    receiver.command.control.count = MESSAGE_COUNT.get(receiver.implementation)
    receiver.command.logging.log_msgs = 'dict'

    # Starting the Receiver
    receiver.receive()


def start_sender(sender, length):
    """
    Starts the sender instance, preparing a dummy message whose body size has
    the provided length.

    Currently message content is passed via command line.
    TODO: We must enhance our clients to generate a temporary file (on the executing node)
          and use the related file as input for message content.
    :param sender:
    :param length:
    :return:
    """
    assert sender

    sender.command.control.count = MESSAGE_COUNT.get(sender.implementation)

    # Starting the Sender
    message = Message(body="X" * length)
    sender.send(message)


def exchange_messages(receiver, sender, length):
    """
    Starts both receiver and sender (with message sizes set to appropriate length).
    :param receiver:
    :param sender:
    :param length:
    :return:
    """
    start_receiver(receiver)
    start_sender(sender, length)


def validate_client_results(receiver, sender):
    """
    Validate that both clients completed (or timed out) and if the
    number of messages received by receiver instance matches
    expected count.
    :param receiver:
    :param sender:
    :return:
    """
    #
    # Validating results
    #
    # Wait till both processes complete
    while receiver.execution.is_running() or sender.execution.is_running():
        pass

    # Validate that both processes completed with return code 0
    assert not receiver.execution.is_running()
    assert receiver.execution.returncode == 0, \
        '%s did not complete successfully' % receiver.implementation.upper()
    assert not sender.execution.is_running()
    assert sender.execution.returncode == 0

    # Each message received will be printed as one line (plus some extra lines from Ansible)
    assert len(receiver.execution.read_stdout(lines=True)) >= MESSAGE_COUNT.get(receiver.implementation)
