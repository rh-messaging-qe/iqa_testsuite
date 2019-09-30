import math
import hashlib
import logging
import ast
import time
import os

import pytest
from messaging_abstract.message import Message
from messaging_components.brokers import Artemis
from pytest_iqa.instance import IQAInstance

from integration.int_3Ri_2BhaRi2_3Re_2BhaRe3.receiver import Receiver
from integration.int_3Ri_2BhaRi2_3Re_2BhaRe3.sender import Sender

class Outcome: pass
Outcome.accept = "accept"
Outcome.release = "release"
Outcome.modify = "modify"
Outcome.reject = "reject"

class _Receiver(Receiver):
    def __init__(self, *args, settle=Outcome.accept, **kwargs):
        super(_Receiver, self).__init__(*args, **kwargs)
        self.auto_accept = kwargs["auto_accept"]
        if not self.auto_accept:
            self._settle = getattr(self, settle)

    def modify(self, delivery):
        super(_Receiver, self).release(delivery, delivered=True)

    def release(self, delivery):
        super(_Receiver, self).release(delivery, delivered=False)

    def on_message(self, event):
        """
        Processes an incoming message
        :param event:
        :return:
        """

        # Ignore received message from user id
        if self.ignore_dups and event.message.user_id and event.message.id and \
                event.message.user_id in self.last_received_id and \
                self.last_received_id[event.message.user_id] == event.message.id:
            logging.warning('Ignoring duplicated message [id: %s]' % event.message.id)
            return

        logging.debug("%s - received message" % self.container_id)
        self.last_received_id[event.message.user_id] = event.message.id
        self.received += 1

        # Saving received message for further validation
        if self.save_messages:
            self.messages.append(event.message.body)

        if not self.auto_accept:
            logging.error("===== _settle ==== {} ".format(self._settle.__name__))
            self._settle(event.delivery)

        # Validate if receiver is done receiving
        if self.is_done_receiving():
            self.stop_receiver(event.receiver, event.connection)

class TestMulticast:
    MESSAGES = 5
    MESSAGE_SIZE = 128
    MESSAGE_BODY = (("ABCDEFGHIJKLMNOPQRSTUVWXYZ" * math.ceil(MESSAGE_SIZE / 10))[:MESSAGE_SIZE])
    MESSAGE_SHA1SUM = hashlib.sha1(MESSAGE_BODY.encode('utf-8')).hexdigest()

    TIMEOUT = 6
    address = "multicast/bla"

    @staticmethod
    def _get_router_url(router, topic):
        """
        Returns an "amqp" url to connect with the given router / topic
        :param router:
        :param topic:
        :rtype: str
        :return:
        """
        return "amqp://%s:%s/%s" % (router.node.get_ip(), router.port, topic)

    def _sender(self, router, topic, auto_settle=True):
        s = Sender(url=self._get_router_url(router, topic),
                   message_count=self.MESSAGES,
                   sender_id='sender-%s' % router.node.hostname,
                   timeout=self.TIMEOUT,
                   message_size=self.MESSAGE_SIZE,
                   use_unique_body=True)

        s.start()
        return s

    def _receiver(self, router, topic, auto_accept=True, settle=Outcome.modify):
        r = _Receiver(url=self._get_router_url(router, topic),
                              message_count=self.MESSAGES,
                              settle=settle,
                              timeout=self.TIMEOUT,
                              save_messages=True,
                              auto_accept=auto_accept)

        # Starting subscriber
        r.start()
        return r

    def test_base_multicast_rejected(self, iqa: IQAInstance):
        l = [
            [Outcome.accept, Outcome.reject],
            [Outcome.reject, Outcome.reject],
        ]
        for outcomes in l:
            sender = self._test_base_multicast(iqa, outcomes[0], outcomes[1])
            assert sender.rejected == self.MESSAGES

    def test_base_multicast_accepted(self, iqa: IQAInstance):
        sender = self._test_base_multicast(iqa, Outcome.accept, Outcome.accept)
        assert sender.confirmed == self.MESSAGES

    def _test_base_multicast(self, iqa: IQAInstance, outcome_r1, outcome_r2):

        def _wait(*args):
            for r in args:
                while not r.receiver:
                    time.sleep(1)

        def _join(*args):
            for p in args:
                p.join()

        routers = iqa.get_routers()
        router_send = iqa.get_routers('Router.E1')[0]
        router_recv_1 = iqa.get_routers('Router.E2')[0]
        router_recv_2 = iqa.get_routers('Router.E3')[0]

        r1 = self._receiver(router_recv_1, self.address, auto_accept=False, settle=outcome_r1)
        r2 = self._receiver(router_recv_2, self.address, auto_accept=False, settle=outcome_r2)

        _wait(r1, r2)

        #auto_settle not working?
        s = self._sender(router_send, self.address, auto_settle=True)

        #assert r.received == expected_count
        #assert r.messages == losmensajes
        #assert s.sent == expected_count

        _join(r1, r2, s)

        logging.error("====== sent_id: {}, sent_sent: {}".format(s.sender_id, s.sent))
        logging.info("""====== sent: accepted: {}, rejected: {} released: {}""".format(
                      s.confirmed,
                      s.rejected,
                      s.released))

        for r in [r1, r2]:
            logging.error("====== messages: {}".format(r.messages))

        assert r1.messages == r2.messages
        assert len(r1.messages) == self.MESSAGES

        return s

