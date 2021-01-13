'''
Created on 9 Jan 2021

@author: lawrence
'''
import gpxpy
import gpxpy.gpx
import geopy
from geopy.distance import distance
import datetime
import os

# Constants to decide frequency of data output
SPLIT = 5

# Input / output files
Path = '/Users/lawrence/Downloads/'
InputFile = Path + 'activity_5824501437.gpx'
# Temporary output File - don't know real name yet
TempFileName = Path + 'gpxtocsv-temp.gpx'

# Other variables
PointCount = 0
PreviousCoord = (0.0,0.0)
IncrementalDistance = 0
TotalDistance = 0
PreviousTime = 0
TotalTime = 0
StartTime = datetime.time(0, 0, 0)
SplitDistance = 0
LinesWritten = 0

# Open Source File
GPXFile = open(InputFile, 'r')
InputGPX = gpxpy.parse(GPXFile)

# GPX output file
gpx = gpxpy.gpx.GPX()
# Create first track in our GPX:
gpx_track = gpxpy.gpx.GPXTrack()
gpx.tracks.append(gpx_track)
# Create first segment in our GPX track:
gpx_segment = gpxpy.gpx.GPXTrackSegment()
gpx_track.segments.append(gpx_segment)

# Open temp output file and write header
# OutputFile = open(TempFileName, 'w')
# OutputFile.write(Header) 

# Parse file to extract data
for track in InputGPX.tracks:
    for segment in track.segments:
        for point in segment.points:
            PointCount += 1
            if PointCount > 1:
                # Position and distance
                CurrentCoord = (point.latitude, point.longitude)
                IncrementalDistance = distance (CurrentCoord, PreviousCoord).m
                SplitDistance += IncrementalDistance
                TotalDistance += IncrementalDistance
                TotalTime = point.time - StartTime

            else:
                # First time just set things up
                SplitDistance = 0
                StartTime = point.time
                
            PreviousCoord = (point.latitude, point.longitude)
            
            if SplitDistance >= SPLIT:
                # Write to gpx 
                gpx_segment.points.append(point)
#                print(s)
#                OutputFile.write(s)
                LinesWritten += 1
                # Reset for next split
                SplitDistance = 0

            EndTime = point.time
            
# OutputFile.close()

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

OutputFileName = '%s%s_%s_%dMile.gpx' % (Path, Activity, StartTime.strftime('%Y-%m-%d_%H%M'), (TotalDistance / MILE))
# If output file already exists delete it
if os.path.isfile(OutputFileName):
    os.remove(OutputFileName)
# Rename temporary file
# os.rename(TempFileName, OutputFileName)

print('Created GPX:', gpx.to_xml())


print('%d lines written to %s' % (LinesWritten, OutputFileName))

