'''
Created on 9 Jan 2021

@author: lawrence
'''
import gpxpy
import gpxpy.gpx
import geopy
from geopy.distance import distance
import datetime

# Constants to decide frequency of data output (meters)
MILE = 1609
HALF_MILE = MILE / 2
QUARTER_MILE = MILE / 4
 
SPLIT = 100 

# Input / output files
InputFile = '/Users/lawrence/Downloads/activity_6083628856.gpx'
OutputFileName = '/Users/lawrence/Downloads/activity_6083628856.csv'
Header = 'Date,Time,Split Time,Split Distance,Total Time,Total Distance\n'

# Other variables
PointCount = 0
PreviousCoord = (0.0,0.0)
IncrementalDistance = 0
TotalDistance = 0
PreviousTime = 0
TotalTime = 0
StartTime = datetime.time(0, 0, 0)
SplitDistance = 0
SplitTime = datetime.timedelta(0, 0, 0)
LinesWritten = 0


# Open Source File
gpx_file = open('/Users/lawrence/Downloads/activity_6083628856.gpx', 'r')
gpx = gpxpy.parse(gpx_file)

# Open Output File
OutputFile = open(OutputFileName, 'w')
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
                DateTime = point.time
                IncrementalTime = point.time - PreviousTime
                SplitTime += IncrementalTime
                TotalTime = point.time - StartTime
            else:
                # First time just set things up
                StartTime = point.time
                SplitDistance = 0
                SplitTime = datetime.timedelta(0, 0, 0)
                
            PreviousCoord = (point.latitude, point.longitude)
            PreviousTime = point.time
            
            if SplitDistance >= SPLIT:
                s = DateTime.strftime('%Y-%m-%d, %H:%M:%S,') + str(SplitTime) + ',%.0f,' % SplitDistance + str(TotalTime) + ',%.0f' % TotalDistance + '\n'
                # print(s)
                OutputFile.write(s)
                SplitDistance -= SPLIT
                SplitTime = datetime.timedelta(0, 0, 0)
                LinesWritten += 1
#            print('Point: ', PointCount, ' ', DateTime.strftime('%Y-%m-%d'), ', ', IncrementalTime, ', ', TotalTime, ', ' "%.1f" % IncrementalDistance, 'm, ', "%.0f" % TotalDistance, 'm' )

print('Lines written: ', LinesWritten, 'Distance: ', "%.2fkm" % (TotalDistance/1000), 'Time: ', TotalTime)

OutputFile.close()