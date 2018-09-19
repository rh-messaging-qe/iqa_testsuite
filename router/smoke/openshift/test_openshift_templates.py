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
    cmd_scale_up = Command(args=['oc', 'scale', '--replicas=%d' % MESH_SIZE, 'dc', 'amq-interconnect'], timeout=30,
                           stderr=True, stdout=True)
    execution: Execution = router.execute(cmd_scale_up)
    execution.wait()

    assert execution.completed_successfully()


def test_router_mesh_after_scale_up(router: Dispatch):
    assert router
    validate_mesh_size(router, MESH_SIZE)


def test_basic_messaging_with_java(java_receiver: ReceiverJava, java_sender: SenderJava, length):
    exchange_messages(java_receiver, java_sender, length)
    validate_client_results(java_receiver, java_sender)


def test_basic_messaging_with_python(python_receiver: ReceiverPython, python_sender: SenderPython, length):
    exchange_messages(python_receiver, python_sender, length)
    validate_client_results(python_receiver, python_sender)


def test_basic_messaging_with_nodejs(nodejs_receiver: ReceiverNodeJS, nodejs_sender: SenderNodeJS, length):
    exchange_messages(nodejs_receiver, nodejs_sender, length)
    validate_client_results(nodejs_receiver, nodejs_sender)


def test_basic_messaging_with_all_clients_concurrently(iqa: IQAInstance, length):

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
    cmd_scale_up = Command(args=['oc', 'scale', '--replicas=1', 'dc', 'amq-interconnect'], timeout=30)
    execution: Execution = router.execute(cmd_scale_up)
    execution.wait()
    assert execution.completed_successfully()


def test_router_mesh_after_scale_down(router: Dispatch):
    assert router
    validate_mesh_size(router, 1)


def validate_mesh_size(router, new_size):
    time.sleep(60)
    query = RouterQuery(host=router.node.ip, port=router.port, router=router)
    node_list = query.node()
    assert node_list
    assert len(node_list) == new_size


def start_receiver(receiver):
    assert receiver

    # Defining number of messages to exchange
    receiver.command.control.count = MESSAGE_COUNT.get(receiver.implementation)
    receiver.command.logging.log_msgs = 'dict'

    # Starting the Receiver
    receiver.receive()


def start_sender(sender, length):
    assert sender

    sender.command.control.count = MESSAGE_COUNT.get(sender.implementation)

    # Starting the Sender
    message = Message(body="X" * length)
    sender.send(message)


def exchange_messages(receiver, sender, length):
    start_receiver(receiver)
    start_sender(sender, length)


def validate_client_results(receiver, sender):
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
