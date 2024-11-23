import requests
import json
import os
from datetime import datetime

# URL of the ArcGIS REST service
url = "https://maps.helcom.fi/arcgis/rest/services/MADS/Shipping/MapServer/323/query"

# Parameters for the query
params = {
    "where": "Year > 2014 AND Spill_cat = 'Oil' AND Date IS NOT NULL AND Time_UTC IS NOT NULL",
    "outFields": "*",
    "returnGeometry": "true",
    "f": "json"
}

# Make the request
response = requests.get(url, params=params)
data = response.json()

# Create a directory to store the JSON files
output_dir = "detected_spills"
os.makedirs(output_dir, exist_ok=True)

# Process each feature
for feature in data['features']:
    attributes = feature['attributes']
    geometry = feature['geometry']
    
    # Create a unique filename using the OBJECTID
    object_id = attributes['OBJECTID']
    filename = f"spill_{object_id}.json"
    
    # Prepare the data for the individual JSON file
    entry_data = {
        "type": "Feature",
        "properties": attributes,
        "geometry": geometry
    }
    
    # Save the entry as a JSON file
    with open(os.path.join(output_dir, filename), 'w') as f:
        json.dump(entry_data, f, indent=2)

print(f"Downloaded {len(data['features'])} entries to the '{output_dir}' directory.")
