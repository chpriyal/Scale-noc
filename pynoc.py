#!/usr/bin/env python3
#Write parsing logic
ports = 2
arrays = 4
tracesrcif = "./Layer-scale-sram/outputs/alexnet_is_64x64/layer_wise/alexnet_is_64x64_Conv1_dram_ifmap_read.csv"
tracesrcof = "./Layer-scale-sram/outputs/alexnet_is_64x64/layer_wise/alexnet_is_64x64_Conv1_dram_ofmap_write.csv"
tracesrcfilt = "./Layer-scale-sram/outputs/alexnet_is_64x64/layer_wise/alexnet_is_64x64_Conv1_dram_filter_read.csv"
linkwidth = 4

buf_len = 10000

class trace:
    def __init__(self,path):
        self.path = path
        self.file_ptr = open(path,"r")
        self.readbuf = []
        # self.read_cursor = 0 #next word to read/ If word to read is greater then num words in line move to next line
        self.line_cursor = 0 #line to read
        self.curr_epoch_address = []
        self.epoch_num = 0
        self.eof = False
        # i=0
        for line in (self.file_ptr):
            # print(line)
            cols = [(l.strip()) for l in line.strip().split(",") if l.strip() != ""]
            cycle = cols[0]
            cols = cols[1:]
            self.line_cursor+=1
            self.curr_epoch_address += cols
            # print(cycle)
            # i+=1
            if(float(cycle)==-1):
                break
        # exit()
        # print(self.curr_epoch_address)
        self.epoch_size = len(self.curr_epoch_address)

    def getbuf_line(self):
        while(not self.eof):
            if len(self.readbuf)==0:
                for i in range(buf_len):
                    line = self.file_ptr.readline()
                    if line:
                        self.readbuf.append(line)
                    else:
                        return 
            if len(self.readbuf)>0:
                retstr = self.readbuf.pop(0)
                if retstr:
                    yield retstr
         
    def refill_epoch_trace(self):
        self.epoch_num+=1
        for line in self.file_ptr:
            cols = [(l.strip()) for l in line.strip().split(",") if l.strip() != ""]
            cycle = cols[0]
            cols = cols[1:]
            self.line_cursor+=1
            self.curr_epoch_address += cols
            assert(len(self.curr_epoch_address)<=self.epoch_size)
            if(len(self.curr_epoch_address)==self.epoch_size):
                return
        self.eof = True
        # self.file_ptr.close()

    def get_next_n_addr(self, n):
        popcount = min(n,len(self.curr_epoch_address))
        retaddr = self.curr_epoch_address[0:popcount]
        self.curr_epoch_address = self.curr_epoch_address[popcount:]
        if(len(self.curr_epoch_address)==0):
            self.refill_epoch_trace()
        return retaddr

    def iseof(self):
        return len(self.curr_epoch_address)==0 and self.eof

tracelist = []
for i in range(arrays):
    tracelist.append(trace(tracesrcif))
    tracelist.append(trace(tracesrcof))
    tracelist.append(trace(tracesrcfilt))
    


cycle = 0
arbitration_map = {}


for i in range(ports):
    arbitration_map[i]= None
noc_dram_trace = open("outfile",'w')
total_addr_fetched = 0
index = 0
exitflag = False
writeBuf = []
while(not exitflag):
    #Arbitration Logic
    for port in arbitration_map:
        found_node = False
        for sub_index in range (len(tracelist)):
            iter_index = (index + sub_index) % len(tracelist)
            if(not (tracelist[iter_index].iseof()) and iter_index not in arbitration_map.values()):
                arbitration_map[port] = iter_index
                index = (iter_index+1) % len(tracelist)
                found_node = True
                break
        if not found_node:
            arbitration_map[port] = None
    
    # get all addr for this cycles 
    this_cycle_addr = []
    exitflag = True
    for port in arbitration_map:
        if arbitration_map[port] != None:
            exitflag = False
            addr = tracelist[arbitration_map[port]].get_next_n_addr(linkwidth)
            this_cycle_addr += addr
            total_addr_fetched += len(addr)
    
    # Append to file
    writestr = ", ".join(this_cycle_addr)
    writestr = str(cycle+2)+" :\t"+writestr+"\n"
    writeBuf.append(writestr)
    if (cycle%1000==0):
        print("Cycle: {} , ReqSize: {}".format(cycle,len(this_cycle_addr)))
    if(len(writeBuf)>buf_len):
        noc_dram_trace.write("".join(writeBuf))
        writeBuf = []
    cycle += 1
        
if(len(writeBuf)>0):
    noc_dram_trace.write("".join(writeBuf))
noc_dram_trace.close()
print("-"*20)
print("Cycle Count: "+str(cycle))
print("Address Count: "+ str(total_addr_fetched))
print("Average NOC Bandwidth" + str(total_addr_fetched/cycle))
