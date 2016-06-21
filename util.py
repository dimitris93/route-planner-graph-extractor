import math

# Convert latitude and longitude to
# spherical coordinates in radians.
degrees_to_radians = math.pi / 180.0
earth_radius_in_meters = 6378137


def distance_in_meters(lat1, lng1, lat2, lng2):
    """
    Calculates the distance in meters between 2 coordinates (lat, lon)
    """
    # Great circle distance
    x1 = lat1 * degrees_to_radians
    y1 = lng1 * degrees_to_radians
    x2 = lat2 * degrees_to_radians
    y2 = lng2 * degrees_to_radians
    x = x2 - x1
    y = (y2 - y1) * math.cos((x1 + x2) / 2.0)
    # make sure distance is float
    return float(math.hypot(x, y) * earth_radius_in_meters)


def is_float(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


def is_int(value):
    try:
        int(value)
        return True
    except ValueError:
        return False


def remove_adjacent_duplicates(x):
    for i in xrange(len(x) - 1, 0, -1):
        if x[i] == x[i - 1]:
            del x[i]


class Node:
    def __init__(self, osm_id, my_id, lat, lng):
        self.osm_id = osm_id
        self.my_id = my_id
        self.lat = lat
        self.lng = lng
