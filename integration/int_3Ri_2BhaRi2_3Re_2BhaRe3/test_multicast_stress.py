import time, logging
from itertools import cycle

from integration.int_3Ri_2BhaRi2_3Re_2BhaRe3.receiver import Receiver
from integration.int_3Ri_2BhaRi2_3Re_2BhaRe3.sender import Sender

# for now it looks like the normal receiver is a hang receiver
# it closes the connection on received expected message count (before settlement
# and outome update)
class HangReceiver(Receiver): pass

class _Sender(Sender):
    def is_done_sending(self):
        return self.stopped or (self.total > 0 and (self.accepted >= self.total))

class TestMulticastStress:
    SEND_MESSAGES_COUNT = 5010

    RECV_TIMEOUT_S = 150
    SEND_TIMEOUT_S = 150 # timeout are just to make sure test completes, should not
                         # happend if it is not intentional.

    MESSAGE_SIZE = 128

    address = "multicast/bla"

    @staticmethod
    def _get_router_url(router, address):
        return "amqp://%s:%s/%s" % (router.node.get_ip(), router.port, address)

    def _receiver(self, router, topic, save_messages, durable, r_class,
                  message_count):
        r = r_class(url=self._get_router_url(router, topic),
                    message_count=message_count,
                    timeout=self.RECV_TIMEOUT_S,
                    save_messages=save_messages,
                    durable=durable,
                    container_id = router.name
                    )
        r.start()
        return r

    def launch_receivers(self, recv_count_list, iqa, r_class=Receiver):
        #remember I3 router has an intentional eth 100ms delay
        all_routers = iqa.get_routers()
        cycle_routers = cycle(all_routers)

        def _wait(receivers):
            for r in receivers:
                while not r.receiver:
                    time.sleep(1)

        receivers = []
        for  recv_count in recv_count_list:
            receivers.append(self._receiver(router=next(cycle_routers),
                                            topic=self.address,
                                            save_messages=True,
                                            durable=False,
                                            r_class=r_class,
                                            message_count=recv_count,
                                           )
                            )

        _wait(receivers)
        return receivers

    def _sender(self, router, topic):
        s = _Sender(url=self._get_router_url(router, topic),
                   message_count=self.SEND_MESSAGES_COUNT,
                   sender_id='sender-%s' % router.node.hostname,
                   timeout=self.SEND_TIMEOUT_S,
                   message_size=self.MESSAGE_SIZE,
                   use_unique_body=True,
                   auto_settle=True,
                  )
        s.start()
        return s

    def test_multiple_working_receivers(self, iqa, router_e1):
        def evaluate_sender(s):
            logging.info("""
                            total: {}
                            sent: {}
                            accepted: {}
                            rejected: {}
                            released: {}
                            modified: {}
                            settled: {}
                            timed_out: {}
                         """.format(
                          s.total,
                          s.sent,
                          s.accepted,
                          s.rejected,
                          s.released,
                          s.modified,
                          s.settled,
                          s.timed_out,
                         ))

            #TODO check what to assert
            assert s.accepted >= s.total
            assert s.timed_out == False
            assert s.rejected == 0

        def _log_info_receiver(r):
            logging.info("""name = %s""" % r.receiver.name)
            logging.info("""
                         received: {}
                         timeout: {}
                        """.format(
                            r.received,
                            r.timed_out,
                            )
                        )

        def evaluate_receiver(r):
            _log_info_receiver(r)

            assert r.timed_out == False, "%s timed out" % r.container_id
            assert r.received == r.total

        def evaluate_timeout_receiver(r):
            #accepted messages are at minimum self.SEND_MESSAGES_COUNT
            _log_info_receiver(r)
            assert r.received >= self.SEND_MESSAGES_COUNT

        def evaluate_result(no_timeout_receivers, timeout_receivers, sender):
            for r in no_timeout_receivers:
                evaluate_receiver(r)

            for r in timeout_receivers:
                evaluate_timeout_receiver(r)

            evaluate_sender(sender)

        def _wait_for_all_process_to_terminate(threads):
            for t in threads:
                t.join()

        router_send = router_e1

        #receivers dropping when receiving an arbitrary number of messages
        good_recv_count_list = 5*[int(0.9 * self.SEND_MESSAGES_COUNT)] + \
                               5 * [int(0.7 * self.SEND_MESSAGES_COUNT)] + \
                               10 * [int(0.3 * self.SEND_MESSAGES_COUNT)]
        broken_receivers_count_list = [1232, 123, 190]

        good_receivers = self.launch_receivers(good_recv_count_list, iqa)
        broken_receivers = self.launch_receivers(broken_receivers_count_list, iqa, HangReceiver)
        timeout_receivers = self.launch_receivers([self.SEND_MESSAGES_COUNT * 2], iqa)

        no_timeout_receivers = good_receivers + broken_receivers

        sender = self._sender(router_send, self.address)

        _wait_for_all_process_to_terminate(no_timeout_receivers + timeout_receivers + [sender])

        evaluate_result(no_timeout_receivers, timeout_receivers, sender)




