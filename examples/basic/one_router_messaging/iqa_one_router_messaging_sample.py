"""
Simple example that demonstrates how to use IQA components and tools
to handle clients messaging through a router component.
"""
import sys

from messaging_abstract.component import Component, Sender
from messaging_abstract.component import Receiver
from messaging_abstract.component import Router
from messaging_abstract.message import Message
from messaging_components.clients import ClientExternal, ReceiverJava
from pytest_iqa.instance import IQAInstance

# Inventory file to use
TIMEOUT = 10
MESSAGE_COUNT = 1000
inventory = sys.argv[1] if len(sys.argv) > 1 else 'inventory_local.yml'

# Message explaining what this sample does
intro_message = """
This sample will first iterate through all components (router and clients)
defined through the inventory file %s and then it will start:
- One receiver instance of each client consuming messages from:
  /client/<implementation> (implementation being: java, python or nodejs)
  - Receivers will expect 1000 messages each
- One sender instance of each client sending messages to the same address
  pattern explained above (small message)
- Display results
""" % inventory
print(intro_message)

# Loading the instance
print("Loading IQAInstance using inventory file: %s" % inventory)
iqa = IQAInstance(inventory)

# Listing all routers in inventory
print("\n-> List of messaging components parsed from inventory")
for component in iqa.components:  # type: Component

    # List component name and type
    print("   * Name: %-20s | Type: %-10s | Implementation: %s" % (
        component.node.hostname,
        type(component),
        component.implementation
    ))

# Router instance to use on clients
router1: Router = iqa.get_routers()[0]

# Starting receivers
print("\n-> Starting receiver components")
for receiver in iqa.get_clients(Receiver):
    receiver.set_url('amqp://%s:%s/client/%s' % (router1.node.get_ip(), router1.port, receiver.implementation))
    receiver.command.timeout = TIMEOUT
    receiver.command.control.timeout = TIMEOUT
    receiver.command.control.count = MESSAGE_COUNT
    receiver.receive()


# Starting senders
print("-> Starting sender components")
msg = Message(body="1234567890")
for sender in iqa.get_clients(Sender):
    sender.set_url('amqp://%s:%s/client/%s' % (router1.node.get_ip(), router1.port, sender.implementation))
    sender.command.timeout = TIMEOUT
    sender.command.control.timeout = TIMEOUT
    sender.command.control.count = MESSAGE_COUNT
    sender.send(msg)

# Wait till all senders and receivers are done
print("\n** Waiting all senders and receivers to complete **")
client_errors = []
for client in iqa.get_clients(Sender) + iqa.get_clients(Receiver):  # type: ClientExternal
    # Wait till execution finishes/timeout
    while client.execution.is_running():
        pass

    # Validate return code
    if not client.execution.completed_successfully():
        client_errors.append(client)

# Verifying clients
if not client_errors:
    print("   => All clients completed successfully")
else:
    print("   => The following clients did not complete successfully:")
    for client in client_errors:
        client_type = 'receiver' if isinstance(client, Receiver) else 'sender'
        print('      - %s [%s]' % (client_type, client.implementation))
