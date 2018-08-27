#! /usr/bin/env python
"""
A module for authenticating against and communicating with selected
parts of the Garmin Connect REST API.
"""
import json
import logging
import os
import re
import requests
import sys
import zipfile
import dateutil
import dateutil.parser
import os.path
from io import BytesIO
from functools import wraps
from builtins import range

log = logging.getLogger(__name__)

logging.getLogger("requests").setLevel(logging.ERROR)

SSO_LOGIN_URL = "https://sso.garmin.com/sso/login"
GARMIN_API_URL = "https://connect.garmin.com/modern/proxy"

def require_session(client_function):
    @wraps(client_function)
    def check_session(*args, **kwargs):
        client_object = args[0]
        if not client_object.session:
            raise Exception("Attempt to use GarminClient without being connected. Call connect() before first use.'")
        return client_function(*args, **kwargs)
    return check_session

"""
A client class used to authenticate with Garmin Connect and
extract data from the user account.

Since this class implements the context manager protocol, this object
can preferably be used together with the with-statement. This will
automatically take care of logging in to Garmin Connect before any
further interactions and logging out after the block completes or
a failure occurs.

Example of use:
    with GarminClient("my.sample@sample.com", "secretpassword") as client:
        ids = client.list_activity_ids()
        for activity_id in ids:
            gpx = client.get_activity_gpx(activity_id)

"""
class GarminClient(object):

    """
    Initialize a :class:`GarminClient` instance.

    :param username: Garmin Connect user name or email address.
    :type username: str
    :param password: Garmin Connect account password.
    :type password: str
    """
    def __init__(self, username, password, user=None):
        self.username = username
        self.password = password
        self.user = user
        self.session = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.disconnect()

    def connect(self):
        self.session = requests.Session()
        if self.password != None:
            self._authenticate()

    def disconnect(self):
        if self.session:
            self.session.close()
            self.session = None

    def _authenticate(self):
        log.info("Authenticating user ...")
        form_data = {
            "username": self.username,
            "password": self.password,
            "embed": "false"
        }
        request_params = {
            "service": "https://connect.garmin.com/modern"
        }

        auth_response = self.session.post(
            SSO_LOGIN_URL, params=request_params, data=form_data)
        log.debug("Got auth response: %s", auth_response.text)
        if auth_response.status_code != 200:
            raise ValueError("authentication failure: did you enter valid credentials?")
        auth_ticket_url = self._extract_auth_ticket_url(auth_response.text)
        log.debug("Auth ticket url: '%s'", auth_ticket_url)

        log.info("Claiming auth ticket ...")
        response = self.session.get(auth_ticket_url)
        if response.status_code != 200:
            raise RuntimeError("auth failure: failed to claim auth ticket: %s: %d\n%s" % (auth_ticket_url, response.status_code, response.text))

        self.session.get('https://connect.garmin.com/legacy/session')

    """
    Extracts an authentication ticket URL from the response of an
    authentication form submission. The auth ticket URL is typically
    of form:
        https://connect.garmin.com/modern?ticket=ST-0123456-aBCDefgh1iJkLmN5opQ9R-cas
    :param auth_response: HTML response from an auth form submission.
    """
    def _extract_auth_ticket_url(self, auth_response):
        match = re.search(r'response_url\s*=\s*"(https:[^"]+)"', auth_response)
        if not match:
            raise RuntimeError("auth failure: unable to extract auth ticket URL. did you provide a correct username/password?")
        auth_ticket_url = match.group(1).replace("\\", "")
        return auth_ticket_url

    """
    Return all activity ids stored by the logged in user, along
    with their starting timestamps.

    :returns: The full list of activity identifiers (along with their
        starting timestamps).
    :rtype: tuples of (int, datetime)
    """
    @require_session
    def list_activities(self):
        ids = []
        batch_size = 100
        for start_index in range(0, sys.maxsize, batch_size):
            next_batch = self._fetch_activity_ids_and_ts(start_index, batch_size)
            if not next_batch:
                break
            ids.extend(next_batch)
        return ids

    """
    Return a sequence of activity ids (along with their starting
    timestamps) starting at a given index, with index 0 being the user's
    most recently registered activity.

    Should the index be out of bounds or the account empty, an empty
    list is returned.

    :param start_index: The index of the first activity to retrieve.
    :type start_index: int
    :param max_limit: The (maximum) number of activities to retrieve.
    :type max_limit: int

    :returns: A list of activity identifiers (along with their
        starting timestamps).
    :rtype: tuples of (int, datetime)
    """
    @require_session
    def _fetch_activity_ids_and_ts(self, start_index, max_limit=100):
        log.debug("fetching activities {} through {} ...".format(start_index, start_index+max_limit-1))
        response = self.session.get(GARMIN_API_URL + "activitylist-service/activities/search/activities", params={"start": start_index, "limit": max_limit})
        if response.status_code != 200:
            raise Exception(u"failed to fetch activities {} to {} types: {}\n{}".format(start_index, (start_index+max_limit-1), response.status_code, response.text))
        activities = json.loads(response.text)
        if not activities:
            return []

        entries = []
        for activity in activities:
            id = int(activity["activityId"])
            timestamp_utc = dateutil.parser.parse(activity["startTimeGMT"])
            timestamp_utc = timestamp_utc.replace(tzinfo=dateutil.tz.tzutc())
            entries.append( (id, timestamp_utc) )
        log.debug("got {} activities.".format(len(entries)))
        return entries

    @require_session
    def get_daily_sleep_data(self, request_date):
        daily_sleep_url = GARMIN_API_URL + "/wellness-service/wellness/dailySleepData/{}?date={}&nonSleepBufferMinutes=60".format(self.user, request_date)
        return self.get_json_data(daily_sleep_url)

    @require_session
    def get_daily_hr_data(self, request_date):
        daily_hr_url = GARMIN_API_URL + "/wellness-service/wellness/dailyHeartRate/{}?date={}&_=1532359756927".format(self.user, request_date)
        return self.get_json_data(daily_hr_url)

    @require_session
    def get_daily_movement(self, request_date):
        daily_movement_url = GARMIN_API_URL + "/wellness-service/wellness/dailyMovement/{}?calendarDate={}&_=1532359756928".format(self.user, request_date)
        return self.get_json_data(daily_movement_url)

    @require_session
    def get_user_summary(self, request_date):
        user_summary_url = GARMIN_API_URL + "/usersummary-service/usersummary/daily/{}?calendarDate={}&_=1532359756925".format(self.user, request_date)
        return self.get_json_data(user_summary_url)

    """
    Return a summary about a given activity. The
    summary contains several statistics, such as duration, GPS starting
    point, GPS end point, elevation gain, max heart rate, max pace, max
    speed, etc).

    :param activity_id: Activity identifier.
    :type activity_id: int
    :returns: The activity summary as a JSON dict.
    :rtype: dict
    """
    @require_session
    def get_activity_summary(self, activity_id):
        activity_summary_url = GARMIN_API_URL + "activity-service/activity/{}".format(activity_id)
        return get_json_data(activity_summary_url)

    """
    Return a JSON representation of a given activity including
    available measurements such as location (longitude, latitude),
    heart rate, distance, pace, speed, elevation.

    :param activity_id: Activity identifier.
    :type activity_id: int
    :returns: The activity details as a JSON dict.
    :rtype: dict
    """
    @require_session
    def get_activity_details(self, activity_id):
        activity_details_url = GARMIN_API_URL + "activity-service-1.3/json/activityDetails/{}".format(activity_id)
        return get_json_url(activity_details_url)

    """
    Return a GPX (GPS Exchange Format) representation of a
    given activity. If the activity cannot be exported to GPX
    (not yet observed in practice, but that doesn't exclude the
    possibility), a :obj:`None` value is returned.

    :param activity_id: Activity identifier.
    :type activity_id: int
    :returns: The GPX representation of the activity as an XML string
        or ``None`` if the activity couldn't be exported to GPX.
    :rtype: str
    """
    @require_session
    def get_activity_gpx(self, activity_id):
        activity_gpx_url = GARMIN_API_URL + "download-service/export/gpx/activity/{}".format(activity_id)
        return self.get_data(activity_gpx_url)

    """
    Return a TCX (Training Center XML) representation of a
    given activity. If the activity doesn't have a TCX source (for
    example, if it was originally uploaded in GPX format, Garmin
    won't try to synthesize a TCX file) a :obj:`None` value is
    returned.

    :param activity_id: Activity identifier.
    :type activity_id: int
    :returns: The TCX representation of the activity as an XML string
        or ``None`` if the activity cannot be exported to TCX.
    :rtype: str
    """
    @require_session
    def get_activity_tcx(self, activity_id):
        activity_tcx_url = GARMIN_API_URL + "download-service/export/tcx/activity/{}".format(activity_id)
        return self.get_data(activity_tcx_url)

    """
    Return the original file that was uploaded for an activity.
    If the activity doesn't have any file source (for example,
    if it was entered manually rather than imported from a Garmin
    device) then :obj:`(None,None)` is returned.

    :param activity_id: Activity identifier.
    :type activity_id: int
    :returns: A tuple of the file type (e.g. 'fit', 'tcx', 'gpx') and
        its contents, or :obj:`(None,None)` if no file is found.
    :rtype: (str, str)
    """
    def get_original_activity(self, activity_id):
        response = self.session.get(GARMIN_API_URL + "download-service/files/activity/{}".format(activity_id))
        if response.status_code == 404:
            return (None, None)
        if response.status_code != 200:
            raise Exception(u"Failed to get original activity file for {}: {}\n{}".format(activity_id, response.status_code, response.text))

        zip = zipfile.ZipFile(StringIO(response.content), mode="r")
        for path in zip.namelist():
            fn, ext = os.path.splitext(path)
            if fn==str(activity_id):
                return ext[1:], zip.open(path).read()
        return (None,None)

    """
    Return a FIT representation for a given activity. If the activity
    doesn't have a FIT source (for example, if it was entered manually
    rather than imported from a Garmin device) a :obj:`None` value is
    returned.

    :param activity_id: Activity identifier.
    :type activity_id: int
    :returns: A string with a FIT file for the activity or :obj:`None`
        if no FIT source exists for this activity (e.g., entered manually).
    :rtype: str
    """
    def get_activity_fit(self, activity_id):
        fmt, orig_file = self.get_original_activity(activity_id)
        return orig_file if fmt=='fit' else None

    def get_json_data(self, get_url):
        data = json.loads(self.get_data(get_url))
        return data

    @require_session
    def get_data(self, get_url):
        response = self.session.get(get_url)
        if response.status_code in (404, 204):
            log.info("Response unavailable for request {}".format(get_url))
            return None
        if response.status_code != 200:
            raise Exception(u"Failed to fetch json {}\n{}".format(response.status_code, response.text))
        return response.text

    """
    Upload a GPX, TCX, or FIT file for an activity.

    :param file: Path or open file
    :param format: File format (gpx, tcx, or fit); guessed from filename if None
    :param name: Optional name for the activity on Garmin Connect
    :param description: Optional description for the activity on Garmin Connect
    :param activity_type: Optional activityType key (lowercase: e.g. running, cycling)
    :param private: If true, then activity will be set as private.
    :returns: ID of the newly-uploaded activity
    :rtype: int
    """
    @require_session
    def upload_activity(self, file, format=None, name=None, description=None, activity_type=None, private=None):
        if isinstance(file, basestring):
            file = open(file, "rb")

        fn = os.path.basename(file.name)
        _, ext = os.path.splitext(fn)
        if format is None:
            if ext.lower() in ('.gpx','.tcx','.fit'):
                format = ext.lower()[1:]
            else:
                raise Exception(u"Could not guess file type for {}".format(fn))

        files = dict(data=(fn, file))
        response = self.session.post(GARMIN_API_URL + "upload-service/upload/.{}".format(format), files=files, headers={"nk": "NT"})

        try:
            j = response.json()["detailedImportResult"]
        except (json.JSONDecodeException, KeyError):
            raise Exception(u"Failed to upload {} for activity: {}\n{}".format(format, response.status_code, response.text))

        if len(j["failures"]) or len(j["successes"]) < 1:
            raise Exception(u"Failed to upload {} for activity: {}\n{}".format(format, response.status_code, j["failures"]))

        if len(j["successes"])>1:
            raise Exception(u"Uploading {} resulted in multiple activities ({})".format(format, len(j["successes"])))

        activity_id = j["successes"][0]["internalId"]

        data = {}
        if name is not None: data['activityName'] = name
        if description is not None: data['description'] = name
        if activity_type is not None: data['activityTypeDTO'] = {"typeKey": activity_type}
        if private: data['privacy'] = {"typeKey": "private"}
        if data:
            data['activityId'] = activity_id
            encoding_headers = {"Content-Type": "application/json; charset=UTF-8"} # see Tapiriik
            response = self.session.put("https://connect.garmin.com/proxy/activity-service/activity/{}".format(activity_id), data=json.dumps(data), headers=encoding_headers)
            if response.status_code != 204:
                raise Exception(u"failed to set metadata for activity {}: {}\n{}".format(activity_id, response.status_code, response.text))

        return activity_id
