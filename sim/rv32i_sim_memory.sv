module rv32i_sim_memory #(
    parameter logic [31:0] BASE_ADDR = 32'h8000_0000,
    parameter integer MEM_BYTES = 65536,
    parameter logic [31:0] UART_ADDR = 32'h1000_0000
) (
    input  logic        clk,
    input  logic        reset,
    input  logic        valid,
    input  logic        we,
    input  logic [31:0] addr,
    input  logic [31:0] wdata,
    input  logic [3:0]  wstrb,
    output logic        ready,
    output logic [31:0] rdata
);
    localparam integer WORDS = MEM_BYTES/4;
    logic [31:0] ram [0:WORDS-1];

    logic pending;
    logic req_we;
    logic [31:0] req_addr, req_wdata;
    logic [3:0] req_wstrb;
    integer i;
    integer idx;
    string memfile;

    initial begin
        for (i = 0; i < WORDS; i = i + 1)
            ram[i] = 32'd0;
        if ($value$plusargs("MEMFILE=%s", memfile)) begin
            $display("Loading memory image: %s", memfile);
            $readmemh(memfile, ram);
        end
    end

    always_ff @(posedge clk or posedge reset) begin
        if (reset) begin
            pending   <= 1'b0;
            ready     <= 1'b0;
            rdata     <= 32'd0;
            req_we    <= 1'b0;
            req_addr  <= 32'd0;
            req_wdata <= 32'd0;
            req_wstrb <= 4'd0;
        end else begin
            ready <= 1'b0;

            if (pending) begin
                pending <= 1'b0;
                ready   <= 1'b1;

                if ((req_addr >= BASE_ADDR) && (req_addr < BASE_ADDR + MEM_BYTES)) begin
                    idx = (req_addr - BASE_ADDR) >> 2;
                    if (req_we) begin
                        if (req_wstrb[0]) ram[idx][7:0]   <= req_wdata[7:0];
                        if (req_wstrb[1]) ram[idx][15:8]  <= req_wdata[15:8];
                        if (req_wstrb[2]) ram[idx][23:16] <= req_wdata[23:16];
                        if (req_wstrb[3]) ram[idx][31:24] <= req_wdata[31:24];
                    end else begin
                        rdata <= ram[idx];
                    end
                end else if (req_addr == UART_ADDR) begin
                    if (req_we && req_wstrb[0])
                        $write("%c", req_wdata[7:0]);
                    rdata <= 32'd0;
                end else begin
                    $display("WARNING: access outside simulated memory: %08x", req_addr);
                    rdata <= 32'd0;
                end
            end

            if (valid && !pending) begin
                pending   <= 1'b1;
                req_we    <= we;
                req_addr  <= addr;
                req_wdata <= wdata;
                req_wstrb <= wstrb;
            end
        end
    end
endmodule
