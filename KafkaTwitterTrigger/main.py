import logging,json
from azure_functions.kafka import KafkaEvent
from textblob import TextBlob

def main(kevent : KafkaEvent):
    # KafkaEvent rich type
    logging.info(kevent.get_body().decode('utf-8'))
    logging.info(kevent.key)
    logging.info(kevent.offset)
    logging.info(kevent.partition)
    logging.info(kevent.topic)
    logging.info(kevent.timestamp)

    # Sentiment Analysis
    msg = json.loads(kevent.get_body().decode('utf-8'))
    logging.info(msg["Value"])
    testimonial = TextBlob(msg["Value"])
    logging.info(testimonial.sentiment)
    if testimonial.sentiment.polarity < 0:
        logging.info("Negative")
    else:
        logging.info("Positive")

