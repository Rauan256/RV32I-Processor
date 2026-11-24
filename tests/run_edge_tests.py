#!/usr/bin/env python3
"""Supplemental self-checking RV32I directed regression (not official ACT)."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))
sys.path.insert(0, str(ROOT / 'tools'))
from gen_tests import Asm, write_hex
from ref_model import run

PASS = 0xA11A0003
IMAGE = ROOT / 'tests' / 'edge_cases.hex'


def build():
    a = Asm()
    a.emit('auipc', 'x1', 0)
    def check(reg, expected):
        a.li('x30', expected)
        a.emit('bne', reg, 'x30', 'fail')

    # Overflow wraps modulo 2**32; extreme immediate and shift values.
    a.li('x3', 0x7fffffff)
    a.emit('addi', 'x4', 'x3', 1); check('x4', 0x80000000)
    a.li('x3', 0xffffffff)
    a.emit('addi', 'x4', 'x3', 1); check('x4', 0)
    a.emit('addi', 'x4', 'x0', -2048); check('x4', 0xfffff800)
    a.emit('addi', 'x4', 'x0', 2047); check('x4', 2047)
    a.emit('sub', 'x4', 'x0', 'x3'); check('x4', 1)
    a.li('x3', 1)
    a.emit('slli', 'x4', 'x3', 31); check('x4', 0x80000000)
    a.emit('srai', 'x5', 'x4', 31); check('x5', 0xffffffff)
    a.emit('srli', 'x5', 'x4', 31); check('x5', 1)
    a.li('x6', 32)
    a.emit('sll', 'x5', 'x4', 'x6'); check('x5', 0x80000000)
    a.li('x6', 63)
    a.emit('srl', 'x5', 'x4', 'x6'); check('x5', 1)
    a.emit('sra', 'x5', 'x4', 'x6'); check('x5', 0xffffffff)
    a.emit('slt', 'x5', 'x4', 'x3'); check('x5', 1)
    a.emit('sltu', 'x5', 'x4', 'x3'); check('x5', 0)
    a.emit('sltiu', 'x5', 'x3', -1); check('x5', 1)
    a.emit('addi', 'x0', 'x0', 99); check('x0', 0)

    # All six conditional branches must also work when NOT taken.
    a.li('x10', 1); a.li('x11', 2); a.li('x12', -1)
    for m, r1, r2 in [('beq', 'x10', 'x11'), ('bne', 'x10', 'x10'),
                       ('blt', 'x11', 'x10'), ('bge', 'x12', 'x10'),
                       ('bltu', 'x12', 'x10'), ('bgeu', 'x10', 'x12')]:
        a.emit(m, r1, r2, 'fail')
    a.li('x13', 5); a.li('x14', 0)
    a.label('loop')
    a.emit('add', 'x14', 'x14', 'x13')
    a.emit('addi', 'x13', 'x13', -1)
    a.emit('bne', 'x13', 'x0', 'loop'); check('x14', 15)

    # Exact JAL/JALR link addresses and function return, odd JALR target.
    a.base_label_addi('x20', 'ret1')
    a.emit('jal', 'x21', 'fn1'); a.label('ret1')
    a.emit('jal', 'x0', 'after1')
    a.label('fn1'); a.emit('bne', 'x21', 'x20', 'fail')
    a.emit('jalr', 'x0', 'x21', 0)
    a.label('after1')
    a.base_label_addi('x20', 'ret2')
    a.base_label_addi('x22', 'fn2', 1)
    a.emit('jalr', 'x21', 'x22', 0); a.label('ret2')
    a.emit('jal', 'x0', 'after2')
    a.label('fn2'); a.emit('bne', 'x21', 'x20', 'fail')
    a.emit('jalr', 'x0', 'x21', 0)
    a.label('after2')

    # Byte/halfword lanes preserve neighboring bytes; sign extension.
    a.li('x17', 0x80000800); a.li('x18', 0x11223344)
    a.emit('sw', 'x18', 0, 'x17')
    a.li('x18', 0x80); a.emit('sb', 'x18', 2, 'x17')
    a.emit('lw', 'x19', 0, 'x17'); check('x19', 0x11803344)
    a.emit('lb', 'x19', 2, 'x17'); check('x19', 0xffffff80)
    a.emit('lbu', 'x19', 2, 'x17'); check('x19', 0x80)
    a.li('x18', 0xff); a.emit('sb', 'x18', 3, 'x17')
    a.emit('lw', 'x19', 0, 'x17'); check('x19', 0xff803344)
    a.li('x18', 0x8001); a.emit('sh', 'x18', 2, 'x17')
    a.emit('lw', 'x19', 0, 'x17'); check('x19', 0x80013344)
    a.emit('lh', 'x19', 2, 'x17'); check('x19', 0xffff8001)
    a.emit('lhu', 'x19', 2, 'x17'); check('x19', 0x8001)
    a.li('x18', 0xabcd); a.emit('sh', 'x18', 0, 'x17')
    a.emit('lw', 'x19', 0, 'x17'); check('x19', 0x8001abcd)
    a.pass_signature(PASS); a.fail_signature()
    return a.assemble()


def main():
    words = build()
    assert len(words)*4 < 0x400, 'Code overlaps signature memory'
    write_hex(IMAGE, words)
    result = run(IMAGE)
    sig = int.from_bytes(result['mem'][0x400:0x404], 'little')
    ok = not result['illegal'] and result['halt_code'] == 2 and sig == PASS
    print(f"Reference model: {'PASS' if ok else 'FAIL'} steps={result['steps']} signature={sig:08x}", flush=True)
    if not ok:
        return 1
    exe = ROOT / 'obj_dir' / 'Vtb_rv32i'
    if not exe.is_file():
        print('RTL executable missing; run python3 scripts/run_verilator.py first.', flush=True)
        return 1
    subprocess.run([str(exe), '+MEMFILE=tests/edge_cases.hex', '+EXPECT=a11a0003',
                    '+SIGOFF=00000400', '+HALT=2'], cwd=ROOT, check=True)
    print('Supplemental RTL edge-case regression PASS', flush=True)
    return 0

if __name__ == '__main__':
    sys.exit(main())
