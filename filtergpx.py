"""
Created on 9 Jan 2021
Parses gpx file and creates new file. Any points less than 5m from previous point are excluded.
Temperature data also excluded.
New gpx named meaningfully, by activity type, date, tine and distance,
Creates much smaller gpx that can be uploaded to outddorsgb
Output splits data and activity metadata to csvs
@author: lawrence
"""


import gpxpy
import gpxpy.gpx
from geopy.distance import distance
from datetime import datetime, timedelta
import time
import os
import subprocess
import json
import requests
import re
import io
import garmincredential
import config
from garminconnect import (
    Garmin,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
    GarminConnectAuthenticationError,
)


# Constants and definitions
# Meters in a mile
MILE = 1609
SPLIT = 250
# Only write points farther apart than this (meters)
MINPOINTSEPARATION = 5
# For splits data output
split_csv_header = 'Date,Time,Split Time,Split Distance,Total Time,Total Distance,Pace,Pace(m:s)\n'
split_csv_format_string = '%s,%s,%.0f,%s,%.0f,%.2f,%02d:%02d\n'

gpx_csv_header = 'Date,Time,Incr Time,Incr Distance,Total Distance,Speed(m/s)\n'
gpx_csv_format_string = '%s,%f,%f,%f,%f\n'

metadata_csv_name_format_string = '%sImport%sProcessGPX.csv'
metadata_csv_header = 'Date,Time,Activity,Garmin ID,Distance,Duration,Location\n'
logfile_name_format_string = '%sImport%sProcessGPX.log'


def get_output_path(activity='', year=''):
    """
    Get path for output files.
    Creates any folders that don't already exist.
    Just return root path if no params provided
    """
    if os.name == 'nt':
        path = config.local_path
    else:
        path = "/Users/lawrence/Documents/GPSData/"

    if activity != '':
        # Just create these if they don't exist
        if not os.path.isdir(path + 'Activities/' + activity):
            os.mkdir(path + 'Activities/' + activity)

        path += 'Activities' + os.sep + activity + os.sep + year + os.sep
        if not os.path.isdir(path):
            os.mkdir(path)

    return path


class State:

    def __init__(self):
        self.status = 'Not started'
        self.logfile_name = logfile_name_format_string % (get_output_path(), os.sep)

    def Update(self, status):
        self.status = status
        print(self.status)

    def Write(self, status=''):
        if status != '':
            self.status = status
        print(self.status)
        with open(self.logfile_name, 'a') as logfile:
            logfile.write('%s\t%s\n' % (datetime.now().strftime("%d-%m-%Y %H:%M:%S"), self.status))


class MetadataCSV:
    """Manages metadata csv.
    File is only created if there is something to write.
    """
    def __init__(self):
        """Primarily initialises output filename"""
        self.lines_written = 0
        self.file = None
        self.metadata_csv_filename = metadata_csv_name_format_string % (get_output_path(),
                                                                        os.sep)

    def __enter__(self):
        """To allow use of 'with'."""
        return self

    def write(self, activity_id, activity_type, track):
        """Writes line to file.
        If nothing written yet create the file and write header
        :type activity_id: str
        :type activity_type: str
        :type track: TrackData
        """

        if not os.path.isfile(self.metadata_csv_filename):
            self.file = io.open(self.metadata_csv_filename, 'a', encoding='utf-8')
            self.file.write(metadata_csv_header)
        elif self.lines_written == 0:
            self.file = io.open(self.metadata_csv_filename, 'a', encoding='utf-8')

        s = ('%s,%s,activity_%s,%d,%s,%s\n' % (time.strftime('%Y-%m-%d, %H:%M', time.localtime(track.start_point.time.timestamp())),
                                                             activity_type,
                                                             activity_id,
                                                             track.track_distance,
                                                             track.last_point.time - track.start_point.time,
                                                             track.get_locality_string()))
        self.file.write(s)
        self.lines_written += 1

        return

    def __exit__(self, exc_type, exc_val, exc_tb):
        """"To allow use of 'with'."""
        pass

    def __del__(self):
        """File will only need closing if lines have been written."""
        if self.lines_written > 0:
            self.file.close()


def get_pace(time, distance):
    """Calculate pace in minutes per mile"""
    return time / 60 * MILE / distance


class GPXData:
    """"""
    def __init__(self):
        """Set up GPX"""
        self.separation = 0
        self.points_written = 0
        self.stopped_seconds = 0

        self.gpx = gpxpy.gpx.GPX()
        # Create track
        track = gpxpy.gpx.GPXTrack()
        self.gpx.tracks.append(track)
        # Create segment
        segment = gpxpy.gpx.GPXTrackSegment()
        track.segments.append(segment)

        return

    def __del__(self):
        """Nothing required."""
        pass

    def process_point(self, point, distance):
        """Increment distance, if complete split, write csv data and reset for next split"""
        self.separation += distance
        if self.separation >= MINPOINTSEPARATION:
            # Create new point and add it
            new_point = gpxpy.gpx.GPXTrackPoint()
            new_point.latitude = point.latitude
            new_point.longitude = point.longitude
            new_point.time = point.time
            new_point.elevation = point.elevation
            # Only ever single track and segment
            self.gpx.tracks[0].segments[0].points.append(new_point)
            self.points_written += 1
            # Reset distance
            self.separation = 0

            return

    def write(self, filename):
        """Write to file"""
        with open(filename + '.gpx', 'w') as gpx_file:
            gpx_file.write(self.gpx.to_xml())


class Splits:
    """Manages calculation and saving of split data
    Initialised with first point, called for each point and adds csv data for splits.
    """
    def __init__(self, point):
        """"""
        self.start_point = point
        self.split_distance = 0
        self.csv_data = split_csv_header

    def __del__(self):
        """Nothing required."""
        pass

    def process_point(self, point, distance, total_distance):
        """Increment distance, if complete split, write csv data and reset for next split"""
        self.split_distance += distance
        if self.split_distance >= SPLIT:
            split_time = point.time - self.start_point.time
            pace = get_pace(split_time.seconds, self.split_distance)
            # Pace output as decimal minutes and MM:SS
            self.csv_data += split_csv_format_string % (time.strftime('%Y-%m-%d, %H:%M:%S', time.localtime(point.time.timestamp())),
                                                        split_time,
                                                        self.split_distance,
                                                        point.time - self.start_point.time,
                                                        total_distance,
                                                        pace,
                                                        int(pace),
                                                        (pace % 1 * 60))
            # Reset for next split - don't set distance to 0 to avoid cumulative errors
            self.split_distance -= SPLIT
            self.start_point = point

        return

    def write(self, filename):
        """Write to file"""
        with open(filename + '.csv', 'w') as file:
            file.write(self.csv_data)


class GPXcsv:
    """Manages csv output of gpx data
    Initialised with first point, called for each point outputs csv data.
    """
    def __init__(self, point):
        """"""
        self.prev_point = point
        self.total_distance = 0
        self.csv_data = gpx_csv_header

    def __del__(self):
        """Nothing required."""
        pass

    def process_point(self, point, incremental_distance):
        """Increment distance, if complete split, write csv data and reset for next split"""
        self.total_distance += incremental_distance
        incremental_time = point.time - self.prev_point.time
        # Pace output as decimal minutes and MM:SS
        self.csv_data += gpx_csv_format_string % (time.strftime('%Y-%m-%d, %H:%M:%S', time.localtime(point.time.timestamp())),
                                                    incremental_time.seconds,
                                                    incremental_distance,
                                                    self.total_distance,
                                                    incremental_distance / incremental_time.seconds)
        self.prev_point = point

        return

    def write(self, filename):
        """Write to file"""
        with open(filename + '.csv', 'w') as file:
            file.write(self.csv_data)

class TrackData:
    def __init__(self, point):
        self.start_point = point
        # Farthest straight line distance from start
        self.max_distance = 0
        # Total distance covered
        self.track_distance = 0
        # Private - always get via call
        self._locality_string = ''

    def process_point(self, point, incremental_distance):
        self.track_distance += incremental_distance
        self.last_point = point
        distance_from_start = calculate_distance(self.start_point, point)
        if distance_from_start > self.max_distance:
            self.max_distance = distance_from_start
            self.farthest_point = point


    def get_locality_string(self):
        """Returns human readable location info
        If we already have it just return it.
        """
        if self._locality_string == '':
            # Get info for start/end/farthest - remove any spaces, don't want them in filename
            start_locality = get_locality(self.start_point.latitude, self.start_point.longitude).replace(' ', '')
            end_locality = get_locality(self.last_point.latitude, self.last_point.longitude).replace(' ', '')
            farthest_locality = get_locality(self.farthest_point.latitude, self.farthest_point.longitude).replace(' ', '')
            # print('Start: %s, End: %s, Farthest: %s' % (start_town, end_town, farthest_town))

            # Might have been circular, in which case use farthest. Avoid repetition if all the same.
            if start_locality == end_locality:
                if end_locality == farthest_locality:
                    self._locality_string = start_locality
                else:
                    self._locality_string = start_locality + farthest_locality
            else:
                self._locality_string = start_locality + end_locality

            # Remove problem characters
            self._locality_string = self._locality_string.replace('/', '-')

        return self._locality_string.replace('/', '-')


def get_activity_type(track):
    """Calculate pace (min/mile) and return matching activity.
    :type track: TrackData
    """
    time = track.last_point.time - track.start_point.time
    pace = get_pace(time.seconds, track.track_distance)
    if pace > 12:
        activity = 'Hike'
    elif pace > 7:
        activity = 'Run'
    elif pace > 2.5:
        activity = 'Cycle'
    else:
        activity = 'Unknown'

    return activity


def calculate_distance(point1, point2):
    """Wrapper for distance calculation
    Pass in gps points, return separation
    """
    coord1 = (point1.latitude, point1.longitude)
    coord2 = (point2.latitude, point2.longitude)

    return distance(coord1, coord2).meters


def get_locality(latitude, longitude):
    """Get location from co-ordinates. Use Open Street Map.
    Using street level (zoom = 16) and picking second item, gives more accurate result
    """
    osm_request = "https://nominatim.openstreetmap.org/reverse?lat=%f&lon=%f&zoom=16&format=json"
    result = subprocess.check_output(['curl', '-s', osm_request % (latitude, longitude)]).decode("utf-8")
    result_json = json.loads(result)
#    result = requests.get(osm_request % (latitude, longitude))
    # Extract second item from 'display_name'
    # Need to handle case where no locality - eg at sea
#    print(result_json)
    try:
        location = re.split(',', result_json['display_name'])[1]
    except IndexError:
        location = ""
    except KeyError:
        location = ""
    return location


def process_gpx(activity_id, gpx_xml):
    """Process gpx data as follows:
    Filter gpx to only include points with >=5m separation and basic data only (lat, long, time, elev)
    Generate split data and (for run and cycle activities) write to csv
    Determine activity type from average pace
    Determine location from start, end and farthest points
    Name output files <activity>_<date>_<time>_<distance>_<location>
    Write output files to dir structure by activitiy type and year
    Add row of metadata for activity

    :param activity_id: id of activity (eg garmin id or other identifier)
    :type activity_id: str
    :param gpx_xml: gpx data
    :type gpx_xml: xml
    """
    # Variables
    point_count = 0
    total_distance = 0
    output_gpx = GPXData()

    # Parse to gpx and iterate through
    input_gpx = gpxpy.parse(gpx_xml)
    for track in input_gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                point_count += 1
                if point_count > 1:
                    # Distance from last point
                    incremental_distance = calculate_distance(previous_point, point)
                    # print(str(incremental_distance) + ", " + time.strftime('%H:%M:%S', time.localtime(point.time.timestamp())))
                    total_distance += incremental_distance
                    # Manage split
                    split_tracker.process_point(point, incremental_distance, total_distance)
                    # Manage gpx
                    output_gpx.process_point(point, incremental_distance)
                    # Manage data
                    track_data.process_point(point, incremental_distance)
                    # csv output
                    gpx_csv_data.process_point(point, incremental_distance)
                else:
                    # First time, set things up
                    split_tracker = Splits(point)
                    track_data = TrackData(point)
                    gpx_csv_data = GPXcsv(point)

                previous_point = point

    # Save everything, but only if we actually have some data
    if output_gpx.points_written != 0:
        activity_type = get_activity_type(track_data)
        output_filename = '%s%s_%s_%dMile_%s' % (get_output_path(activity_type, track_data.start_point.time.strftime('%Y')),
                                                 activity_type,
                                                 time.strftime('%Y-%m-%d_%H%M', time.localtime(track_data.start_point.time.timestamp())),
                                                 (track_data.track_distance / MILE),
                                                 track_data.get_locality_string())

        if activity_type == 'Run':
            split_tracker.write(output_filename + '_split')
        elif activity_type == 'Cycle':
            gpx_csv_data.write(output_filename + '_points')
        output_gpx.write(output_filename)
        # Write metadata to csv
        metadata_csv.write(activity_id, activity_type, track_data)

        print('%s trackpoints written to %s' % (point_count, output_filename))

    return


metadata_csv = MetadataCSV()

if __name__ == "__main__":
    # Don't necessarily want to download everything
    max_activities = config.max_activities
    activities_saved = 0
    status = State()

    print("Download activities from Garmin Connect.")
    try:
        client = Garmin(garmincredential.username, garmincredential.password)
        client.login()
        activities = client.get_activities(0, max_activities)  # 0=start, 1=limit
    except (
            GarminConnectConnectionError,
            GarminConnectAuthenticationError,
            GarminConnectTooManyRequestsError
    ) as err:
        status.Write("Error occurred during Garmin Connect Client init: %s" % err)
        quit()
    except Exception:  # pylint: disable=broad-except
        status.Write("Unknown error occurred during Garmin Connect Client init")
        quit()

    for activity in activities:
        activity_id = activity["activityId"]
        output_file = '%s/Import/Raw/activity_%d.gpx' % (get_output_path(), activity_id)
        # Only save and process if file not already saved from previous download
        if not os.path.isfile(output_file):
            # Download and process the gpx file
            gpx = client.download_activity(activity_id, dl_fmt=client.ActivityDownloadFormat.GPX)
            process_gpx('%d' % activity_id, gpx)
            # Save it
            with open(output_file, 'wb') as gpx_file:
                gpx_file.write(gpx)
                activities_saved += 1

    status.Write('Activities saved: %d' % activities_saved)
