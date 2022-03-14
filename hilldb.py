import csv
import pandas
import gpxpy
from geopy.distance import distance
import os
import glob


hill_db_file = "/Users/lawrence/Downloads/DoBIH_v17_3.csv"
# gpx_file = "/Users/lawrence/Documents/GPSData/Activities/Hike/2022/Hike_2022-02-27_0907_13Mile_HighlandAlba-Scotland.gpx"
path = "/Users/lawrence/Documents/GPSData/Activities/Hike/"
csv_filename = "/Users/lawrence/Documents/GPSData/Activities/Hike/Munros.csv"
df = pandas.read_csv(hill_db_file)

def calculate_distance(lat1, long1, lat2, long2):
    """Wrapper for distance calculation
    Pass in gps points, return separation
    """
    coord1 = (lat1, long1)
    coord2 = (lat2, long2)

    return distance(coord1, coord2).meters


def analyse_track(gpx_file, csv_writer):

    with open(gpx_file, 'r') as file:
        gpx_data = file.read()
        input_gpx = gpxpy.parse(gpx_data)

    #    print(list(df.columns))
    #    print(df['Latitude'].dtypes)

        match_index = 0

        for track in input_gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    lat = point.latitude
                    # Find lat in hill db data
                    index = abs(df['Latitude'] - lat).idxmin()
                    min_distance = calculate_distance(lat, point.longitude, df['Latitude'][index], df['Longitude'][index])
                    if min_distance < 5:
                        # Match
                        if match_index != index:
                            match_index = index
                            # Check classification
                            is_munro = False
                            if df['M'][index] == 1:
                                is_munro = True
                                type = "Munro"
                            elif df['MT'][index] == 1:
                                is_munro = True
                                type = "Munro Top"
                            if is_munro:
                                print("%s: %s. Height: %d. Time: %s" % (type, df['Name'][index], df['Metres'][index], point.time))
                                csv_writer.writerow({'Type': type,
                                                 'Name': df['Name'][index],
                                                 'Height': df['Metres'][index],
                                                 'Region': df['Region'][index],
                                                 'Datetime': point.time,
                                                 'GPXFile': gpx_file})


output_csv = open(csv_filename, 'w', newline='')
fieldnames = ['Type', 'Name', 'Height', 'Region', 'Datetime', 'GPXFile']
writer = csv.DictWriter(output_csv, fieldnames=fieldnames)
writer.writeheader()

file_count = 0
for filename in glob.iglob(path + '**/*.gpx', recursive=True):
    print(filename)
    file_count += 1
    analyse_track(filename, writer)

output_csv.close()

print("%d files analysed" % file_count)
