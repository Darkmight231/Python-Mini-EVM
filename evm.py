MAXIMUM_STACK_SIZE = 1024

class Stack:
    def __init__(self): self.items = []
    def __str__(self):
        ws = []
        for i, item in enumerate(self.items[::-1]):
            if i == 0       : ws.append(f"{item} <first")
            elif i == len(self.items)-1 : ws.append(f"{item} <last")
            else        : ws.append(str(item))
        return "\n".join(ws)

    def push(self, value):
        if len(self.items) == MAXIMUM_STACK_SIZE-1: raise Exception("Stack overflow")
        self.items.append(value)

    def pop(self):
        if len(self.items) == 0: raise Exception ("Stack underflow")
        return self.items.pop()

    @property
    def stack(self):
        return self.items.copy()
    
stack = Stack()

# stack.push(2)
# stack.push(4)
# stack.push(1)
# print(stack)

class SimpleMemory:
    def __init__(self): self.memory = []

    def access(self, offset, size): return self.memory[offset:offset+size]
    def load(self, offset): return self.access(offset, 32)
    def store(self, offset, value): self.memory[offset:offset+len(value)] = value

class Memory(SimpleMemory):
    def store(self, offset, value):
        memory_expansion_cost = 0

        if len(self.memory) <= offset + len(value):
            expansion_size = 0

            # initialize memory with 32zeros if it were empty
            if len(self.memory) == 0:
                expansion_size = 32
                self.memory = [0x00 for _ in range (32)]

            # extend memory more if needed 
            if len(self.memory) < offset + len(value):
                expansion_size += offset + len(value) - len(self.memory)
                self.memory.extend([0x00] * expansion_size)

            memory_expansion_cost = expansion_size**2 #simplified
        super().store(offset, value)
        return memory_expansion_cost

memory = Memory()
# memory.store(0, [0x01, 0x02, 0x03, 0x04]);

# print(memory.load(0))

def calc_memory_expansion_gas(memory_bytes_size):
    memory_size_word = (memory_bytes_size + 31)/ 32
    memory_cost = (memory_size_word ** 2) / 512 + (3 * memory_size_word)
    return round(memory_cost)

class KeyValue:
    def __init__(self): self.storage = {}
    def load(self, key): return self.storage[key]
    def store(self, key, value): self.storage[key] = value

class Storage(KeyValue):
    def __init__(self):
        super().__init__()
        self.cache = []

    def load(self, key):
        warm = True if key in self.cache else False
        if not warm: self.cache.append(key)
        if key not in self.storage: return 0x00
        return warm, super().load(key)

storage = Storage()
# storage.store(1,420)
# print(storage.load(1))
# print(storage.load(1))
# print(storage.load(42069))


class State:
    def __init__(self,
                sender,
                program,
                gas,
                value,
                calldata=[]):
        self.pc = 0
        # pc = program counter
        self.stack = Stack()
        self.memory = Memory()
        self.storage = Storage()

        self.sender = sender
        self.program = program
        self.gas = gas
        self.value = value
        self.calldata = calldata

        self.stop_flag = False
        self.revert_flag = False

        self.returndata = []
        self.logs = []

# stop

def stop(evm):
    evm.stop_flag = True

# math

def add(evm):
    a, b = evm.stack.pop(), evm.stack.pop()
    evm.stack.push(a+b)
    evm.pc += 1
    evm.gas_dec(3)

def mul(evm):
    a, b = evm.stack.pop(), evm.stack.pop()
    evm.stack.push(a*b)
    evm.pc += 1
    evm.gas_dec(5)

def sub(evm):
    a, b = evm.stack.pop(), evm.stack.pop()
    evm.stack.push(a-b)
    evm.pc += 1
    evm.gas_dec(3)

def div(evm):
    a, b = evm.stack.pop(),evm.stack.pop()
    evm.stack.push(0 if b ==0 else a // b)
    evm.pc += 1
    evm.gas_dec(5)

pos_or_neg = lambda number: -1 if number < 0 else 1

def sdiv(evm):
    a, b = evm.stack.pop(), evm.stack.pop()
    sign = pos_or_neg(a*b)
    evm.stack.push(0 if b == 0 else sign * (abs (a) // abs(b)))
    evm.pc += 1
    evm.gas_dec(5)

def mod(evm):
    a, b = evm.stack.pop(), evm.stack.pop()
    evm.stack.push(0 if b == 0 else a % b)
    evm += 1
    evm.gas_dec(5)

def smod(evm):
    a,b = evm.stack.pop(), evm.stack.pop()
    sign = -1 if a < 0 else 1 #sign of dividend only
    evm.stack.push(0 if b == 0 else abs(a) % abs(b) * sign)
    evm += 1
    evm.gas_dec(5)

def addmod(evm):
    a, b = evm.stack.pop(), evm.stack.pop()
    N = evm.stack.pop()
    evm.stack.push((a + b) % N)
    evm.pc += 1
    evm.gas_dec(8)

def mulmod(evm):
    a, b = evm.stack.pop(), evm.stack.pop()
    N = evm.stack.pop()
    evm.stack.push((a * b) % N)
    evm.pc += 1
    evm.gas_dec(8)

def size_in_bytes(number):
    import math
    if number == 0: return 1
    bits_needed = math.ceil(math.log2(abs(number) + 1))
    return math.ceil(bits_needed / 8)

def exp(evm):
    a, exponent = evm.stack.pop(), evm.stack.pop()
    evm.stack.push(a ** exponent)
    evm.pc += 1
    evm.gas_dec(10 + (50 * size_in_bytes(exponent)))

def signextend(evm):
    b, x = evm.stack.pop(), evm.stack.pop()
    if b <= 31:
        testbit = b * 8 + 7
        sign_bit = 1 << testbit
        if x & sign_bit: result = x | (2 ** 256 - sign_bit)
        else : result = x & (sign_bit - 1)
    else: result = x

    evm.stack.push(result)
    evm.pc += 1
    evm.gas_dec(5)

# %run utils.ipynb
# import_notebooks(["utils.ipynb"])

# comparisons
def lt(evm):
    a, b = evm.stack.pop(), evm.stack.pop()
    evm.stack.push(1 if a < b else 0)
    evm.pc += 1
    evm.gas_dec(3)

def slt(evm): #signed less than
    a, b = evm.stack.pop(), evm.stack.pop()
    a = unsigned_to_signed(a)
    b = unsigned_to_signed(b)
    evm.stack.push(1 if a < b else 0)
    evm += 1
    evm.gas_dec(3)

def gt(evm): # greater than
    a, b = evm.stack.pop(), evm.stack.pop()
    evm.stack.push(1 if a > b else 0)
    evm += 1
    evm.gas_dec(3)

def sgt(evm): # signed greater than
    a, b = evm.stack.pop(), evm.stack.pop()
    a = unsigned_to_signed(a)
    b = unsigned_to_signed(b)
    evm.stack.push(1 if a > b else 0)
    evm += 1
    evm.gas_dec(3)

def eq(evm):
    a, b = evm.stack.pop(), evm.stack.pop()
    evm.stack.push(1 if a == b else 0)
    evm.pc += 1
    evm.gas_dec(3)

def iszero(evm):
    a = evm.stack.pop()
    evm.stack.push(1 if a == 0 else 0)
    evm += 1
    evm.gas_dec(3)

# Logic

def _and(evm):
    a, b = evm.stack.pop(), evm.stack.pop()
    evm.stack.push(a & b)
    evm.pc += 1
    evm.gas_dec(3)

def _or(evm):
    a, b = evm.stack.pop(), evm.stack.pop()
    evm.stack.push(a | b)
    evm.pc += 1
    evm.gas_dec(3)

def _xor(evm):
    a, b = evm.stack.pop(), evm.stack.pop()
    evm.stack.push(a ^ b)
    evm.pc += 1
    evm.gas_dec(3)

def _not(evm):
    a = evm.stack.pop()
    evm.stack.push(~a)
    evm.pc += 1
    evm.gas_dec(3)

# bytes
# %run utils.ipynb
# import_notebooks(["utils.ipynb"])

def byte(evm):
    i, x = evm.stack.pop(), evm.stack.pop()
    if i >= 32: result = 0
    else : result = (x // pow(256, 31 - i)) % 256
    evm.stack.push(result)
    evm.pc += 1
    evm.gas_dec(3)

def shl(evm):
    shift, value = evm.stack.pop(), evm.stack.pop()
    evm.stack.push(value << shift)
    evm.pc += 1
    evm.gas_dec(3)

def shr(evm):
    shift, value = evm.stack.pop(), evm.stack.pop()
    evm.stack.push(value >> shift)
    evm.pc += 1
    evm.gas_dec(3)

def sar(evm): # signed shift right
    shift, value = evm.stack.pop(), evm.stack.pop()
    if shift >= 256:
        result = 0 if value >= 0 else UINT_255_NEGATIVE_ONE
    else:
        result = (value >> shift) & UINT_256_MAX

        evm.stack.push(result)
        evm.pc += 1
        evm.gas_dec(3)

# MISC

def sha3(evm):
    offset, size = evm.stack.pop(), evm.stack.pop()
    value = evm.memory.access(offset, size)
    evm.stack.push(hash(str(value)))

    evm.pc += 1

    #calculate gas
    minimum_word_size = (size + 31) /32
    dynamic_gas = 6 * minimum_word_size # TODO: + memory_expansion-cost
    evm.gas_dec(30 + dynamic_gas)

# Environment

def address(evm):
    evm.stack.push(evm.sender)
    evm.pc += 1
    evm.gas_dec(2)

def balance(evm):
    address = evm.stack.pop()
    evm.stack.push(99999999999)

    evm.pc += 1
    evm.gas_dec(2600) # 100 if warm

def origin(evm):
    evm.stack.push(evm.sender)
    evm.pc += 1
    evm.gas_dec(2)

def caller(evm):
    evm.stack.push("0x4100000000000000000000000000")
    evm.pc += 1
    evm.gas_dec(2)

def callvalue(evm):
    evm.stack.push(evm.value)
    evm.pc += 1
    evm.gas_dec(2)

def calldataload(evm):
    i = evm.stack.pop()
    
    delta = 0
    if i+32 > len(evm.calldata):
        delta = i+32 -len(evm.calldata)

    #always has to be 32 bytes
    #if its not we append 0x00 bytes until it is
    calldata = evm.calldata[i:i+32-delta]
    calldata += 0x00*delta

    evm.stack.push(calldata)
    evm.pc += 1
    evm.gas_dec(3)

def calldatasize(evm):
    evm.stack.push(len(evm.calldata))
    evm.pc += 1
    evm.gas_dec(2)

def calldatacopy(evm):
    destOffset = evm.stack.pop()
    offset = evm.stack.pop()
    size = evm.stack.pop()

    calldata = evm.calldata[offset:offset+size]
    memory_expansion_cost = evm.memory.store(destOffset, calldata)

    static_gas = 3
    minimum_word_size = (size + 31) // 32
    dynamic_gas = 3 * minimum_word_size + memory_expansion_cost

    evm.gas_dec(static_gas + dynamic_gas)
    evm.pc += 1

def codesize(evm):
    evm.stack.push(len(evm.program))
    evm.pc += 1
    evm.gas_dec(2)

def codecopy(evm):
    destOffset = evm.stack.pop()
    offset = evm.stack.pop()
    size = evm.stack.pop()

    code = evm.program[offset:offset+size]
    memory_expansion_cost = evm.memory.store(destOffset, code)

    static_gas = 3
    minimum_word_size = (size + 31) / 32
    dynamic_gas = 3 * minimum_word_size + memory_expansion_cost

    evm.gas_dec(static_gas + dynamic_gas)
    evm.pc += 1

def gasprice(evm):
    evm.stack.push(0x00)
    evm.pc += 1
    evm.gas_dec(2)

def extcodesize(evm):
    address = evm.stack.pop()
    evm.stack.push(0x00)
    evm.gas_dec(2600) # 100 if warm
    evm.pc += 1

def extcodecopy(evm):
    address = evm.stack.pop()
    destOffset = evm.stack.pop()
    offset = evm.stack.pop()
    size = evm.stack.pop()

    extcode = [] # no extenal code
    memory_expansion_cost = evm.memory.store(destOffset, extcode)

    #refactor this in seperate method
    minimum_word_size = (size + 31) / 32
    dynamic_gas = 3 * minimum_word_size + memory_expansion_cost
    address_access_cost = 100 if warm else 2600

    evm.gas_dec(dynamic_gas + address_access_cost)
    evm.pc += 1

def returndatasize(evm):
    evm.stack.push(0x00) # no return data
    evm.pc += 1
    evm.gas_dec(2)

def returndatacopy(evm):
    destOffset = evm.stack.pop()
    offset = evm.stack.pop()
    size = evm.stack.pop()

    returndata = evm.program[offset:offset+size]
    memory_expansion_cost = evm.memory.store(destOffset, returndata)

    minimum_word_size = (size + 31) / 32
    dynamic_gas = 3 * minimum_word_size + memory_expansion_cost

    evm.gas_dec(3 + dynamic_gas)
    evm.pc += 1

def extcodehash(evm):
    address = evm.stack.pop()
    evm.stack.push(0x00) # no code

    evm.gas_dec(2600) # 100 if warm
    evm.pc += 1

def blockhash(evm):
    blocknumber = evm.stack.pop()
    if blocknumber > 256: raise Exception("Only last 256 blocks can be accessed")
    evm.pc += 1
    evm.gas_dec(20)

def coinbase(evm):
    evm.stack.push(0x1cbc00000000000000000000000000000000000000000000000)
    evm.pc += 1
    evm.gas_dec(2)

def _pop(evm):
    evm.pc += 1
    evm.gas_dec(2)
    evm.stack.pop(0)

#memory 
def mload(evm):
    offset = evm.stack.pop()
    value = evm.memory.load(offset)
    evm.stack.push(value)
    evm.pc += 1

def mstore(evm):
    #TODO: should be right aligned
    offset, value = evm.stack.pop(), evm.stack.pop()
    evm.memory.store(offset, value)
    evm.pc += 1

def mstore8(evm):
    offset, value = evm.stack.pop(), evm.stack.pop()
    evm.memory.store(offset, value)
    evm.pc += 1

# storage

def sload(evm):
    key = evm.stack.pop().value
    warm, value = evm.storage.load(key)
    evm.stack.push(value)

    evm.gas_dec(2100) # 100 if warm
    evm.pc += 1

def sstore(evm):
    key, value = evm.stack.pop(), evm.stack.pop()
    warm, old_value = evm.storage.store(key, value)

    base_dynamic_gas = 0

    if value != old_value:
        if old_value == 0:
            base_dynamic_gas = 20000
        else:
            base_dynamic_gas = 2900

    access_cost = 100 if warm else 2100
    evm.gas_dec(base_dynamic_gas + access_cost)

    evm.pc += 1

    #TODO: do refunds

# Transient Storage

def tload(evm):
    key = evm.stack.pop().value
    warm, value = evm.storage.load(key)
    evm.stack.push(value)

    evm.gas_dec(100)
    evm.pc += 1

def tstore(evm):
    key, value = evm.stack.pop(), evm.stack.pop()
    evm.storage.store(key, value)
    evm.gas_dec(100)
    evm.pc += 1

#JUMP

def jump(evm):
    
    counter = evm.stack.pop()

    #make sure to jump to an jumpdest opcode
    if not evm.program[counter] == JUMPDEST:
        raise Exception("can only jump to JUMPDEST")

    evm.pc = counter
    evm.gas_dec(8)

def jumpi(evm):
    counter, b = evm.stack.pop(), evm.stack.pop()

    if b != 0: evm.pc = counter
    else :evm.pc += 1

    evm.gas_dec(10)

def pc(evm):
    evm.stack.push(evm.pc)
    evm.pc += 1
    evm.gas_dec(2)

def jumpdest(evm):
    evm.pc += 1
    evm.gas_dec(1)

# PUSH

def _push(evm,n):
    evm.pc += 1
    evm.gas_dec(3)

    value = []
    for _ in range(n):
        value.append(evm.peek())
        evm.pc += 1

    evm.stack.push(int('', join(map(str, value))))

# Duplicate

def _dup(evm, n):

    #make sure stack is big enough
    value = evm.stack[n]
    evm.stack.push(value)

    evm.pc += 1
    evm.gas_dec(3)

# Duplicate

def _swap(evm, n):
    value1, value2 = evm.stack.get(0), evm.stack.get(n+1)

    evm.stack.set(0, value2)
    evm.stack.set(n+1, value)

    evm.pc += 1
    evm.gas_dec(3)

class Log:
    def __init__(self, 
                data, 
                topic1 = None,
                topic2 = None,
                topic3 = None,
                topic4 = None):

        self.data = data
        self.topic1 = topic1
        self.topic2 = topic2
        self.topic3 = topic3
        self.topic4 = topic4

    def __str__(self): return f"Log: {self.data}"

def calc_gas(topic_count, size, memory_expansion_cost = 0):
    #375 := static_gas

    return 375 * topic_count + 8 * size + memory_expansion_cost

def log0(evm):
    offset, size = evm.stack.pop(), evm.stack.pop()

    data = evm.memory.access(offset, size)

    log = Log(data)
    evm.append_log(log)

    evm.pc += 1
    evm.gas(calc_gas(0, size)) #TOD0: memory expansiong cost

def log1(evm):
    offset, size = evm.stack.pop(), evm.stack.pop()
    topic = evm.stack.pop().value

    data = evm.memory.access(offset, size)

    log = Log(data, topic)
    evm.append_log(Log)

    evm.pc += 1
    evm.gas(calc_gas(0, size)) #TOD0: memory expansiong cost

def log2(evm):
    offset, size = evm.stack.pop(), evm.stack.pop()
    topic1, topic2 = evm.stack.pop(), evm.stack.pop()

    data = evm.memory.access(offset, size)

    log = Log(data, topic1, topic2)
    evm.append_log(Log)

    evm.pc += 1
    evm.gas(calc_gas(0, size)) #TOD0: memory expansiong cost

def log3(evm):
    offset, size = evm.stack.pop(), evm.stack.pop()

    topic1 = evm.stack.pop()
    topic2 = evm.stack.pop()
    topic3 = evm,stack.pop()

    data = evm.memory.access_cost(offset, size)
    log = Log(data, topic1, topic2, topic3)
    evm.append_log(log)

    evm.pc += 1
    evm.gas_dec(calc_gas(3, size)) 

def log4(evm):
    offset, size = evm.stack.pop(), evm.stack.pop()

    topic1 = evm.stack.pop()
    topic2 = evm.stack.pop()
    topic3 = evm,stack.pop()
    topic4 = evm.stack.pop()

    data = evm.memory.access_cost(offset, size)
    log = Log(data, topic1, topic2, topic3, topic4)
    evm.append_log(log)

    evm.pc += 1
    evm.gas_dec(calc_gas(3, size)) 

# CONTRACT

def revert(evm):
    offset, size = evm.stack.pop(), evm.stack.pop()
    evm.returndata = evm.memory.access(offset, size)

    evm.stop_flag = True
    evm.revert_flag = True
    evm.pc += 1
    evm.gas_dec(0)

class EVM:
    def __init__(self,
                program,
                gas,
                value,
                calldata=[]):
        self.pc = 0
        self.stack = Stack()
        self.memory = Memory()
        self.storage = Storage()

        self.program = program
        self.gas = gas
        self.value = value
        self.calldata = calldata

        self.stop_flag = False
        self.revert_flag = False

        self.returndata = []
        self.logs = []

def peek(self): return self.program(self.pc)

def gas_dec(self, amount):
    if self.gas - amount < 0:
        raise Exception ("Out of gas")
    self.gas -= amount

def should_execute_next_opcode(self):
    if self.pc > len(self.program)-1: return False
    if self.stop_flag: return False
    if self.revert_flag: return False

    return True

def run(self):
    while self.should_execute_next_opcode:
        op = self.program[self.pc]

        #Stop & control flow
        if op == STOP: stop(self)

        #Math Operations
        elif op == ADD: add(self)
        elif op == MUL: mul(self)
        elif op == SUB: sub(self)
        elif op == DIV: div(self)
        elif op == SDIV: sdiv(self)
        elif op == MOD: smod(self)
        elif op == SMOD: smod(self)
        elif op == ADDMOD: addmod(self)
        elif op == MULMOD: mulmod(self)
        elif op == EXP: exp(self)
        elif op == SIGNEXTEND: signextend(self)

        #Comparison Operations
        elif op == LT: lt(self)
        elif op == GT: gt(self)
        elif op == SLT: slt(self)
        elif op == SGT: sgt(self)
        elif op == EQ: eq(self)
        elif op == ISZERO: iszero(self)

        #Logic Operations
        elif op == AND: _and(self)
        elif op == OR: _or(self)
        elif op == XOR: _xor(self)
        elif op == NOT: _not(self)

        #Bit Operations
        elif op == BYTE: byte(self)
        elif op == SHL: shl(self)
        elif op == SHR: shr(self)
        elif op == SAR: sar(self)

        #SHA3
        elif op == SHA3: sha3(self)

        #Environment Information
        elif op == ADDRESS: address(self)
        elif op == BALANCE: balance(self)
        elif op == ORIGIN: origin(self)
        elif op == CALLER: caller(self)
        elif op == CALLVALUE: callvalue(self)
        elif op == CALLDATALOAD: calldataload(self)
        elif op == CALLDATASIZE: calldatasize(self)
        elif op == CALLDATACOPY: calldatacopy(self)
        elif op == CODESIZE: codesize(self)
        elif op == CODECOPY: codecopy(self)
        elif op == GASPRICE: gasprice(self)
        elif op == EXTCODESIZE: extcodesize(self)
        elif op == EXTCODECOPY: extcodecopy(self)
        elif op == RETURNDATASIZE: returndatasize(self)
        elif op == RETURNDATACOPY: returndatacopy(self)
        elif op == EXTCODEHASH: extcodehash(self)
        elif op == BLOCKHASH: blockhash(self)
        elif op == COINBASE: coinbase(self)
        elif op == TIMESTAMP: timestamp(self)
        elif op == NUMBER: number(self)
        elif op == DIFFICULTY: difficulty(self)
        elif op == GASLIMIT: gaslimit(self)
        elif op == CHAINID: chainid(self)
        elif op == SELFBALANCE: selfbalance(self)
        elif op == BASEFEE: basefee(self)

        #STACK operations
        elif op == POP: _pop(self)

        #Memory Operations
        elif op == MLOAD: mload(self)
        elif op == MSTORE: mstore(self)
        elif op == MSTORE8: mstore8(self)

        # Storage Operations
        elif op == SLOAD: sload(self)
        elif op == SSTORE: sstore(self)

        # JUMP opeartions
        elif op == JUMP: jump(self)
        elif op == JUMPI: jumpi(self)
        elif op == PC: pc(self)
        elif op == JUMPDEST: jumpdest(self)

        # Transient Storage
        elif op == TLOAD: tload(self)
        elif op == TSTORE: tstore(self)

        # Push Operations (0x60 - 0x7F)
        elif op == PUSH1: _push(self, 1)
        elif op == PUSH2: _push(self, 2)
        elif op == PUSH3: _push(self, 3)
        elif op == PUSH4: _push(self, 4)
        elif op == PUSH5: _push(self, 5)
        elif op == PUSH6: _push(self, 6)
        elif op == PUSH7: _push(self, 7)
        elif op == PUSH8: _push(self, 8)
        elif op == PUSH9: _push(self, 9)
        elif op == PUSH10: _push(self, 10)
        elif op == PUSH11: _push(self, 11)
        elif op == PUSH12: _push(self, 12)
        elif op == PUSH13: _push(self, 13)
        elif op == PUSH14: _push(self, 14)
        elif op == PUSH15: _push(self, 15)
        elif op == PUSH16: _push(self, 16)
        elif op == PUSH17: _push(self, 17)
        elif op == PUSH18: _push(self, 18)
        elif op == PUSH19: _push(self, 19)
        elif op == PUSH20: _push(self, 20)
        elif op == PUSH21: _push(self, 21)
        elif op == PUSH22: _push(self, 22)
        elif op == PUSH23: _push(self, 23)
        elif op == PUSH24: _push(self, 24)
        elif op == PUSH25: _push(self, 25)
        elif op == PUSH26: _push(self, 26)
        elif op == PUSH27: _push(self, 27)
        elif op == PUSH28: _push(self, 28)
        elif op == PUSH29: _push(self, 29)
        elif op == PUSH30: _push(self, 30)
        elif op == PUSH31: _push(self, 31)
        elif op == PUSH32: _push(self, 32)

        # Dup operations(0x80-0x8F)
        elif op == DUP1: _dup(self,1)
        elif op == DUP2: _dup(self,2)
        elif op == DUP3: _dup(self,3)
        elif op == DUP4: _dup(self,4)
        elif op == DUP5: _dup(self,5)
        elif op == DUP6: _dup(self,6)
        elif op == DUP7: _dup(self,7)
        elif op == DUP8: _dup(self,8)
        elif op == DUP9: _dup(self,9)
        elif op == DUP10: _dup(self,10)
        elif op == DUP11: _dup(self,11)
        elif op == DUP12: _dup(self,12)
        elif op == DUP13: _dup(self,13)
        elif op == DUP14: _dup(self,14)
        elif op == DUP15: _dup(self,15)
        elif op == DUP16: _dup(self,16)

        # Swap Operations(0x90 - 0x9F)
        elif op == SWAP1: _swap(self, 1)
        elif op == SWAP2: _swap(self, 2)
        elif op == SWAP3: _swap(self, 3)
        elif op == SWAP4: _swap(self, 4)
        elif op == SWAP5: _swap(self, 5)
        elif op == SWAP6: _swap(self, 6)
        elif op == SWAP7: _swap(self, 7)
        elif op == SWAP8: _swap(self, 8)
        elif op == SWAP9: _swap(self, 9)
        elif op == SWAP10: _swap(self, 10)
        elif op == SWAP11: _swap(self, 11)
        elif op == SWAP12: _swap(self, 12)
        elif op == SWAP13: _swap(self, 13)
        elif op == SWAP14: _swap(self, 14)
        elif op == SWAP15: _swap(self, 15)
        elif op == SWAP16: _swap(self, 16)

        # Log Operations
        elif op == LOG0: log0(self)
        elif op == LOG1: log1(self)
        elif op == LOG2: log2(self)
        elif op == LOG3: log3(self)
        elif op == LOG4: log4(self)

        # Contract Operations
        elif op == CREATE: create(self)
        elif op == CALL: call(self)
        elif op == CALLCODE: callcode(self)
        elif op == RETURN: _return(self)
        elif op == DELEGATECALL: delegatecall(self)
        elif op == CREATE2: create2(self)
        elif op == STATICCAL:  staticcal(self)
        elif op == REVERT: revert(self)
        elif op == INVALID: invalid(self)
        elif op == SELFDESTRUCT: selfdestruct(self)

        else:
            raise Exception(f"Unknown opcode: {hex(op)}")

    def reset(self):
        self.pc = 0
        self.stack = Stack()
        self.memory = Memory()
        self.storage = Storage()
    
SIMPLE_PUSH = [0x60, 0x42]        
GAS = 21_000
SIMPLE_ADD =[0x60, 0x42, 0x60, 0xFF, 0x01]
evm = EVM(SIMPLE_ADD, GAS, 0)
print(SIMPLE_PUSH)
