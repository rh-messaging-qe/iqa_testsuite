import math
import hashlib
import logging
import ast
import time
import os
import random

import pytest
from messaging_abstract.message import Message
from messaging_components.brokers import Artemis
from pytest_iqa.instance import IQAInstance

from integration.int_3Ri_2BhaRi2_3Re_2BhaRe3.receiver import Receiver
from integration.int_3Ri_2BhaRi2_3Re_2BhaRe3.sender import Sender

class Outcome:
    accept = "accept"
    release = "release"
    modify = "modify"
    reject = "reject"

class Expected:
    accepted = "accepted"
    released = "released"
    modified = "modified"
    rejected = "rejected"

def idfn(outcome):
    return outcome["test_id"]

outcomes_config_list = [
    {
     "recv_outcomes": 4*[Outcome.accept],
     "expected": Expected.accepted,
     "test_id": "Expect accepted if all accept.",
    },
    {
     ## expect REJECTED if any reject:
     "recv_outcomes": [Outcome.reject, Outcome.modify, Outcome.release],
     "expected": Expected.rejected,
     "test_id": "Expect rejected if any reject.",
    },
    {
     "recv_outcomes": [Outcome.reject, Outcome.release],
     "expected": Expected.rejected,
     "test_id": "Expect rejected if any reject.",
    },
    #two issues here:
    #1) proton sender counts modified as released
    #2) the "Expect accept if no rejects" (taken from system tests) fails but according to documentation...
    #probably it should fail, from documentation:
    #accepted means:
    # - All consumers received the message,
    # - Or, at least one consumer received the message, but no consumers rejected it.
    #in this case no consumer is accepting ...
    #{
     #"recv_outcomes": [Outcome.modify, Outcome.release],
     #"expected": Expected.accepted,
     #"test_id": "Expect accept if no rejects=====",
    #},
    #{
     #"recv_outcomes": 3*[Outcome.release] + [Outcome.modify],
     #"expected": Expected.modified,
     #"test_id": "Expect modified over released=====",
    #},
    #{
     #"recv_outcomes": 2*[Outcome.modify],
     #"expected": Expected.modified,
     #"test_id": "Expected modify if all modify",
    #},
    {
     "recv_outcomes": 6*[Outcome.release],
     "expected": Expected.released,
     "test_id": "Release only if all released",
    },
]

@pytest.fixture(params=outcomes_config_list, ids=idfn)
def outcomes(request):
    return request.param

class _Receiver(Receiver):
    def __init__(self, *args, settle=Outcome.accept, **kwargs):
        super(_Receiver, self).__init__(*args, auto_accept=False, **kwargs)
        self._settle = getattr(self, settle)

    def modify(self, delivery):
        super(_Receiver, self).release(delivery, delivered=True)

    def release(self, delivery):
        super(_Receiver, self).release(delivery, delivered=False)

    def on_message(self, event):
        self.last_received_id[event.message.user_id] = event.message.id
        self.received += 1
        self.messages.append(event.message.body)

        logging.info("settle = %s" % self._settle.__name__)
        self._settle(event.delivery)

        if self.is_done_receiving():
            self.stop_receiver(event.receiver, event.connection)

class _Sender(Sender):
    def is_done_sending(self):
        return (self.stopped or (self.total > 0 and self.sent == self.total))

class TestMulticast:
    MESSAGES_COUNT = 5
    MESSAGE_SIZE = 128

    TIMEOUT = 4 #why?
    address = "multicast/bla"

    @staticmethod
    def _get_router_url(router, topic):
        return "amqp://%s:%s/%s" % (router.node.get_ip(), router.port, topic)

    def _sender(self, router, topic):
        s = _Sender(url=self._get_router_url(router, topic),
                   message_count=self.MESSAGES_COUNT,
                   sender_id='sender-%s' % router.node.hostname,
                   timeout=self.TIMEOUT,
                   message_size=self.MESSAGE_SIZE,
                   use_unique_body=True,
                   auto_settle=False,
                  )

        s.start()
        return s

    def _receiver(self, router, topic, settle=Outcome.modify):
        r = _Receiver(url=self._get_router_url(router, topic),
                      message_count=self.MESSAGES_COUNT,
                      settle=settle,
                      timeout=self.TIMEOUT,
                      )
        r.start()
        return r

    def launch_receivers(self, outcomes, iqa):
        def _wait(receivers):
            for r in receivers:
                while not r.receiver:
                    time.sleep(1)

        all_routers = iqa.get_routers()
        routers = random.sample(all_routers, len(outcomes))
        receivers = []
        for idx, router in enumerate(routers):
            receivers.append(self._receiver(router, self.address,
                                            settle=outcomes[idx]))
        _wait(receivers)
        return receivers

    def test_base_multicast(self, iqa: IQAInstance, router, outcomes):

        def _wait_for_all_process_to_terminate(threads):
            for t in threads:
                t.join()

        def _assert_all_receivers_messages(receivers, expected):
            for r in receivers:
                assert r.messages == expected

        def _assert_sender_expected_settlement(sender, expected):
            assert sender.settled == self.MESSAGES_COUNT
            for e in [Expected.accepted, Expected.released,
                      Expected.rejected, Expected.modified]:

                outcome_count = getattr(sender, e)
                if e == expected:
                    assert outcome_count == self.MESSAGES_COUNT
                else:
                    assert outcome_count == 0

        router_send = router

        receivers = self.launch_receivers(outcomes["recv_outcomes"], iqa)
        sender = self._sender(router_send, self.address)

        _wait_for_all_process_to_terminate(receivers + [sender])

        logging.info("sender_id: {}".format(sender.sender_id))
        assert sender.sent == self.MESSAGES_COUNT

        logging.info("""sent: accepted: {}
                        rejected: {}
                        released: {}
                        modified: {}
                        settled {}
                     """.format(
                      sender.accepted,
                      sender.rejected,
                      sender.released,
                      sender.modified,
                      sender.settled))

        _assert_all_receivers_messages(receivers,
                                       expected = [sender.message_body] * self.MESSAGES_COUNT)
        _assert_sender_expected_settlement(sender, outcomes["expected"])