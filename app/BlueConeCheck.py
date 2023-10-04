import math
from geopy import distance
from geopy import Point
from shapely.geometry import LineString, Polygon
#from geopy.distance import geodesic

# info that are important:
# point -> point to check
# cone_center -> the tower
# cone_radius_m -> how long the cone is
# cone_direction -> where the cone is facing (0 = up, 90 = right, 180 = down, 270 = left)
# cone_angle -> how big the cone expands from the center

# To check whether a grid cell intersects the cone, you would need to call this function for each corner of the cell and the cell center, 
# and if any of those points are in the cone, then the cell intersects the cone.

def is_point_in_cone(point, cone_center, cone_radius_m, cone_angle, cone_direction):
    # Calculate the length of one degree of latitude in kilometers (it's the same all over the Earth)
    km_per_lat_degree = distance.distance((cone_center[0], cone_center[1]), (cone_center[0] + 1, cone_center[1])).km

    # Calculate the length of one degree of longitude at this latitude in kilometers
    km_per_lon_degree = distance.distance((cone_center[0], cone_center[1]), (cone_center[0], cone_center[1] + 1)).km

    # Convert the cone radius from meters to degrees
    cone_radius_lat = cone_radius_m / 1000 / km_per_lat_degree
    cone_radius_lon = cone_radius_m / 1000 / km_per_lon_degree

    # Calculate the distance from the cone center to the point in degrees
    dx, dy = point[0] - cone_center[0], point[1] - cone_center[1]
    distance_lat = abs(dx)
    distance_lon = abs(dy)

    # Check if the point is within the circle defined by the cone
    if distance_lat > cone_radius_lat or distance_lon > cone_radius_lon:
        #print('here')
        return False

    # Calculate the angle from the cone center to the point
    #point_angle = math.degrees(math.atan2(dy, dx)) --> this is erroneous!
    
    # use a different computation
    point_angle = calculate_initial_compass_bearing(cone_center, point)
    
    #print(point_angle)#, point_angle_2 - 360)

    # Normalize angles to 0-360 range
    point_angle = (point_angle + 360) % 360
    cone_direction = (cone_direction + 360) % 360

    # Calculate the start and end angles of the cone
    start_angle = (cone_direction - cone_angle / 2 + 360) % 360
    end_angle = (cone_direction + cone_angle / 2 + 360) % 360
    #print(start_angle, end_angle)

    # Check if the point is within the cone's angular range
    if start_angle < end_angle:
        return start_angle <= point_angle <= end_angle
    else:  # Cone crosses the 0/360 degree line
        return point_angle >= start_angle or point_angle <= end_angle

    return False

def calculate_initial_compass_bearing(point1, point2):
    """
    Calculate the bearing between two points.
    The formula used to calculate bearing is:
        θ = atan2(sin(Δlong).cos(lat2), cos(lat1).sin(lat2) - sin(lat1).cos(lat2).cos(Δlong))
    :param point1: tuple of float (latitude, longitude)
    :param point2: tuple of float (latitude, longitude)
    :returns: initial compass bearing in degrees, from point1 to point2
    """

    if (type(point1) != tuple) or (type(point2) != tuple):
        raise TypeError("Only tuples are supported as arguments")

    lat1 = math.radians(point1[0])
    lat2 = math.radians(point2[0])

    diffLong = math.radians(point2[1] - point1[1])

    x = math.sin(diffLong) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1) * math.cos(lat2) * math.cos(diffLong))

    initial_bearing = math.atan2(x, y)

    # Now we have the initial bearing but math.atan2() returns values from -π to +π 
    # so we need to normalize the result, converting it to a compass bearing as it 
    # is customary to measure it in the range 0° to 360°
    initial_bearing = math.degrees(initial_bearing)
    compass_bearing = (initial_bearing + 360) % 360

    return compass_bearing

def calculate_next(coors, distance_m, bearing):
    # Define the starting coordinates
    if type(coors) == str:
        start_latitude = float(coors.split(',')[0])  # Example latitude in degrees
        start_longitude = float(coors.split(',')[1])  # Example longitude in degrees
    else:
        start_latitude = coors[0]
        start_longitude = coors[1]
    
    # Define the distance in meters
    distance_meters = distance_m

    # Calculate the destination coordinates
    destination = distance.distance(meters=distance_meters).destination(point=(start_latitude, start_longitude), bearing=bearing)

    # Extract the latitude and longitude of the destination
    destination_latitude = destination.latitude
    destination_longitude = destination.longitude
    
    return destination_latitude, destination_longitude

### ----- Find the grid cell where the Blue Cone Origin is ----- ###


# called by find_bc_cell to check if point is in selected grid
def is_point_in_bbox(point, bbox):
    """
    Checks if a point is inside a bounding box.

    Parameters:
    point (tuple): a tuple with latitude and longitude of the point.
    bbox (tuple): a tuple with coordinates of the southwest and northeast corners of the bounding box.
# Define the coordinates of the square
coords = [(0, 0), (0, 1), (1, 1), (1, 0)]

# Create a Shapely Polygon object representing the square
square = Polygon(coords)

# Print the square's area and perimeter
print("Area:", square.area)
print("Perimeter:", square.length)
    Returns:
    bool: True if the point is inside the bounding box, False otherwise.
    """

    p_lat, p_lon = point
    sw_lat, sw_lon, ne_lat, ne_lon = bbox

    return sw_lat <= p_lat <= ne_lat and sw_lon <= p_lon <= ne_lon

def find_bc_cell(grid_cells, cone_origin):
    for idx in range(len(grid_cells)):
        bbox = (grid_cells.iloc[idx]['southwest'][0], grid_cells.iloc[idx]['southwest'][1],
                grid_cells.iloc[idx]['northeast'][0], grid_cells.iloc[idx]['northeast'][1])
        
        if is_point_in_bbox(cone_origin, bbox) == True:
            return idx

### ----- Grid extraction methods ----- ###

def get_cone_segments(cone_origin, cone_radius_m, cone_angle_deg, cone_direction_deg):
    # this is a crude estimation of the cone depending on the angle.
    adjusted_r = cone_radius_m/math.cos((cone_angle_deg/180)*(math.pi/2))
    
    #get the first segment
    bearing = cone_direction_deg + cone_angle_deg/2
    pos_seg = calculate_next(cone_origin, adjusted_r, bearing)
    
    #get the second segment
    bearing = cone_direction_deg - cone_angle_deg/2
    neg_seg = calculate_next(cone_origin, adjusted_r, bearing)
    
    return pos_seg, neg_seg    

# method for check bbox points
def check_bbox_points(grid_cell, cone_origin, cone_radius_m, cone_angle, cone_direction):
    ne = grid_cell['northeast']
    sw = grid_cell['southwest']
    
    #nw = calculate_next(ne, 300, 270) --> commented out due to rounding errors (|x| is the polygon being created)
    nw = (ne[0], sw[1])
    #se = calculate_next(sw, 300, 90) --> commented out due to rounding errors (|x| is the polygon being created)
    se = (sw[0], ne[1])
    
    center = ((grid_cell['northeast'][0] + grid_cell['southwest'][0])/2, (grid_cell['northeast'][1] + grid_cell['southwest'][1])/2)
    
    bbox_points = [ne, nw, sw, se, center]
    for point in bbox_points:
        if is_point_in_cone(point, cone_origin, cone_radius_m, cone_angle, cone_direction) == True:
            #print(point)
            return True
    
    # check for intersections of grid edges with cone line segments
    p1 = cone_origin
    p2, p3 = get_cone_segments(cone_origin, cone_radius_m, cone_angle, cone_direction)
    
    # Define the polygon (representing the grid)
    # You might need to create a more complex Polygon to accurately represent the grid.
    polygon = Polygon([nw, ne, se, sw])
    
    # Define the line (representing the cone's edge)
    # You might need to create a more complex LineString to accurately represent the cone.
    for point in [p2, p3]:
        line = LineString([p1, point])
        if line.intersects(polygon) == True:
            return True

    # any of the points not in cone
    return False

# find all the indices encompassed by the cone
def get_grids_subset(grid_cells, cone_origin, cone_radius_m, cone_angle, cone_direction):
    grid_subset_idx = []
    for idx in range(len(grid_cells)):
        
        # check if any of the points of the grid are inside the blue cone
        grid_check = check_bbox_points(grid_cells.loc[idx], cone_origin, cone_radius_m, cone_angle, cone_direction)
        if grid_check == True:
            grid_subset_idx.append(idx)
            
    return grid_subset_idx

# return the bounding box coordinates of the grid subset
def get_bbox_subset(grid_cells_subset):
    grid_cells_subset = grid_cells_subset.reset_index()
    
    grid_subset = []
    for grid in range(len(grid_cells_subset)):
        ne = grid_cells_subset.loc[grid]['northeast']
        sw = grid_cells_subset.loc[grid]['southwest']
   
        stage_coors = {
            "grid_number": int(grid_cells_subset.loc[grid]['grid_num']),
            "northeast": [float(i) for i in ne],
            "southeast": [float(sw[0]), float(ne[1])],
            "southwest": [float(i) for i in sw],
            "northwest": [float(ne[0]), float(sw[1])],
        }
        grid_subset.append(stage_coors)
        
    return grid_subset