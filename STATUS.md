# Project status

Verified baseline: 24 November 2026 — `v0.2-fall-verified` (`5941c4d`).

Overall status: **On track.** Our Fall simulation milestone (M4) is met. The early FPGA timing check awaits authorized Vivado access.

## Verified items

| Item | Result | Evidence |
| --- | --- | --- |
| Python reference model and directed instruction coverage | PASS — 40 base mnemonics covered by the directed manifest | [`verilator_regression.txt`](results/verilator_regression.txt), [`manifest.json`](tests/manifest.json) |
| RTL `all40_ebreak` | PASS — `0xA11A0001`, 711 cycles | [`verilator_regression.txt`](results/verilator_regression.txt) |
| RTL `ecall` | PASS — `0xA11A0002`, 31 cycles | [`verilator_regression.txt`](results/verilator_regression.txt) |
| RTL `edge_cases` | PASS — `0xA11A0003`, 893 cycles | [`edge_regression.txt`](results/edge_regression.txt) |
| ACT4 selected RV32I suite | PASS — 39/39, zero failures, timeouts or errors | [`act4_regression.txt`](results/act4_regression.txt), [`act4_version.txt`](results/act4_version.txt) |
| GCC 14.2 compiler inspection (RR-2) | PASS — RV32I/ILP32, 16-byte stack alignment | [`compiler_attributes.txt`](results/compiler_attributes.txt), [`compiler_disassembly.txt`](results/compiler_disassembly.txt) |
| Yosys 0.52 structural schematics | Generated — core and register file | [`rv32i_schematic.svg`](results/rv32i_schematic.svg), [`register_file.svg`](results/register_file.svg) |
| Version-controlled simulation baseline | Tagged | [`v0.2-fall-verified`](https://github.com/Rauan256/RV32I-Processor/tree/v0.2-fall-verified) |

We ran the directed tests with 64 KiB simulation memory and the ACT4 tests with a separate 4 MiB simulation memory configuration. The ACT4 results are limited to the selected suite; ECALL and EBREAK are covered by our directed regression.

## Planned / not yet run

| Item | Status | Milestone |
| --- | --- | --- |
| Early XC7A35T synthesis, 25 MHz timing and preliminary LUT utilization (RR-3) | Not yet run; authorized Vivado access pending. [`run_ooc.tcl`](vivado/run_ooc.tcl) is available. | Originally Fall W13; outstanding ahead of M5 |
| Basys 3 top level and XDC constraints | Planned | M5 — Spring W3 |
| Synthesizable BRAM wrapper and memory initialization | Planned | M5 — Spring W3 |
| UART TX and hardware MMIO at `0x10000000` | Planned | M5 — Spring W3 |
| Bitstream, clock/reset/LED/UART smoke tests | Not yet run | M5 — Spring W3 |
| Linked C program executing on FPGA with UART output | Not yet run; compiler inspection completed separately | M6 — Spring W6 |
| Final FPGA timing, utilization, full system regression and demo release | Not yet run | M8 — Spring W13 |

Clean-clone end-to-end reproduction and formal architectural certification are not established by the current simulation results.
