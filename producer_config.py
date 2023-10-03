import logging

config = {
    'bootstrap.servers': 'YOUR_KAFKA_BROKER_ADDRESS',
    # Example configs
    'enable.idempotence': True,
    'acks': 'all',
    'retries': 100,
    'max.in.flight.requests.per.connection': 5,
    'compression.type': 'snappy',
    'linger.ms': 5,
    'batch.num.messages': 30
}


def delivery_report(err, msg):
    if err:
        logging.error("Failed to deliver message: {0}: {1}"
                      .format(msg.value(), err.str()))
    else:
        logging.info(f"msg produced. \n"
                     f"Topic: {msg.topic()} \n" +
                     f"Partition: {msg.partition()} \n" +
                     f"Offset: {msg.offset()} \n" +
                     f"Timestamp: {msg.timestamp()} \n")
