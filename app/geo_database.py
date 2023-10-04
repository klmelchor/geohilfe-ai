import requests
import math
from geopy.distance import distance
import pprint
import re
import pandas as pd

from gensim.models import KeyedVectors

# Load the pre-trained Word2Vec model
#model = KeyedVectors.load_word2vec_format('GoogleNews-vectors-negative300.bin', binary=True)

# Set your Google Maps API key
api_key = "AIzaSyBhQC4vVQqZzjXDmrpnS96uj9e8YPLY-TY"

# Set the latitude and longitude of the center of the area you want to capture
def get_satellite_image(coordinates, grid_no_lat, grid_no_long):

    latitude = coordinates[0]
    longitude = coordinates[1]

    # Set the zoom level of the map (1 to 20)
    zoom = 18

    # Set the size of the map image in pixels
    width_pixels = 640 # 480->960
    height_pixels = 640 # 480->960

    scale = 1

    # Build the Google Maps Static API URL with the specified parameters
    #url = f"https://maps.googleapis.com/maps/api/staticmap?center={latitude},{longitude}&zoom={zoom}&size={width_pixels}x{height_pixels}&scale=2&key={api_key}"
    url = f"https://maps.googleapis.com/maps/api/staticmap?center={latitude},{longitude}&zoom={zoom}&size={width_pixels}x{height_pixels}&scale={scale}&maptype=satellite&key={api_key}"

    # Get the aspect ratio of the image
    aspect_ratio = width_pixels / height_pixels

    # Send a GET request to the Static API and save the image
    response = requests.get(url)
    image_path = f"map_image_{grid_no_lat}_{grid_no_long}.png"

    with open(image_path, "wb") as image_file:
        image_file.write(response.content)

    print("Map image saved successfully!")


def calculate_next(coors, distance_m, bearing):
    # Define the starting coordinates
    start_latitude = coors[0]  # Example latitude in degrees
    start_longitude = coors[1]  # Example longitude in degrees
    
    # Define the distance in meters
    distance_meters = distance_m

    # Calculate the destination coordinates
    destination = distance(meters=distance_meters).destination(point=(start_latitude, start_longitude), bearing=bearing)

    # Extract the latitude and longitude of the destination
    destination_latitude = destination.latitude
    destination_longitude = destination.longitude
    
    return destination_latitude, destination_longitude

def get_landmarks(coordinates, api_key):
    radius = 128
    latitude = coordinates[0]
    longitude = coordinates[1]
    
    #url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={latitude},{longitude}&radius={radius}&type=point_of_interest&key={api_key}"
    url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={latitude},{longitude}&radius={radius}&key={api_key}"
    response = requests.get(url)
    data = response.json()

    #pprint.pprint(data["results"])
    if data["status"] == "OK":
        results = data["results"]
        #print(results["address_components"])
        
        # get landmarks 
        landmarks = [result["name"] for result in results]
        
        # get all addresses listed in grid cell
        pattern = r'^\D*'
        addresses = [result["vicinity"] for result in results]
        
        # get street names only and clean for duplicates
        poss_streets = [re.match(pattern, street).group(0)[:-1] for street in addresses]  
        streets = [] 
        [streets.append(x) for x in poss_streets if x not in streets] 
        
        # get possible keywords and clean for duplicates
        poss_keywords = [result["types"] for result in results]
        poss_keywords = [item for sub_list in poss_keywords for item in sub_list]
        keywords = [] 
        [keywords.append(x) for x in poss_keywords if x not in keywords] 
        
        return landmarks, addresses, streets, keywords
    else:
        return None

#initial_coors = "47.663495, 9.173372"
def create_dataset():
    initial_coors = (47.663495, 9.173372)
    bearing = 90
    distance_m = 256
    sample_database = pd.DataFrame(columns=['latitude', 'longitude', 'landmarks', 'street', 'known_addresses', 'keywords'])

    coors = initial_coors
    x_slices = 3
    y_slices = 5
    for y in range(y_slices):
        # the 0th column before iterating over the longitude
        anchor_coor = coors
        for x in range(x_slices):
            #get_satellite_image(coors, y, x)

            lm, ad, st, pk = get_landmarks(coors, api_key)
            #new_row = pd.Series([coors[0], coors[1], lm, st, ad, pk], index=sample_database.columns)
            #print(new_row)
            info_dict = {'latitude': coors[0], 
                         'longitude': coors[1], 
                         'landmarks': [lm], 
                         'street': [st], 
                         'known_addresses': [ad], 
                         'keywords': [pk]}

            df = pd.DataFrame.from_dict(info_dict)
            sample_database = sample_database.append(df, ignore_index=True)

            next_coors = calculate_next(coors, distance_m, bearing)
            coors = next_coors
        coors = calculate_next(anchor_coor, distance_m, 180)
    return sample_database