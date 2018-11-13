# Initial static configuration
from messaging_abstract.message import Message
from messaging_components.clients import \
    ReceiverJava, SenderJava, \
    ReceiverPython, SenderPython, \
    ReceiverNodeJS, SenderNodeJS

MESSAGE_COUNT = 10
MESH_SIZE = 3


def test_basic_messaging(
        receiver: [ReceiverJava, ReceiverPython, ReceiverNodeJS],
        sender: [SenderJava, SenderPython, SenderNodeJS],
        msg_length: [int]):
    """
    Exchange messages through the router using a pair of Java Sender and Receiver.
    Expects that all messages are exchanged and external clients complete successfully.
    :param receiver:
    :param sender:
    :param msg_length:
    :return:
    """
    exchange_messages(receiver, sender, msg_length)
    validate_client_results(receiver, sender)


def start_receiver(receiver: [ReceiverJava, ReceiverPython, ReceiverNodeJS]):
    """
    Starts the provided receiver instance using pre-defined message count (per implementation)
    and sets it to log received messages as a dictionary (one message per line).
    :param receiver:
    :return:
    """
    # Defining number of messages to exchange
    receiver.command.control.count = MESSAGE_COUNT
    receiver.command.logging.log_msgs = 'dict'

    # Starting the Receiver
    receiver.receive()


def start_sender(sender: [SenderJava, SenderPython, SenderNodeJS], length: int):
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
    sender.command.control.count = MESSAGE_COUNT

    # Starting the Sender
    message = Message(body="X" * length)
    sender.send(message)


def exchange_messages(receiver: [ReceiverJava, ReceiverPython, ReceiverNodeJS],
                      sender: [SenderJava, SenderPython, SenderNodeJS],
                      length):
    """
    Starts both receiver and sender (with message sizes set to appropriate length).
    :param receiver:
    :param sender:
    :param length:
    :return:
    """
    start_receiver(receiver)
    start_sender(sender, length)


def validate_client_results(receiver: [ReceiverJava, ReceiverPython, ReceiverNodeJS],
                            sender: [SenderJava, SenderPython, SenderNodeJS]):
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
    import time
    while receiver.execution.is_running() or sender.execution.is_running():
        time.sleep(0.1)

    # Validate that both processes completed with return code 0
    assert not receiver.execution.is_running()
    assert receiver.execution.returncode == 0, \
        '%s did not complete successfully' % receiver.implementation.upper()
    assert not sender.execution.is_running()
    assert sender.execution.returncode == 0

    # Each message received will be printed as one line (plus some extra lines from Ansible)
    assert len(receiver.execution.read_stdout(lines=True)) >= MESSAGE_COUNT
