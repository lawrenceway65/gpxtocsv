"""Process local files gpx files
Processes all gpx files in a directory.
Uses files name as an id.
"""

import filtergpx
import os
import config
import shutil


root_path = config.local_path
raw_path = root_path + "Import\\Raw"
import_path = root_path + "Import\\FilesIn"
# import_path = "C:\\Users\\lawre\\Downloads\\GPXFilesIn"
metadata_csv = filtergpx.MetadataCSV()
files_processed = 0

if os.path.isdir:
    # Iterate over every gpx file in dir
    for entry in os.scandir(import_path):
        # Only if file not already processed
        if os.path.isfile(raw_path + "\\" + os.path.basename(entry.path)):
            print("%s skipped" % entry.path)
            continue
            
        if entry.path.endswith(".gpx"):
            with open(entry.path, 'r') as input_file:
        #       print((os.path.basename(entry.path).replace('.gpx', '')).replace('activity_',''))
                filtergpx.process_gpx((os.path.basename(entry.path).replace('.gpx', '')).replace('activity_',''), input_file.read())
            files_processed += 1
            # Move file now it's done
            os.rename(entry.path, raw_path + "\\" + os.path.basename(entry.path))
            print("%s processed" % entry.path)

    print('%d files processed' % files_processed)
else:
    print('Import folder does not exist %s' % import_path)
