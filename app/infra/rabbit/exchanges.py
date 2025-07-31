from faststream.rabbit import RabbitExchange, ExchangeType

dlx_exchange = RabbitExchange(name="dlx", type=ExchangeType.DIRECT, durable=True)
