# Start Here if You Did Not Build miniRV

You do not need to understand the entire textbook before touching the code. Learn the system in this order.

## 1. What the CPU does

Every instruction repeats the same basic idea:

1. **Fetch** a 32-bit instruction from the address in the PC.
2. **Decode** its opcode/funct fields and read `rs1`/`rs2`.
3. **Execute** an ALU operation, comparison, jump calculation, or memory address calculation.
4. **Memory** access if the instruction is a load/store.
5. **Write back** a result to `rd` when required.
6. Update the PC and fetch the next instruction.

A multicycle CPU performs these pieces over multiple clock cycles instead of forcing an entire instruction through one long combinational path.

## 2. Five objects to learn first

### PC
`pc` is the address of the current instruction. Reset sets it to `0x80000000`.

### Instruction register (`ir`)
The memory response is stored here so the same instruction remains stable while it is decoded/executed.

### Register file
32 registers, each 32 bits. `x0` always reads as zero and ignores writes.

### ALU / comparisons
Arithmetic, logical operations, shifts, signed/unsigned comparisons, and address calculations reuse the same basic arithmetic resources.

### FSM/state
`state` tells you which phase the processor is currently performing.

## 3. How an ADDI executes

For:

```asm
addi x3, x0, 5
```

- fetch the instruction
- decode `rs1=x0`, `rd=x3`, immediate `5`
- execute `0 + 5`
- write `5` to x3
- PC becomes PC+4

## 4. How LW is different

For:

```asm
lw x5, 8(x3)
```

- fetch/decode
- calculate address `x3 + 8`
- issue memory read request
- wait for the memory response
- extract the word and write it to x5
- PC becomes PC+4

This extra waiting is why a multicycle design fits synchronous FPGA BRAM naturally.

## 5. How a branch works

For:

```asm
blt x4, x5, target
```

The CPU performs a **signed** comparison. If true, next PC is `current PC + branch immediate`; otherwise it is `PC+4`.

Unsigned branches (`bltu`, `bgeu`) use an unsigned comparison instead.

## 6. What files to read first

1. `rtl/rv32i_regfile.sv` — easiest module.
2. `sim/tb_rv32i.sv` — learn what counts as PASS.
3. `rtl/rv32i_core.sv` lines containing `ST_FETCH`, `ST_DECODE`, `ST_EXEC`.
4. In `ST_EXEC`, read one opcode family at a time: OP-IMM, OP, BRANCH, LOAD/STORE, JUMP.
5. `tests/gen_tests.py` — see concrete assembly programs that exercise the hardware.

## 7. Textbook reading order

For this Fall milestone, focus on:

- Chapter 6: RISC-V architecture/machine language
- Section 6.4: instruction formats and immediates
- Chapter 7: microarchitecture
- Section 7.4: multicycle processor
- Section 7.6: HDL/testbench examples
- Chapter 4/5 only when you need SystemVerilog, FSM, ALU, register file, or memory background

## 8. Questions you must be able to answer before presenting

- Why multicycle instead of single-cycle or pipeline?
- Why does the processor need an instruction register?
- Why is x0 special?
- What is the difference between signed and unsigned comparison?
- How are I/S/B/U/J immediates constructed?
- Why do load/store instructions need more cycles?
- What do byte write strobes do?
- What does JAL write to `rd`?
- Why does JALR clear bit 0 of the target?
- What is your project-defined behavior for FENCE, ECALL and EBREAK?
- What evidence proves all 40 mnemonics were exercised?

If you can answer those from the code, you are no longer depending on the old miniRV experience.
