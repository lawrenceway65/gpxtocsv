import csv
import pandas
import gpxpy
from geopy.distance import distance
import glob
import config


# hill_db_file = "/Users/lawrence/Downloads/DoBIH_v17_3.csv"
subdir = "2018"
gpxcsv_filename = "/Users/lawrence/Documents/GPSData/Activities/Hike/Test/gpx.csv"
# Approx 30m lat/lon
margin = 0.0003

hill_db_file = config.local_path + "HillList\\DoBIH_v17_3.csv"
path = config.local_path + "Activities\\Hike\\" + subdir
csv_filename = config.local_path + "Activities\\Hike\\" + subdir + "\\Munros_" + subdir + ".csv"

df = pandas.read_csv(hill_db_file)
headers = df.columns

class Stats:
    def __init__(self):
        self.munros = 0
        self.tops = 0
        self.other = 0
        self.dups = 0
        self.files = 0

    def add_munro(self):
        self.munros += 1

    def add_top(self):
        self.tops += 1

    def add_dup(self):
        self.dups += 1

    def add_file(self):
        self.files += 1

    def output_total(self):
        print("%d files analysed, %d Munros, %d Munro Tops, %d Other Tops, %d Duplicates" % (self.files,
                                                                                             self.munros,
                                                                                             self.tops,
                                                                                             self.other,
                                                                                             self.dups))


def calculate_distance(lat1, long1, lat2, long2):
    """Wrapper for distance calculation
    Pass in gps points, return separation
    """
    coord1 = (lat1, long1)
    coord2 = (lat2, long2)

    return distance(coord1, coord2).meters


def analyse_track(gpx_file, csv_writer, stat_counter):

    with open(gpx_file, 'r') as file:
        gpx_data = file.read()
        input_gpx = gpxpy.parse(gpx_data)

        hill_number = 0
        min_summit_distance = 1000
        near_summit = False

        # Check if any summits in areas of track
        min_lat = 90.0
        max_lat = -90.0
        min_long = 180.0
        max_long = -180.0

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
        filtered_list = df[(df['Latitude'] >= min_lat - margin) &
                           (df['Latitude'] <= max_lat + margin) &
                           (df['Longitude'] >= min_long - margin) &
                           (df['Longitude'] <= max_long + margin)]
        if len(filtered_list.index) == 0:
            # No summits
            print("Min Lat: %f Max Lat: %f Min long: %f Max Long: %f" % (min_lat, max_lat, min_long, max_long))
            return

        summits = []

        for track in input_gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    if not near_summit:
                        # Filter hill data
                        filtered_list = df[(df['Latitude'] > point.latitude - margin) &
                                           (df['Latitude'] < point.latitude + margin) &
                                           (df['Longitude'] > point.longitude - margin) &
                                           (df['Longitude'] < point.longitude + margin)]

                    # Should be at most one match
                    if len(filtered_list.index) == 1:
                        hill_number = filtered_list['Name'].item()
                        near_summit = True
                        summit_distance = calculate_distance(point.latitude,
                                                             point.longitude,
                                                             filtered_list['Latitude'].item(),
                                                             filtered_list['Longitude'].item())
#                        print("Hill: %s Summit dist: %d" % (hill_number, summit_distance))
                        if summit_distance < min_summit_distance:
                            min_summit_distance = summit_distance
                            nearest_point = point
                        elif summit_distance > 50:
                            # We have moved away from summit, so need to record
                            # First check we haven't already been to this summit on this track
                            dup = False
                            for i in summits:
                                if i == hill_number:
                                    dup = True
                                    print("Duplicate: %s. Height: %s Dist: %d" % (filtered_list['Name'].item(),
                                                                                    filtered_list['Metres'].item(),
                                                                                    min_summit_distance))
                                    stat_counter.add_dup()
                                    break
                            if not dup:
                                # It's a new summit so save details
                                is_munro = False
                                if filtered_list['M'].item() == 1:
                                    is_munro = True
                                    summit_type = "Munro"
                                    stat_counter.add_munro()
                                elif filtered_list['MT'].item() == 1:
                                    is_munro = True
                                    summit_type = "Munro Top"
                                    stat_counter.add_top()
                                else:
                                    summit_type = "Other Top"
                                    stat_counter.other += 1

                                print("%s: %s. Height: %d Dist: %d" % (summit_type,
                                                                       filtered_list['Name'].item(),
                                                                       filtered_list['Metres'].item(),
                                                                       min_summit_distance))
                                csv_writer.writerow({'Type': summit_type,
                                                     'Name': filtered_list['Name'].item(),
                                                     'Height': filtered_list['Metres'].item(),
                                                     'Grid Ref': filtered_list['GridrefXY'].item(),
                                                     'Region': filtered_list['Region'].item(),
                                                     'Datetime': nearest_point.time,
                                                     'GPXFile': gpx_file})

                            # Reset to find the next summit
                            summits.append(hill_number)
                            min_summit_distance = 1000
                            near_summit = False

                    elif len(filtered_list.index) > 1:
                        # Should not get here
                        print("More than one match - should not be possible!")

    return


output_csv = open(csv_filename, 'w', newline='')
fieldnames = ['Type', 'Name', 'Height', 'Grid Ref', 'Region', 'Datetime', 'GPXFile']
writer = csv.DictWriter(output_csv, fieldnames=fieldnames)
writer.writeheader()

counter = Stats()

for filename in glob.iglob(path + '**/*.gpx', recursive=True):
    print(filename)
    counter.add_file()
    analyse_track(filename, writer, counter)

output_csv.close()
counter.output_total()
