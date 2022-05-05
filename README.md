# Scale-noc
##Introduction
This is a github repository for the code for NOC extention to the scale sim.
Using this, one can estimate the scale up vs scale out apporach of scaling systolic arrays and how NOCs affect it.
This model assumes a crossbar topology and builds upon scalesim.

##Requirements

Getting started is simple! This repository is completely written in python. At the moment, it has dependencies on the following python packages. Make sure you have them in your environment.

* os
* subprocess
* math
* configparser
* tqdm
* absl-py


*NOTE: Scale-Noc needs python3 to run correctly. If you are using python2, you might run into typecasting errors* 


##Run the experiment

It will run alexnet as its network topology and google TPU config as its 
* Run the command: ```python3 Layer-scale-sram/scale.py```
* Wait for the run to finish
* Run the command: ```python3 Tile-scale-sram/scale.py```
* Wait for the run to finish
* Run the command: ```python3 scalenoc.py```
* Wait for the run to finish

#Output
Estimates the number of cycles taken by scale up and scale out systems with 2 workload splitting schemes(Tile wise and Filter wise)
