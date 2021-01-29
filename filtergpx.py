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
from garminexport.garminclient import GarminClient
import re
import io
import garmincredential
import config


# Constants and definitions
# Meters in a mile
MILE = 1609
SPLIT = 250
# Only write points farther apart than this (meters)
MINPOINTSEPARATION = 5
# For splits data output
split_csv_header = 'Date,Time,Split Time,Split Distance,Total Time,Total Distance,Pace,Pace(m:s)\n'
split_csv_format_string = '%s,%s,%.0f,%s,%.0f,%.2f,%02d:%02d\n'

metadata_csv_name_format_string = '%sImport%sProcessGPX_%s.csv'
metadata_csv_header = 'Date,Time,Activity,Garmin ID,Distance,Duration,Location\n'

def get_output_path(activity='', year=''):
    """
    Get path for output files.
    Creates any folders that don't already exist.
    Just return root path if no params provided
    """
    if os.name == 'nt':
        path = "D:\\Documents\\GPSData\\"
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


class MetadataCSV:
    """Manages metadata csv.
    File is only created if there is something to write.
    """
    def __init__(self):
        """Primarily initialises output filename"""
        self.lines_written = 0
        self.file = None
        self.metadata_csv_filename = metadata_csv_name_format_string % (get_output_path(),
                                                                        os.sep,
                                                                        datetime.now().strftime("%d-%m-%Y_%H%M"))

    def __enter__(self):
        """To allow use of 'with'."""
        return self

    def write(self, s):
        """Writes line to file.
        If nothing written yet create the file and write header
        """
        if self.lines_written == 0:
            self.file = io.open(self.metadata_csv_filename, 'w', encoding='utf-8')
            self.file.write(metadata_csv_header)
        self.file.write(s)
        self.lines_written += 1

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


class TrackLocations:
    def __init__(self, point):
        self.start_point = point
        self.max_distance = 0

        return

    def process_point(self, point):
        self.last_point = point
        distance_from_start = calculate_distance(self.start_point, point)
        if  distance_from_start > self.max_distance:
            self.max_distance = distance_from_start
            self.farthest_point = point

        return


def get_activity_type(location_data, distance):
    """Calculate pace (min/mile) and return matching activity.
    :type location_data: TrackLocations
    :type distance: float
    """
    time = location_data.last_point.time - location_data.start_point.time
    pace = get_pace(time.seconds, distance)
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
    #   print(OSMRequest % (Latitude, Longitude))
    result = subprocess.check_output(['curl', '-s', osm_request % (latitude, longitude)]).decode("utf-8")
    result_json = json.loads(result)

    # Extract second item from 'display_name'
    return re.split(',', result_json['display_name'])[1]


def get_locality_string(start_point, end_point, farthest_point):
    """Get location string for filename
    Default is: <start><end>
    """
    # Start/end - remove any spaces, don't want them in filename
    start_locality = get_locality(start_point.latitude, start_point.longitude).replace(' ', '')
    end_locality = get_locality(end_point.latitude, end_point.longitude).replace(' ', '')
    farthest_locality = get_locality(farthest_point.latitude, farthest_point.longitude).replace(' ', '')
#    print('Start: %s, End: %s, Farthest: %s' % (start_town, end_town, farthest_town))

    # Might have been circular, in which case use farthest. Avoid repetition if all the same.
    if start_locality == end_locality:
        if end_locality == farthest_locality:
            return start_locality
        else:
            return start_locality + farthest_locality
    else:
        return start_locality + end_locality


def save_activity_data(activity_id, start_point, end_point, farthest_point, distance, point_count, gpx_data, split_data):
    """Save associated data.
    Generate filename, save gpx data, save split data, save meta data.

    :param activity_id: identifier of original file
    :param start_point: start - with next two params, used to generate location string
    :param end_point: end
    :param farthest_point: farthest
    :param distance: activity total distance
    :param point_count: number of gpx points to write (for info)
    :param gpx_data: gpx xml to write
    :param split_data: csv split data
    """
    # Path / filename for gpx and split csv
    activity_type = get_activity_type((end_point.time-start_point.time).seconds, distance)
    location = get_locality_string(start_point, end_point, farthest_point)
    output_filename = '%s%s_%s_%dMile_%s' % (get_output_path(activity_type, start_point.time.strftime('%Y')),
                                                activity_type,
                                                time.strftime('%Y-%m-%d_%H%M', time.localtime(start_point.time.timestamp())),
                                                (distance / MILE),
                                                location)
    # Write gpx track
    with open(output_filename + '.gpx', 'w') as gpx_file:
        gpx_file.write(gpx_data.to_xml())

    # Write split csv data only for run and cycle
    if activity_type == 'Run' or activity_type == 'Cycle':
        with open(output_filename + '.csv', 'w') as csv_file:
            csv_file.write(split_data)

    # Write metadata to csv
    metadata_csv.write('%s,%s,activity_%s,%d,%s,%s\n' % (time.strftime('%Y-%m-%d, %H:%M', time.localtime(start_point.time.timestamp())),
                                                   activity_type,
                                                   activity_id,
                                                   distance,
                                                   end_point.time - start_point.time,
                                                   location))

    print('%s trackpoints written to %s' % (point_count, output_filename))

    return


def get_output_filename(location_data, distance, activity_type):
    """Save associated data.
    Generate filename, save gpx data, save split data, save meta data.

    :param location_data: start - with next two params, used to generate location string
    :type location_data: TrackLocations
    :param distance: activity total distance
    :type distance: float
    :type activity_type: str
    """
    # Path / filename for gpx and split csv
    location = get_locality_string(location_data.start_point,
                                   location_data.last_point,
                                   location_data.farthest_point)
    output_filename = '%s%s_%s_%dMile_%s' % (get_output_path(activity_type, location_data.start_point.time.strftime('%Y')),
                                                activity_type,
                                                time.strftime('%Y-%m-%d_%H%M', time.localtime(location_data.start_point.time.timestamp())),
                                                (distance / MILE),
                                                location)

    return output_filename



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
    :type activity_id: string
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
                    total_distance += incremental_distance
                    # Manage split
                    split_tracker.process_point(point, incremental_distance, total_distance)
                    # Manage gpx
                    output_gpx.process_point(point, incremental_distance)
                    # Manage locations
                    location_tracker.process_point(point)
                else:
                    # First time, set things up
                    split_tracker = Splits(point)
                    location_tracker = TrackLocations(point)

                previous_point = point

    # Save everything, but only if we actually have some data
    if output_gpx.points_written != 0:
        activity_type = get_activity_type(location_tracker, total_distance)
        output_filename = get_output_filename(location_tracker, total_distance, activity_type)

        if activity_type == 'Run' or activity_type == 'Cycle':
            split_tracker.write(output_filename)
        output_gpx.write(output_filename)

        # # Write metadata to csv
        # metadata_csv.write('%s,%s,activity_%s,%d,%s,%s\n' % (
        # time.strftime('%Y-%m-%d, %H:%M', time.localtime(location_tracker.start_point.time.timestamp())),
        # activity_type,
        # activity_id,
        # total_distance,
        # location_tracker.last_point.time - location_tracker.start_point.time,
        # location))

        print('%s trackpoints written to %s' % (point_count, output_filename))

        # save_activity_data(activity_id,
        #                    location_tracker.start_point,
        #                    location_tracker.last_point,
        #                    location_tracker.farthest_point,
        #                    total_distance,
        #                    output_gpx.points_written,
        #                    output_gpx.gpx,
        #                    split_tracker.csv_data)

    return


metadata_csv = MetadataCSV()

if __name__ == "__main__":
    # Don't necessarily want to download everything
    max_activities = config.max_activities

    activities_saved = activities_processed = 0
    with GarminClient(garmincredential.username, garmincredential.password) as client:
        # By default download last five activities
        ids = client.list_activities()
        for activity_id in ids:
            output_file = '%s/Import/Raw/activity_%d.gpx' % (get_output_path(), activity_id[0])
    #        print(output_file)

            # Only save and process if file not already saved from previous download
            if os.path.isfile(output_file):
                print("activity_%d already downloaded" % activity_id[0])
            else:
                # Download and process the gpx file
                gpx = client.get_activity_gpx(activity_id[0])
                process_gpx('%d' % activity_id[0], gpx)
                # Save it
                raw_gpx_file = open(output_file, 'w')
                raw_gpx_file.write(gpx)
                raw_gpx_file.close()
    #            print('Saved activity_%d.gpx' % (activity_id[0]))
                activities_saved += 1
            activities_processed += 1

            # Drop out if limit reached
            if activities_processed >= max_activities:
                break

#    MetaDataCSV.close()
    print('Activities processed: %d, Activities saved: %d' % (activities_processed, activities_saved))
