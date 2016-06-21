from car_parser import CarGraphParser
import time

t = time.time()

CarGraphParser(250,  # max edge segment length
               'E:/europe-latest.osm',
               'E:/car_nodes.txt',
               'E:/car_ways.txt',
               'E:/car_graph.sqlite')

print str(time.time() - t) + ' seconds elapsed.'
