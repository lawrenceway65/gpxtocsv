"""Process local files gpx files
Processes all gpx files in a directory.
Uses files name as an id.
"""

import filtergpx
import os
import config


root_path = config.local_path
raw_path = root_path + "Import\\Raw"
import_path = root_path + "Import\\FilesIn"

files_processed = 0
# Iterate over every gpx file in dir
for entry in os.scandir(import_path):
    if (entry.path.endswith(".gpx")):
        with open(entry.path, 'r') as input_file:
            filtergpx.process_gpx(os.path.basename(entry.path).replace('.gpx', ''), input_file.read())
#        print("%s processed" % entry.path)
        files_processed += 1
        # Move file now it's done
        os.rename(entry.path, raw_path + "\\" + os.path.basename(entry.path))

print('%d files processed' % files_processed)

