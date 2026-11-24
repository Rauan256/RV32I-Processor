module rv32i_sim_top (
    input  logic        clk,
    input  logic        reset,
    output logic        halted,
    output logic        illegal_insn,
    output logic [1:0]  halt_code,
    output logic [31:0] debug_pc,
    output logic [31:0] debug_instr,
    output logic [3:0]  debug_state
);
    logic        mem_valid, mem_we, mem_ready;
    logic [31:0] mem_addr, mem_wdata, mem_rdata;
    logic [3:0]  mem_wstrb;

    rv32i_core core (
        .clk(clk), .reset(reset),
        .mem_valid(mem_valid), .mem_we(mem_we),
        .mem_addr(mem_addr), .mem_wdata(mem_wdata), .mem_wstrb(mem_wstrb),
        .mem_ready(mem_ready), .mem_rdata(mem_rdata),
        .halted(halted), .illegal_insn(illegal_insn), .halt_code(halt_code),
        .debug_pc(debug_pc), .debug_instr(debug_instr), .debug_state(debug_state)
    );

    rv32i_sim_memory mem (
        .clk(clk), .reset(reset),
        .valid(mem_valid), .we(mem_we), .addr(mem_addr),
        .wdata(mem_wdata), .wstrb(mem_wstrb),
        .ready(mem_ready), .rdata(mem_rdata)
    );
endmodule
