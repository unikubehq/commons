import functools
import logging
from typing import List

from hurricane.amqp.basehandler import TopicHandler

logger = logging.getLogger("mytesthandler")


class MyTestHandler(TopicHandler):
    def on_message(self, _unused_channel, basic_deliver, properties, body):
        print("message!")
        logger.info(f"Message from {properties.app_id}: {body.decode('utf-8')}")
        self.acknowledge_message(basic_deliver.delivery_tag)

    def get_routing_keys(self, queue_name: str) -> List[str]:
        return [queue_name.rsplit(".", 1)[0]]
