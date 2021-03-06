#! /usr/bin/env python
"""
A program that downloads one particular activity from a given Garmin
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
    parser.add_argument(
        "activity", metavar="<activity>", type=int, help="Activity ID.")
    parser.add_argument(
        "format", metavar="<format>", type=str,
        help="Export format (one of: {}).".format(
            garminexport.backup.export_formats))

    # optional args
    parser.add_argument(
        "--password", type=str, help="Account password.")
    parser.add_argument(
        "--destination", metavar="DIR", type=str,
        help=("Destination directory for downloaded activity. Default: "
              "./activities/"), default=os.path.join(".", "activities"))
    parser.add_argument(
        "--log-level", metavar="LEVEL", type=str,
        help=("Desired log output level (DEBUG, INFO, WARNING, ERROR). "
              "Default: INFO."), default="INFO")

    args = parser.parse_args()
    if not args.log_level in LOG_LEVELS:
        raise ValueError("Illegal log-level argument: {}".format(
            args.log_level))
    if not args.format in garminexport.backup.export_formats:
        raise ValueError(
            "Uncrecognized export format: '{}'. Must be one of {}".format(
                args.format, garminexport.backup.export_formats))
    logging.root.setLevel(LOG_LEVELS[args.log_level])

    try:
        if not os.path.isdir(args.destination):
            os.makedirs(args.destination)

        if not args.password:
            args.password = getpass.getpass("Enter password: ")
        with GarminClient(args.username, args.password) as client:
            log.info("fetching activity {} ...".format(args.activity))
            summary = client.get_activity_summary(args.activity)
            starttime = dateutil.parser.parse(summary["activity"]["activitySummary"]["BeginTimestamp"]["value"])
            garminexport.backup.download(
                client, (args.activity, starttime), args.destination, export_formats=[args.format])
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        log.error(u"failed with exception: %s", e)
        raise
