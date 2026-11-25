# Fall 2026 deliverables

We completed the Fall RV32I simulation milestone (M4). Our verified baseline is [`v0.2-fall-verified`](https://github.com/Rauan256/RV32I-Processor/tree/v0.2-fall-verified), commit `5941c4d`, verified on 24 November 2026. The early FPGA timing check (RR-3) awaits authorized Vivado access.

## Fall verification and evidence

- [x] Processor architecture and FSM documented in the [architecture overview](START_HERE.md) and design progress report.
- [x] [Core RTL](../rtl/rv32i_core.sv) and [register file](../rtl/rv32i_regfile.sv) committed and tagged.
- [x] Register file and x0 behavior verified in directed regression.
- [x] All 40 RV32I base mnemonics covered by the [directed test manifest](../tests/manifest.json).
- [x] Arithmetic, immediate and shift operations tested.
- [x] All six conditional branch instructions tested.
- [x] JAL/JALR and upper-immediate instructions tested.
- [x] Byte, halfword and word load/store operations tested.
- [x] FENCE, ECALL and EBREAK behavior documented and tested.
- [x] Reset and first fetch at `0x80000000` documented in the report waveform.
- [x] Three directed RTL programs passed with expected signatures: [standard regression](../results/verilator_regression.txt) and [edge-case regression](../results/edge_regression.txt).
- [x] GTKWave screenshots of reset, fetch and instruction execution included in the design progress report.
- [x] Yosys structural schematics generated for the [core](../results/rv32i_schematic.svg) and [register file](../results/register_file.svg).
- [x] All 39 selected official ACT4 programs passed, with zero failures, timeouts or errors: [ACT4 regression](../results/act4_regression.txt).
- [x] GCC RV32I/ILP32 compiler inspection completed, including 16-byte stack alignment: [attributes](../results/compiler_attributes.txt) and [disassembly](../results/compiler_disassembly.txt).
- [x] Baseline and updated schedule included in the design progress report.
- [x] Git commit and tag recorded in the design progress report.

## Planned for Spring 2027

The RR-3 checks were originally scheduled for Fall W13 and remain outstanding. The remaining hardware milestones are scheduled for Spring.

- [ ] RR-3: early Vivado synthesis on XC7A35T using [run_ooc.tcl](../vivado/run_ooc.tcl); awaits authorized access.
- [ ] RR-3: 25 MHz timing feasibility (WNS >= 0) and preliminary LUT/FF utilization; target below 30% LUTs.
- [ ] M5 (Spring W3): Basys 3 top level, XDC constraints, BRAM wrapper, UART MMIO at `0x10000000`, bitstream and hardware smoke tests.
- [ ] M6 (Spring W6): compiled C program running on FPGA with deterministic UART output.
- [ ] M8 (Spring W13): final 25/50 MHz timing and resource verification, 1000-character UART test, system regression and final hardware demonstration.

See [STATUS.md](../STATUS.md) for the full milestone and verification record. The completed tests establish the simulation baseline; FPGA operation has not yet been verified.
