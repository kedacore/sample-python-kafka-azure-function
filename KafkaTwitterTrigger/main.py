from azure_functions.kafka import KafkaEvent
import logging

def main(kevent : KafkaEvent):
    logging.info(kevent.get_body().decode('utf-8'))
    logging.info(kevent.key)
    logging.info(kevent.offset)
    logging.info(kevent.partition)
    logging.info(kevent.topic)
    logging.info(kevent.timestamp)