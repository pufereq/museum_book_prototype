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
    lg.basicConfig(
        level=lg.DEBUG,
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
        format=(
            "%(asctime)s : %(levelname)-8s : %(threadName)s : %(filename)s:"
            "%(lineno)d : %(name)s :: %(message)s"
        ),
    )
    # TODO: add rotating file handler

    lg.info("hello!")

    # init App
    app = App()

    # init SwitchStates
    switch_states = SwitchStates(app.handle_input)

    # init DataParser
    data_parser = DataParser(state_update_callback=switch_states.update_states)

    # init SerialReceiver
    serial_receiver = SerialReceiver(parse_callback=data_parser.input_line)
    receiver_thread = threading.Thread(
        name="SerialReceiver", target=serial_receiver.run, daemon=True
    )
    receiver_thread.start()

    app.run()


if __name__ == "__main__":
    main()
