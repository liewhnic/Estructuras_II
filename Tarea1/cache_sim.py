#! /usr/bin/python2.7
import argparse
import csv

# default files used for simulation
default_programcpu1 = "mem_trace_core1.txt"
default_programcpu2 = "mem_trace_core2.txt"


###############################################################################
# CSV data logger, writes number of misses per cache to a csv file
filename_csv = 'misses_dat.csv'


class CSVLog:

    def __init__(self):
        with open(filename_csv, 'w') as csvfile:
            # sets header and fields
            self.fieldnames = ['Cycle CPU1', 'Cycle CPU2', 'Misses L1 CPU1', 'Misses L1 CPU2', 'Misses L2']
            self.writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames)
            self.writer.writeheader()

    def write(self, cyclecpu1, cyclecpu2, missesL1, missesLL1, missesL2):
        """
        Adds a row to the csv file.
        :param cyclecpu1: Number of cycles for the cpu1.
        :param cyclecpu2: Number of cycles for the cpu2.
        :param missesL1: Number of misses for the L1-cpu1 cache.
        :param missesLL1: Number of misses for the L1-cpu2 cache.
        :param missesL2: Number of misses for the L2 shared cache.
        :return: None
        """
        with open(filename_csv, 'a') as csvfile:
            self.writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames)
            self.writer.writerow({'Cycle CPU1': cyclecpu1, 'Cycle CPU2': cyclecpu2,
                                  'Misses L1 CPU1': missesL1, 'Misses L1 CPU2': missesLL1,
                                  'Misses L2': missesL2})


###############################################################################
# Functions for addresses manipulation
def get_fields(address, tagb, indexb):
    """
    Extracts the index, tag and offset values from a given address.
    :param address: Int, memory address to parse.
    :param tagb: bit position of first tag bit.
    :param indexb: bit position of first index bit.
    :return: index, tag and offset as a list of ints.
    """
    index = address/(2**indexb)
    tag = (address % (2**indexb))/(2**tagb)
    offset = (address % (2**tagb))
    return [index, tag, offset]


def form_address(index, indexb, tag, tagb, offset):
    """
    Forms the full address, given an index, tag and offset, the bit positions
    of index and tag are necessary to form the address
    :param index: Int.
    :param indexb: Int, bit position of first index bit.
    :param tag: Int.
    :param tagb: Int, bit position of first tag bit.
    :param offset: Int.
    :return: Int, the corresponding formed address.
    """
    return index*(2**indexb)+tag*(2**tagb)+offset


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
        """
        Creates a L1 cache.
        :param n_sets: Number of sets in the cache.
        :param n_blocks_ps: Number of blocks per set.
        """
        self.n_sets = n_sets
        self.n_blocks_ps = n_blocks_ps
        self.sets = []
        for n in range(n_sets):
            self.sets += [SetLru(n_blocks_ps)]

    def read(self, address):
        """
        Returns the state of a block in the L1 cache, given an address.
        :param address: Int, memory address.
        :return: Returns the state of a given address in the L1 cache, where the state may be
        M(Modified), E(Exclusive), S(Shared), I(Invalid) and N(Not present) is used to indicate that there is no
        corresponding entry.
        """
        [index, tag, offset] = get_fields(address, 5, 16)
        return self.sets[index].read(tag)

    def set_state(self, address, mode):
        """
        Sets the state of a given block in the L1 cache.
        :param address: Int, memory address.
        :param mode: New block state, may be [MESI].
        :return: None.
        """
        [index, tag, offset] = get_fields(address, 5, 16)
        self.sets[index].set_state(tag, mode)

    def update_set(self, address, state):
        """
        Writes a tag and a corresponding state to L1 cache.
        :param address: Int, memory address.
        :param state: State for the corresponding new block, may be [MESI].
        :return: None.
        """
        [index, tag, offset] = get_fields(address, 5, 16)
        self.sets[index].update_set(tag, state)

    def get_similar(self, address):
        """
        Gets the address of block in L1 cache that it is about to be replaced.
        :param address: Int, memory address of the new value.
        :return: Int, memory address of the block to be replaced by the new block.
        """
        [index, tag, offset] = get_fields(address, 5, 16)
        existent_tag = self.sets[index].get_lrutag()
        return form_address(index, 16, existent_tag, 5, 0)

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
        """
        Creates a n-way set associative, where n=n_blocks.
        :param n_blocks: Number of blocks per set.
        """
        self.n_blocks = n_blocks
        self.lrubits = [1]*self.n_blocks  # indicates least recent used block
        self.lrubits[0] = 0
        self.blocks = []
        for n in range(n_blocks):
            self.blocks += [BlockMESI()]

    def read(self, tag):
        """
        Returns the state of a block in the set, given a tag.
        :param tag: Int.
        :return: Returns the state of a given address in the L1 cache, where the state may be
        M(Modified), E(Exclusive), S(Shared), I(Invalid) and N(Not present) is used to indicate that there is no
        corresponding entry.
        """
        # tries to find valid blocks
        n = 0
        for bl in self.blocks:
            if bl.get_tag() == tag and bl.get_state() != "I":
                # value present in L1
                self.lrubits = [1]*self.n_blocks
                self.lrubits[n] = 0
                return bl.get_state()
            n += 1

        # if there are no valid blocks, search for invalid blocks
        n = 0
        for bl in self.blocks:
            if bl.get_tag() == tag:
                # value present in L1
                self.lrubits = [1] * self.n_blocks
                self.lrubits[n] = 0
                return bl.get_state()
            n += 1

        # value not present in L1
        return "N"

    def update_set(self, tag, state):
        """
        Writes a tag and a corresponding state to the set, according to the LRU bits.
        :param tag: Int.
        :param state: State for the new block, may be [MESI].
        :return: None.
        """
        block_idx = self.lrubits.index(1)  # finds LRU block
        self.blocks[block_idx].set_tag(tag)  # overwrites that block
        self.blocks[block_idx].set_state(tag, state)
        self.lrubits = [1] * self.n_blocks
        self.lrubits[block_idx] = 0  # now the state is recent

    def set_state(self, tag, state):
        """
        Sets the state of a block in the set, given a tag.
        :param tag: Int.
        :param state: State for the new block, may be [MESI].
        :return: None.
        """
        n = 0
        for bl in self.blocks:
            n += 1
            if bl.get_tag == tag:
                # value present in L1
                self.blocks[n].set_state(tag, state)

    def get_lrutag(self):
        """
        Returns the tag of the LRU block.
        :return: Int, tag of LRU block.
        """
        return self.blocks[self.lrubits.index(1)].get_tag()


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
    def __init__(self, n_sets):
        """
        Creates a direct-mapped cache L2, with a given number of sets.
        :param n_sets: Number of sets in the cache.
        """
        self.n_sets = n_sets
        self.sets = []
        for n in range(n_sets):
            self.sets += [BlockMESI()]

    def read(self, address):
        """
        Gets the state of a block in the cache, given an address.
        :param address:
        :return: State of the block, may be [MESI], if it's not present returns [N].
        """
        [index, tag, offset] = get_fields(address, 5, 12)
        return self.sets[index].read(tag)

    def update_set(self, address, state):
        """
        Writes a tag and a corresponding state to the set.
        :param tag: Int.
        :param state: State for the new block, may be [MESI].
        :return: None.
        """
        [index, tag, offset] = get_fields(address, 5, 12)
        self.sets[index].set_tag(tag)
        self.sets[index].set_state(tag, state)

    def set_state(self, address, state):
        """
        Sets the state of a block in the set, given a tag.
        :param tag: Int.
        :param state: State for the new block, may be [MESI].
        :return: None.
        """
        [index, tag, offset] = get_fields(address, 5, 12)
        self.sets[index].set_state(tag, state)

    def get_similar(self, address):
        """
        Gets the address of the block in the L2 cache, that it is about to be replaced by a new block.
        :param address: Int, new block address.
        :return: Int, block address to be replaced.
        """
        [index, tag, offset] = get_fields(address, 5, 12)
        existent_tag = self.sets[index].get_tag()
        return form_address(index, 12, existent_tag, 5, 0)

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
        """
        Creates a block, with an invalid state and meaningless tag and data.
        """
        self.MESI = "I"
        self.tag = 0
        self.data = 0  # dummy variable

    def read(self, tag):
        """
        Returns the state for a given tag.
        :param tag: Int.
        :return: State for the corresponding block, where state may be [MESI], if it's not present returns [N].
        """
        if self.tag == tag:
            return self.MESI
        else:
            return "N"

    def get_tag(self):
        """
        Gets tag of block.
        :return: Int.
        """
        return self.tag

    def set_tag(self, tag):
        """
        Sets the tag for the block.
        :param tag: Int.
        :return: None.
        """
        self.tag = tag

    def get_state(self):
        """
        Gets the state of the block.
        :return: State for the corresponding block, where state may be [MESI].
        """
        return self.MESI

    def set_state(self, tag, state_value):
        """
        Sets the states of the block with a given tag, if the tags are different there is no change in the block state.
        :param tag: Int.
        :param state_value: New block state, where state may be [MESI]
        :return: None.
        """
        if self.tag == tag:
            self.MESI = state_value
###############################################################################


###############################################################################
# Handles the execution(simulation) of instructions and the state of caches blocks.
class CpuMaster:
    def __init__(self):

        # create caches
        self.ch_local_cpu1 = CacheL1(256, 2)
        self.ch_local_cpu2 = CacheL1(256, 2)
        self.ch_shared_cpu = CacheL2(4*1024)

        # relevant info about performance
        self.missesL1 = 0       # misses in L1-cpu1
        self.missesLL1 = 0      # misses in L1-cpu2
        self.missesL2 = 0       # misses in L2
        self.cyclecpu1 = 0      # number of clock cycle for the cpu1
        self.cyclecpu2 = 0      # number of clock cycle for the cpu2

    def simulate(self, program_core1, program_core2):
        """
        Reads the read/write commands from a file and simulates them.
        :param program_core1: File name, memory trace for the cpu1.
        :param program_core2: File name, memory trace for the cpu2.
        :return: None.
        """
        print "Processing program {0} in core 1".format(program_core1)
        print "Processing program {0} in core 2".format(program_core2)

        cpu1_file = open(program_core1, "r")
        cpu2_file = open(program_core2, "r")
        # dummy values just to enter the loop
        cpu1_line = "x"
        cpu2_line = "x"

        # miss counters
        self.missesL1 = 0
        self.missesLL1 = 0
        self.missesL2 = 0
        self.cyclecpu1 = 0
        self.cyclecpu2 = 0

        # saves performance info
        log_misses = CSVLog()

        # begin simulation
        while cpu1_line or cpu2_line:
            for n in range(3):
                cpu1_line = cpu1_file.readline()
                if cpu1_line:
                    # process instruction in cpu1
                    cpu1_instr = cpu1_line.split()
                    address1 = int(cpu1_instr[0], 16)
                    mode1 = cpu1_instr[1]
                    self.execute_cpu1(address1, mode1)
                    log_misses.write(self.cyclecpu1, self.cyclecpu2, self.missesL1, self.missesLL1, self.missesL2)
                    self.cyclecpu1 += 1
                else:
                    print "{0}: There are no more lines to execute".format("CPU1")
                    
            cpu2_line = cpu2_file.readline()
            if cpu2_line:
                # process instruction in cpu2
                cpu2_instr = cpu2_line.split()
                address2 = int(cpu2_instr[0], 16)
                mode2 = cpu2_instr[1]
                self.execute_cpu2(address2, mode2)
                log_misses.write(self.cyclecpu1, self.cyclecpu2, self.missesL1, self.missesLL1, self.missesL2)
                self.cyclecpu2 += 1
            else:
                print "{0}: There are no more lines to execute".format("CPU2")
    def execute_cpu1(self, address, mode):
        """
        Simulates read/write of address in cpu1.
        :param address: Int, memory address to read/write.
        :param mode: Read/write mode, may be L(Read) or S(Write).
        :return: None.
        """
        self.execute_cpu(address=address, mode=mode, local_cache=self.ch_local_cpu1, local_cache_name="CPU1",
                         extraneous_cache=self.ch_local_cpu2, extraneous_cache_name="CPU2")

    def execute_cpu2(self, address, mode):
        """
        Simulates read/write of address in cpu2.
        :param address: Int, memory address to read/write.
        :param mode: Read/write mode, may be L(Read) or S(Write).
        :return: None.
        """
        self.execute_cpu(address=address, mode=mode, local_cache=self.ch_local_cpu2, local_cache_name="CPU2",
                         extraneous_cache=self.ch_local_cpu1, extraneous_cache_name="CPU1")

    def execute_cpu(self, address, mode, local_cache, local_cache_name, extraneous_cache, extraneous_cache_name):
        """
        Generic method to execute a read/write instruction.
        :param address: Int, memory address to read/write.
        :param mode: Read/write mode, may be L(Read) or S(Write).
        :param local_cache: CacheL1 object, corresponds to local cache,
        defined by from where is the instruction running.
        :param local_cache_name: String, name of local cache.
        :param extraneous_cache: CacheL1 object, corresponds to additional cache,
        the instruction is not running from here running.
        :param extraneous_cache_name: String, name of additional cache.
        :return: None.
        """

        hit_L2 = False
        # try L1
        state_L1 = local_cache.read(address)

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
            print "{0}: Read address {1}".format(local_cache_name, address)

            if hit_L1:
                    print "{0}: Read HIT L1, address {1}".format(local_cache_name, address)
                    # remain in previous state, finish execution
                    return

            else:
                    print "{0}: Read MISS L1, address {1}".format(local_cache_name, address)
                    if local_cache_name == "CPU1":
                        self.missesL1 += 1
                    elif local_cache_name == "CPU2":
                        self.missesLL1 += 1

                    # next step is to check in L2

                    self.delete_procL1(address)

                    if hit_L2:
                        print "CPU1: Read HIT L2, address {0}".format(address)

                        # check for other L1 copy
                        mode_copy_cpuext = extraneous_cache.read(address)

                        if mode_copy_cpuext == "M":
                            print "Found modified entry in {0}, address {1}".format(extraneous_cache_name, address)
                            print "{0}: Write back to L2, address {1}".format(extraneous_cache_name, address)
                            extraneous_cache.set_state(address, "I")
                            local_cache.update_set(address, "E")
                            self.ch_shared_cpu.set_state(address, "S")

                        elif mode_copy_cpuext == "S":
                            local_cache.update_set(address, "S")
                            self.ch_shared_cpu.set_state(address, "S")

                        elif mode_copy_cpuext == "E":
                            extraneous_cache.set_state(address, "S")
                            local_cache.update_set(address, "S")
                            self.ch_shared_cpu.set_state(address, "S")

                        else:
                            local_cache.update_set(address, "E")
                            self.ch_shared_cpu.set_state(address, "S")

                    else:
                        self.missesL2 += 1
                        print "{0}: Read MISS L2, address {0}, must read from memory".format(local_cache_name, address)
                        self.delete_procL2(address)
                        local_cache.update_set(address, "E")
                        self.ch_shared_cpu.update_set(address, "S")

        # writing
        elif mode == 'S':
            print "{0}: Write to address {1}".format(local_cache_name, address)

            if hit_L1:
                if state_L1 in "EM":
                    print "{0}: Write HIT L1, address {1}".format(local_cache_name, address)
                    local_cache.set_state(address, "M")
                elif state_L1 == "S":
                    print "{0}: Write HIT L1, address {1}".format(local_cache_name, address)
                    print "{0}: But there is a copy in {1}, invalidating {1} local cache block, address {2}"\
                        .format(local_cache_name, extraneous_cache_name, address)
                    self.ch_local_cpu1.set_state(address, "M")
                    self.ch_local_cpu2.set_state(address, "I")
                return

            else:
                if local_cache_name == "CPU1":
                    self.missesL1 += 1
                elif local_cache_name == "CPU2":
                    self.missesLL1 += 1
                print "{0}: Write MISS L1, address {1}".format(local_cache_name, address)
                self.delete_procL1(address)

                if hit_L2:
                    print "{0}: Write HIT L2, address {1}".format(local_cache_name, address)

                    mode_copy_cpuext = self.ch_local_cpu2.read(address)
                    if mode_copy_cpuext in "MES":
                        print "{0}: Invalidating copy, address {1}".format(extraneous_cache_name, address)
                        local_cache.update_set(address, "M")
                        extraneous_cache.set_state(address, "I")
                        self.ch_shared_cpu.set_state(address, "S")
                    else:
                        local_cache.update_set(address, "M")
                        self.ch_shared_cpu.set_state(address, "S")
                else:
                    self.missesL2 += 1
                    print "{0}: Write MISS L2, address {1}".format(local_cache_name, address)
                    self.delete_procL2(address)
                    local_cache.update_set(address, "M")
                    self.ch_shared_cpu.update_set(address, "S")

        else:
            print "Invalid action: {0}".format(mode)

    def delete_procL1(self, address):
        """
        Deletes a block in the L1-cpu1 cache, and handles write-backs if necessary.
        :param address: Int, memory address of the block that it is about to be replaced.
        :return: None.
        """
        address = self.ch_local_cpu1.get_similar(address)
        mode_L1 = self.ch_local_cpu1.read(address)

        if mode_L1 in "ESIN":
            None  # No action required

        elif mode_L1 == "M":
            print "Value to overwrite in L1 cpu1 is in M state, " \
                  "write back to L2, address {0}".format(address)
            self.ch_shared_cpu.set_state(address, "M")

        else:
            print "Invalid mode in L1 cpu1: {0}".format(mode_L1)

    def delete_procLL1(self, address):
        """
        Deletes a block in the L1-cpu2 cache, and handles write-backs if necessary.
        :param address: Int, memory address of the block that it is about to be replaced.
        :return: None.
        """
        address = self.ch_local_cpu2.get_similar(address)
        mode_LL1 = self.ch_local_cpu2.read(address)

        if mode_LL1 in "ESIN":
            None  # No action required

        elif mode_LL1 == "M":
            print "Value to overwrite in L1 cpu2 is in M state, " \
                  "write back to L2, address {0}".format(address)
            self.ch_shared_cpu.set_state(address, "M")

        else:
            print "Invalid mode in L1 cpu2: {0}".format(mode_LL1)

    def delete_procL2(self, address):
        """
        Deletes a block in the L2 cache, and handles snoop-invalidate and write-backs if necessary.
        :param address: Int, memory address of the block that it is about to be replaced.
        :return: None.
        """
        address = self.ch_shared_cpu.get_similar(address)

        # get state
        mode_L2 = self.ch_shared_cpu.read(address)

        if mode_L2 in "EIN":
            None  # No action required

        elif mode_L2 == "M":
            print "Value to overwrite in L2 is in M state, " \
                  "write back to memory, address {0}".format(address)

        elif mode_L2 == "S":
            # invalidate L1 entries
            self.ch_local_cpu1.set_state(address, "I")
            self.ch_local_cpu2.set_state(address, "I")

        else:
            print "Invalid mode in L2: {0}".format(mode_L2)


###############################################################################
def main():
    # Obtaining parameters from cli
    parser = argparse.ArgumentParser(
        description='''Simulates the use of a multilevel cache, used by two cores''')

    parser.add_argument('program_core1', nargs='?',
                        default=default_programcpu1,
                        help='program to execute with cpu1')
    parser.add_argument('program_core2', nargs='?',
                        default=default_programcpu2,
                        help='program to execute with cpu2')
    args = parser.parse_args()

    cores = CpuMaster()  # manages the two cores

    # begins simulation
    cores.simulate(args.program_core1, args.program_core2)

if __name__ == "__main__":
    main()
