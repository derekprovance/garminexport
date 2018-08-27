#! /usr/bin/env python
"""
A program that downloads one particular activity from a given Garmin
Connect account and stores it locally on the user's computer.
"""
import argparse
import getpass
from garminexport.garminclient import GarminClient
from garminexport.database import Database
import garminexport.backup
import logging
import os
import sys
import traceback
from dateutil import parser
from datetime import date, timedelta

logging.basicConfig(
    level=logging.INFO, format="%(asctime)-15s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR
}

def process_range(start_date, end_date):
    d1 = parser.parse(start_date)
    d2 = parser.parse(end_date)

    delta = d2 - d1
    for i in range(delta.days + 1):
        process(d1 + timedelta(i))

def process(request_date):
    logging.info("Pulling api data for {}".format(request_date))

    db = Database()
    with GarminClient(args.username) as client:
        db.insert_sleep_data(client.get_daily_sleep_data(request_date))
        db.insert_hr_data(client.get_daily_hr_data(request_date))
        db.insert_movement_data(client.get_daily_movement(request_date))
        db.insert_user_summary(client.get_user_summary(request_date))
        db.disconnect()

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(
        description=("Downloads Daily API Information from Garmin."))
    arg_parser.add_argument(
        "username", metavar="<username>", type=str, help="Account user name.")
    arg_parser.add_argument(
        "--end", type=str, help="Process multiple days.")
    arg_parser.add_argument(
        "--start", type=str, help="How many days from the current date to start processing? YYYY-MM-DD")
    arg_parser.add_argument(
        "--log-level", metavar="LEVEL", type=str,
        help=("Desired log output level (DEBUG, INFO, WARNING, ERROR). "
              "Default: INFO."), default="INFO")

    args = arg_parser.parse_args()

    if not args.log_level in LOG_LEVELS:
        raise ValueError("Illegal log-level argument: {}".format(
            args.log_level))

    logging.root.setLevel(LOG_LEVELS[args.log_level])

    try:
        if not args.start:
            request_date = (date.today() - timedelta(1)).strftime('%Y-%m-%d')
        else:
            request_date = args.start
            
        if args.end:
            process_range(args.start, args.end)
        else:
            process(request_date)
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        log.error(u"Failed with exception: %s", e)
        raise
