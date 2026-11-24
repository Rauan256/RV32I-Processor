# Early Fall feasibility run for the RV32I CPU core only.
# This is intentionally OUT-OF-CONTEXT: FPGA BRAM/UART board integration is Spring work.
set_part xc7a35tcpg236-1
file mkdir reports

read_verilog -sv rtl/rv32i_regfile.sv
read_verilog -sv rtl/rv32i_core.sv

synth_design -top rv32i_core -part xc7a35tcpg236-1 -mode out_of_context
create_clock -name cpu_clk -period 40.000 [get_ports clk]

opt_design
place_design
route_design

report_utilization -file reports/rv32i_core_utilization.rpt
report_timing_summary -file reports/rv32i_core_timing_25MHz.rpt
report_drc -file reports/rv32i_core_drc.rpt

puts "=== RV32I FALL OOC CHECK COMPLETE ==="
puts "See reports/rv32i_core_utilization.rpt"
puts "See reports/rv32i_core_timing_25MHz.rpt"
