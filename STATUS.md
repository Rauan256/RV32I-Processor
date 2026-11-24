# Verification status

## Implemented in this package

- Multicycle, in-order RV32I core written from scratch in SystemVerilog.
- 32 architectural registers (`x0` hardwired to zero) and 32-bit PC.
- Reset PC `0x8000_0000`.
- Decode/execute support for all 40 RV32I base mnemonics in the project manifest.
- Loads/stores: LB, LH, LW, LBU, LHU, SB, SH, SW.
- All RV32I ALU-immediate, ALU-register, branch, jump, LUI/AUIPC instructions.
- `FENCE` as a deterministic no-op for this single-hart uncached baseline.
- Project-defined deterministic `ECALL` / `EBREAK` halt behavior.
- Request/ready memory interface intended to tolerate synchronous-memory latency.
- 64 KiB simulation memory and self-checking testbench.
- Directed generated programs plus an independent Python RV32I reference model.
- Early Vivado out-of-context 25 MHz timing/utilization script.

## Validation completed in the creation environment

The generated programs pass the independent Python reference model:

- `all40_ebreak` -> signature `0xA11A0001`, EBREAK halt.
- `ecall` -> signature `0xA11A0002`, ECALL halt.
- Manifest coverage contains all 40 required RV32I mnemonics.

## Validation that still requires your EDA installation

The creation environment does not contain Verilator, Icarus Verilog, or Vivado. Therefore the following artifacts cannot truthfully be marked PASS yet:

1. SystemVerilog compile/lint log.
2. RTL regression console log/waveform.
3. Vivado post-route 25 MHz timing report.
4. Vivado utilization report.

Run `python scripts/run_verilator.py` and then `vivado -mode batch -source vivado/run_ooc.tcl` on a machine with those tools. If either reports an error, fix it before presenting the RTL as verified.

## Not Fall baseline / planned for Spring

- Physical Basys 3 clocking/top-level constraints.
- Synthesizable on-board BRAM wrapper and memory image preload flow.
- Physical UART TX module and MMIO decode on the board.
- Bitstream generation and hardware smoke test.
- Compiled C program executing on the physical FPGA.
