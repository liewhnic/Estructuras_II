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
    |   Set0    |
    +-----------+
    |   Set1    |
    +-----------+
    |   ...     |
    +-----------+

"""
class CacheL1:
    def __init__(self, n_sets, n_blocks_ps):
        self.n_sets = n_sets
        self.n_blocks_ps = n_blocks_ps
        self.sets = []
        for n in range(n_sets):
            self.sets += [SetLru(n_blocks_ps)]

    def read_addr(self, address):
        index = address/2^16
        tag = (address%2^16)/2^5
        offset = address%2^5
        return self.sets[index].read(tag)

    def write_addr(self, address):
        index = address/2^16
        tag = (address%2^16)/2^5
        offset = address%2^5
        return self.sets[index].write(tag)

    def invalidate(self, address):
        index = address/2^16
        tag = (address%2^16)/2^5
        offset = address%2^5
        self.sets[index].set_state("I")

    def delete_block(self, address):
        index = address/2^16
        tag = (address%2^16)/2^5
        offset = address%2^5
        self.sets[index].update(tag)


###############################################################################


###############################################################################
"""
Represents a set in a n-way associative cache(n_blocks_pl=n)
    +----------+--------------+--------------+-----+
    | LRU bits |    Block0    |    Block1    | ... |
    +----------+--------------+--------------+-----+

"""
class SetLru:
    def __init__(self, n_blocks):
        self.lrubit = 0  # indicates last recent used block
        self.blocks = []
        for n in range(n_blocks):
            self.blocks += [BlockMESI()]

    def read(self, tag):
        n = 0
        for bl in self.blocks:
            n += 1
            if bl.get_tag == tag and bl.get_state != "I":
                # value present in L1
                self.lrubit = n
                return bl.get_state

        # value not present in L1
        return "I"

    def write(self, tag):
        #Set state to modified
        self.blocks[self.lrubit].set_state("M")
        self.update(tag)

    def update(self, tag):
        prev_state = self.blocks[self.lrubit].get_state()
        if prev_state == "I":
            # do nothing
            continue

        self.blocks[self.lrubit].set_tag(tag)


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
    def __init__(self, n_sets, caches):
        self.caches = caches
        self.n_sets = n_sets
        self.sets = []
        for n in range(n_sets):
            self.sets += [BlockMESI()]

    def read_addr(self, address, cache_num):
        index = address/2^12
        tag = (address%2^12)/2^5
        offset = address%2^5
        if self.sets[index].read(tag):
            # hit
            print "READ HIT on L2, address {0}".format(address)
            self.sets[index].update_CVb(cache_num, 1)
            return [True, self.sets[index].get_CVb()]

        else:
            # miss
            print "READ MISS on L2, bringing {0} \
                address from main memory".format(address)
            # now L2 evicts a line, so invalidate snooping is called
            self.snoop_invalidate(address)
            self.sets[index].set_tag(tag)
            self.sets[index].set_CVb([0,0])
            return [False, self.sets[index].get_CVb()]

    def snoop_invalidate(self, address):
        """
        Invalidates a given address on all local caches
        """
        for ch in self.caches:
            ch.invalidate(address)

    def write_addr(self, address, cache_num):
        index = address/2^12
        tag = (address%2^12)/2^5
        offset = address%2^5
        self.lines[index].write(tag, cache_num)
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
        self.MESI = "I"
        self.tag = ""
        self.data = "" # dummy variable

    def get_tag(self):
        return self.tag

    def set_tag(self, tag):
        self.tag = tag

    def get_state(self):
        return self.MESI

    def set_state(self, state_value):
        self.MESI = state_value
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
        state_L1 = self.ch_local_cpu1.read(address)
        if state_L1 in "EMS":
            hit_L1 = True
        else:
            hit_L1 = False
            # if not in L1 then try L2
            state_L2 = self.ch_shared_cpu.read(address)
            if state_L2 in "EMS":
                hit_L2 = True
            else:
                hit_L2 = False

        # reading
        if mode == 'L':
            print "CPU1: Read address {0}".format(address)

            if hit_L1:
                    print "CPU1: Read HIT L1, address {0}".format(address)
                    # remain in previous state, finish execution
                    return

            else:
                    print "CPU1: Read MISS L1, address {0}".format(address)
                    # next step is to check in L2

                    self.delete_procL1(address)

                    if hit_L2:
                        print "CPU1: Read HIT L2, address {0}".format(address)

                        # check for other L1 copy
                        mode_copy_cpu2 = self.ch_local_cpu2.read(address)

                        if mode_copy_cpu2 == "M":
                            print "Found modified entry in CPU2, address {0}".format(address)
                            print "CPU2: Write back to L2, address {0}".format(address)
                            self.ch_local_cpu2.set_mode(address, "I")
                            self.ch_local_cpu1.update_set(address, "E")
                            self.ch_shared_cpu.set_mode(address, "S")

                        elif mode_copy_cpu2 == "S":
                            self.ch_local_cpu1.update_set(address, "S")
                            self.ch_shared_cpu.set_mode(address, "S")

                        elif mode_copy_cpu2 == "E":
                            self.ch_local_cpu2.set_mode(address, "S")
                            self.ch_local_cpu1.update_set(address, "S")
                            self.ch_shared_cpu.set_mode(address, "S")

                        else:
                            self.ch_local_cpu1.update_set(address, "E")
                            self.ch_shared_cpu.set_mode(address, "S")

                    else:
                        print "CPU1: Read MISS L2, address {0}, must read from memory".format(address)
                        self.delete_procL2(address)
                        self.ch_local_cpu1.update_set(address, "E")
                        self.ch_shared_cpu.set_mode(address, "S")

        # writing
        elif mode == 'S':
            print "CPU1: Write to address {0}".format(address)
            # TODO
            if hit_L1:
                if state_L1 in "EM":
                    print "CPU1: Write HIT L1, address {0}".format(address)
                    self.ch_local_cpu1.set_mode(address, "M")
                elif state_L1 == "S":
                    print "CPU1: Write HIT L1, address {0}".format(address)
                    print "CPU1: But there is a copy in cpu2, invalidating cpu2 local cache block, address {0}".format(address)
                    self.ch_local_cpu1.set_mode(address, "M")
                    self.ch_local_cpu2.set_mode(address, "I")
                return

            else:
                print "CPU1: Write MISS L1, address {0}".format(address)
                self.delete_procL1(address)

                if hit_L2:
                    print "CPU1: Write HIT L2, address {0}".format(address)

                    state_L1cpu2 = self.ch_local_cpu2.read(address)
                    if state_L1cpu2 in "MES":
                        print "CPU2: Invalidating copy, address {0}".format(address)
                        self.ch_local_cpu1.update_set(address, "M")
                        self.ch_local_cpu2.set_mode(address, "I")
                        self.ch_shared_cpu.set_mode(address, "S")
                    else:
                        self.ch_local_cpu1.update_set(address, "M")
                        self.ch_shared_cpu.set_mode(address, "S")
                else:
                    print "CPU1: Write MISS L2, address {0}".format(address)
                    self.delete_procL2(address)
                    self.ch_local_cpu1.update_set(address, "M")
                    self.ch_shared_cpu.update_set(address, "S")


        else:
            print "Invalid action: {0}".format(mode)

    def execute_cpu2(self, address, mode):
        None

    def delete_procL1(self, address):
        address = self.ch_local_cpu1.get_similar(address)
        mode_L1 = self.ch_local_cpu1.read(address)

        if mode_L1 in "ESI":
            None # No action required

        elif mode_L1 == "M":
            print "Value to overwrite in L1 cpu1 is in M state, " \
                  "write back to L2, address {0}".format(address)
            self.ch_shared_cpu.set_mode(address, "M")

        else:
            print "Invalid mode in L1 cpu1: {0}".format(mode_L1)

    def delete_procLL1(self, address):
        address = self.ch_local_cpu2.get_similar(address)
        mode_LL1 = self.ch_local_cpu2.read(address)

        if mode_LL1 in "ESI":
            None  # No action required

        elif mode_LL1 == "M":
            print "Value to overwrite in L1 cpu2 is in M state, " \
                  "write back to L2, address {0}".format(address)
            self.ch_shared_cpu.set_mode(address, "M")

        else:
            print "Invalid mode in L1 cpu2: {0}".format(mode_LL1)

    def delete_procL2(self, address):

        address = self.ch_shared_cpu.get_similar(address)

        # get state
        mode_L2 = self.ch_shared_cpu.read(address)

        if mode_L2 in "EI":
            None # No action required

        elif mode_L2 == "M":
            print "Value to overwrite in L2 is in M state, " \
                  "write back to memory, address {0}".format(address)

        elif mode_L2 == "S":
            # invalidate L1 entries
            self.ch_local_cpu1.set_mode(address, "I")
            self.ch_local_cpu2.set_mode(address, "I")

        else:
            print "Invalid mode in L2: {0}".format(mode_L2)

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
