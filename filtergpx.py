'''
Created on 9 Jan 2021

@author: lawrence
'''

# Parses gpx file and creates new file. Any points less than 5m from previous point are excluded.
# Temperature data also excluded.
# New gpx named meaningfully, by activity type, date, tine and distance,
# Creates much smaller gpx that can be uploaded to outddorsgb  

import gpxpy
import gpxpy.gpx
import geopy
from geopy.distance import distance
# import datetime
from datetime import datetime, timedelta
import time
import os
import subprocess
import json
import shutil
from garminexport.garminclient import GarminClient
import garmincredential
import re
import io

# Constants and definitions
# Meters in a mile
MILE = 1609
SPLIT = 250
# Only write points farther apart than this (meters)
MINPOINTSEPARATION = 5


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


def get_activity_type(distance, time):
    """Calculate pace (min/mile) and return matching activity.
    """
    pace = time / 60 * MILE / distance
    if pace > 12:
        activity = 'Hike'
    elif pace > 7:
        activity = 'Run'
    elif pace > 2.5:
        activity = 'Cycle'
    else:
        activity = 'Unknown'

    return activity


def add_gps_point(gpx_track, point):
    """Create new point and add to track."""
    new_point = gpxpy.gpx.GPXTrackPoint()
    new_point.latitude = point.latitude
    new_point.longitude = point.longitude
    new_point.time = point.time
    new_point.elevation = point.elevation
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


def get_locality_string(start_coord, end_coord, farthest_coord):
    """Get location string for filename
    Default is: <start><end>
    """
    # Start/end - remove any spaces, don't want them in filename
    start_locality = get_locality(start_coord[0], start_coord[1]).replace(' ', '')
    end_locality = get_locality(end_coord[0], end_coord[1]).replace(' ', '')
    farthest_locality = get_locality(farthest_coord[0], farthest_coord[1]).replace(' ', '')
#    print('Start: %s, End: %s, Farthest: %s' % (start_town, end_town, farthest_town))

    # Might have been circular, in which case use farthest. Avoid repetition if all the same.
    if start_locality == end_locality:
        if end_locality == farthest_locality:
            return start_locality
        else:
            return start_locality + farthest_locality
    else:
        return start_locality + end_locality


# Open metadata csv file and write header
def OpenMetaDataCSV():
    # Filename ProcessGPX_YY-MM-DD_HHMM.csv
    MetaDataCSV = io.open('%sImport%sProcessGPX_%s.csv' % (get_output_path(), os.sep, datetime.now().strftime("%d-%m-%Y_%H%M")),
        'w', encoding='utf-8')
    MetaDataCSV.write('Date,Time,Activity,Garmin ID,Distance,Duration,Location\n')

    return MetaDataCSV


# Setup GPX - always one track and one segment
def set_up_gpx():
    # GPX output
    OutputGPX = gpxpy.gpx.GPX()
    # Create track
    GPXTrack = gpxpy.gpx.GPXTrack()
    OutputGPX.tracks.append(GPXTrack)
    # Create segment
    GPXSegment = gpxpy.gpx.GPXTrackSegment()
    GPXTrack.segments.append(GPXSegment)

    return OutputGPX


# Format string for writung split to csv
def GetCSVFormat():
    return '%s,%s,%s,%.0f,%s,%.0f,%.2f,%02d:%02d\n'


# Function does nearly all the work - processes a single gpx file
# Generates filtered gpx, split csv and add row of metadata
def process_gpx(activity_id, gpx):
    # Variables
    PointCount = 0
    PreviousCoord = (0.0, 0.0)
    StartCoord = None
    incremental_distance = 0
    TotalDistance = 0
    PreviousTime = 0
    TotalTime = timedelta(0, 0, 0)
    #    SplitTime = 0
    StartTime = None
    SplitDistance = 0
    PointsWritten = 0
    MaxDistance = 0
    SplitCSV = 'Date,Time,Split Time,Split Distance,Total Time,Total Distance,Pace,Pace(m:s)\n'

    # Open input File
    #    GPXFile = open(InputFile, 'r')
    InputGPX = gpxpy.parse(gpx)

    # GPX output
    OutputGPX = set_up_gpx()

    # Parse file to extract data
    for track in InputGPX.tracks:
        for segment in track.segments:
            for point in segment.points:
                PointCount += 1
                if PointCount > 1:
                    # Position and incremental distance
                    current_coord = (point.latitude, point.longitude)
                    incremental_distance = distance(current_coord, PreviousCoord).m
                    SplitDistance += incremental_distance
                    TotalDistance += incremental_distance
                    separation += incremental_distance
                    # Straight line distance from start point
                    Distance = distance(StartCoord, current_coord).m
                    if Distance > MaxDistance:
                        MaxDistance = Distance
                        FarthestCoord = current_coord
                    # Time    
                    TotalTime = point.time - StartTime
                    SplitTime += point.time - PreviousTime

                else:
                    # First time just set things up
                    separation = 0
                    SplitDistance = 0
                    StartTime = point.time
                    local_start_time = time.localtime(point.time.timestamp())
                    StartCoord = (point.latitude, point.longitude)
                    SplitTime = timedelta(0, 0, 0)

                PreviousCoord = (point.latitude, point.longitude)
                PreviousTime = point.time

                if separation >= MINPOINTSEPARATION:
                    # Add to track
                    add_gps_point(OutputGPX, point)
                    PointsWritten += 1
                    # Reset for next split
                    separation = 0

                if SplitDistance > SPLIT:
                    # Write split record to csv
                    # Calculate minutes per mile
                    Pace = SplitTime.seconds / 60 * MILE / SPLIT
                    # Add to csv. Pace output as decimal minutes and MM:SS
                    local_time = time.localtime(point.time.timestamp())
                    SplitCSV += GetCSVFormat() % (time.strftime('%Y-%m-%d', local_time),
                                                  time.strftime('%H:%M:%S', local_time),
                                                  SplitTime,
                                                  SplitDistance,
                                                  TotalTime,
                                                  TotalDistance,
                                                  Pace,
                                                  int(Pace), (Pace % 1 * 60))
                    # Reset for next split - don't set distance to 0 to avoid cumulative errors
                    SplitDistance -= SPLIT
                    SplitTime = timedelta(0, 0, 0)
                    PreviousTime = point.time

    #                EndTime = point.time

    # Sometimes get an empty file
    if PointsWritten != 0:
        # Path / filename for gpx and split csv
        Activity = get_activity_type(TotalDistance, TotalTime.seconds)
        location = get_locality_string(StartCoord, PreviousCoord, FarthestCoord)
        OutputFileName = '%s%s_%s_%dMile_%s' % (get_output_path(Activity, StartTime.strftime('%Y')),
                                                Activity,
                                                time.strftime('%Y-%m-%d_%H%M', local_start_time),
                                                (TotalDistance / MILE),
                                                location)
        # Write gpx track
        OutputGPXFile = open(OutputFileName + '.gpx', 'w')
        OutputGPXFile.write(OutputGPX.to_xml())
        OutputGPXFile.close()

        # Write split csv data only for run and cycle
        if Activity == 'Run' or Activity == 'Cycle':
            OutputGPXFile = open(OutputFileName + '.csv', 'w')
            OutputGPXFile.write(SplitCSV)
            OutputGPXFile.close()

        # Write metadata to csv
        MetaDataCSV.write('%s,%s,%s,%s,%d,%s,%s\n' % (time.strftime('%Y-%m-%d', local_start_time), time.strftime('%H:%M',local_start_time),
                                                  Activity,
                                                  'activity_%d' % activity_id,
                                                  TotalDistance,
                                                  TotalTime,
                                                  location))
        print('%s trackpoints written to %s' % (PointsWritten, OutputFileName))

    return


MetaDataCSV = OpenMetaDataCSV()

activities = 0
with GarminClient(garmincredential.username, garmincredential.password) as client:
    # By default download last five activities
    ids = client.list_activities(5)
    for activity_id in ids:
        output_file = '%s/Import/Raw/activity_%d.gpx' % (get_output_path(), activity_id[0])
#        print(output_file)

        # Only save and process if file not already saved from previous download
        if os.path.isfile(output_file):
            print("activity_%d already downloaded" % activity_id[0])
        else:
            # Download and process the gpx file
            gpx = client.get_activity_gpx(activity_id[0])
            process_gpx(activity_id[0], gpx)
            # Save it
            raw_gpx_file = open(output_file, 'w')
            raw_gpx_file.write(gpx)
            raw_gpx_file.close()
#            print('Saved activity_%d.gpx' % (activity_id[0]))
            activities += 1


MetaDataCSV.close()
print('%d files processed' % activities)
