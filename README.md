# Mini-EVM (Python)

A lightweight Python implementation of the Ethereum Virtual Machine (EVM) built for education and security research. This project moves beyond the Solidity abstraction to provide a direct look at how smart contract bytecode executes.

This interpreter is designed to be a simple, readable, and hackable tool for:

Analyzing opcode behavior

Understanding stack/memory/storage manipulation

Prototyping and testing low-level EVM logic

Researching gas costs and optimization patterns

# Why I Built This

To truly understand Ethereum security, you must understand the EVM. While Solidity is the primary language for smart contracts, the EVM is the ultimate arbiter of execution.

I built this project to deconstruct the "magic" of the EVM and build a mental model of its core components from the ground up. This foundation is critical for advanced vulnerability analysis, gas optimization, and contributing to core protocol discussions.

# Core Features

This EVM implementation is built from scratch and includes models for all essential components of the virtual machine:

Custom Stack: A full stack implementation with a MAXIMUM_STACK_SIZE of 1024, complete with overflow and underflow protections.

Expandable Memory: A byte-array-based memory model that simulates memory expansion and calculates the (simplified) gas cost associated with it.

Warm/Cold Storage (EIP-2929): A key-value storage model that maintains a cache of accessed slots to simulate the gas cost difference between "warm" and "cold" SLOADs and SSTOREs.

Opcode Interpreter: A central run() loop that dispatches opcodes to their corresponding Python functions.

Gas Accounting: Each opcode implementation deducts a (simplified) gas amount from the EVM's gas supply, raising an "Out of gas" exception on failure.

# Implemented Opcodes

A wide range of opcodes are implemented. (Note: This list reflects functions present in evm.py. The complete hex-to-opcode mapping is forthcoming).

Arithmetic: ADD, MUL, SUB, DIV, SDIV, MOD, SMOD, ADDMOD, MULMOD, EXP, SIGNEXTEND

Comparison & Logic: LT, GT, SLT, SGT, EQ, ISZERO, AND, OR, XOR, NOT

Bitwise Operations: BYTE, SHL, SHR, SAR

Environment: ADDRESS, BALANCE (mocked), ORIGIN, CALLER (mocked), CALLVALUE, CALLDATALOAD, CALLDATASIZE, CALLDATACOPY, CODESIZE, CODECOPY, GASPRICE (mocked)

Stack / Memory / Storage: PUSH1-32, DUP1-16, SWAP1-16, POP, MLOAD, MSTORE, MSTORE8, SLOAD, SSTORE, TLOAD, TSTORE

Flow Control: JUMP, JUMPI, JUMPDEST, PC, STOP, REVERT

Logging: LOG0, LOG1, LOG2, LOG3, LOG4

Hashing: SHA3 (simplified)

# Example Usage

(Note: This example is conceptual. The full opcode constants and hex mapping are currently being integrated.)

Once the opcode mapping is complete, you will be able to run bytecode directly.

## --- This is a conceptual example ---

- Import the EVM and the opcode constants (e.g., PUSH1=0x60, ADD=0x01)
from evm import EVM
from opcodes import PUSH1, ADD, STOP

- Bytecode for:
- PUSH1 0x42   (Push 66)
- PUSH1 0xFF   (Push 255)
- ADD          (66 + 255 = 321)
- STOP
bytecode = [PUSH1, 0x42, PUSH1, 0xFF, ADD, STOP]

## Initialize the EVM
evm = EVM(program=bytecode, gas=21000, value=0)

## Run the interpreter
evm.run()

## Inspect the final state
print(f"EVM finished successfully: {evm.stop_flag}")
print(f"Remaining gas: {evm.gas}")
print(f"Stack top item: {evm.stack.pop()}")
## Expected Output: Stack top item: 321


# Roadmap & Future Improvements

This project is an active work in progress. The next steps are focused on building a more robust and complete interpreter:

[ ] Opcode Mapping: Implement the full 0x00 to 0xFF opcode mapping to run raw contract bytecode.

[ ] Accurate Gas Costs: Refine all gas calculations to match the latest Ethereum hard fork, including SSTORE refunds and dynamic gas for CALL.

[ ] Helper Functions: Integrate missing helper utilities (e.g., unsigned_to_signed).

[ ] Call Opcodes: Fully implement CALL, DELEGATECALL, STATICCALL, and CREATE/CREATE2 to allow for multi-contract interactions.

[ ] Robust Testing: Build a comprehensive test suite by comparing execution traces against a production EVM (like Geth's) using official Ethereum tests.

📄 License

This project is open-sourced under the MIT License.
