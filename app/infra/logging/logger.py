import logging
import logging.config
import pathlib
import re
import yaml
from uvicorn.logging import DefaultFormatter


class LogFormatter(DefaultFormatter):
    CYAN = "\033[96m"
    RESET = "\033[0m"

    def formatMessage(self, record):
        if getattr(record, "queue", None):
            record.queue_fmt = f" [queue={getattr(record, 'queue')}]"
        else:
            record.queue_fmt = ""

        if getattr(record, "channel", None):
            record.channel_fmt = f" [channel={getattr(record, 'channel')}]"
        else:
            record.channel_fmt = ""

        msg = super().formatMessage(record)

        words = msg.split(" ")

        for index, word in enumerate(words):
            if "\033[" not in word:
                words[index] = re.sub(
                    r"\[([^\s\[\]]+)\]", rf"[{self.CYAN}\1{self.RESET}]", word
                )

        return " ".join(words)


class HideReceived(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage() != "Received" and record.getMessage() != "Processed"


def _get_config() -> dict:
    config_path = (pathlib.Path(__file__).parent / "config.yaml").resolve().as_posix()

    with open(config_path, "r") as config_file:
        config = yaml.safe_load(config_file)
        config["formatters"]["default"]["()"] = LogFormatter
        return config


def _create_logger(config: dict) -> logging.Logger:
    logging.config.dictConfig(config)
    return logging.getLogger("uvicorn")


config = _get_config()
logger = _create_logger(config)
logger.addFilter(HideReceived())
