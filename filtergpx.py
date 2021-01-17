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

# Constants and definitions
# Meters in a mile
MILE = 1609
SPLIT = 250
# Only write points farther apart than this (meters)
MINPOINTSEPARATION = 5

# Format string for OpenStreetMap request, zoom level = suburb
OSMRequest = "https://nominatim.openstreetmap.org/reverse?lat=%f&lon=%f&zoom=14&format=json"

# Input dir - os dependent
def GetInputPath():
    if os.name == 'nt':
        return "C:\\Users\\Lawrence\\Downloads\\"
    else:
        return "/Users/lawrence/Documents/GPX/Raw/"

# Output dir of format <activity>/<year>
# Creates folders if they don't exist
def GetOutputPath(Activity, Year):
    if os.name == 'nt':
        Path = "C:\\Users\\Lawrence\\Documents\\GPX\\"
        Separator = '\\'
    else:
        Path = "/Users/lawrence/Documents/GPX/"
        Separator = '/'

    # Just create these if they don't exist
    if not os.path.isdir(Path + Activity):
        os.mkdir(Path + Activity)

    FullPath = Path + Activity + Separator + Year + Separator
    if not os.path.isdir(FullPath):
        os.mkdir(FullPath)

    return FullPath

# Works out activity from average pace (min/mile)
# Distance in meters, time in seconds
def GetActvityType(Distance, Time):
    AveragePace = Time / 60 * MILE / Distance
    if AveragePace > 12:
        Activity = 'Hike'
    elif AveragePace > 7:
        Activity = 'Run'
    elif AveragePace > 2.5:
        Activity = 'Cycle'
    else:
        Activity = 'Unknown'

    return Activity

# Add new point (equals passed point)
def AddGPSPoint(GPXTrack, point):
    NewPoint = gpxpy.gpx.GPXTrackPoint()
    NewPoint.latitude = point.latitude
    NewPoint.longitude = point.longitude
    NewPoint.time = point.time
    NewPoint.elevation = point.elevation
    GPXTrack.tracks[0].segments[0].points.append(NewPoint)

    return

# Gets town/city from lat/long
# Uses Open Street Map api
# Uses first item in display name - should be generic
def GetTown(Latitude, Longitude):
    Result = subprocess.check_output(['curl', OSMRequest % (Latitude, Longitude)]).decode("utf-8")
#    print(OSMRequest % (Latitude, Longitude))
    ResultJSON = json.loads(Result)
    DisplayName = ResultJSON['display_name']

    return DisplayName[:DisplayName.find(',')]

# Get location string for file name
def GetLocation(StartCoord, EndCoord, FarthestCoord):
    # Start/end - remove any spaces, don't want them in filename
    StartTown = GetTown(StartCoord[0], StartCoord[1]).replace(' ', '')
    EndTown = GetTown(EndCoord[0], EndCoord[1]).replace(' ', '')
    FarthestTown = GetTown(FarthestCoord[0], FarthestCoord[1]).replace(' ', '')
    # print('Start: %s, End: %s, Farthest: %s' % (StartTown, EndTown, FarthestTown))
    # Might have been circular, in which case use farthest, avoid repetition if all the same
    if StartTown == EndTown:
        if EndTown == FarthestTown:
            return StartTown
        else:
            return StartTown + FarthestTown
    else:
        return StartTown + EndTown

# Open metadata csv file and write header
def OpenMetaDataCSV():
    # Filename ProcessGPX_YY-MM-DD_HHMM.csv
    MetaDataCSV = open('%sOutput/ProcessGPX_%s.csv' % (GetInputPath(), datetime.now().strftime("%d-%m-%Y_%H%M")), 'w')
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
def ParseGPX( InputFile ):

    # Variables
    PointCount = 0
    PreviousCoord = (0.0,0.0)
    StartCoord = None
    IncrementalDistance = 0
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
    GPXFile = open(InputFile, 'r')
    InputGPX = gpxpy.parse(GPXFile)

    # GPX output
    OutputGPX = SetUpGPX()

    # Parse file to extract data
    for track in InputGPX.tracks:
        for segment in track.segments:
            for point in segment.points:
                PointCount += 1
                if PointCount > 1:
                    # Position and incremental distance
                    CurrentCoord = (point.latitude, point.longitude)
                    IncrementalDistance = distance(CurrentCoord, PreviousCoord).m
                    SplitDistance += IncrementalDistance
                    TotalDistance += IncrementalDistance
                    Separation += IncrementalDistance
                    # Straight line distance from start point
                    Distance = distance(StartCoord, CurrentCoord).m
                    if Distance > MaxDistance:
                        MaxDistance = Distance
                        FarthestCoord = CurrentCoord
                    # Time    
                    TotalTime = point.time - StartTime
                    SplitTime += point.time - PreviousTime

                else:
                    # First time just set things up
                    Separation = 0
                    SplitDistance = 0
                    StartTime = point.time
                    StartCoord = (point.latitude, point.longitude)
                    SplitTime = timedelta(0, 0, 0)

                PreviousCoord = (point.latitude, point.longitude)
                PreviousTime = point.time

                if Separation >= MINPOINTSEPARATION:
                    # Add to track
                    AddGPSPoint(OutputGPX, point)
                    PointsWritten += 1
                    # Reset for next split
                    Separation = 0

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

                EndTime = point.time


    # Filename for gpx and split csv - output directory
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

    # Write split csv data
    OutputGPXFile = open(OutputFileName + '.csv', 'w')
    OutputGPXFile.write(SplitCSV)
    OutputGPXFile.close()

    # Write metadata to csv
    MetaDataCSV.write('%s,%s,%s,%s,%d,%s,%s\n' % (StartTime.strftime('%Y-%m-%d'),StartTime.strftime('%H:%m'),
                                                Activity,
                                                InputFile[len(GetInputPath()):-4],
                      TotalDistance,
                      TotalTime,
                      GetTown(StartCoord[0],StartCoord[1])))
    print('%s trackpoints written %s' % (PointsWritten, OutputFileName))

    return
# End of ParseGPX

MetaDataCSV = OpenMetaDataCSV()

# Iterate over every gpx file in dir
FilesProcessed = 0
for entry in os.scandir(GetInputPath()):
    if (entry.path.endswith(".gpx")):
        print('Processing: %s' % entry.path)
        ParseGPX(entry.path)

        # Move file
        #
        # if os.path.isfile(entry.path + '/Processed'):
        #     os.remove(OutputFileName)

        FilesProcessed += 1


MetaDataCSV.close()
print('%d files processed' % FilesProcessed)





