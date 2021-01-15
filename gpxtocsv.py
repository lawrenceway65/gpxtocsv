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
MILE = 1609
HALF_MILE = MILE / 2
QUARTER_MILE = MILE / 4
# A record will be output every SPLIT distance (meters) 
SPLIT = 250 

# Input / output files
Path = '/Users/lawrence/Downloads/'
InputFile = Path + 'activity_6061903291.gpx'
# Temporary output File - don't know real name yet
TempFileName = Path + 'gpxtocsv-temp.csv'
# CSV header
Header = 'Date,Time,Split Time,Split Distance,Total Time,Total Distance,Pace,Pace(m:s)\n'
# Formatting for csv data output
FormatString = '%s,%s,%s,%.0f,%s,%.0f,%.2f,%02d:%02d\n' 

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
gpx = gpxpy.parse(GPXFile)

# Open temp output file and write header
OutputFile = open(TempFileName, 'w')
OutputFile.write(Header) 

# Parse file to extract data
for track in gpx.tracks:
    for segment in track.segments:
        for point in segment.points:
            PointCount += 1
            if PointCount > 1:
                # Position and distance
                CurrentCoord = (point.latitude, point.longitude)
                IncrementalDistance = distance (CurrentCoord, PreviousCoord).m
                SplitDistance += IncrementalDistance
                TotalDistance += IncrementalDistance
                # Time
                SplitTime += point.time - PreviousTime
                TotalTime = point.time - StartTime

            else:
                # First time just set things up
                StartTime = point.time
                SplitDistance = 0
                SplitTime = datetime.timedelta(0, 0, 0)
                
            PreviousCoord = (point.latitude, point.longitude)
            PreviousTime = point.time
            
            if SplitDistance >= SPLIT:
                # Calculate minutes per mile
                Pace = SplitTime.seconds / 60 * MILE / SPLIT
                # Write to csv. Pace output as decimal minutes and MM:SS 
                s = FormatString % (point.time.strftime('%Y-%m-%d'),
                                    point.time.strftime('%H:%M:%S'), 
                                    SplitTime, 
                                    SplitDistance, 
                                    TotalTime, 
                                    TotalDistance, 
                                    Pace, 
                                    int(Pace), (Pace % 1 * 60))
#                print(s)
                OutputFile.write(s)
                LinesWritten += 1
                # Reset for next split
                SplitDistance -= SPLIT
                SplitTime = datetime.timedelta(0, 0, 0)
#            print('Point: ', PointCount, ' ', DateTime.strftime('%Y-%m-%d'), ', ', IncrementalTime, ', ', TotalTime, ', ' "%.1f" % IncrementalDistance, 'm, ', "%.0f" % TotalDistance, 'm' )

OutputFile.close()

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

OutputFileName = '%s%s_%s_%dMile.csv' % (Path, Activity, StartTime.strftime('%Y-%m-%d_%H%M'), (TotalDistance / MILE))
# If output file already exists delete it
if os.path.isfile(OutputFileName):
    os.remove(OutputFileName)
# Rename temporary file
os.rename(TempFileName, OutputFileName)

print('%d lines written to %s' % (LinesWritten, OutputFileName))
# print('Distance: %.2fkm, Time %s' % ((TotalDistance/1000), TotalTime))

