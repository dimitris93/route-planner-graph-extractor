## Synopsis

The purpose of this Python code is to parse the `.osm` data, which are downloadable from various links, for example [here](https://www.geofabrik.de/data/download.html), and then parse those data to produce a real road graph, for example, the **car graph**.

## Input

An .osm file, for example, `greece-latest.osm`, or `europe-latest.osm`. And, a distance in meters, for example `250` which will be the highest distance that we want to have to any edge in our graph. If an edge is more than `250` when we split it and add more nodes, so that it remains short. This is optional. The reasoning behind why we do this is explained [here](https://github.com/outerpixels/routing-engine-backend/blob/master/README.md) in detail.

## Output

2 .txt files, named `nodes.txt` and `ways.txt`. 

The `nodes.txt` file contains all the **nodes**, and follows the following format:

**id      <br> 
latitude  <br>
longitude**

0      37.5042194  23.4567436 <br>
1      37.5039174  23.456488  <br>
2      37.503815   23.4567841 <br>
3      37.5036181  23.4573291 <br>
...                          

The `ways.txt` file contains all **edges**, and follows the following format:

**A <br> 
B <br> 
forward_mode <br> 
backward_mode <br> 
forward_duration <br> 
backward_duration <br> 
duration <br> 
is_startpoint <br> 
is_access_restricted <br> 
road_name**

292 293 DRIVING INACCESSIBLE 1.66359093354 1.66359093354 None True False Ρήγα Φεραίου<br>
293 294 DRIVING INACCESSIBLE 1.42879660177 1.42879660177 None True False Ρήγα Φεραίου<br>
294 295 DRIVING INACCESSIBLE 1.92864344384 1.92864344384 None True False Ρήγα Φεραίου<br>
295 296 DRIVING INACCESSIBLE 1.56874919292 1.56874919292 None True False Ρήγα Φεραίου<br>

## The .osm data parsing process 

The parsing process can be tricky, and there is more than one correct ways to do it, meaning that someone could choose to include `parking` or `private roads` in his graph and someone might opt to not include them. Another example is that our graph's edge weights could slightly differ from someone else's edge weights.

The process I followed when implementing this graph-extractor is very similar to the script of Project-Osrm as seen [here](https://github.com/Project-OSRM/osrm-backend/blob/master/profiles/car.lua). 

When parsing the `.osm` data, we also want to associate the `osm_node_ids` to our own, smaller ids, named `my_ids`, which take values **from 0 to N**. The reason behind that is that we need those ids as indexes in our c++ application, which solves the shortest path problem. To do that, I am using a temporary **Sqlite** database (which is built-in python) to help me with the data parsing. Otherwise, an in-memory approach would require way too much memory. The **Sqlite** database file which contains the `osm_node_id, my_id, latitude, longitude` takes up 80GBs of space for the Europe car graph.

## Important things we consider when parsing the .osm data

 - Road's type. This is indicated in the `highway` tag, which takes values such as `motorway`, `residential`, `living_street`, etc.
 - Road's texture. For example, `asphalt`, `dirt`, etc.
 - Road's accessibility tags. For example, accessible by the general public, private parking lots, roads that are accessible only in certain hours, etc.
 - Max-speed road signs
