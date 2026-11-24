#!/usr/bin/env python3
from pathlib import Path
import json, shutil, subprocess, sys
ROOT=Path(__file__).resolve().parents[1]

def run(cmd):
    print('+', ' '.join(map(str,cmd)))
    subprocess.run(cmd,cwd=ROOT,check=True)

def main():
    run([sys.executable,'tests/gen_tests.py'])
    run([sys.executable,'tools/ref_model.py'])
    if not shutil.which('verilator'):
        print('\nVerilator is not installed on this machine. Python reference tests passed; install Verilator to run the RTL regression.')
        return 0
    cmd=['verilator','--binary','--trace','--timing','-Wall','-Wno-fatal','--top-module','tb_rv32i',
         'rtl/rv32i_regfile.sv','rtl/rv32i_core.sv','sim/rv32i_sim_memory.sv','sim/rv32i_sim_top.sv','sim/tb_rv32i.sv',
         '-o','Vtb_rv32i']
    run(cmd)
    manifest=json.loads((ROOT/'tests/manifest.json').read_text())
    sig=manifest['signature_offset'].replace('0x','')
    for name,t in manifest['tests'].items():
        expect=t['expected_signature'].replace('0x','')
        run([str(ROOT/'obj_dir/Vtb_rv32i'),f'+MEMFILE=tests/{t["image"]}',f'+EXPECT={expect}',f'+SIGOFF={sig}',f'+HALT={t["expected_halt_code"]}'])
    print('\nRTL regression PASS')
    return 0
if __name__=='__main__': raise SystemExit(main())
