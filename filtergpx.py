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
import os
import subprocess
import json
import shutil
from garminget import GarminClient
import garmincredential

# Constants and definitions
# Meters in a mile
MILE = 1609
SPLIT = 250
# Only write points farther apart than this (meters)
MINPOINTSEPARATION = 5


def GetInputPath():
    """Return path for input data."""
    if os.name == 'nt':
        return "C:\\Users\\Lawrence\\Downloads\\"
    else:
        return "/Users/lawrence/Downloads/"


def GetOutputPath(activity='', year=0):
    """
    Get path for output files.
    Creates any folders that don't already exist.
    Just return root path if no params provided
    """
    if os.name == 'nt':
        path = "C:\\Users\\Lawrence\\Documents\\GPX\\"
        separator = '\\'
    else:
        path = "/Users/lawrence/Documents/GPX/"
        separator = '/'

    if activity != '':
        # Just create these if they don't exist
        if not os.path.isdir(path + activity):
            os.mkdir(path + activity)

        path += activity + separator + year + separator
        if not os.path.isdir(path):
            os.mkdir(path)

    return path


def GetActvityType(distance, time):
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


def AddGPSPoint(gpx_track, point):
    """Create new point and add to track."""
    new_point = gpxpy.gpx.GPXTrackPoint()
    new_point.latitude = point.latitude
    new_point.longitude = point.longitude
    new_point.time = point.time
    new_point.elevation = point.elevation
    gpx_track.tracks[0].segments[0].points.append(new_point)

    return


def GetTown(latitude, longitude):
    """Get location from co-ordinates. Use Open Street Map."""
    # Format string for OpenStreetMap request, zoom level 14 = suburb
    osm_request = "https://nominatim.openstreetmap.org/reverse?lat=%f&lon=%f&zoom=14&format=json"
    result = subprocess.check_output(['curl', osm_request % (latitude, longitude)]).decode("utf-8")
    #    print(OSMRequest % (Latitude, Longitude))
    result_json = json.loads(result)
    town = result_json['display_name']

    # Return first item in display name
    return town[:town.find(',')]


def GetLocation(start_coord, end_coord, farthest_coord):
    """Get location string for filename"""
    # Start/end - remove any spaces, don't want them in filename
    start_town = GetTown(start_coord[0], start_coord[1]).replace(' ', '')
    end_town = GetTown(end_coord[0], end_coord[1]).replace(' ', '')
    farthest_town = GetTown(farthest_coord[0], farthest_coord[1]).replace(' ', '')
#    print('Start: %s, End: %s, Farthest: %s' % (start_town, end_town, farthest_town))

    # Horrible hack
    if start_town == 'NewHaw':
        start_town = 'Addlestone'

    # Might have been circular, in which case use farthest, avoid repetition if all the same
    if start_town == end_town:
        if end_town == farthest_town:
            return start_town
        else:
            return start_town + farthest_town
    else:
        return start_town + end_town


# Open metadata csv file and write header
def OpenMetaDataCSV():
    # Filename ProcessGPX_YY-MM-DD_HHMM.csv
    MetaDataCSV = open(
        '%sRaw/Output/ProcessGPX_%s.csv' % (GetOutputPath(), datetime.now().strftime("%d-%m-%Y_%H%M")),
        'w')
    MetaDataCSV.write('Date,Time,Activity,Garmin ID,Distance,Duration,Location\n')

    return MetaDataCSV


# Setup GPX - always one track and one segment
def SetUpGPX():
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
def ParseGPX(activity_id, gpx):
    # Variables
    PointCount = 0
    PreviousCoord = (0.0, 0.0)
    StartCoord = None
    incremental_distance = 0
    TotalDistance = 0
    PreviousTime = 0
    TotalTime = 0
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
    OutputGPX = SetUpGPX()

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
                    StartCoord = (point.latitude, point.longitude)
                    SplitTime = timedelta(0, 0, 0)

                PreviousCoord = (point.latitude, point.longitude)
                PreviousTime = point.time

                if separation >= MINPOINTSEPARATION:
                    # Add to track
                    AddGPSPoint(OutputGPX, point)
                    PointsWritten += 1
                    # Reset for next split
                    separation = 0

                if SplitDistance > SPLIT:
                    # Write split record to csv
                    # Calculate minutes per mile
                    Pace = SplitTime.seconds / 60 * MILE / SPLIT
                    # Add to csv. Pace output as decimal minutes and MM:SS
                    SplitCSV += GetCSVFormat() % (point.time.strftime('%Y-%m-%d'),
                                                  point.time.strftime('%H:%M:%S'),
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

    # Path / filename for gpx and split csv
    Activity = GetActvityType(TotalDistance, TotalTime.seconds)
    OutputFileName = '%s%s_%s_%dMile_%s' % (GetOutputPath(Activity, StartTime.strftime('%Y')),
                                            Activity,
                                            StartTime.strftime('%Y-%m-%d_%H%M'),
                                            (TotalDistance / MILE),
                                            GetLocation(StartCoord, PreviousCoord, FarthestCoord))
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
    MetaDataCSV.write('%s,%s,%s,%s,%d,%s,%s\n' % (StartTime.strftime('%Y-%m-%d'), StartTime.strftime('%H:%m'),
                                                  Activity,
                                                  'activity_%d' % activity_id,
                                                  TotalDistance,
                                                  TotalTime,
                                                  GetTown(StartCoord[0], StartCoord[1])))
    print('%s trackpoints written %s' % (PointsWritten, OutputFileName))

    return


MetaDataCSV = OpenMetaDataCSV()

activities = 0
with GarminClient(garmincredential.username, garmincredential.password) as client:
    # By default download last five activities
    ids = client.list_activities(5)
    for activity_id in ids:
        gpx = client.get_activity_gpx(activity_id[0])
        # Only save and process if file not already saved from previous download
        output_file = '%s/Raw/activity_%d.gpx' % (GetOutputPath(), activity_id[0])
        if not os.path.isfile(output_file):
            raw_gpx_file = open(output_file, 'w')
            raw_gpx_file.write(gpx)
            raw_gpx_file.close()
            print('Saved activity_%d.gpx' % (activity_id[0]))
            ParseGPX(activity_id[0], gpx)
            activities += 1


MetaDataCSV.close()
print('%d files processed' % activities)
