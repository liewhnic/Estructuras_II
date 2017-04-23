#! /usr/bin/python2.7
import math
import argparse

# default files used for simulation
default_programcpu1 = "mem_trace_core1.txt"
default_programcpu2 = "mem_trace_core2.txt"

###############################################################################
"""
Represents cache Level 1
    
    +-----------+
    |   Line0   |
    +-----------+
    |   Line1   |
    +-----------+
    |   ...     |
    +-----------+

"""
class CacheL1:
    def __init__(self, n_lines, n_blocks_pl):
        self.n_lines = n_lines
        self.n_blocks_pl = n_blocks_pl        
        self.lines = []
        for n in range(n_lines):
            self.lines += [LineLru(n_blocks_pl)]

    def read_addr(self, address):
        index = address/2^16
        tag = (address%2^16)/2^5
        offset = address%2^5
        self.lines[index].read(tag)

    def write_addr(self, address):
        index = address/2^16
        tag = (address%2^16)/2^5
        offset = address%2^5
        self.lines[index].read(tag)
        
     def invalidate(self, address):
         None
         # TODO!!!
         
###############################################################################


###############################################################################
"""
Represents a line in a cache, whether is a direct-mapped cache(n_blocks_pl=0)
or a n-way associative cache(n_blocks_pl=n)
    +----------+--------------+--------------+-----+ 
    | LRU bits |    Block0    |    Block1    | ... |
    +----------+--------------+--------------+-----+
    
"""
class LineLru:
    def __init__(self, n_blocks_pl):     
        self.n_lrubits=math.ceil(math.log(n_blocks_pl,2))     
        self.blocks = []
        for n in range(n_blocks_pl):
            self.blocks += [Block()]
###############################################################################


###############################################################################
"""
Represents a line in a cache, whether is a direct-mapped cache(n_blocks_pl=0)
or a n-way associative cache(n_blocks_pl=n)
    +--------------+--------------+-----+ 
    |    Block0    |    Block1    | ... |
    +--------------+--------------+-----+

The blocks include the tag and MESI bits
"""

###############################################################################
            


###############################################################################
"""
Represents a block and the associated MESI bits and tag
    +------+-------+----------+
    | MESI |  Tag  |   Data   |
    +------+-------+----------+
    
"""
class BlockMESI:
    def __init__(self):
        self.MESI = {'M':0, 'E':0, 'S':0, 'I':1}
        self.tag = ""
        self.data = "" # dummy variable
        
    def set_tag(self, tag):
        self.tag = tag
    
    def get_state(self, state_key):
        return self.MESI[state_key]
        
    def set_state(self, state_key, state_value):
        self.MESI[state_key] = state_value



       
    
###############################################################################  
    
    




###############################################################################
"""
Represents cache Level 2
    
    +------------+
    |    Set0    |
    +------------+
    |    Set1    |
    +------------+
    |    ...     |
    +------------+

"""

class CacheL2:
    def __init__(self, n_lines, caches):
        self.caches = caches        
        self.n_lines = n_lines      
        self.lines = []
        for n in range(n_lines):
            self.lines += [Line()]

    def read_addr(self, address):
        index = address/2^12
        tag = (address%2^12)/2^5
        offset = address%2^5
        if self.lines[index].read(tag):
            # hit
            print "READ HIT on L2, address {0}".format(address)
            self.lines[index].update_CVb(, 1)
            return [True, self.lines[index].get_CVb()]
        else:   
            # miss
            print "READ MISS on L2, bringing {0} \
                address from main memory".format(address)
            # now L2 evicts a line, so invalidate snooping is called
            self.snoop_invalidate(address)
            self.lines[index].set_tag(tag)
            self.lines[index].set_CVb([0,0])
            return [False, self.lines[index].get_CVb()]
            
    def snoop_invalidate(self, address):
        """
        Invalidates a given address on all local caches
        """
        for ch in self.caches:
            ch.invalidate(address)
        
    def write_addr(self, address):
        index = address/2^12
        tag = (address%2^12)/2^5
        offset = address%2^5
        self.lines[index].write(tag)


class Line:
    def __init__(self):     
        
        self.block = Block()
            
    def read(self, tag):
        return self.block.read(tag)
        
    def write(self, ):
        self.block.write(tag)
        
        
        
class Block:
    def __init__(self):
        self.tag = ""
        self.data = "" # dummy variable
        self.CVb = [0,0]
        
    def read(self, tag):
        if tag==self.tag:
            return True
        else:
            return False
        
    def set_tag(self, tag):
        self.tag = tag
    
    def get_tag(self):
        return self.tag
        
    def set_CVb(self, new_cvb):
        self.CVb = new_cvb[:]
    
    def update_CVb(self, n, value):
        self.CVb[n] = value
    def get_CVb(self):
        return self.CVb 
###############################################################################       
       
           
    

###############################################################################      

class CpuMaster:
    def __init__(self):
        # create caches
        self.ch_local_cpu1 = CacheL1(256, 2)
        self.ch_local_cpu2 = CacheL1(256, 2)
        self.ch_shared_cpu = CacheL2(4*1024, [self.ch_local_cpu1, self.ch_local_cpu2])
    
    def simulate(self, program_core1, program_core2):
        print "Processing program {0} in core 1".format(program_core1)
        print "Processing program {0} in core 2".format(program_core2)    
        
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
                    # process instruction in cpu1
                    cpu1_instr = cpu1_line.split()
                    address1 = int(cpu1_instr[0])
                    mode1 = cpu1_instr[1]
                    self.execute_cpu1(address1, mode1)
            
            cpu2_line = cpu2_file.readline()
            if cpu2_line:
                # process instruction in cpu2
                cpu2_instr = cpu2_line.split()
                address2 = int(cpu2_instr[0])
                mode2 = cpu2_instr[1]
                self.execute_cpu2(address2, mode2)
                
    def execute_cpu1(self, address, mode):
        # try L1
        hit_L1 = False
        if mode == 'L':
            hit_L1 = self.ch_local_cpu1.read(address)
        elif mode == 'S':
            hit_L1 = self.ch_local_cpu1.write(address)
            # check pending invalidation messages
            # TODO check an execute invalidation messages!!!!
            addr2inv = self.ch_local_cpu1.get_invalidation()
            if addr2inv:
                self.ch_local_cpu2.invalidate(addr2inv)
        else:
            print "Invalid action L/S"
        
        if not hit_L1:
            # try L2
            hit_L2 = False
            if mode == 'L':
                hit_L2 = self.ch_shared_cpu.read(address)
            elif mode == 'S':
                hit_L2 = self.ch_shared_cpu.write(address)
            else:
                print "Invalid action L/S"
            
    def execute_cpu2(self, address, mode):
        # try L1
        hit_L1 = False
        if mode == 'L':
            hit_L1 = self.ch_local_cpu2.read(address)
        elif mode == 'S':
            hit_L1 = self.ch_local_cpu2.write(address)
            # check pending invalidation messages
            # TODO check an execute invalidation messages!!!!
            addr2inv = self.ch_local_cpu2.get_invalidation()
            if addr2inv:
                self.ch_local_cpu1.invalidate(addr2inv)
        else:
            print "Invalid action L/S"       
        
        if not hit_L1:
            # try L2
            hit_L2 = False
            if mode == 'L':
                hit_L2 = self.ch_shared_cpu.read(address)
            elif mode == 'S':
                hit_L2 = self.ch_shared_cpu.write(address)
            else:
                print "Invalid action L/S"             
            
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
