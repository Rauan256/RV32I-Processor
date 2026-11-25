# Architecture overview

Our Fall 2026 baseline is a multicycle, in-order RV32I processor implemented in SystemVerilog. The core and register file are independent of the simulation memory and testbench.

## Datapath

| Block | Function |
| --- | --- |
| PC (`pc`) | Current instruction address; reset to `0x80000000` |
| Instruction register (`ir`) | Holds the fetched 32-bit instruction during decode and execution |
| Register file (`rv32i_regfile`) | 32 × 32-bit registers; two read ports and one write port; `x0` always reads zero |
| Decoder and immediate logic | Extracts opcode, register indices, funct fields and I/S/B/U/J immediates |
| ALU and branch logic | Computes arithmetic, logic, comparisons, shifts, addresses and next PC |
| Memory and writeback logic | Issues load/store requests and writes ALU or load results into `rd` |

Source: [`rv32i_core.sv`](../rtl/rv32i_core.sv) and [`rv32i_regfile.sv`](../rtl/rv32i_regfile.sv).

## Control FSM

| State | RTL identifier | Function |
| ---: | --- | --- |
| 0 | `ST_FETCH_REQ` | Issue instruction fetch |
| 1 | `ST_FETCH_WAIT` | Wait for instruction response |
| 2 | `ST_DECODE` | Capture operands and destination register |
| 3 | `ST_EXEC` | Execute, calculate next PC or prepare a memory request |
| 4 | `ST_WB_ALU` | Write back when enabled and advance PC |
| 5 | `ST_MEM_REQ` | Issue data memory request |
| 6 | `ST_MEM_WAIT` | Wait for data or store acknowledgement |
| 7 | `ST_WB_LOAD` | Extend load data and write it to the register file |
| 8 | `ST_HALT` | Stop execution |

Typical instruction flow: `FETCH_REQ → FETCH_WAIT → DECODE → EXEC → WB_ALU → FETCH_REQ`. Loads pass through `MEM_REQ → MEM_WAIT → WB_LOAD`; stores return to fetch after acknowledgement. Branches select either the branch target or `PC + 4`. Jump instructions save `PC + 4` when a destination register is specified.

## Memory interface

We use a single outstanding request. The core pulses `mem_valid` for one cycle; memory returns `mem_ready` with read data or a write acknowledgement. The interface comprises `mem_addr`, `mem_we`, `mem_wdata`, `mem_wstrb` and `mem_rdata` in addition to the handshake. Four byte strobes select the lanes written during a store. Loads select and sign- or zero-extend the required bytes or halfwords; word accesses use all four bytes.

The standard simulation RAM starts at `0x80000000` and contains 64 KiB. The ACT4 adapter uses a separate 4 MiB simulation configuration. The simulated memory also includes console output at `0x10000000`; the corresponding physical UART and BRAM wrapper are planned for Spring.

## System instructions and scope

| Instruction / condition | Behavior |
| --- | --- |
| `FENCE` | No-op in the uncached, single-hart system |
| `ECALL` | Halt, `halt_code = 1` |
| `EBREAK` | Halt, `halt_code = 2` |
| Illegal instruction or detected misalignment | Halt, `halt_code = 3`, `illegal_insn = 1` |

These are project-defined termination behaviors rather than privileged trap handling. Privileged CSRs, interrupts, caches, MMU, pipelining and optional ISA extensions are outside the current baseline.

## Verification

Our self-checking testbench uses the final memory signature and halt code to verify each directed program. The ACT4 adapter uses the self-checking ELF's `tohost` result. See [STATUS.md](../STATUS.md) for the recorded results and [README.md](../README.md) for commands.

Structural diagrams: [processor](../results/rv32i_schematic.svg), [register file](../results/register_file.svg).
