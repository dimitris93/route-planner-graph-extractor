import util
import re
import xml.sax
import codecs

from db import DB

barrier_whitelist = {'cattle_grid', 'border_control', 'checkpoint', 'toll_booth', 'sally_port', 'gate', 'lift_gate',
                     'no', 'entrance'}
access_tag_whitelist = {'yes', 'motorcar', 'motor_vehicle', 'vehicle', 'permissive', 'designated', 'destination'}
access_tag_blacklist = {'no', 'private', 'agricultural', 'forestry', 'emergency', 'psv', 'delivery'}
access_tag_restricted = {'destination', 'delivery'}
access_tags_hierarchy = {'motorcar', 'motor_vehicle', 'vehicle', 'access'}
service_tag_restricted = {'parking_aisle'}
restriction_exception_tags = {'motorcar', 'motor_vehicle', 'vehicle'}

speed_profile = {
    'motorway': 90,
    'motorway_link': 45,
    'trunk': 85,
    'trunk_link': 40,
    'primary': 65,
    'primary_link': 30,
    'secondary': 55,
    'secondary_link': 25,
    'tertiary': 40,
    'tertiary_link': 20,
    'unclassified': 25,
    'residential': 25,
    'living_street': 10,
    'service': 15,
    # 'track': 5,
    'ferry': 5,
    'movable': 5,
    'shuttle_train': 10,
    'default': 10,
}

surface_speeds = {
    # 'asphalt': None,  # None mean no limit. removing the line has the same effect
    # 'concrete': None,
    # 'concrete:plates': None,
    # 'concrete:lanes': None,
    # 'paved': None,

    'cement': 80,
    'compacted': 80,
    'fine_gravel': 80,

    'paving_stones': 60,
    'metal': 60,
    'bricks': 60,

    'grass': 40,
    'wood': 40,
    'sett': 40,
    'grass_paver': 40,
    'gravel': 40,
    'unpaved': 40,
    'ground': 40,
    'dirt': 40,
    'pebblestone': 40,
    'tartan': 40,

    'cobblestone': 40,
    'clay': 40,

    'earth': 20,
    'stone': 20,
    'rocky': 20,
    'sand': 20,

    'mud': 10
}

tracktype_speeds = {
    'grade1': 60,
    'grade2': 40,
    'grade3': 30,
    'grade4': 25,
    'grade5': 20
}

smoothness_speeds = {
    'intermediate': 80,
    'bad': 40,
    'very_bad': 20,
    'horrible': 10,
    'very_horrible': 5,
    'impassable': 0
}

# http://wiki.openstreetmap.org/wiki/Speed_limits
maxspeed_table_default = {
    'urban': 50,
    'rural': 90,
    'trunk': 110,
    'motorway': 130
}

# List only exceptions
maxspeed_table = {
    'ch:rural': 80,
    'ch:trunk': 100,
    'ch:motorway': 120,
    'de:living_street': 7,
    'ru:living_street': 20,
    'ru:urban': 60,
    'ua:urban': 60,
    'at:rural': 100,
    'de:rural': 100,
    'at:trunk': 100,
    'cz:trunk': 0,
    'ro:trunk': 100,
    'cz:motorway': 0,
    'de:motorway': 0,
    'ru:motorway': 110,
    'gb:nsl_single': (60 * 1609) / 1000.0,
    'gb:nsl_dual': (70 * 1609) / 1000.0,
    'gb:motorway': (70 * 1609) / 1000.0,
    'uk:nsl_single': (60 * 1609) / 1000.0,
    'uk:nsl_dual': (70 * 1609) / 1000.0,
    'uk:motorway': (70 * 1609) / 1000.0,
    'none': 140
}

# Note: this biases right-side driving.  Should be
# inverted for left-driving countries.
turn_bias = 1.2
u_turn_penalty = 20.0
traffic_signal_penalty = 2.0
use_turn_restrictions = True
continue_straight_at_waypoint = True
side_road_speed_multiplier = 0.8
turn_penalty = 10.0
obey_oneway = True
ignore_areas = True
speed_reduction = 0.8
math_huge = 9223372036854775807.0


# http://wiki.openstreetmap.org/wiki/Key:maxspeed#Parser
def parse_maxspeed(source):
    speed = None

    if source is None or source == '':
        return speed

    find_number = re.search('\d+', source)
    if find_number is not None:
        speed = int(find_number.group(0))
        if 'mph' in source or 'mp/h' in source:
            speed = (speed * 1609) / 1000.0
    else:  # parse maxspeed like FR:urban
        source = source.lower()
        if source in maxspeed_table:
            speed = maxspeed_table[source]
        else:
            find_highway_type = re.search('[a-z]{2}:(\w+)', source)
            if find_highway_type is not None:
                highway_type = find_highway_type.group(1)
                if highway_type in maxspeed_table_default:
                    speed = maxspeed_table_default[highway_type]
    return speed


def parse_duration(duration):
    if duration is None:
        return None

    if util.is_int(duration):
        return max(int(duration) * 60,
                   1)

    find_duration = re.search('PT(\d+)M([\w.,]+)S', duration)
    if find_duration is not None:
        if util.is_float(find_duration.group(2)):
            return max(int(find_duration.group(1)) * 60 +
                       float(find_duration.group(2)) * 1,
                       1)

    find_duration = re.search('PT(\d+)M', duration)
    if find_duration is not None:
        return max(int(find_duration.group(1)) * 60,
                   1)

    find_duration = re.search('PT(\d+)H(\d+)M', duration)
    if find_duration is not None:
        return max(int(find_duration.group(1)) * 3600 +
                   int(find_duration.group(2)) * 60,
                   1)

    find_duration = re.search('PT([\w.,]+)S', duration)
    if find_duration is not None:
        if util.is_float(find_duration.group(1)):
            return max(float(find_duration.group(1)) * 1,
                       1)

    find_duration = re.search('(\d+):(\d+):(\d+)', duration)
    if find_duration is not None:
        return max(int(find_duration.group(1)) * 86400 +
                   int(find_duration.group(2)) * 3600 +
                   int(find_duration.group(3)) * 60,
                   1)

    find_duration = re.search('(\d+):(\d+)', duration)
    if find_duration is not None:
        return max(int(find_duration.group(1)) * 3600 +
                   int(find_duration.group(2)) * 60,
                   1)

    return None


def find_access_tag(way):
    for v in access_tags_hierarchy:
        tag = way.get_value_by_key(v)
        if tag is not None and tag != '':
            return tag
    return ''


def get_destination(way):
    destination = way.get_value_by_key('destination')
    destination_ref = way.get_value_by_key('destination:ref')

    # Assemble destination as: "A59: Dusseldorf, Koln"
    #          destination:ref  ^    ^  destination

    rv = ''

    if destination_ref is not None and destination_ref != '':
        rv += unicode.replace(destination_ref, ';', ', ')

    if destination is not None and destination != '':
        if rv != '':
            rv += ': '
        rv += unicode.replace(destination, ';', ', ')

    return rv


class Way:
    def __init__(self):
        self.nodes_sequence = []
        self.tags = {}

    def get_value_by_key(self, key):
        if key in self.tags:
            return self.tags[key]
        return None

    def to_string(self):
        return str(self.nodes_sequence) + '\n' + str(self.tags)


class WayMode:
    DRIVING = 'DRIVING'
    FERRY = 'FERRY'
    INACCESSIBLE = 'INACCESSIBLE'


class WayResult:
    def __init__(self):
        self.forward_speed = None
        self.backward_speed = None
        self.forward_mode = None
        self.backward_mode = None
        self.duration = None
        self.name = None
        self.is_access_restricted = False
        self.is_startpoint = False
        self.roundabout = False

    def to_string(self):
        print ('f_speed ' + str(self.forward_speed) + '\n' +
               'b_speed ' + str(self.backward_speed) + '\n' +
               'f_mode ' + str(self.forward_mode) + '\n' +
               'b_mode ' + str(self.backward_mode) + '\n' +
               'duration ' + str(self.duration) + '\n' +
               'name ' + self.name + '\n' +
               'access_restr ' + str(self.is_access_restricted) + '\n' +
               'start_point ' + str(self.is_startpoint) + '\n' +
               'round_about ' + str(self.roundabout) + '\n')


def parse_way(way):
    result = WayResult()

    highway = way.get_value_by_key('highway')
    route = way.get_value_by_key('route')
    bridge = way.get_value_by_key('bridge')

    if not ((highway is not None and highway != '') or
                (route is not None and route != '') or
                (bridge is not None and bridge != '')):
        return result

    # We don't route over areas
    area = way.get_value_by_key('area')
    if ignore_areas and area == 'yes':
        return result

    # Check if oneway tag is unsupported
    oneway = way.get_value_by_key('oneway')
    if oneway == 'reversible':
        return result

    impassable = way.get_value_by_key('impassable')
    if impassable == 'yes':
        return result

    status = way.get_value_by_key('status')
    if status == 'impassable':
        return result

    # Check if we are allowed to access the way
    access = find_access_tag(way)
    if access in access_tag_blacklist:
        return result

    result.forward_mode = WayMode.DRIVING
    result.backward_mode = WayMode.DRIVING

    # Handling ferries and piers
    route_speed = None
    if route in speed_profile:
        route_speed = speed_profile[route]
    if route_speed is not None and route_speed > 0:
        highway = route
        duration = way.get_value_by_key('duration')
        parsed_duration = parse_duration(duration)
        if parsed_duration is not None:
            result.duration = float(parsed_duration)
        result.forward_mode = WayMode.FERRY
        result.backward_mode = WayMode.FERRY
        result.forward_speed = route_speed
        result.backward_speed = route_speed

    # Handling movable bridges
    bridge_speed = None
    if bridge in speed_profile:
        bridge_speed = speed_profile[bridge]
    capacity_car = way.get_value_by_key('capacity:car')
    if bridge_speed is not None and bridge_speed > 0 and capacity_car != 0:
        highway = bridge
        duration = way.get_value_by_key('duration')
        parsed_duration = parse_duration(duration)
        if parsed_duration is not None:
            result.duration = float(parsed_duration)
        result.forward_speed = bridge_speed
        result.backward_speed = bridge_speed

    # Leave early of this way is not accessible
    if highway == '':
        return result

    if result.forward_speed is None:
        highway_speed = None
        if highway in speed_profile:
            highway_speed = speed_profile[highway]
        max_speed = parse_maxspeed(way.get_value_by_key('maxspeed'))
        if highway_speed is not None:
            if max_speed is not None and max_speed > highway_speed:
                result.forward_speed = max_speed
                result.backward_speed = max_speed
            else:
                result.forward_speed = highway_speed
                result.backward_speed = highway_speed
        # Set the avg speed on ways that are marked accessible
        else:
            if access in access_tag_whitelist:
                result.forward_speed = speed_profile['default']
                result.backward_speed = speed_profile['default']
        if max_speed is None or max_speed == 0:
            max_speed = math_huge
        result.forward_speed = min(result.forward_speed, max_speed)
        result.backward_speed = min(result.backward_speed, max_speed)

    if result.forward_speed is None and result.backward_speed is None:
        return result

    # Reduce speed on special side roads
    sideway = way.get_value_by_key('side_road')
    if sideway == 'yes' or sideway == 'rotary':
        result.forward_speed *= side_road_speed_multiplier
        result.backward_speed *= side_road_speed_multiplier

    # Reduce speed on bad surfaces
    surface = way.get_value_by_key('surface')
    tracktype = way.get_value_by_key('tracktype')
    smoothness = way.get_value_by_key('smoothness')

    if surface is not None and surface in surface_speeds:
        result.forward_speed = min(surface_speeds[surface], result.forward_speed)
        result.backward_speed = min(surface_speeds[surface], result.backward_speed)

    if tracktype is not None and tracktype in tracktype_speeds:
        result.forward_speed = min(tracktype_speeds[tracktype], result.forward_speed)
        result.backward_speed = min(tracktype_speeds[tracktype], result.backward_speed)

    if smoothness is not None and smoothness in smoothness_speeds:
        result.forward_speed = min(smoothness_speeds[smoothness], result.forward_speed)
        result.backward_speed = min(smoothness_speeds[smoothness], result.backward_speed)

    # Parse the remaining tags
    name = way.get_value_by_key('name')
    ref = way.get_value_by_key('ref')
    junction = way.get_value_by_key('junction')
    service = way.get_value_by_key('service')

    has_ref = ref is not None and ref != ''
    has_name = name is not None and name != ''

    if has_name and has_ref:
        result.name = name + ' (' + ref + ')'
    elif has_ref:
        result.name = ref
    elif has_name:
        result.name = name

    if junction is not None and junction == 'roundabout':
        result.roundabout = True

    # Set access restriction flag if access is allowed under certain restrictions only
    if access != '' and access in access_tag_restricted:
        result.is_access_restricted = True

    # Set access restriction flag if service is allowed under certain restrictions only
    if service is not None and service != '' and service in service_tag_restricted:
        result.is_access_restricted = True

    # Set direction according to tags on way
    if obey_oneway:
        if oneway == '-1':
            result.forward_mode = WayMode.INACCESSIBLE
        elif (oneway == 'yes' or
                      oneway == '1' or
                      oneway == 'true' or
                      junction == 'roundabout' or
                  (highway == 'motorway_link' and oneway != 'no') or
                  (highway == 'motorway' and oneway != 'no')):
            result.backward_mode = WayMode.INACCESSIBLE

            # If we're on a oneway and there is no ref tag, re-use destination tag as ref
            destination = get_destination(way)
            has_destination = destination != ''

            if has_destination and has_name and not has_ref:
                result.name = name + ' (' + destination + ')'

    # Override speed settings if explicit forward/backward maxspeeds are given
    maxspeed_forward = parse_maxspeed(way.get_value_by_key('maxspeed:forward'))
    maxspeed_backward = parse_maxspeed(way.get_value_by_key('maxspeed:backward'))
    if maxspeed_forward is not None and maxspeed_forward > 0:
        if (result.forward_mode != WayMode.INACCESSIBLE and
                    result.backward_mode != WayMode.INACCESSIBLE):
            result.backward_speed = result.forward_speed
        result.forward_speed = maxspeed_forward
    if maxspeed_backward is not None and maxspeed_backward > 0:
        result.backward_speed = maxspeed_backward

    # Override speed settings if advisory forward/backward maxspeeds are given
    advisory_speed = parse_maxspeed(way.get_value_by_key('maxspeed:advisory'))
    advisory_forward = parse_maxspeed(way.get_value_by_key('maxspeed:advisory:forward'))
    advisory_backward = parse_maxspeed(way.get_value_by_key('maxspeed:advisory:backward'))
    # Apply bi-directional advisory speed first
    if advisory_speed is not None and advisory_speed > 0:
        if result.forward_mode != WayMode.INACCESSIBLE:
            result.forward_speed = advisory_speed
        if result.backward_mode != WayMode.INACCESSIBLE:
            result.backward_speed = advisory_speed
    if advisory_forward is not None and advisory_forward > 0:
        if (result.forward_mode != WayMode.INACCESSIBLE and
                    result.backward_mode != WayMode.INACCESSIBLE):
            result.backward_speed = result.forward_speed
        result.forward_speed = advisory_forward
    if advisory_backward is not None and advisory_backward > 0:
        result.backward_speed = advisory_backward

    width = math_huge
    lanes = math_huge
    if result.forward_speed > 0 or result.backward_speed > 0:
        width_string = way.get_value_by_key('width')
        if width_string is not None:
            find_width_number = re.search('\d+', width_string)
            if find_width_number is not None:
                width = int(find_width_number.group(0))

        lanes_string = way.get_value_by_key('lanes')
        if lanes_string is not None:
            find_lanes_number = re.search('\d+', lanes_string)
            if find_lanes_number is not None:
                lanes = int(find_lanes_number.group(0))

    is_bidirectional = (result.forward_mode != WayMode.INACCESSIBLE and
                        result.backward_mode != WayMode.INACCESSIBLE)

    # Scale speeds to get better avg driving times
    if result.forward_speed > 0:
        scaled_speed = result.forward_speed * speed_reduction + 11.0
        penalized_speed = math_huge
        if width <= 3 or (lanes <= 1 and is_bidirectional):
            penalized_speed = result.forward_speed / 2.0
        result.forward_speed = min(penalized_speed, scaled_speed)

    if result.backward_speed > 0:
        scaled_speed = result.backward_speed * speed_reduction + 11.0
        penalized_speed = math_huge
        if width <= 3 or (lanes <= 1 and is_bidirectional):
            penalized_speed = result.backward_speed / 2.0
        result.backward_speed = min(penalized_speed, scaled_speed)

    # Only allow this road as start point if it not a ferry
    result.is_startpoint = (result.forward_mode == WayMode.DRIVING or
                            result.backward_mode == WayMode.DRIVING)
    return result


class CarGraphParser:
    def __init__(self, max_edge_segment_length, osm_file_path, nodes_file_path, ways_file_path, db_path):
        sax_parser = xml.sax.make_parser()
        sax_parser.setContentHandler(_CarGraphParser(max_edge_segment_length, nodes_file_path, ways_file_path, db_path))
        sax_parser.parse(osm_file_path)


class _CarGraphParser(xml.sax.ContentHandler):
    def __init__(self, max_edge_segment_length, nodes_file_path, ways_file_path, db_path):
        self.db = DB(db_path)
        self.current_way = Way()  # the current Way we are parsing
        self.max_edge_segment_length = max_edge_segment_length  # the max length of an edge segment
        self.in_between_nodes_counter = 0
        self.undirected_edges_counter = 0
        self.level_1_element_is_way = False
        self.ways_file = codecs.open(ways_file_path, 'w', 'utf-8')  # open file to write
        self.nodes_file = codecs.open(nodes_file_path, 'w', 'utf-8')  # open file to write
        self.ways_file.write('a  b  forward_mode  backward_mode  forward_duration  '
                             'backward_duration  duration  is_startpoint  is_access_restricted  road_name\n')
        self.nodes_file.write('id    lat    lng\n')

    def startElement(self, tag, attributes):
        # Way
        if tag == 'node':
            self.db.insert_node(int(attributes['id']), float(attributes['lat']), float(attributes['lon']))
            self.level_1_element_is_way = False
        elif tag == 'way':
            self.current_way = Way()
            self.level_1_element_is_way = True
        # Way -> nd
        elif tag == 'nd':
            self.current_way.nodes_sequence.append(int(attributes['ref']))  # add osm_node_id to way
        # Way -> tag
        elif tag == 'tag' and self.level_1_element_is_way:
            self.current_way.tags[attributes['k']] = attributes['v']  # (key, value) pair
        else:
            self.level_1_element_is_way = False

    def endElement(self, tag):
        # Way
        if tag == 'way':
            if len(self.current_way.nodes_sequence) < 2:
                return

            # Parse way
            result = parse_way(self.current_way)

            # If this way is not accessible by car
            if ((result.forward_mode is None or result.forward_mode == WayMode.INACCESSIBLE) and
                    (result.backward_mode is None or result.backward_mode == WayMode.INACCESSIBLE)):
                return
            if ((result.forward_speed is None or result.forward_speed <= 0) and
                    (result.backward_speed is None or result.backward_speed <= 0)):
                return

            if result.forward_speed <= 0 or result.backward_speed <= 0:
                print 'Error: Speed is 0. We will divide by 0. Fixme'

            # Get nodes from osm_ids
            nodes = self.db.osm_ids_to_nodes(self.current_way.nodes_sequence)
            if nodes is None:
                return

            # Iterate the edges of the way
            for i in range(len(nodes) - 1):
                a = nodes[i]
                b = nodes[i + 1]
                distance = util.distance_in_meters(a.lat, a.lng, b.lat, b.lng)
                if distance <= 0:
                    print 'Notice: Distance was <= 0 between nodes ' + str(a.osm_id) + ' and ' + str(
                        b.osm_id) + '. Fixme.'

                # Add in-between nodes to really long edges
                in_between_nodes = None
                if distance > self.max_edge_segment_length and result.is_startpoint:
                    in_between_nodes = self.db.add_in_between_nodes(a, b, distance, self.max_edge_segment_length)

                if in_between_nodes is None:
                    self.ways_file.write(str(a.my_id) + ' ' +
                                         str(b.my_id) + ' ' +
                                         str(result.forward_mode) + ' ' +
                                         str(result.backward_mode) + ' ' +
                                         str(distance / float(result.forward_speed)) + ' ' +
                                         str(distance / float(result.backward_speed)) + ' ' +
                                         str(result.duration) + ' ' +
                                         str(result.is_startpoint) + ' ' +
                                         str(result.is_access_restricted) + ' ' +
                                         ('Unknown' if result.name is None else result.name) + '\n')
                    self.undirected_edges_counter += 1
                else:  # in-between nodes
                    self.in_between_nodes_counter += len(in_between_nodes) - 2
                    distance /= len(in_between_nodes) - 1
                    if result.duration is not None:
                        result.duration /= len(in_between_nodes) - 1  # result.duration needs to be float
                    for k in range(0, len(in_between_nodes) - 1):
                        self.ways_file.write(str(in_between_nodes[k].my_id) + ' ' +
                                             str(in_between_nodes[k + 1].my_id) + ' ' +
                                             str(result.forward_mode) + ' ' +
                                             str(result.backward_mode) + ' ' +
                                             str(distance / float(result.forward_speed)) + ' ' +
                                             str(distance / float(result.backward_speed)) + ' ' +
                                             str(result.duration) + ' ' +
                                             str(result.is_startpoint) + ' ' +
                                             str(result.is_access_restricted) + ' ' +
                                             ('Unknown' if result.name is None else result.name) + '\n')
                        self.undirected_edges_counter += 1

    def endDocument(self):
        """
        Called only once, at the end of the xml
        """
        # Query all nodes and order them by my_id
        self.db.select_all_nodes()

        nodes_counter = 0
        for row in self.db.c:
            # Write nodes to our nodes_file
            self.nodes_file.write(str(row[0]) + ' ' +  # my_id
                                  str(row[1]) + ' ' +  # lat
                                  str(row[2]) + ' ' +  # lng
                                  '\n')
            nodes_counter += 1

        print str(self.in_between_nodes_counter) + ' in-between nodes added.'
        print 'Number of nodes: ' + str(nodes_counter)
        print 'Number of edges: ' + str(self.undirected_edges_counter)

        # Close file streams
        self.nodes_file.close()
        self.ways_file.close()
