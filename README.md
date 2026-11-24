# RV32I Fall-Semester Baseline

This repository is a **from-scratch educational baseline** for the Fall ENG 400 milestone: a complete RV32I processor working in simulation before Spring FPGA integration.

It follows the project scope in the approved proposal:

- 32-bit RV32I architectural state (`x0`-`x31`, 32-bit PC)
- all 40 RV32I base mnemonics across the directed test manifest
- reset vector `0x8000_0000`
- multicycle control organization
- synchronous-memory-compatible request/response interface
- byte/halfword/word loads and stores
- deterministic project-defined `ECALL` / `EBREAK` halt behavior
- `FENCE` implemented as a no-op for the baseline uncached, single-hart system
- no pipeline, cache, MMU, privileged CSRs, interrupts, or optional M/A/F/D/C extensions

The code is intentionally split into small files so every block can be explained during a defense.

## Folder layout

- `rtl/rv32i_core.sv` — multicycle CPU and instruction decode/control
- `rtl/rv32i_regfile.sv` — 32x32 register file, x0 hardwired to zero
- `sim/rv32i_sim_memory.sv` — delayed/synchronous-style 64 KiB simulation memory
- `sim/rv32i_sim_top.sv` — CPU + simulation memory
- `sim/tb_rv32i.sv` — self-checking testbench
- `tests/gen_tests.py` — small assembler/test generator
- `tests/manifest.json` — frozen-style test manifest and mnemonic coverage
- `tools/ref_model.py` — independent Python RV32I functional model used to validate the generated test images
- `scripts/run_verilator.py` — generates tests, runs the Python reference model, and runs RTL tests when Verilator is installed
- `docs/START_HERE.md` — explanation for a team member who did not build miniRV
- `docs/fall_deliverables.md` — what evidence to collect for the Design Progress milestone
- `docs/instruction_coverage.md` — instruction groups and where they are handled

## What is already validated here

The generated directed programs were run through the independent Python reference model:

- `all40_ebreak.hex` -> pass signature `0xA11A0001`, then EBREAK
- `ecall.hex` -> pass signature `0xA11A0002`, then ECALL
- the union of the manifest contains all 40 required RV32I base mnemonics

This validates the **test program encodings and intended architectural results**.

## What still must be validated on your development machine

The current environment used to create this package does not have Verilator or Vivado installed. Therefore you still must:

1. Compile/lint the SystemVerilog with Verilator.
2. Run both RTL test images and save console logs/waveforms.
3. Add more directed tests (especially corner cases) before calling the verification manifest final.
4. Run an early Vivado synthesis to check the 25 MHz timing target.
5. Later replace the simulation memory/peripheral model with the synthesizable FPGA BRAM/MMIO path.

Do **not** claim that those steps are complete until you have the actual artifacts.

## Quick start

### Python-only validation

```bash
python3 tests/gen_tests.py
python3 tools/ref_model.py
```

Expected output:

```text
all40_ebreak: PASS ... signature=0xa11a0001
ecall: PASS ... signature=0xa11a0002
```

### Verilator RTL regression

After installing Verilator:

```bash
python3 scripts/run_verilator.py
```

or:

```bash
make rtl
```

The script compiles the CPU/testbench and executes every test in `tests/manifest.json`.


## Early Vivado feasibility run

For the Fall milestone, an out-of-context implementation script is included for the CPU core:

```bash
vivado -mode batch -source vivado/run_ooc.tcl
```

It targets the Basys 3 Artix-7 device and a 25 MHz (40 ns) CPU-clock requirement, then writes timing, utilization, and DRC reports to `reports/`. This is an early feasibility check, not the final Spring board implementation.

On Windows, `scripts/run_all_windows.bat` runs the available checks in sequence.

See `STATUS.md` for the exact boundary between implemented, validated, and still-unverified work.

## Important design behavior

### Multicycle sequence

The core uses these conceptual states:

```text
FETCH_REQ -> FETCH_WAIT -> DECODE -> EXEC
                                  |-> WB_ALU -> next fetch
                                  |-> MEM_REQ -> MEM_WAIT -> WB_LOAD -> next fetch
                                  |-> HALT (ECALL/EBREAK/illegal)
```

This is a practical multicycle implementation inspired by the textbook methodology rather than a line-for-line reproduction of its HDL.

### Memory

The CPU has a one-request-at-a-time interface. Requests are issued with `mem_valid`; the memory later pulses `mem_ready`. This deliberately avoids assuming combinational/asynchronous FPGA RAM and makes the core easier to adapt to synchronous block RAM.

### Loads/stores

The core implements:

- `LB`, `LH`, `LW`, `LBU`, `LHU`
- `SB`, `SH`, `SW`

The baseline directed tests use naturally aligned halfword and word accesses. Misaligned halfword/word accesses deterministically halt as an implementation error because privileged trap machinery is outside the baseline project scope.

### FENCE

There is no cache, write buffer, multiple hart, or out-of-order memory system in this baseline. `FENCE` therefore completes as a no-op and advances the PC.

### ECALL / EBREAK

Privileged trap CSRs are explicitly outside the baseline scope. For simulation evidence:

- `ECALL` -> `halt_code = 1`
- `EBREAK` -> `halt_code = 2`
- illegal/misaligned -> `halt_code = 3`, `illegal_insn = 1`

This behavior must be stated in the frozen test manifest and report rather than presented as machine-mode trap support.

## Academic/project use

Treat this as a baseline you own and understand, not a black box to submit unseen. Before your progress defense, every team member responsible for the CPU should be able to explain the PC, instruction register, register file, immediates, ALU operations, branch decisions, memory strobes, and state transitions.
