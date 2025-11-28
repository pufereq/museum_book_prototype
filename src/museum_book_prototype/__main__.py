# -*- coding: utf-8 -*-
"""Museum Book Prototype package entry point."""

import logging as lg
import threading

from logging.handlers import TimedRotatingFileHandler

from museum_book_prototype.serial_receiver import SerialReceiver
from museum_book_prototype.parse import DataParser
from museum_book_prototype.switch_states import SwitchStates
from museum_book_prototype.app import App


def main() -> None:
    """Main function to start the Museum Book Prototype application."""
    log_format: str = (
        "%(asctime)s : %(levelname)-8s : %(threadName)s : %(filename)s:"
        "%(lineno)d : %(name)s :: %(message)s"
    )
    lg.basicConfig(
        level=lg.INFO,
        handlers=[
            lg.StreamHandler(),
            TimedRotatingFileHandler(
                filename="logs/mbp.log",
                when="midnight",
                interval=1,
                backupCount=7,
                encoding="utf-8",
            ),
        ],
        format=log_format,
    )
    error_handler = TimedRotatingFileHandler(
        filename="logs/mbp_errors.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    error_handler.setLevel(lg.ERROR)
    error_handler.setFormatter(lg.Formatter(log_format))
    lg.getLogger().addHandler(error_handler)

    lg.info("hello!")

    # init App
    app: App = App()

    # init SwitchStates
    switch_states: SwitchStates = SwitchStates(app.handle_input)

    # init DataParser
    data_parser: DataParser = DataParser(
        state_update_callback=switch_states.update_states
    )

    # init SerialReceiver
    serial_receiver: SerialReceiver = SerialReceiver(
        parse_callback=data_parser.input_line
    )
    receiver_thread: threading.Thread = threading.Thread(
        name="SerialReceiver", target=serial_receiver.run, daemon=True
    )
    receiver_thread.start()

    app.run()


if __name__ == "__main__":
    main()
