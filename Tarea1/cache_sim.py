#! /usr/bin/python2.7
import math
import argparse

# default files used for simulation
default_programcpu1 = "mem_trace_core1.txt"
default_programcpu2 = "mem_trace_core2.txt"

###############################################################################
"""
Represents a cache
    
    +-----------+
    |   Line0   |
    +-----------+
    |   Line1   |
    +-----------+
    |   ...     |
    +-----------+

"""
class Cache:
    def __init__(n_lines, n_blocks_pl, tag_length, block_length):
        self.n_lines = n_lines
        self.n_blocks_pl = n_blocks_pl        
        self.lines = []
        for n in range(n_lines):
            self.lines += [Line(n_blocks_pl)]

###############################################################################

        
###############################################################################
"""
Represents a line in a cache, whether is a direct-mapped cache(n_blocks_pl=0)
or a n-way associative cache(n_blocks_pl=n)
    +----------+--------------+--------------+-----+ 
    | LRU bits |    Block0    |    Block1    | ... |
    +----------+--------------+--------------+-----+
    
"""
class Line:
    def __init__(n_blocks_pl):     
        self.n_lrubits=math.ceil(math.log(n_blocks_pl,2))     
        self.blocks = []
        for n in range(n_blocks_pl):
            self.blocks += [Block()]
###############################################################################


###############################################################################
"""
Represents a block
    +---+---+---+---+-------+----------+
    | M | E | S | I |  Tag  |   Data   |
    +---+---+---+---+-------+----------+
    
"""
class Block:
   def __init__():
        self.MESI = {'M':0, 'E':0, 'S':0, 'I':1}
        self.tag = ""
        self.data = "" # dummy variable
        
    def set_tag(self, tag):
        self.tag = tag
    
    def get_state(state_key):
        return self.MESI[state_key]
        
    def set_state(state_key, state_value):
        self.MESI[state_key] = state_value
###############################################################################      
    

###############################################################################      

class CpuMaster:
    def __init__(self):
        # create caches
        self.ch_local_cpu1 = Cache()
        self.ch_local_cpu2 = Cache()
        self.ch_shared_cpu = Cache()
    
    def simulate(self, program_core1, program_core2):
        print "Processing program {0} in core 1".format(args.program_core1)
        print "Processing program {0} in core 2".format(args.program_core2)    
        
        cpu1_file = open(program_core1, "r")
        cpu2_file = open(program_core2, "r")
        # dummy values just to enter the loop    
        cpu1_line = "x"
        cpu2_line = "x"
         
        # begin simulation
        while cpu1_line or cpu2_line:
            for n in range(3):
                cpu1_line = cpu1_file.readline()
                if cpu1_line:
                    # process instruction
                    
            
            cpu2_line = cpu2_file.readline()
            if cpu2_line:
                # process instruction
            
            
###############################################################################
def main():
     # Obtaining parameters from cli
    parser = argparse.ArgumentParser(
        description='''Simulates the use of a multilevel cache, used by two cores''')
        
    parser.add_argument('program_core1',nargs='?', 
                        default=default_programcpu1, 
                        help='program to execute with cpu1')
    parser.add_argument('program_core2',nargs='?', 
                        default=default_programcpu2, 
                        help='program to execute with cpu2')    
    args = parser.parse_args()
    
    
    cores = CpuMaster() # manages the two cores
    
    # begins simulation
    cores.simulate(args.program_core1, args.program_core2)
        
if __name__ == "__main__":
    main()
