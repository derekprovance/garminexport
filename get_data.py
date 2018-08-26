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
        "--end", type=str, help="Process multiple days.")
    parser.add_argument(
        "--start", type=str, help="How many days from the current date to start processing? YYYY-MM-DD")
    parser.add_argument(
        "--log-level", metavar="LEVEL", type=str,
        help=("Desired log output level (DEBUG, INFO, WARNING, ERROR). "
              "Default: INFO."), default="INFO")

    args = parser.parse_args()

    if not args.log_level in LOG_LEVELS:
        raise ValueError("Illegal log-level argument: {}".format(
            args.log_level))

    logging.root.setLevel(LOG_LEVELS[args.log_level])

    try:
        if not args.password:
            args.password = getpass.getpass("Enter password: ")

        if not args.start:
            request_date = (date.today() - timedelta(1)).strftime('%y-%m-%d')
        else:
            request_date = args.start
        
        db = Database()

        logging.info("Pulling data for {}".format(request_date))
    
        with GarminClient(args.username, args.password) as client:
            db.insert_sleep_data(client.get_daily_sleep_data(request_date))
            db.insert_hr_data(client.get_daily_hr_data(request_date))
            db.insert_movement_data(client.get_daily_movement(request_date))
            db.insert_user_summary(client.get_user_summary(request_date))
            db.disconnect()
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        log.error(u"Failed with exception: %s", e)
        raise
