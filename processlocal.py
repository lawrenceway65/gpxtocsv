"""Process local files gpx files
Processes all gpx files in a directory.
Uses files name as an id.
"""

import filtergpx
import os


# Input dir

Path = '/Users/lawrence/Documents/Python/'
# Path = '/Users/lawrence/Documents/Python/Test/'

files_processed = 0
# Iterate over every gpx file in dir
for entry in os.scandir(Path):
    if (entry.path.endswith(".gpx")):
        with open(entry.path, 'r') as input_file:
            filtergpx.process_gpx(os.path.basename(entry.path).replace('.gpx', ''), input_file.read())
        print("%s processed" % entry.path)
        files_processed += 1

print('%d files processed' % files_processed)

