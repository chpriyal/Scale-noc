#!/usr/bin/env python3
from itertools import cycle
import os 
import sys
import re
import pandas as pd
import math
import glob


############
# LINKWIDTH = 8
# DRAM_PORTS = 4
cfg_path = "/usr/scratch/pchhatrapati3/kfinal/Layer-scale-sram/configs/google.cfg"

base_path= "/usr/scratch/pchhatrapati3/kfinal"
LINKWIDTH_SWEEP = [1,2,4,8,16,32,64]
DRAM_PORTS_SWEEP = [1,2,4,8]
SPLIT_SWEEP = ["Layer-scale-sram","Tile-scale-sram"]


############

def parse_cfg(cfg_path):
    with open(cfg_path,"r") as tgt:
        lines = tgt.readlines()
    flag = True
    cfg = dict()
    for line in lines:
        if "[architecture_presets]" in line:
            flag = False
        if flag:
            continue
        
        items = line.split(":")
        if len(items) == 2:
            key = items[0].strip()
            strvalue = items[1].strip()
            try:
                value = int(strvalue)
            except:
                value = strvalue
            cfg[key] = value
    return cfg

def read_csv(path,converter_map= None, sep=",",strip=True):
    with open(path,"r") as tgt:
        csv = tgt.readlines()
    
    csv = [l.split(sep) for l in csv] 
    for i in range(len(csv)):
        csv[i] = [x.strip() for x in csv[i]]
    header = csv[0]
    data = csv[1:]
    outdata = []
    for row in data:
        frame = dict()
        for index,col in enumerate(header):
            if col != "":
                if col in converter_map:
                    val = converter_map[col](row[index])
                else :
                    val = row[index]
                frame[col] = val
        outdata.append(frame)
    return outdata


convert_map={
        "Layer":str,	
        "DRAM_IFMAP_start":float,	
        "DRAM_IFMAP_stop":float,	
        "DRAM_IFMAP_bytes"	:float,
        "DRAM_Filter_start"	:float,
        "DRAM_Filter_stop":float,
        "DRAM_Filter_bytes"	:float,
        "DRAM_OFMAP_start":float,
        "DRAM_OFMAP_stop":float,
        "DRAM_OFMAP_bytes":float,
        "SRAM_read_start":float,
        "SRAM_read_stop":float,
        "SRAM_read_bytes":float,
        "SRAM_write_start":float,
        "SRAM_write_stop":float,
        "SRAM_write_bytes":float,
    }


def get_read_cycles(layer_details,words_per_epoch,linkwidth, in_read_ports, out_ports,include_pretectch=True):
    cycles = dict()
    for trace in ["IFMAP","Filter"]:
        bytes_to_fetch = layer_details["DRAM_"+trace+"_bytes"]
        if not include_pretectch :
            bytes_to_fetch  = bytes_to_fetch - words_per_epoch[trace]
        
        cycles[trace] = float(bytes_to_fetch) / float(linkwidth) * float(in_read_ports) / float(out_ports)
    # print(cycles)
    return max(cycles.values()) + (in_read_ports-1)

def get_write_cycles(layer_details,linkwidth, in_write_ports, out_ports):
    trace = "OFMAP"
    bytes_to_fetch = layer_details["DRAM_"+trace+"_bytes"]
    write_start = layer_details["DRAM_"+trace+"_start"]
    read_stop = max(layer_details["DRAM_IFMAP_stop"],layer_details["DRAM_Filter_stop"])
    compute_time = write_start - read_stop
    cycles = float(bytes_to_fetch) / float(linkwidth) * float(in_write_ports) / float(out_ports)
    # print("Compute:", compute_time)
    # print("OFMAP:",cycles+ (in_write_ports-1))
    return cycles + (in_write_ports-1) + compute_time
    pass

def get_words_per_epoch(tracepath):
    with open(tracepath) as tgt:
        words = 0
        for line in tgt:
            cols = line.split(",")
            try:
                cycle = float(cols[0].strip())
            except:
                print(line)
                print(cols)
                sys.exit(-1)
            cols = cols[1:]
            words +=   len(cols)-1
            if(cycle==-1):
                break
    return words


def get_cycles(src,suffix,num_arrays):
    details_path = "/".join([src,suffix+"_detail.csv"])
    details = read_csv(details_path,converter_map=convert_map)
    prefetch= False
    layer_cycles=dict()
    for layer in details:
        layer_name = layer["Layer"]
        # print(layer_name)
        words_per_epoch = dict()
        words_per_epoch["IFMAP"]= get_words_per_epoch("/".join([src,"layer_wise",suffix+"_"+layer_name+"_dram_ifmap_read.csv"]))
        words_per_epoch["Filter"]=get_words_per_epoch("/".join([src,"layer_wise",suffix+"_"+layer_name+"_dram_filter_read.csv"]))
        
        readcycles = get_read_cycles(layer_details=layer,
                                words_per_epoch=words_per_epoch,
                                linkwidth=LINKWIDTH,
                                in_read_ports=num_arrays*2,
                                out_ports=DRAM_PORTS,
                                include_pretectch=prefetch)
        writecycles = get_write_cycles(layer_details=layer,
                                linkwidth=LINKWIDTH,
                                in_write_ports=num_arrays,
                                out_ports=DRAM_PORTS)
        layer_cycles[layer_name] = readcycles + writecycles
        # print("Cycles:",layer_cycles)
        prefetch = True
    return layer_cycles




cfg = parse_cfg(cfg_path=cfg_path)
DATA = [["WORKLOAD","DATAFLOW","LAYER_NAME","SPLIT","NUM_ARRAYS","HEIGHT","WIDTH","LINKWIDTH","DRAMPORTS","Cycles"]]
progress_bar = 0
total_progress = len(LINKWIDTH_SWEEP)* len(DRAM_PORTS_SWEEP) * len(SPLIT_SWEEP) 
for LINKWIDTH in LINKWIDTH_SWEEP:
    for DRAM_PORTS in DRAM_PORTS_SWEEP:
        for split in SPLIT_SWEEP:

            print(str(progress_bar/total_progress * 100.0) +r"% completed")
            progress_bar+=1
            scalesim_outputs_path = "/".join([base_path,split,"outputs"])
            for src in glob.glob(scalesim_outputs_path+"/*"):
                
                suffix = src.rstrip("/").split("/")[-1]
                print(LINKWIDTH,DRAM_PORTS,split,suffix)
                array_height = int(suffix.split("_")[-1].split("x")[0])
                array_width = int(suffix.split("_")[-1].split("x")[1])
                dnn =  suffix.split("_")[0]
                data_flow =  suffix.split("_")[1]
                num_arrays = int(cfg["ArrayHeight"]*cfg["ArrayWidth"]/(array_height*array_width))

                layer_cycles = get_cycles(src,suffix,num_arrays)
                for layer,cycles in layer_cycles.items():
                    dat = [dnn,data_flow,layer,split,num_arrays,array_height,array_width,LINKWIDTH,DRAM_PORTS,cycles]
                    dat = [str(x) for x in dat]
                    DATA.append(dat)
                    # print("layer:",layer,"Cycles = ",cycles)



with open("Ananlysis.csv","w") as tgt:
    tgt.write("\n".join([",".join(d) for d in DATA]))