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
from geopy.geocoders import Nominatim
import datetime
import os
import subprocess
import json

# Constants to decide frequency of data output
MILE = 1609
SPLIT = 5
# Format string for OpenStreetMap request, zoom level = suburb
OSMRequest = "https://nominatim.openstreetmap.org/reverse?lat=%f&lon=%f&zoom=14&format=json"


# Works out activity from avaerage pace (min/mile)
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
    StartTime = datetime.time(0, 0, 0)
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
                    IncrementalDistance = distance (CurrentCoord, PreviousCoord).m
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

                if SplitDistance >= SPLIT:
                    # Add to track
                    AddGPSPoint(GPXSegment, point)
                    PointsWritten += 1
                    # Reset for next split
                    SplitDistance = 0

                EndTime = point.time


    # Now work out what we are calling output file
    # Start/end - remove any spaces
    StartTown = GetTown(StartCoord[0], StartCoord[1]).replace(' ','')
    EndTown = GetTown(PreviousCoord[0],PreviousCoord[1]).replace(' ','')
    FarthestTown = GetTown(FarthestCoord[0],FarthestCoord[1]).replace(' ','')
#    print('Start: %s, End: %s, Farthest: %s' % (StartTown, EndTown, FarthestTown))
    # Might have been circular, in which case use farthest
    if StartTown == EndTown:
        EndTown = FarthestTown

    # Activity Type
    Activity = GetActvityType(TotalDistance, TotalTime.seconds)
    # Write track to file - output directory
    OutputFileName = '%sOutput/%s_%s_%dMile_%s%s.gpx' % (Path, Activity, StartTime.strftime('%Y-%m-%d_%H%M'), (TotalDistance / MILE), StartTown, EndTown)
    OutputGPXFile = open(OutputFileName, 'w')
    OutputGPXFile.write(OutputGPX.to_xml())
    OutputGPXFile.close()

    #Metadata
    print('Distance travelled: %dm, max distance from start: %dm' % (TotalDistance, MaxDistance))
    print('%s trackpoints written %s' % (PointsWritten, OutputFileName))

    return
# End of ParseGPX


# Input dir - os dependent
if os.name == 'nt':
    Path = "C:\\Users\\Lawrence\\Downloads\\"
else:
    Path = "/Users/lawrence/Documents/GPX/Raw/"


# Iterate over every gpx file in dir
FilesProcessed = 0
for entry in os.scandir(Path):
    if (entry.path.endswith(".gpx")):
        print('Processing: %s' % entry.path)
        ParseGPX(entry.path)
        FilesProcessed += 1

print('%d files processed' % FilesProcessed)





