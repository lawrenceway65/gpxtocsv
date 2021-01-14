'''
Created on 9 Jan 2021

@author: lawrence
'''

# Parses gpx file and creates new file. Any points less than 5m from previous point are excluded.
# Temperature data also excluded.
# New gpx named meaningfull, by actvity type, date, tine and distance,
# Creates much smaller gpx that can be uploaded to outddorsgb  

import gpxpy
import gpxpy.gpx
import geopy
from geopy.distance import distance
import datetime
import os

# Constants to decide frequency of data output
MILE = 1609
SPLIT = 5


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
                    Distance = distance (StartCoord, CurrentCoord).m
                    if Distance > MaxDistance:
                        MaxDistance = Distance
                    # Time    
                    TotalTime = point.time - StartTime
    
                else:
                    # First time just set things up
                    SplitDistance = 0
                    StartTime = point.time
                    StartCoord = (point.latitude, point.longitude)
                    
                PreviousCoord = (point.latitude, point.longitude)
                
                if SplitDistance >= SPLIT:
                    # Write to gpx 
                    NewPoint = gpxpy.gpx.GPXTrackPoint()
                    NewPoint.latitude = point.latitude
                    NewPoint.longitude = point.longitude
                    NewPoint.time = point.time
                    NewPoint.elevation = point.elevation
                    GPXSegment.points.append(NewPoint)
    #                print(s)
    #                OutputFile.write(s)
                    PointsWritten += 1
                    # Reset for next split
                    SplitDistance = 0
    
                EndTime = point.time
                

    # Now work out what we are calling output file
    AveragePace = TotalTime.seconds / 60 * MILE / TotalDistance
    if AveragePace > 12:
        Activity = 'Hike'
    elif AveragePace > 7:
        Activity = 'Run'
    elif AveragePace > 2.5:
        Activity = 'Cycle'
    else:
        Activity = 'Unknown'

    # Write track to file - output directory
    OutputFileName = '%sOutput/%s_%s_%dMile.gpx' % (Path, Activity, StartTime.strftime('%Y-%m-%d_%H%M'), (TotalDistance / MILE))
    OutputGPXFile = open(OutputFileName, 'w')
    OutputGPXFile.write(OutputGPX.to_xml())
    OutputGPXFile.close()
    
    #Metadata
    print('Distance travelled: %dm, max distance from start: %dm' % (TotalDistance, MaxDistance))
    print('%s trackpoints written %s' % (PointsWritten, OutputFileName))
    
    return    
# End of ParseGPX


# Input dir
Path = '/Users/lawrence/Documents/GPX/Raw/'
# Iterate over every gpx file in dir
for entry in os.scandir(Path):
    if (entry.path.endswith(".gpx")):
        print(entry.path)
        ParseGPX(entry.path) 





