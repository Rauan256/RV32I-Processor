# Fall W14 Deliverables / Evidence Checklist

The approved proposal sets Fall W14 as the **complete RV32I simulation baseline**, not the final physical FPGA demo.

Collect these artifacts as you work:

- [ ] Architecture/datapath diagram and FSM diagram frozen
- [ ] `rv32i_core.sv` + modular RTL committed/tagged
- [ ] 32-register file with x0 behavior verified
- [ ] all 40 RV32I base mnemonics represented in the frozen test manifest
- [ ] directed test logs for arithmetic/immediate/shift families
- [ ] directed test logs for all six branches
- [ ] directed tests for JAL/JALR and upper-immediate instructions
- [ ] byte/halfword/word load/store tests
- [ ] explicit FENCE/ECALL/EBREAK project behavior documented
- [ ] reset test showing first fetch at `0x80000000`
- [ ] testbench log showing pass signatures
- [ ] waveform screenshots for at least fetch/decode/execute, branch, and load/store
- [ ] early Vivado synthesis report
- [ ] 25 MHz timing feasibility evidence (WNS target >= 0)
- [ ] estimated LUT/FF use recorded
- [ ] baseline-vs-actual schedule table for Design Progress report
- [ ] Git commit/tag IDs linked to claims in the progress report

## Do not claim yet unless actually completed

These are mainly Spring deliverables in the proposal:

- physical Basys 3 BRAM/UART smoke test
- final hardware UART 1000-character test
- full C program running on physical FPGA
- final 25/50 MHz timing/resource closure
- final physical demonstration
