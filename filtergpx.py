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
import datetime
from datetime import datetime
import os
import subprocess
import json

# Constants and definitions
# Meters in a mile
MILE = 1609
SPLIT = 5
# Only write points farther apart than this (meters)
MINPOINTSEPARATION = 5

# Format string for OpenStreetMap request, zoom level = suburb
OSMRequest = "https://nominatim.openstreetmap.org/reverse?lat=%f&lon=%f&zoom=14&format=json"

# MetaDataCSV = None

# Input dir - os dependent
def GetPath():
    if os.name == 'nt':
        return "C:\\Users\\Lawrence\\Downloads\\"
    else:
        return "/Users/lawrence/Documents/GPX/Raw/"

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
def AddGPSPoint(GPXSegment, point):
    NewPoint = gpxpy.gpx.GPXTrackPoint()
    NewPoint.latitude = point.latitude
    NewPoint.longitude = point.longitude
    NewPoint.time = point.time
    NewPoint.elevation = point.elevation
    GPXSegment.points.append(NewPoint)

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
    MetaDataCSV = open('%sOutput/ProcessGPX_%s.csv' % (GetPath(), datetime.now().strftime("%d-%m-%Y_%H%M")), 'w')
    MetaDataCSV.write('Date,Time,Activity,Garmin ID,Distance,Duration,Location\n')

    return MetaDataCSV

# Function does nearly all the work - processes a single file
def ParseGPX( InputFile ):

    # Variables
    PointCount = 0
    PreviousCoord = (0.0,0.0)
    StartCoord = None
    IncrementalDistance = 0
    TotalDistance = 0
    PreviousTime = 0
    TotalTime = 0
    StartTime = None
    SplitDistance = 0
    PointsWritten = 0
    MaxDistance = 0

    # Open input File
    GPXFile = open(InputFile, 'r')
    InputGPX = gpxpy.parse(GPXFile)

    # GPX output
    OutputGPX = gpxpy.gpx.GPX()
    # Create track
    GPXTrack = gpxpy.gpx.GPXTrack()
    OutputGPX.tracks.append(GPXTrack)
    # Create segment
    GPXSegment = gpxpy.gpx.GPXTrackSegment()
    GPXTrack.segments.append(GPXSegment)

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
                    # Straight line distance from start point
                    Distance = distance(StartCoord, CurrentCoord).m
                    if Distance > MaxDistance:
                        MaxDistance = Distance
                        FarthestCoord = CurrentCoord
                    # Time    
                    TotalTime = point.time - StartTime

                else:
                    # First time just set things up
                    SplitDistance = 0
                    StartTime = point.time
                    StartCoord = (point.latitude, point.longitude)

                PreviousCoord = (point.latitude, point.longitude)

                if SplitDistance >= MINPOINTSEPARATION:
                    # Add to track
                    AddGPSPoint(GPXSegment, point)
                    PointsWritten += 1
                    # Reset for next split
                    SplitDistance = 0

                EndTime = point.time


    # Write track to file - output directory
    OutputFileName = '%sOutput/%s_%s_%dMile_%s.gpx' % (GetPath(),
                                                       GetActvityType(TotalDistance, TotalTime.seconds),
                                                       StartTime.strftime('%Y-%m-%d_%H%M'),
                                                       (TotalDistance / MILE),
                                                       GetLocation(StartCoord, PreviousCoord, FarthestCoord))
    OutputGPXFile = open(OutputFileName, 'w')
    OutputGPXFile.write(OutputGPX.to_xml())
    OutputGPXFile.close()

    #Metadata
    MetaDataCSV.write('%s,%s,%s,%s,%d,%s,%s' % (StartTime.strftime('%Y-%m-%d'),StartTime.strftime('%H:%m'),
                                                GetActvityType(TotalDistance, TotalTime.seconds),
                                                InputFile,
                      TotalDistance,
                      TotalTime,
                      GetTown(StartCoord[0],StartCoord[1])))
    print('%s trackpoints written %s' % (PointsWritten, OutputFileName))

    return
# End of ParseGPX

MetaDataCSV = OpenMetaDataCSV()

# Iterate over every gpx file in dir
FilesProcessed = 0
for entry in os.scandir(GetPath()):
    if (entry.path.endswith(".gpx")):
        print('Processing: %s' % entry.path)
        ParseGPX(entry.path)
        FilesProcessed += 1

MetaDataCSV.close()
print('%d files processed' % FilesProcessed)





