## Synopsis

The purpose of this Python code is to parse the `.osm` data, which are downloadable from various links, for example [here](https://www.geofabrik.de/data/download.html), and then parse those data to produce a real road graph, for example, the **car graph**.

## Input

An .osm file, for example, `greece-latest.osm`, or `europe-latest.osm`.

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

