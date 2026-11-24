module rv32i_core #(
    parameter logic [31:0] RESET_PC = 32'h8000_0000
) (
    input  logic        clk,
    input  logic        reset,

    // One-request-at-a-time memory interface. A request is issued with
    // mem_valid for one cycle; mem_ready later pulses with read data/ack.
    output logic        mem_valid,
    output logic        mem_we,
    output logic [31:0] mem_addr,
    output logic [31:0] mem_wdata,
    output logic [3:0]  mem_wstrb,
    input  logic        mem_ready,
    input  logic [31:0] mem_rdata,

    output logic        halted,
    output logic        illegal_insn,
    output logic [1:0]  halt_code,   // 01=ECALL, 10=EBREAK, 11=illegal/misaligned
    output logic [31:0] debug_pc,
    output logic [31:0] debug_instr,
    output logic [3:0]  debug_state
);
    // RV32I opcodes
    localparam logic [6:0] OP_LUI      = 7'b0110111;
    localparam logic [6:0] OP_AUIPC    = 7'b0010111;
    localparam logic [6:0] OP_JAL      = 7'b1101111;
    localparam logic [6:0] OP_JALR     = 7'b1100111;
    localparam logic [6:0] OP_BRANCH   = 7'b1100011;
    localparam logic [6:0] OP_LOAD     = 7'b0000011;
    localparam logic [6:0] OP_STORE    = 7'b0100011;
    localparam logic [6:0] OP_IMM      = 7'b0010011;
    localparam logic [6:0] OP_REG      = 7'b0110011;
    localparam logic [6:0] OP_MISC_MEM = 7'b0001111;
    localparam logic [6:0] OP_SYSTEM   = 7'b1110011;

    typedef enum logic [3:0] {
        ST_FETCH_REQ = 4'd0,
        ST_FETCH_WAIT= 4'd1,
        ST_DECODE    = 4'd2,
        ST_EXEC      = 4'd3,
        ST_WB_ALU    = 4'd4,
        ST_MEM_REQ   = 4'd5,
        ST_MEM_WAIT  = 4'd6,
        ST_WB_LOAD   = 4'd7,
        ST_HALT      = 4'd8
    } state_t;

    state_t state;
    logic [31:0] pc, ir;
    logic [31:0] a_reg, b_reg;
    logic [4:0]  rd_reg;
    logic [31:0] wb_result_reg, next_pc_reg;
    logic        wb_enable_reg;

    logic [31:0] mem_addr_reg, store_wdata_reg, load_data_reg;
    logic [3:0]  store_wstrb_reg;
    logic [2:0]  mem_funct3_reg;
    logic        pending_load_reg;

    logic        rf_we;
    logic [31:0] rf_wdata;
    logic [31:0] rs1_data, rs2_data;

    wire [6:0] opcode = ir[6:0];
    wire [2:0] funct3 = ir[14:12];
    wire [6:0] funct7 = ir[31:25];
    wire [4:0] rs1 = ir[19:15];
    wire [4:0] rs2 = ir[24:20];
    wire [4:0] rd  = ir[11:7];

    wire [31:0] imm_i = {{20{ir[31]}}, ir[31:20]};
    wire [31:0] imm_s = {{20{ir[31]}}, ir[31:25], ir[11:7]};
    wire [31:0] imm_b = {{19{ir[31]}}, ir[31], ir[7], ir[30:25], ir[11:8], 1'b0};
    wire [31:0] imm_u = {ir[31:12], 12'b0};
    wire [31:0] imm_j = {{11{ir[31]}}, ir[31], ir[19:12], ir[20], ir[30:21], 1'b0};

    wire [31:0] load_shifted = load_data_reg >> (8 * mem_addr_reg[1:0]);

    rv32i_regfile rf (
        .clk(clk), .reset(reset),
        .rs1(rs1), .rs2(rs2),
        .rd(rd_reg), .we(rf_we), .wd(rf_wdata),
        .rd1(rs1_data), .rd2(rs2_data)
    );

    always_comb begin
        rf_we    = 1'b0;
        rf_wdata = 32'd0;
        if (state == ST_WB_ALU && wb_enable_reg) begin
            rf_we    = 1'b1;
            rf_wdata = wb_result_reg;
        end else if (state == ST_WB_LOAD) begin
            rf_we = 1'b1;
            case (mem_funct3_reg)
                3'b000: rf_wdata = {{24{load_shifted[7]}},  load_shifted[7:0]};   // LB
                3'b001: rf_wdata = {{16{load_shifted[15]}}, load_shifted[15:0]};  // LH
                3'b010: rf_wdata = load_data_reg;                                  // LW (aligned)
                3'b100: rf_wdata = {24'd0, load_shifted[7:0]};                    // LBU
                3'b101: rf_wdata = {16'd0, load_shifted[15:0]};                   // LHU
                default: rf_wdata = 32'd0;
            endcase
        end
    end

    always_comb begin
        mem_valid = 1'b0;
        mem_we    = 1'b0;
        mem_addr  = 32'd0;
        mem_wdata = 32'd0;
        mem_wstrb = 4'b0000;

        case (state)
            ST_FETCH_REQ: begin
                mem_valid = 1'b1;
                mem_addr  = pc;
            end
            ST_MEM_REQ: begin
                mem_valid = 1'b1;
                mem_we    = ~pending_load_reg;
                mem_addr  = mem_addr_reg;
                mem_wdata = store_wdata_reg;
                mem_wstrb = pending_load_reg ? 4'b0000 : store_wstrb_reg;
            end
            default: begin end
        endcase
    end

    assign debug_pc    = pc;
    assign debug_instr = ir;
    assign debug_state = state;

    function automatic logic branch_taken(
        input logic [2:0] f3,
        input logic [31:0] lhs,
        input logic [31:0] rhs
    );
        begin
            case (f3)
                3'b000: branch_taken = (lhs == rhs);                    // BEQ
                3'b001: branch_taken = (lhs != rhs);                    // BNE
                3'b100: branch_taken = ($signed(lhs) < $signed(rhs));   // BLT
                3'b101: branch_taken = ($signed(lhs) >= $signed(rhs));  // BGE
                3'b110: branch_taken = (lhs < rhs);                     // BLTU
                3'b111: branch_taken = (lhs >= rhs);                    // BGEU
                default: branch_taken = 1'b0;
            endcase
        end
    endfunction

    function automatic logic valid_branch_f3(input logic [2:0] f3);
        valid_branch_f3 = (f3 == 3'b000) || (f3 == 3'b001) ||
                          (f3 == 3'b100) || (f3 == 3'b101) ||
                          (f3 == 3'b110) || (f3 == 3'b111);
    endfunction

    task automatic enter_illegal;
        begin
            halted       <= 1'b1;
            illegal_insn <= 1'b1;
            halt_code    <= 2'b11;
            state        <= ST_HALT;
        end
    endtask

    logic [31:0] alu_tmp;
    logic [31:0] eff_addr;
    logic        valid_exec;

    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            state            <= ST_FETCH_REQ;
            pc               <= RESET_PC;
            ir               <= 32'h0000_0013; // NOP = ADDI x0,x0,0
            a_reg            <= 32'd0;
            b_reg            <= 32'd0;
            rd_reg           <= 5'd0;
            wb_result_reg    <= 32'd0;
            next_pc_reg      <= RESET_PC;
            wb_enable_reg    <= 1'b0;
            mem_addr_reg     <= 32'd0;
            store_wdata_reg  <= 32'd0;
            store_wstrb_reg  <= 4'd0;
            mem_funct3_reg   <= 3'd0;
            pending_load_reg <= 1'b0;
            load_data_reg    <= 32'd0;
            halted           <= 1'b0;
            illegal_insn     <= 1'b0;
            halt_code        <= 2'b00;
        end else begin
            case (state)
                ST_FETCH_REQ: begin
                    state <= ST_FETCH_WAIT;
                end

                ST_FETCH_WAIT: begin
                    if (mem_ready) begin
                        ir    <= mem_rdata;
                        state <= ST_DECODE;
                    end
                end

                ST_DECODE: begin
                    a_reg  <= rs1_data;
                    b_reg  <= rs2_data;
                    rd_reg <= rd;
                    state  <= ST_EXEC;
                end

                ST_EXEC: begin
                    // Defaults for any non-memory instruction that reaches WB_ALU.
                    wb_result_reg <= 32'd0;
                    wb_enable_reg <= 1'b0;
                    next_pc_reg   <= pc + 32'd4;
                    valid_exec    = 1'b1;
                    alu_tmp       = 32'd0;
                    eff_addr      = 32'd0;

                    case (opcode)
                        OP_LUI: begin
                            wb_result_reg <= imm_u;
                            wb_enable_reg <= 1'b1;
                            state         <= ST_WB_ALU;
                        end

                        OP_AUIPC: begin
                            wb_result_reg <= pc + imm_u;
                            wb_enable_reg <= 1'b1;
                            state         <= ST_WB_ALU;
                        end

                        OP_JAL: begin
                            eff_addr = pc + imm_j;
                            if (eff_addr[1:0] != 2'b00) begin
                                enter_illegal();
                            end else begin
                                wb_result_reg <= pc + 32'd4;
                                wb_enable_reg <= 1'b1;
                                next_pc_reg   <= eff_addr;
                                state         <= ST_WB_ALU;
                            end
                        end

                        OP_JALR: begin
                            if (funct3 == 3'b000) begin
                                eff_addr = (a_reg + imm_i) & 32'hFFFF_FFFE;
                                if (eff_addr[1:0] != 2'b00) begin
                                    enter_illegal();
                                end else begin
                                    wb_result_reg <= pc + 32'd4;
                                    wb_enable_reg <= 1'b1;
                                    next_pc_reg   <= eff_addr;
                                    state         <= ST_WB_ALU;
                                end
                            end else begin
                                enter_illegal();
                            end
                        end

                        OP_BRANCH: begin
                            if (!valid_branch_f3(funct3)) begin
                                enter_illegal();
                            end else begin
                                wb_enable_reg <= 1'b0;
                                if (branch_taken(funct3, a_reg, b_reg)) begin
                                    eff_addr = pc + imm_b;
                                    if (eff_addr[1:0] != 2'b00)
                                        enter_illegal();
                                    else begin
                                        next_pc_reg <= eff_addr;
                                        state <= ST_WB_ALU;
                                    end
                                end else begin
                                    state <= ST_WB_ALU;
                                end
                            end
                        end

                        OP_LOAD: begin
                            eff_addr = a_reg + imm_i;
                            if ((funct3 == 3'b001 || funct3 == 3'b101) && eff_addr[0]) begin
                                enter_illegal();
                            end else if ((funct3 == 3'b010) && (eff_addr[1:0] != 2'b00)) begin
                                enter_illegal();
                            end else if (!((funct3 == 3'b000) || (funct3 == 3'b001) ||
                                           (funct3 == 3'b010) || (funct3 == 3'b100) ||
                                           (funct3 == 3'b101))) begin
                                enter_illegal();
                            end else begin
                                mem_addr_reg     <= eff_addr;
                                mem_funct3_reg   <= funct3;
                                pending_load_reg <= 1'b1;
                                state            <= ST_MEM_REQ;
                            end
                        end

                        OP_STORE: begin
                            eff_addr = a_reg + imm_s;
                            pending_load_reg <= 1'b0;
                            mem_addr_reg     <= eff_addr;
                            mem_funct3_reg   <= funct3;
                            case (funct3)
                                3'b000: begin // SB
                                    store_wstrb_reg <= (4'b0001 << eff_addr[1:0]);
                                    store_wdata_reg <= ({24'd0, b_reg[7:0]} << (8 * eff_addr[1:0]));
                                    state <= ST_MEM_REQ;
                                end
                                3'b001: begin // SH
                                    if (eff_addr[0]) begin
                                        enter_illegal();
                                    end else begin
                                        store_wstrb_reg <= eff_addr[1] ? 4'b1100 : 4'b0011;
                                        store_wdata_reg <= eff_addr[1] ? {b_reg[15:0],16'd0} : {16'd0,b_reg[15:0]};
                                        state <= ST_MEM_REQ;
                                    end
                                end
                                3'b010: begin // SW
                                    if (eff_addr[1:0] != 2'b00) begin
                                        enter_illegal();
                                    end else begin
                                        store_wstrb_reg <= 4'b1111;
                                        store_wdata_reg <= b_reg;
                                        state <= ST_MEM_REQ;
                                    end
                                end
                                default: enter_illegal();
                            endcase
                        end

                        OP_IMM: begin
                            wb_enable_reg <= 1'b1;
                            case (funct3)
                                3'b000: wb_result_reg <= a_reg + imm_i; // ADDI
                                3'b010: wb_result_reg <= ($signed(a_reg) < $signed(imm_i)) ? 32'd1 : 32'd0; // SLTI
                                3'b011: wb_result_reg <= (a_reg < imm_i) ? 32'd1 : 32'd0; // SLTIU
                                3'b100: wb_result_reg <= a_reg ^ imm_i; // XORI
                                3'b110: wb_result_reg <= a_reg | imm_i; // ORI
                                3'b111: wb_result_reg <= a_reg & imm_i; // ANDI
                                3'b001: begin // SLLI
                                    if (funct7 == 7'b0000000)
                                        wb_result_reg <= a_reg << ir[24:20];
                                    else
                                        valid_exec = 1'b0;
                                end
                                3'b101: begin
                                    if (funct7 == 7'b0000000)
                                        wb_result_reg <= a_reg >> ir[24:20]; // SRLI
                                    else if (funct7 == 7'b0100000)
                                        wb_result_reg <= $signed(a_reg) >>> ir[24:20]; // SRAI
                                    else
                                        valid_exec = 1'b0;
                                end
                                default: valid_exec = 1'b0;
                            endcase
                            if (valid_exec)
                                state <= ST_WB_ALU;
                            else
                                enter_illegal();
                        end

                        OP_REG: begin
                            wb_enable_reg <= 1'b1;
                            case (funct3)
                                3'b000: begin
                                    if (funct7 == 7'b0000000) wb_result_reg <= a_reg + b_reg;       // ADD
                                    else if (funct7 == 7'b0100000) wb_result_reg <= a_reg - b_reg;  // SUB
                                    else valid_exec = 1'b0;
                                end
                                3'b001: begin
                                    if (funct7 == 7'b0000000) wb_result_reg <= a_reg << b_reg[4:0]; // SLL
                                    else valid_exec = 1'b0;
                                end
                                3'b010: begin
                                    if (funct7 == 7'b0000000) wb_result_reg <= ($signed(a_reg) < $signed(b_reg)) ? 32'd1 : 32'd0; // SLT
                                    else valid_exec = 1'b0;
                                end
                                3'b011: begin
                                    if (funct7 == 7'b0000000) wb_result_reg <= (a_reg < b_reg) ? 32'd1 : 32'd0; // SLTU
                                    else valid_exec = 1'b0;
                                end
                                3'b100: begin
                                    if (funct7 == 7'b0000000) wb_result_reg <= a_reg ^ b_reg; // XOR
                                    else valid_exec = 1'b0;
                                end
                                3'b101: begin
                                    if (funct7 == 7'b0000000) wb_result_reg <= a_reg >> b_reg[4:0]; // SRL
                                    else if (funct7 == 7'b0100000) wb_result_reg <= $signed(a_reg) >>> b_reg[4:0]; // SRA
                                    else valid_exec = 1'b0;
                                end
                                3'b110: begin
                                    if (funct7 == 7'b0000000) wb_result_reg <= a_reg | b_reg; // OR
                                    else valid_exec = 1'b0;
                                end
                                3'b111: begin
                                    if (funct7 == 7'b0000000) wb_result_reg <= a_reg & b_reg; // AND
                                    else valid_exec = 1'b0;
                                end
                                default: valid_exec = 1'b0;
                            endcase
                            if (valid_exec)
                                state <= ST_WB_ALU;
                            else
                                enter_illegal();
                        end

                        OP_MISC_MEM: begin
                            // RV32I FENCE. In this single-hart, uncached baseline there is
                            // no buffered memory reordering to drain, so FENCE is a no-op.
                            if (funct3 == 3'b000) begin
                                wb_enable_reg <= 1'b0;
                                state <= ST_WB_ALU;
                            end else begin
                                enter_illegal();
                            end
                        end

                        OP_SYSTEM: begin
                            // Privileged trap machinery is outside baseline scope. We make
                            // ECALL/EBREAK deterministic and observable for simulation.
                            if ((funct3 == 3'b000) && (rs1 == 5'd0) && (rd == 5'd0)) begin
                                if (ir[31:20] == 12'd0) begin
                                    halted    <= 1'b1;
                                    halt_code <= 2'b01; // ECALL
                                    state     <= ST_HALT;
                                end else if (ir[31:20] == 12'd1) begin
                                    halted    <= 1'b1;
                                    halt_code <= 2'b10; // EBREAK
                                    state     <= ST_HALT;
                                end else begin
                                    enter_illegal();
                                end
                            end else begin
                                enter_illegal();
                            end
                        end

                        default: enter_illegal();
                    endcase
                end

                ST_WB_ALU: begin
                    pc    <= next_pc_reg;
                    state <= ST_FETCH_REQ;
                end

                ST_MEM_REQ: begin
                    state <= ST_MEM_WAIT;
                end

                ST_MEM_WAIT: begin
                    if (mem_ready) begin
                        if (pending_load_reg) begin
                            load_data_reg <= mem_rdata;
                            state <= ST_WB_LOAD;
                        end else begin
                            pc    <= pc + 32'd4;
                            state <= ST_FETCH_REQ;
                        end
                    end
                end

                ST_WB_LOAD: begin
                    pc    <= pc + 32'd4;
                    state <= ST_FETCH_REQ;
                end

                ST_HALT: begin
                    state <= ST_HALT;
                end

                default: enter_illegal();
            endcase
        end
    end
endmodule
