import csv
import pandas
import gpxpy
from geopy.distance import distance
import os
import glob


# hill_db_file = "/Users/lawrence/Downloads/DoBIH_v17_3.csv"
subdir = "2023"
hill_db_file = "D:\\Documents\\GPSData\\HillList\\DoBIH_v17_3.csv"
path = "D:\\Documents\\GPSData\\Activities\\Hike\\" + subdir
csv_filename = "D:\\Documents\\GPSData\\Activities\\Hike\\" + subdir + "\\Munros_" + subdir + ".csv"
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

        hill_number = 0
        min_summit_distance = 1000
        near_summit = False

        # Check if any summits in areas of track
        min_lat = 91.0
        max_lat = 0.0
        min_long = 91.0
        max_long = 0.0

        for track in input_gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    if point.latitude < min_lat:
                        min_lat = point.latitude
                    if point.latitude > max_lat:
                        max_lat = point.latitude
                    if point.longitude < min_long:
                        min_long = point.longitude
                    if point.longitude > max_long:
                        max_long = point.longitude
        filtered_list = df[(df['Latitude'] >= min_lat) &
                           (df['Latitude'] <= max_lat) &
                           (df['Longitude'] >= min_long) &
                           (df['Longitude'] <= max_long)]
        if len(filtered_list.index) == 0:
            # No summits
            return

        for track in input_gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    if not near_summit:
                        # Filter hill data
                        filtered_list = df[(df['Latitude'] > point.latitude - 0.0003) &
                                           (df['Latitude'] < point.latitude + 0.0003) &
                                           (df['Longitude'] > point.longitude - 0.0003) &
                                           (df['Longitude'] < point.longitude + 0.0003)]

                    # Should be at most one match
                    if len(filtered_list.index) == 1:
                        near_summit = True
                        summit_distance = calculate_distance(point.latitude,
                                                             point.longitude,
                                                             filtered_list['Latitude'].item(),
                                                             filtered_list['Longitude'].item())
#                        print(summit_distance)
                        if summit_distance < min_summit_distance:
                            min_summit_distance = summit_distance
                            nearest_point = point
                        elif summit_distance > 50:
                            # We have moved away from summit - record details and reset
                            is_munro = False
                            if filtered_list['M'].item() == 1:
                                is_munro = True
                                type = "Munro"
                            elif filtered_list['MT'].item() == 1:
                                is_munro = True
                                type = "Munro Top"
                            if is_munro:
                                print("%s: %s. Height: %d Time: %s Dist: %d" % (type,
                                                                                filtered_list['Name'].item(),
                                                                                filtered_list['Metres'].item(),
                                                                                nearest_point.time,
                                                                                min_summit_distance))
                                csv_writer.writerow({'Type': type,
                                                     'Name': filtered_list['Name'].item(),
                                                     'Height': filtered_list['Metres'].item(),
                                                     'Grid Ref': filtered_list['GridrefXY'].item(),
                                                     'Region': filtered_list['Region'].item(),
                                                     'Datetime': nearest_point.time,
                                                     'GPXFile': gpx_file})

                            min_summit_distance = 1000
                            near_summit = False

                    elif len(filtered_list.index) > 1:
                        # Should not get here
                        print("More than one match - should not be possible!")


output_csv = open(csv_filename, 'w', newline='')
fieldnames = ['Type', 'Name', 'Height', 'Grid Ref', 'Region', 'Datetime', 'GPXFile']
writer = csv.DictWriter(output_csv, fieldnames=fieldnames)
writer.writeheader()


file_count = 0
for filename in glob.iglob(path + '**/*.gpx', recursive=True):
    print(filename)
    file_count += 1
    analyse_track(filename, writer)

output_csv.close()

print("%d files analysed" % file_count)
