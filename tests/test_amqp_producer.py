import json
from time import sleep

from hurricane.testing import HurricanAMQPTest, HurricaneAMQPDriver

from commons.amqp.producer import TopicProducer


class AMQPProducerTests(HurricanAMQPTest):
    @HurricanAMQPTest.cylce_consumer(
        args=["tests.testapp.consumer.MyTestHandler", "--queue", "test", "--exchange", "test"], coverage=False
    )
    def test_send_message(self):
        body = {"body": "This is a test message"}
        host, port = self.driver.get_amqp_host_port()
        tp = TopicProducer(host, port, exchange="test", routing_key="test")
        tp.publish(body)

        std, err = self.driver.get_output(read_all=True)
        self.assertIn(json.dumps(body), std)

    @HurricanAMQPTest.cylce_consumer(
        args=["tests.testapp.consumer.MyTestHandler", "--queue", "test", "--exchange", "test"], coverage=False
    )
    def test_send_multiple_message(self):
        body_one = {"body": "This is message one"}
        body_two = {"body": "This is message two"}
        host, port = self.driver.get_amqp_host_port()
        tp = TopicProducer(host, port, exchange="test", routing_key="test", app_id="producer1")
        tp2 = TopicProducer(host, port, exchange="test", routing_key="test", app_id="producer2")
        tp.publish(body_one)
        tp2.publish(body_two)
        std, err = self.driver.get_output(read_all=True)
        self.assertIn(json.dumps(body_one), std)
        self.assertIn(json.dumps(body_one), std)

    def test_receive_multiple_message(self):
        body_one = {"body": "This is message one"}
        # start the broker
        self.driver.start_amqp()
        host, port = self.driver.get_amqp_host_port()
        test_topic_producer = TopicProducer(
            host, port, exchange="test_ex", routing_key="test.topic", app_id="producer1"
        )

        connection = ["--amqp-host", host, "--amqp-port", str(port)]
        consumer1 = HurricaneAMQPDriver()
        consumer1.start_consumer(
            params=[
                "tests.testapp.consumer.MyTestHandler",
                "--no-probe",
                "--queue",
                "test.*.consumer-1",
                "--exchange",
                "test_ex",
            ]
            + connection,
            coverage=False,
        )
        consumer2 = HurricaneAMQPDriver()
        consumer2.start_consumer(
            params=[
                "tests.testapp.consumer.MyTestHandler",
                "--no-probe",
                "--queue",
                "test.*.consumer-2",
                "--exchange",
                "test_ex",
            ]
            + connection,
            coverage=False,
        )
        test_topic_producer.publish(body_one)
        _exc = None
        try:
            std, _ = consumer1.get_output(read_all=True)
            self.assertIn(json.dumps(body_one), std)
            std, _ = consumer2.get_output(read_all=True)
            self.assertIn(json.dumps(body_one), std)
        except Exception as e:
            _exc = e
        finally:
            consumer1.stop_consumer()
            consumer2.stop_consumer()
            self.driver.stop_amqp()
            if _exc:
                raise _exc
