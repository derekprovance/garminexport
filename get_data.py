#! /usr/bin/env python
"""A program that downloads one particular activity from a given Garmin
Connect account and stores it locally on the user's computer.
"""
import argparse
import getpass
from garminexport.garminclient import GarminClient
import garminexport.backup
import logging
import os
import sys
import traceback
import dateutil.parser

logging.basicConfig(
    level=logging.INFO, format="%(asctime)-15s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR
}
"""Command-line (string-based) log-level mapping to logging module levels."""

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=("Downloads one particular activity for a given "
                     "Garmin Connect account."))
    # positional args
    parser.add_argument(
        "username", metavar="<username>", type=str, help="Account user name.")

    # optional args
    parser.add_argument(
        "--password", type=str, help="Account password.")
    parser.add_argument(
        "--days", type=int, help="Days back from start to process.")
    parser.add_argument(
        "--start", type=str, help="How many days from the current date to start processing?")
    parser.add_argument(
        "--log-level", metavar="LEVEL", type=str,
        help=("Desired log output level (DEBUG, INFO, WARNING, ERROR). "
              "Default: INFO."), default="INFO")

    args = parser.parse_args()
    if not args.log_level in LOG_LEVELS:
        raise ValueError("Illegal log-level argument: {}".format(
            args.log_level))
    logging.root.setLevel(LOG_LEVELS[args.log_level])

    print( args.start )
