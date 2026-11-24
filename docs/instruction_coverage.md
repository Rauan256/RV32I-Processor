# RV32I Base Instruction Coverage

The project baseline uses the 40-mnemonic counting convention in the approved proposal.

| Group | Instructions | Core handling |
|---|---|---|
| Upper immediate | LUI, AUIPC | `OP_LUI`, `OP_AUIPC` |
| Jumps | JAL, JALR | `OP_JAL`, `OP_JALR` |
| Branches | BEQ, BNE, BLT, BGE, BLTU, BGEU | `OP_BRANCH` |
| Loads | LB, LH, LW, LBU, LHU | `OP_LOAD` + `ST_WB_LOAD` |
| Stores | SB, SH, SW | `OP_STORE` + byte write strobes |
| Immediate ALU | ADDI, SLTI, SLTIU, XORI, ORI, ANDI, SLLI, SRLI, SRAI | `OP_IMM` |
| Register ALU | ADD, SUB, SLL, SLT, SLTU, XOR, SRL, SRA, OR, AND | `OP_REG` |
| Ordering | FENCE | `OP_MISC_MEM` (baseline no-op) |
| Environment | ECALL, EBREAK | `OP_SYSTEM` (project-defined halt) |

The generator writes a machine-readable list to `tests/manifest.json`. The test-generation script fails if the union of the directed tests omits any required mnemonic.

Mnemonic presence is only the first layer of verification. Before the manifest is considered final, add corner cases such as zero/negative operands, maximum/minimum signed values, shift amounts, forward/backward branches, and boundary byte/halfword accesses.
