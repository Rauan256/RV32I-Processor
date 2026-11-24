#!/usr/bin/env python3
"""Run ACT4 final self-checking RV32I ELFs on the capstone RTL, without changing it."""
import argparse
import os
from pathlib import Path
import resource
import struct
import subprocess
import sys

BASE = 0x80000000
SIZE = 0x400000
ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / 'obj_dir' / 'act4'
TB = r'''
module tb_act4;
    logic clk = 0, reset = 1;
    logic halted, illegal_insn;
    logic [1:0] halt_code;
    logic [31:0] debug_pc, debug_instr;
    logic [3:0] debug_state;
    logic mem_valid, mem_we, mem_ready;
    logic [31:0] mem_addr, mem_wdata, mem_rdata;
    logic [3:0] mem_wstrb;
    logic [31:0] tohost_addr, low_word;
    integer cycles, limit, word_index;
    rv32i_core core (
        .clk(clk), .reset(reset), .mem_valid(mem_valid), .mem_we(mem_we),
        .mem_addr(mem_addr), .mem_wdata(mem_wdata), .mem_wstrb(mem_wstrb),
        .mem_ready(mem_ready), .mem_rdata(mem_rdata), .halted(halted),
        .illegal_insn(illegal_insn), .halt_code(halt_code),
        .debug_pc(debug_pc), .debug_instr(debug_instr), .debug_state(debug_state)
    );
    rv32i_sim_memory #(.MEM_BYTES(4194304)) mem (
        .clk(clk), .reset(reset), .valid(mem_valid), .we(mem_we),
        .addr(mem_addr), .wdata(mem_wdata), .wstrb(mem_wstrb),
        .ready(mem_ready), .rdata(mem_rdata)
    );
    always #5 clk = ~clk;
    initial begin
        if (!$value$plusargs("TOHOST=%h", tohost_addr)) $fatal(1, "Missing TOHOST");
        if (tohost_addr < 32'h80000000 || tohost_addr > 32'h803ffff8 || tohost_addr[2:0] != 0)
            $fatal(1, "Invalid TOHOST address");
        word_index = (tohost_addr - 32'h80000000) >> 2;
        limit = 10000000;
        void'($value$plusargs("TIMEOUT=%d", limit));
        repeat (4) @(negedge clk);
        reset = 0;
        for (cycles = 0; cycles < limit; cycles = cycles + 1) begin
            @(posedge clk);
            if (halted || illegal_insn) begin
                $display("ACT4 FAIL unexpected halt/illegal pc=%08x instr=%08x halt=%0d", debug_pc, debug_instr, halt_code);
                $finish;
            end
            // The supplied RV32 HTIF macros write low then high words.
            // Observe the high-word store at the memory commit edge, not an
            // arbitrary RAM value. Console messages use a nonzero high word.
            if (mem.pending && mem.req_we && mem.req_addr == tohost_addr + 32'd4 && mem.req_wstrb == 4'hf && mem.req_wdata == 0) begin
                low_word = mem.ram[word_index];
                if (low_word == 32'd1) begin
                    $display("ACT4 PASS cycles=%0d pc=%08x", cycles, debug_pc);
                    $finish;
                end else if (low_word == 32'd3) begin
                    $display("ACT4 FAIL self-check cycles=%0d pc=%08x", cycles, debug_pc);
                    $finish;
                end
            end
        end
        $display("ACT4 TIMEOUT pc=%08x instr=%08x state=%0d", debug_pc, debug_instr, debug_state);
        $finish;
    end
endmodule
'''

def elf_to_hex(elf, out):
    data = elf.read_bytes()
    if data[:6] != b'\x7fELF\x01\x01':
        raise ValueError('Expected little-endian ELF32')
    h = struct.unpack_from('<16sHHIIIIIHHHHHH', data)
    _, typ, machine, _, entry, phoff, _, _, _, phsize, phnum, *_ = h
    if typ != 2 or machine != 243 or entry != BASE or phsize < 32:
        raise ValueError(f'Unexpected ELF type/machine/entry: {typ}/{machine}/{entry:#x}')
    mem = bytearray(SIZE)
    used = 0
    for i in range(phnum):
        kind, offset, va, pa, filesz, memsz, _, _ = struct.unpack_from('<8I', data, phoff+i*phsize)
        if kind != 1 or not memsz:
            continue
        if va != pa or not BASE <= pa < BASE+SIZE or pa+memsz > BASE+SIZE or filesz > memsz or offset+filesz > len(data):
            raise ValueError(f'Invalid PT_LOAD {pa:#x}, size {memsz:#x}')
        start = pa-BASE
        mem[start:start+filesz] = data[offset:offset+filesz]
        used = max(used, start+memsz)
    if not used:
        raise ValueError('No loadable memory')
    with out.open('w') as f:
        for pos in range(0, used, 4):
            f.write(f'{int.from_bytes(mem[pos:pos+4], "little"):08x}\n')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--all', action='store_true', help='Run all generated final ELFs; default is ADDI smoke test')
    p.add_argument('--suite', type=Path, default=Path.home()/'riscv-tools/riscv-arch-test/work/nu-rv32i-capstone/elfs')
    p.add_argument('--cycles', type=int, default=10000000)
    args = p.parse_args()
    elfs = sorted(x for x in args.suite.rglob('*.elf') if not x.name.endswith('.sig.elf'))
    if not elfs:
        sys.exit(f'No final self-checking ELFs in {args.suite}')
    print(f'Found {len(elfs)} final self-checking ELFs', flush=True)
    if not args.all:
        elfs = [next((x for x in elfs if x.name == 'I-addi-00.elf'), elfs[0])]
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    BUILD.mkdir(parents=True, exist_ok=True)
    tb = BUILD/'tb_act4.sv'
    tb.write_text(TB)
    cmd = ['verilator', '--binary', '--timing', '-Wno-fatal', '-j', '4', '--top-module', 'tb_act4', '--Mdir', str(BUILD/'sim'), 'rtl/rv32i_regfile.sv', 'rtl/rv32i_core.sv', 'sim/rv32i_sim_memory.sv', str(tb)]
    build = subprocess.run(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    (BUILD/'compile.log').write_text(build.stdout)
    if build.returncode:
        print(build.stdout)
        sys.exit('Verilator compilation failed')
    nm = Path.home()/'riscv-tools/gcc15/bin/riscv-none-elf-nm'
    counts = {'PASS':0, 'FAIL':0, 'TIMEOUT':0, 'ERROR':0}
    for elf in elfs:
        label = str(elf.relative_to(args.suite))
        try:
            symbols = subprocess.check_output([str(nm), str(elf)], text=True)
            addr = next(int(line.split()[0],16) for line in symbols.splitlines() if len(line.split()) >= 3 and line.split()[-1]=='tohost')
            if not BASE <= addr <= BASE+SIZE-8 or addr%8:
                raise ValueError(f'Invalid tohost {addr:#x}')
            image = BUILD/'image.hex'
            elf_to_hex(elf,image)
            run = subprocess.run([str(BUILD/'sim/Vtb_act4'), f'+MEMFILE={image}', f'+TOHOST={addr:08x}', f'+TIMEOUT={args.cycles}'], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
            log = run.stdout
            if run.returncode or 'WARNING: access outside simulated memory' in log:
                status = 'ERROR'
            elif 'ACT4 FAIL' in log:
                status = 'FAIL'
            elif 'ACT4 TIMEOUT' in log:
                status = 'TIMEOUT'
            elif 'ACT4 PASS' in log:
                status = 'PASS'
            else:
                status = 'ERROR'
            detail = next((line for line in log.splitlines() if line.startswith('ACT4 ')), '')
        except subprocess.TimeoutExpired as exc:
            status, detail, log = 'TIMEOUT', 'host timeout', str(exc)
        except Exception as exc:
            status, detail, log = 'ERROR', str(exc), str(exc)
        counts[status]+=1
        logfile = BUILD/'logs'/Path(label).with_suffix('.log')
        logfile.parent.mkdir(parents=True,exist_ok=True)
        logfile.write_text(log)
        print(f'{status}: {label} {detail}', flush=True)
        if status != 'PASS' and not args.all:
            print(log, flush=True)
    print('Summary: ' + ', '.join(f'{k}={v}' for k,v in counts.items()), flush=True)
    return 0 if counts['PASS'] == len(elfs) else 1

if __name__ == '__main__':
    sys.exit(main())
