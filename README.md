# RV32I Processor

ENG 400 Capstone Project — Electrical and Computer Engineering, Nazarbayev University.

We are developing a 32-bit, multicycle, in-order RISC-V processor in SystemVerilog for implementation on the Basys 3 Artix-7 FPGA. Our Fall 2026 simulation baseline passed all three directed programs and all 39 selected RV32I architectural tests. FPGA integration is planned for Spring 2027.

**Verified baseline (24 November 2026):** [`v0.2-fall-verified`](https://github.com/Rauan256/RV32I-Processor/tree/v0.2-fall-verified), commit [`5941c4d`](https://github.com/Rauan256/RV32I-Processor/commit/5941c4d27a5e189bc0d7d9aaaa2c68aefd3d10b7).

## Team

| Member | Responsibility |
| --- | --- |
| Artur Tagirov | Software, RISC-V toolchain and runtime |
| Rauan Sabyr | ISA, instruction decoder, ALU and control FSM |
| Yerassyl Baktybayev | Register file, memory, I/O and FPGA peripherals |
| Magzhan Zhengis | System integration, FPGA implementation and verification |

Supervisor: Behrouz Maham.

## Architecture

- 32-bit PC, reset vector `0x80000000`, and 32 general-purpose registers with `x0` hardwired to zero.
- Multicycle control FSM with nine states (0–8) and one instruction in progress at a time.
- Single memory port with `mem_valid`/`mem_ready` request/response signaling and four byte-write strobes.
- RV32I arithmetic, logic, shifts, comparisons, branches, jumps, upper immediates, loads and stores.
- `FENCE` is a no-op in our uncached single-hart design. `ECALL` and `EBREAK` halt with codes 1 and 2; illegal instructions or detected misaligned accesses halt with code 3.

The current core has no privileged CSR or interrupt handling, caches, MMU, pipeline, or optional ISA extensions. See [Architecture overview](docs/START_HERE.md) for the datapath and state sequence.

## Repository layout

| Path | Contents |
| --- | --- |
| [`rtl/`](rtl/) | `rv32i_core.sv`, `rv32i_regfile.sv` |
| [`sim/`](sim/) | Simulation memory, top module and self-checking testbench |
| [`tests/`](tests/) | Directed test generator, manifest, HEX images, edge-case and ACT4 runners |
| [`tests/act4_config/`](tests/act4_config/) | ACT4 configuration, Sail configuration, linker script and model macros |
| [`tools/ref_model.py`](tools/ref_model.py) | Python functional reference model |
| [`scripts/`](scripts/) | Regression automation |
| [`software/compiler_check.c`](software/compiler_check.c) | C compiler inspection program |
| [`results/`](results/) | Test logs, compiler inspection and Yosys structural schematics |
| [`vivado/run_ooc.tcl`](vivado/run_ooc.tcl) | Preliminary out-of-context FPGA synthesis/timing script (not yet run) |
| [`docs/`](docs/) | Architecture, instruction coverage and project documentation |

## Running the tests

Commands below run from the repository root in WSL Ubuntu. The RTL tests require Verilator, GNU Make and a host C++ compiler in addition to Python 3.

### Python reference model

```bash
python3 tests/gen_tests.py
python3 tools/ref_model.py
```

The model implements the project's 40 RV32I base mnemonics and checks the generated programs against the expected signatures and halt codes in `tests/manifest.json`.

### Directed RTL regression

```bash
verilator --version
python3 scripts/run_verilator.py
python3 tests/run_edge_tests.py
```

`make rtl` is an alternative to the first regression script. The edge-case runner uses the Verilator executable built by that script. The standard testbench uses 64 KiB of simulated RAM.

### RISC-V Architectural Certification Tests (ACT4)

We use upstream [riscv-arch-test](https://github.com/riscv/riscv-arch-test) at revision `772408a90ee7b35edc5146c1d4e226b4ac7ff6b2`, Sail 0.16, and xPack RISC-V GCC 15.2.0. The ACT4 setup also requires its upstream Mise, UV, Ruby and Bundler dependencies.

With these tools installed and on `PATH`, the following commands prepare the selected tests. The runner currently expects the GCC 15 `nm` executable at `~/riscv-tools/gcc15/bin/riscv-none-elf-nm`.

```bash
# From the capstone repository root
PROJECT="$PWD"
mkdir -p ~/riscv-tools
# For a new ACT4 checkout:
git clone https://github.com/riscv/riscv-arch-test.git ~/riscv-tools/riscv-arch-test
cd ~/riscv-tools/riscv-arch-test
git checkout 772408a90ee7b35edc5146c1d4e226b4ac7ff6b2
mkdir -p config/cores/nu/rv32i-capstone
cp "$PROJECT"/tests/act4_config/* config/cores/nu/rv32i-capstone/
make tests EXTENSIONS=I JOBS=4
make CONFIG_FILES=config/cores/nu/rv32i-capstone/test_config.yaml EXTENSIONS=I JOBS=4
cd "$PROJECT"
python3 tests/run_act4.py --all
```

For an existing checkout, the clone step is unnecessary. The runner converts the final self-checking ELFs into HEX images, uses 4 MiB of simulated RAM, and detects the ACT4 `tohost` result. The default ELF directory is `~/riscv-tools/riscv-arch-test/work/nu-rv32i-capstone/elfs`; `--suite` selects another directory. This setup does not change the core RTL or the 64 KiB standard simulation configuration.

## Verification results

| Test | Signature | RTL cycles | Result |
| --- | --- | ---: | --- |
| `all40_ebreak` | `0xA11A0001` | 711 | PASS |
| `ecall` | `0xA11A0002` | 31 | PASS |
| `edge_cases` | `0xA11A0003` | 893 | PASS |
| ACT4 selected RV32I programs | Self-checking | Per-test log | 39/39 PASS |

Logs: [directed regression](results/verilator_regression.txt), [edge-case regression](results/edge_regression.txt), [ACT4 regression](results/act4_regression.txt). ACT4 reported zero failures, timeouts and errors. The results apply to simulation, not formal certification or FPGA operation.

We also compiled and inspected a C program using GCC 14.2 (`rv32i`/`ilp32`, 16-byte stack alignment). See [ELF attributes](results/compiler_attributes.txt) and [disassembly](results/compiler_disassembly.txt). Yosys structural schematics are available for the [core](results/rv32i_schematic.svg) and [register file](results/register_file.svg).

## Spring 2027 roadmap

- M5 (Spring W3): complete the Basys 3 top level, XDC, BRAM wrapper, UART MMIO at `0x10000000`, bitstream and hardware smoke tests. The early Vivado 25 MHz timing check awaits authorized access.
- M6 (Spring W6): execute a compiled C program on the FPGA and verify deterministic UART output.
- M8 (Spring W13): complete final system regression, timing and resource checks, and demo release.

See [STATUS.md](STATUS.md) for the verification and milestone record.

## Tools and acknowledgements

Windows with WSL Ubuntu; Python 3; GNU Make 4.4.1; Verilator 5.032; GTKWave 3.3.126; Yosys 0.52; GCC 14.2 and 15.2; Sail 0.16. 
