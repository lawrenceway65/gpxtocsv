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


def get_output_path(activity='', year=0):
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


def get_pace(time, distance):
    """Calculate pace in minutes per mile"""
    return time / 60 * MILE / distance


def get_activity_type(time, distance):
    """Calculate pace (min/mile) and return matching activity.
    """
    pace = get_pace(time, distance)
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


def add_gps_point(gpx_track, point):
    """Create new point and add to track."""
    new_point = gpxpy.gpx.GPXTrackPoint()
    new_point.latitude = point.latitude
    new_point.longitude = point.longitude
    new_point.time = point.time
    new_point.elevation = point.elevation
    # Only ever single track and segment
    gpx_track.tracks[0].segments[0].points.append(new_point)

    return


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


def open_metadata_file():
    """Open metadata csv file and write header"""
    # Filename ProcessGPX_YY-MM-DD_HHMM.csv
    csv_file = io.open('%sImport%sProcessGPX_%s.csv' % (get_output_path(), os.sep, datetime.now().strftime("%d-%m-%Y_%H%M")),
        'w', encoding='utf-8')
    csv_file.write('Date,Time,Activity,Garmin ID,Distance,Duration,Location\n')

    return csv_file


def set_up_gpx():
    """Setup GPX - always one track and one segment"""
    gpx = gpxpy.gpx.GPX()
    # Create track
    track = gpxpy.gpx.GPXTrack()
    gpx.tracks.append(track)
    # Create segment
    segment = gpxpy.gpx.GPXTrackSegment()
    track.segments.append(segment)

    return gpx


def save_activity_data(activity_id, start_point, end_point, farthest_point, distance, point_count, gpx_data, split_data):
    """Save associated data
    Generate filename, save gpx data, save split data, save meta data

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
    MetaDataCSV.write('%s,%s,activity_%s,%d,%s,%s\n' % (time.strftime('%Y-%m-%d, %H:%M', time.localtime(start_point.time.timestamp())),
                                                   activity_type,
                                                   activity_id,
                                                   distance,
                                                   end_point.time - start_point.time,
                                                   location))

    print('%s trackpoints written to %s' % (point_count, output_filename))

    return


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
    split_distance = 0
    points_written = 0
    max_distance = 0
    separation = 0
    split_csv = split_csv_header
    output_gpx = set_up_gpx()

    # Parse to gpx and iterate through
    input_gpx = gpxpy.parse(gpx_xml)
    for track in input_gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                point_count += 1
                if point_count > 1:
                    # Distance from last point
                    incremental_distance = calculate_distance(previous_point, point)
                    split_distance += incremental_distance
                    separation += incremental_distance

                    # Straight line distance from start point
                    distance_from_start = calculate_distance(start_point, point)
                    if distance_from_start > max_distance:
                        max_distance = distance_from_start
                        farthest_point = point
                else:
                    # First time, add first point
                    start_point = split_start_point = point
                    add_gps_point(output_gpx, start_point)

                previous_point = point

                # If we have we moved 5m, add next point
                if separation >= MINPOINTSEPARATION:
                    # Add to track and reset
                    add_gps_point(output_gpx, point)
                    points_written += 1
                    total_distance += separation
                    separation = 0

                # If we have completed a split, write a csv record
                if split_distance > SPLIT:
                    split_time = point.time - split_start_point.time
                    pace = get_pace(split_time.seconds, split_distance)
                    # Pace output as decimal minutes and MM:SS
                    split_csv += split_csv_format_string % (time.strftime('%Y-%m-%d, %H:%M:%S', time.localtime(point.time.timestamp())),
                                                  split_time,
                                                  split_distance,
                                                  point.time - start_point.time,
                                                  total_distance,
                                                  pace,
                                                  int(pace), (pace % 1 * 60))
                    # Reset for next split - don't set distance to 0 to avoid cumulative errors
                    split_distance -= SPLIT
                    split_start_point = point

    # Save everything, but only if we actually have some data
    if points_written != 0:
        save_activity_data(activity_id,
                           start_point,
                           point,
                           farthest_point,
                           total_distance,
                           points_written,
                           output_gpx,
                           split_csv)

    return


MetaDataCSV = open_metadata_file()

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

    MetaDataCSV.close()
    print('Activities processed: %d, Activities saved: %d' % (activities_processed, activities_saved))
