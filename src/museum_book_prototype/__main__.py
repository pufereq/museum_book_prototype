# -*- coding: utf-8 -*-
"""Museum Book Prototype package entry point."""

import logging as lg
import threading

from museum_book_prototype.serial_receiver import SerialReceiver


def main() -> None:
    """Main function to start the Museum Book Prototype application."""
    lg.basicConfig(
        level=lg.DEBUG,
        format=(
            "%(asctime)s : %(levelname)-8s : %(threadName)s : %(filename)s:"
            "%(lineno)d : %(name)s :: %(message)s"
        ),
    )
    # TODO: add rotating file handler

    lg.info("hello!")

    serial_receiver = SerialReceiver()
    receiver_thread = threading.Thread(
        name="SerialReceiver", target=serial_receiver.run, daemon=True
    )
    receiver_thread.start()

    lg.info("Serial receiver thread started.")
    receiver_thread.join()


if __name__ == "__main__":
    main()
