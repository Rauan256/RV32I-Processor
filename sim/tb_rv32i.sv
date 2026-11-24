module tb_rv32i;
    logic clk = 1'b0;
    logic reset = 1'b1;
    logic halted, illegal_insn;
    logic [1:0] halt_code;
    logic [31:0] debug_pc, debug_instr;
    logic [3:0] debug_state;

    integer cycles;
    integer sigoff;
    integer timeout_cycles;
    integer expected_halt;
    logic [31:0] expected;
    logic [31:0] signature;

    rv32i_sim_top dut (
        .clk(clk), .reset(reset),
        .halted(halted), .illegal_insn(illegal_insn), .halt_code(halt_code),
        .debug_pc(debug_pc), .debug_instr(debug_instr), .debug_state(debug_state)
    );

    always #5 clk = ~clk;

    initial begin
        $dumpfile("waveform.vcd");
        $dumpvars(0, tb_rv32i);
        sigoff = 16'h0400;
        timeout_cycles = 10000;
        expected = 32'hA11A_0001;
        expected_halt = 2;
        void'($value$plusargs("SIGOFF=%h", sigoff));
        void'($value$plusargs("EXPECT=%h", expected));
        void'($value$plusargs("TIMEOUT=%d", timeout_cycles));
        void'($value$plusargs("HALT=%d", expected_halt));

        repeat (4) @(posedge clk);
        reset <= 1'b0;

        cycles = 0;
        while (!halted && cycles < timeout_cycles) begin
            @(posedge clk);
            cycles = cycles + 1;
        end

        if (!halted) begin
            $display("FAIL: timeout after %0d cycles, pc=%08x instr=%08x state=%0d", cycles, debug_pc, debug_instr, debug_state);
            $fatal(1);
        end

        if (illegal_insn) begin
            $display("FAIL: illegal/misaligned instruction at pc=%08x instr=%08x", debug_pc, debug_instr);
            $fatal(1);
        end

        if (halt_code !== expected_halt[1:0]) begin
            $display("FAIL: halt_code=%0d expected=%0d", halt_code, expected_halt);
            $fatal(1);
        end

        signature = dut.mem.ram[sigoff >> 2];
        if (signature !== expected) begin
            $display("FAIL: signature %08x, expected %08x; halt_code=%0d pc=%08x", signature, expected, halt_code, debug_pc);
            $fatal(1);
        end

        $display("PASS: signature=%08x halt_code=%0d cycles=%0d pc=%08x", signature, halt_code, cycles, debug_pc);
        $finish;
    end
endmodule
