from datetime import date, timedelta, datetime
from dateutil import parser
import pymysql.cursors

class Database(object):
    def __init__(self):
        self.connect()

    def connect(self):
        self.connection = pymysql.connect(
            host='127.0.0.1',
            user='root',
            password='',
            db='biometrics',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor)

    def disconnect(self):
        self.connection.close()

    def create_or_get_daily_statistic_id(self, date=None):
        if(date == None):
            date = (date.today() - timedelta(1)).strftime('%y-%m-%d')
        with self.connection.cursor() as cursor:
            sql = "SELECT `id` FROM `daily_statistics` WHERE `entry_date`=%s"
            cursor.execute(sql, date)
            result = cursor.fetchone()
            if result != None:
                return result['id']

        with self.connection.cursor() as cursor:
            sql = "INSERT INTO `daily_statistics` (`entry_date`) VALUES (%s)"
            cursor.execute(sql, date)
            self.connection.commit()
            return cursor.lastrowid

    def convert_epoch_to_datetime(self, epoch):
        #TODO - Implement a better approach
        if epoch == None:
            return None

        return datetime.fromtimestamp(int(str(epoch)[:10]))

    def insert_sleep_data(self, sleep_data):
        data_date = sleep_data['dailySleepDTO']['calendarDate']
        daily_statistics_id = self.create_or_get_daily_statistic_id(data_date)

        with self.connection.cursor() as cursor:
            daily_sleep_data = sleep_data['dailySleepDTO']

            sql = "UPDATE `daily_statistics` SET `total_sleep` = %s WHERE id = %s"
            cursor.execute(sql, (daily_sleep_data['sleepTimeSeconds'], daily_statistics_id))

            sleep_start = self.convert_epoch_to_datetime(daily_sleep_data['sleepStartTimestampGMT'])
            sleep_end = self.convert_epoch_to_datetime(daily_sleep_data['sleepEndTimestampGMT'])

            sql = "INSERT INTO `sleep` (`daily_statistics_id`, `sleep_start`, `sleep_end`, `deep_sleep`, `light_sleep`, `rem_sleep`, `awake_sleep`) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            cursor.execute(sql, (daily_statistics_id, sleep_start, sleep_end, daily_sleep_data['deepSleepSeconds'],  daily_sleep_data['lightSleepSeconds'], daily_sleep_data['remSleepSeconds'], daily_sleep_data['awakeSleepSeconds']))
            sleep_id = cursor.lastrowid

        with self.connection.cursor() as cursor:
            sleep_movement = sleep_data['sleepMovement']

            if sleep_data['sleepMovement'] != None:
                for movement in sleep_movement:
                    sql = "INSERT INTO `sleep_movement` (`sleep_id`, `start`, `end`, `activity_level`) VALUES (%s, %s, %s, %s)"
                    cursor.execute(sql, (sleep_id, parser.parse(movement['startGMT']), parser.parse(movement['endGMT']), movement['activityLevel']))

        self.connection.commit()

    def insert_hr_data(self, hr_data):
        data_date = hr_data['calendarDate']
        daily_statistics_id = self.create_or_get_daily_statistic_id(data_date)

        with self.connection.cursor() as cursor:
            sql = "UPDATE `daily_statistics` SET `max_hr` = %s, `min_hr` = %s, `resting_hr` = %s WHERE id = %s"
            cursor.execute(sql, (hr_data['maxHeartRate'], hr_data['minHeartRate'], hr_data['restingHeartRate'], daily_statistics_id))

            if hr_data['heartRateValues'] != None:
                for hr_value in hr_data['heartRateValues']:
                    time_entry = self.convert_epoch_to_datetime(hr_value[0])
                    sql = "INSERT INTO `hr_data` (`daily_statistics_id`, `event_time`, `hr_value`) VALUES (%s, %s, %s)"
                    cursor.execute(sql, (daily_statistics_id, time_entry, hr_value[1]))

        self.connection.commit()

    def insert_movement_data(self, movement_data):
        data_date = movement_data['calendarDate']
        daily_statistics_id = self.create_or_get_daily_statistic_id(data_date)

        with self.connection.cursor() as cursor:
            if movement_data['movementValues'] != None:
                for mv_data in movement_data['movementValues']:
                    time_entry = self.convert_epoch_to_datetime(mv_data[0])
                    sql = "INSERT INTO `movement_data` (`daily_statistics_id`, `event_time`, `movement`) VALUES (%s, %s, %s)"
                    cursor.execute(sql, (daily_statistics_id, time_entry, mv_data[1]))

        self.connection.commit()

    def insert_user_summary(self, summary_data):
        data_date = summary_data['calendarDate']
        daily_statistics_id = self.create_or_get_daily_statistic_id(data_date)

        with self.connection.cursor() as cursor:
            sql = "UPDATE `daily_statistics` SET `total_steps` = %s, `highly_active_seconds` = %s, `active_seconds` = %s, `sedentary_seconds` = %s, `sleeping_seconds` = %s, `max_stress_level` = %s, `low_stress_duration` = %s, `medium_stress_duration` = %s, `high_stress_duration` = %s WHERE id = %s"
            cursor.execute(sql, (summary_data['totalSteps'], summary_data['highlyActiveSeconds'], summary_data['activeSeconds'], summary_data['sedentarySeconds'], summary_data['sleepingSeconds'], summary_data['maxStressLevel'], summary_data['lowStressDuration'], summary_data['mediumStressDuration'], summary_data['highStressDuration'], daily_statistics_id))

        self.connection.commit()
