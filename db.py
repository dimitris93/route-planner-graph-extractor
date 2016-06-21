import sqlite3

from util import Node


class DB:
    def __init__(self, db_path, drop_table_if_exists=True):
        self.current_my_id = 0
        self.current_in_between_node_osm_id = 50000000000  # 50 billion
        self.conn = sqlite3.connect(db_path)
        self.c = self.conn.cursor()
        if drop_table_if_exists:
            self.c.execute('DROP TABLE IF EXISTS nodes')
            self.c.execute('CREATE TABLE nodes ('
                           'osm_id int primary key, '
                           'my_id int, '
                           'lat real, '
                           'lng real'
                           ')')

    def insert_node(self, osm_id, lat, lng):
        self.c.execute('INSERT INTO nodes VALUES (?,?,?,?)', [osm_id, -1, lat, lng])

    # If we have a way like A->B->C->A->D, we make 2 queries for A,
    # but that happens extremely rarely
    def osm_ids_to_nodes(self, osm_ids):
        nodes = []
        for i in range(0, len(osm_ids)):
            # Ignore A->A edges
            if i > 0 and osm_ids[i - 1] == osm_ids[i]:
                continue
            self.c.execute('SELECT my_id, lat, lng FROM nodes WHERE osm_id=?', [osm_ids[i]])
            result = self.c.fetchone()
            if result is None:
                # print 'Warning: Node ' + str(osm_ids[i]) + ' of the way does not exist'
                return None
            else:
                my_id = result[0]
                lat = result[1]
                lng = result[2]
                # Ignore A->B edges where A.lat == B.lat and A.lng == B.lng
                if len(nodes) > 0 and nodes[-1].lat == lat and nodes[-1].lng == lng:
                    continue
                # Set the node's my_id if it hasn't been set yet
                if my_id == -1:
                    my_id = self.current_my_id
                    self.c.execute('UPDATE nodes SET my_id=? WHERE osm_id=?', [my_id, osm_ids[i]])
                    self.current_my_id += 1
                nodes.append(Node(osm_ids[i], my_id, lat, lng))
        return nodes

    def add_in_between_nodes(self, a, b, distance, max_edge_segment_length):
        in_between_nodes = [None] * (int(distance / max_edge_segment_length) + 2)
        initial_ratio = 1.0 / (len(in_between_nodes) - 1)
        in_between_nodes[0] = a
        in_between_nodes[-1] = b
        for k in range(1, len(in_between_nodes) - 1):
            ratio = initial_ratio * k
            lat = format((1 - ratio) * a.lat + ratio * b.lat, '.7f')
            lng = format((1 - ratio) * a.lng + ratio * b.lng, '.7f')
            node = Node(self.current_in_between_node_osm_id, self.current_my_id, lat, lng)
            self.c.execute('INSERT INTO nodes VALUES (?,?,?,?)', [node.osm_id, node.my_id, lat, lng])
            self.current_my_id += 1
            self.current_in_between_node_osm_id += 1
            in_between_nodes[k] = node
            # print 'Notice: In-between node my_id=' + str(node.my_id) + ' between ' + str(a.my_id) + ' and ' + str(
            #     b.my_id)
        return in_between_nodes

    def select_all_nodes(self):
        self.c.execute('SELECT my_id, lat, lng FROM nodes WHERE my_id!=-1 ORDER BY my_id ASC')

    def save_and_close(self):
        self.conn.commit()
        self.conn.close()
