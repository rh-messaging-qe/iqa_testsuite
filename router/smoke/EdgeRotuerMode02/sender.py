"""
Custom sender implementation that can be used with the Edge Router topology.
"""

import threading
import uuid
import logging
import math

from iqa_common.utils.timeout import TimeoutCallback
from proton import Message
from proton._handlers import MessagingHandler
from proton._reactor import Container, AtLeastOnce


class Sender(MessagingHandler, threading.Thread):
    """
    Simple sender class to be used with Edge Router testing
    """
    def __init__(self, url, message_count, sender_id, message_size=1024, timeout=0,
                 user_id=None, proton_option=AtLeastOnce()):
        super(Sender, self).__init__()
        threading.Thread.__init__(self)
        self.url = url
        self.total = message_count
        self.sender_id = sender_id
        self.sender = None
        self.connection = None
        self.sent = 0
        self.confirmed = 0
        self.released = 0
        self.rejected = 0
        self.settled = 0
        self.container = None
        self.message_size = message_size or 1024

        # If not a valid message size given, enforce default value of 1024
        try:
            int(self.message_size)
        except ValueError:
            self.message_size = 1024

        self.timeout = timeout
        self.timeout_handler = None

        self.user_id = user_id.encode('utf-8') if user_id else ('sender.%s' % sender_id).encode('utf-8')
        self.proton_option = proton_option
        self.tracker = []

        # Internal variable to control whether or not sender was stopped
        self._stopped = False

    def run(self):
        """
        Starts the thread and the Proton Container
        :return:
        """
        # If a timeout has been given, use it
        if self.timeout > 0:
            self.timeout_handler = TimeoutCallback(self.timeout, self.stop_sender)

        self.container = Container(self)
        self.container.run()

    def on_start(self, event):
        """
        Creates the sender client
        :param event:
        :return:
        """
        self.sender = event.container.create_sender(self.url, options=self.proton_option)
        self.connection = self.sender.connection

    def is_done_sending(self):
        """
        Returns True if all expected messages have been sent or if sender has timed out.
        :return:
        """
        return (self.total > 0 and (self.sent - self.released - self.rejected == self.total)) or \
               (self.timeout > 0 and self.timeout_handler.timed_out())

    def _generate_message_id_and_body(self) -> list:
        """
        Generates a message id and body using UUID and the
        pre-defined message size.
        :return: a list with msg_id and msg_body
        :rtype: list
        """
        # 32 is the length for uuid4 clean string
        multiplier = math.ceil(self.message_size / 32)
        msg_id = str(uuid.uuid4()).replace('-', '')
        msg_body = (msg_id * multiplier)[:self.message_size]
        return [msg_id, msg_body]

    def on_sendable(self, event):
        """
        Sends messages if sender has credits and not yet done sending
        expected amount of messages.
        :param event:
        :return:
        """
        if event.sender.credit > 0 and not self.is_done_sending():

            # Get both id and body
            (msg_id, msg_body) = self._generate_message_id_and_body()

            # Need a better message id (like uuid)
            msg = Message(id=msg_id, user_id=self.user_id, body=msg_body)

            self.tracker.append(event.sender.send(msg))
            self.sent += 1

    def on_accepted(self, event):
        """
        Increases the confirmed count (if delivery not yet in tracker list).
        :param event:
        :return:
        """
        if event.delivery not in self.tracker:
            logging.debug('Ignoring confirmation for other deliveries - %s' % event.delivery.tag)
        self.confirmed += 1
        self.verify_sender_done(event)

    def on_released(self, event):
        """
        Increases the released count
        :param event:
        :return:
        """
        self.released += 1
        logging.debug('Message released - %s' % event.delivery.tag)

    def on_rejected(self, event):
        """
        Increases the rejected count
        :param event:
        :return:
        """
        self.rejected += 1
        logging.debug('Message rejected - %s' % event.delivery.tag)

    def verify_sender_done(self, event):
        """
        Verify if sender is done/timed out and then close it.
        :param event:
        :return:
        """
        if self.is_done_sending():
            # If a timeout has been set, interrupt the callback handler
            if self.timeout_handler:
                self.timeout_handler.interrupt()
            self.stop_sender(event.sender, event.connection)

    def stop_sender(self, sender=None, connection=None):
        """
        Closes the sender and its connection.
        :param sender:
        :param connection:
        :return:
        """
        self._stopped = True
        sdr = sender or self.sender
        con = connection or self.connection
        sdr.close()
        con.close()

    @property
    def stopped(self):
        """
        Returns True if sender has stopped.
        :return:
        """
        return self._stopped
