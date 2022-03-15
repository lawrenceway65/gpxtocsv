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
gpxcsv_filename = "/Users/lawrence/Documents/GPSData/Activities/Hike/Test/gpx.csv"

df = pandas.read_csv(hill_db_file)
headers = df.columns

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

        hill_number = 0

        for track in input_gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    # gpx_writer.writerow({'Lat': point.latitude,
                    #                     'Long': point.longitude,
                    #                     'Elev': point.elevation,
                    #                     'Datetime': point.time})
                    lat = point.latitude
                    # Filter hill data
                    filtered_list = df[(df['Latitude'] > point.latitude - 0.0002) &
                                       (df['Latitude'] < point.latitude + 0.0002) &
                                       (df['Longitude'] > point.longitude - 0.0002) &
                                       (df['Longitude'] < point.longitude + 0.0002)]

                    # Should be only one match
                    if len(filtered_list.index) == 1:
                        if hill_number != filtered_list['Number'].item():
                            hill_number = filtered_list['Number'].item()
                            # Check classification
                            is_munro = False
                            if filtered_list['M'].item() == 1:
                                is_munro = True
                                type = "Munro"
                            elif filtered_list['MT'].item() == 1:
                                is_munro = True
                                type = "Munro Top"
                            if is_munro:
                                print("%s: %s. Height: %d. Time: %s" % (type, filtered_list['Name'].item(), filtered_list['Metres'].item(), point.time))
                                csv_writer.writerow({'Type': type,
                                                 'Name': filtered_list['Name'].item(),
                                                 'Height': filtered_list['Metres'].item(),
                                                 'Region': filtered_list['Region'].item(),
                                                 'Datetime': point.time,
                                                 'GPXFile': gpx_file})
                    elif len(filtered_list.index) > 1:
                        # Should not get here
                        print("More than one match - should not be possible!")


output_csv = open(csv_filename, 'w', newline='')
fieldnames = ['Type', 'Name', 'Height', 'Region', 'Datetime', 'GPXFile']
writer = csv.DictWriter(output_csv, fieldnames=fieldnames)
writer.writeheader()

# gpx_csv = open(gpxcsv_filename, 'w', newline='')
# fieldnames = ['Lat', 'Long', 'Elev', 'Datetime']
# gpxwriter = csv.DictWriter(gpx_csv, fieldnames=fieldnames)
# gpxwriter.writeheader()


# rows = len(df.index)
# print(df.shape)
# df2 = df[(df['Number'] > 500) & (df['Number'] <1000)]
# # rows = len(df2.index)
# print(df2.shape)
# print(df2.info)

file_count = 0
for filename in glob.iglob(path + '**/*.gpx', recursive=True):
    print(filename)
    file_count += 1
    analyse_track(filename, writer)

output_csv.close()
# gpx_csv.close()

print("%d files analysed" % file_count)
