"""
A custom receiver implementation that can be used, as an alternative,
for testing Edge Router topology.
"""
import threading
import logging

from iqa_common.utils.timeout import TimeoutCallback
from proton.handlers import MessagingHandler
from proton.reactor import Container, DurableSubscription


class Receiver(MessagingHandler, threading.Thread):
    """
    Receiver implementation of a Proton client that run as a thread.
    """
    def __init__(self, url, message_count, timeout=0, container_id=None, durable=False):
        super(Receiver, self).__init__()
        threading.Thread.__init__(self)
        self.url = url
        self.receiver = None
        self.connection = None
        self.received = 0
        self.total = message_count
        self.timeout = timeout
        self.timeout_handler = None
        self.container_id = container_id
        self.container = None
        self.durable = durable
        self.last_received_id = {}
        self._stopped = False

    def run(self):
        """
        Starts the thread and the Proton container
        :return:
        """
        # If a timeout has been given, use it
        if self.timeout > 0:
            self.timeout_handler = TimeoutCallback(self.timeout, self.stop_receiver)

        self.container = Container(self)
        self.container.container_id = self.container_id
        self.container.run()

    def on_start(self, event):
        """
        Creates the receiver
        :param event:
        :return:
        """
        subs_opts = None
        if self.durable:
            subs_opts = DurableSubscription()
        self.receiver = event.container.create_receiver(self.url, name=self.container_id, options=subs_opts)
        self.connection = self.receiver.connection

    def on_message(self, event):
        """
        Processes an incoming message
        :param event:
        :return:
        """

        # Ignore received message from user id
        if event.message.user_id and event.message.id and \
                event.message.user_id in self.last_received_id and \
                self.last_received_id[event.message.user_id] == event.message.id:
            logging.debug('Ignoring duplicated message [id: %s]' % event.message.id)
            return

        self.last_received_id[event.message.user_id] = event.message.id
        self.received += 1

        # Validate if receiver is done receiving
        if self.is_done_receiving():
            self.stop_receiver(event.receiver, event.connection)

    def stop_receiver(self, receiver=None, connection=None):
        """
        Stops the receiver. If durable flag is set, then it simply detaches in
        order to preserve the subscription.
        :param receiver:
        :param connection:
        :return:
        """
        self._stopped = True
        rec = receiver or self.receiver
        con = connection or self.connection

        if self.durable:
            rec.detach()
            self.container.stop()
        else:
            rec.close()
            con.close()

    def is_done_receiving(self):
        """
        Validates if all messages have been received (when expecting a
        positive amount of messages)
        :return:
        """
        return self.total > 0 and (self.received == self.total)

    @property
    def stopped(self):
        """
        Returns a bool. True if receiver has stopped (completed or timed out)
        :return:
        """
        return self._stopped
