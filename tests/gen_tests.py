#!/usr/bin/env python3
"""Generate self-checking RV32I directed test images for the Fall baseline.

Output format is one 32-bit little-endian instruction word per line, suitable
for $readmemh into a 32-bit word array.
"""
from pathlib import Path
import json

BASE = 0x80000000
PASS_MAIN = 0xA11A0001
PASS_ECALL = 0xA11A0002
FAIL = 0xDEAD0001

REG = {f"x{i}": i for i in range(32)}


def scheck(v, bits):
    lo, hi = -(1 << (bits-1)), (1 << (bits-1))-1
    if not (lo <= v <= hi):
        raise ValueError(f"signed {bits}-bit immediate out of range: {v}")
    return v & ((1 << bits)-1)


def ucheck(v, bits):
    if not (0 <= v < (1 << bits)):
        raise ValueError(f"unsigned {bits}-bit immediate out of range: {v}")
    return v


def R(f7, rs2, rs1, f3, rd, opc=0x33):
    return (f7<<25)|(rs2<<20)|(rs1<<15)|(f3<<12)|(rd<<7)|opc

def I(imm, rs1, f3, rd, opc):
    imm = scheck(imm, 12)
    return (imm<<20)|(rs1<<15)|(f3<<12)|(rd<<7)|opc

def I_SHIFT(f7, shamt, rs1, f3, rd):
    ucheck(shamt, 5)
    return (f7<<25)|(shamt<<20)|(rs1<<15)|(f3<<12)|(rd<<7)|0x13

def S(imm, rs2, rs1, f3):
    imm = scheck(imm, 12)
    return ((imm>>5)<<25)|(rs2<<20)|(rs1<<15)|(f3<<12)|((imm&0x1f)<<7)|0x23

def B(off, rs2, rs1, f3):
    if off % 2: raise ValueError("branch offset must be even")
    imm = scheck(off, 13)
    return (((imm>>12)&1)<<31)|(((imm>>5)&0x3f)<<25)|(rs2<<20)|(rs1<<15)|(f3<<12)|(((imm>>1)&0xf)<<8)|(((imm>>11)&1)<<7)|0x63

def U(imm20, rd, opc):
    imm20 = ucheck(imm20 & 0xfffff, 20)
    return (imm20<<12)|(rd<<7)|opc

def J(off, rd):
    if off % 2: raise ValueError("jump offset must be even")
    imm = scheck(off, 21)
    return (((imm>>20)&1)<<31)|(((imm>>1)&0x3ff)<<21)|(((imm>>11)&1)<<20)|(((imm>>12)&0xff)<<12)|(rd<<7)|0x6f


class Asm:
    def __init__(self):
        self.items=[]
        self.labels={}
        self.coverage=[]

    @property
    def pc(self): return BASE + 4*sum(1 for x in self.items if x[0] != 'label')

    def label(self, name): self.items.append(('label', name))
    def emit(self, m, *args):
        self.items.append(('insn', m, args)); self.coverage.append(m)
    def base_label_addi(self, rd, label, addend=0):
        self.items.append(('base_label_addi', rd, label, addend)); self.coverage.append('addi')

    def li(self, rd, value):
        value &= 0xffffffff
        signed = value if value < 0x80000000 else value - (1<<32)
        if -2048 <= signed <= 2047:
            self.emit('addi', rd, 'x0', signed)
        else:
            hi = (value + 0x800) >> 12
            lo = (value - ((hi & 0xfffff) << 12)) & 0xffffffff
            lo_signed = lo if lo < 0x80000000 else lo-(1<<32)
            self.emit('lui', rd, hi & 0xfffff)
            self.emit('addi', rd, rd, lo_signed)

    def pass_signature(self, code, halt='ebreak'):
        self.li('x31', code)
        self.emit('sw','x31',0x400,'x1')
        self.emit(halt)

    def fail_signature(self):
        self.label('fail')
        self.li('x31', FAIL)
        self.emit('sw','x31',0x400,'x1')
        self.emit('ebreak')

    def assemble(self):
        # pass 1
        pc=BASE
        for item in self.items:
            if item[0]=='label': self.labels[item[1]]=pc
            else: pc += 4
        words=[]; pc=BASE
        for item in self.items:
            if item[0]=='label': continue
            if item[0]=='base_label_addi':
                _, rd, label, addend = item
                off = self.labels[label]-BASE+addend
                words.append(I(off, REG['x1'],0,REG[rd],0x13)); pc+=4; continue
            _, m, a = item
            r=lambda x: REG[x]
            if m=='lui': w=U(a[1],r(a[0]),0x37)
            elif m=='auipc': w=U(a[1],r(a[0]),0x17)
            elif m=='jal': w=J(self.labels[a[1]]-pc,r(a[0]))
            elif m=='jalr': w=I(a[2],r(a[1]),0,r(a[0]),0x67)
            elif m in ('beq','bne','blt','bge','bltu','bgeu'):
                f3={'beq':0,'bne':1,'blt':4,'bge':5,'bltu':6,'bgeu':7}[m]
                w=B(self.labels[a[2]]-pc,r(a[1]),r(a[0]),f3)
            elif m in ('lb','lh','lw','lbu','lhu'):
                f3={'lb':0,'lh':1,'lw':2,'lbu':4,'lhu':5}[m]
                w=I(a[1],r(a[2]),f3,r(a[0]),0x03)
            elif m in ('sb','sh','sw'):
                f3={'sb':0,'sh':1,'sw':2}[m]
                w=S(a[1],r(a[0]),r(a[2]),f3)
            elif m in ('addi','slti','sltiu','xori','ori','andi'):
                f3={'addi':0,'slti':2,'sltiu':3,'xori':4,'ori':6,'andi':7}[m]
                w=I(a[2],r(a[1]),f3,r(a[0]),0x13)
            elif m in ('slli','srli','srai'):
                f3=1 if m=='slli' else 5; f7=0x20 if m=='srai' else 0
                w=I_SHIFT(f7,a[2],r(a[1]),f3,r(a[0]))
            elif m in ('add','sub','sll','slt','sltu','xor','srl','sra','or','and'):
                f3={'add':0,'sub':0,'sll':1,'slt':2,'sltu':3,'xor':4,'srl':5,'sra':5,'or':6,'and':7}[m]
                f7=0x20 if m in ('sub','sra') else 0
                w=R(f7,r(a[2]),r(a[1]),f3,r(a[0]))
            elif m=='fence': w=0x0000000f
            elif m=='ecall': w=0x00000073
            elif m=='ebreak': w=0x00100073
            else: raise ValueError(m)
            words.append(w&0xffffffff); pc+=4
        return words


def build_main():
    a=Asm()
    # AUIPC + LUI and x0
    a.emit('auipc','x1',0)
    a.emit('lui','x2',0x80000)
    a.emit('bne','x1','x2','fail')
    a.emit('addi','x0','x0',123)
    a.emit('bne','x0','x0','fail')

    # OP-IMM
    a.emit('addi','x3','x0',5)
    a.emit('addi','x4','x0',-3)
    a.emit('slti','x5','x4',0);   a.emit('addi','x6','x0',1); a.emit('bne','x5','x6','fail')
    a.emit('sltiu','x5','x3',6); a.emit('bne','x5','x6','fail')
    a.emit('xori','x5','x3',3);  a.emit('addi','x6','x0',6); a.emit('bne','x5','x6','fail')
    a.emit('ori','x5','x3',8);   a.emit('addi','x6','x0',13); a.emit('bne','x5','x6','fail')
    a.emit('andi','x5','x6',5);  a.emit('addi','x7','x0',5); a.emit('bne','x5','x7','fail')
    a.emit('slli','x5','x3',3);  a.emit('addi','x6','x0',40); a.emit('bne','x5','x6','fail')
    a.emit('srli','x5','x5',2);  a.emit('addi','x6','x0',10); a.emit('bne','x5','x6','fail')
    a.emit('srai','x5','x4',1);  a.emit('addi','x6','x0',-2); a.emit('bne','x5','x6','fail')

    # OP register
    a.emit('add','x5','x3','x3'); a.emit('addi','x6','x0',10); a.emit('bne','x5','x6','fail')
    a.emit('sub','x5','x3','x4'); a.emit('addi','x6','x0',8); a.emit('bne','x5','x6','fail')
    a.emit('sll','x5','x3','x3'); a.emit('addi','x6','x0',160); a.emit('bne','x5','x6','fail')
    a.emit('slt','x5','x4','x3'); a.emit('addi','x6','x0',1); a.emit('bne','x5','x6','fail')
    a.emit('sltu','x5','x3','x4'); a.emit('addi','x6','x0',1); a.emit('bne','x5','x6','fail')
    a.emit('xor','x5','x3','x4'); a.li('x6', (5 ^ 0xfffffffd)); a.emit('bne','x5','x6','fail')
    a.li('x8',0x80000000); a.emit('srl','x5','x8','x3'); a.li('x6',0x04000000); a.emit('bne','x5','x6','fail')
    a.emit('sra','x5','x8','x3'); a.li('x6',0xfc000000); a.emit('bne','x5','x6','fail')
    a.emit('or','x5','x3','x4'); a.li('x6',0xfffffffd); a.emit('bne','x5','x6','fail')
    a.emit('and','x5','x3','x4'); a.emit('addi','x6','x0',5); a.emit('bne','x5','x6','fail')

    # All six branches: if any expected branch is not taken, jump to fail.
    a.emit('addi','x10','x0',5); a.emit('addi','x11','x0',5)
    a.emit('addi','x12','x0',-1); a.emit('addi','x13','x0',1)
    for m,rs1,rs2 in [('beq','x10','x11'),('bne','x10','x13'),('blt','x12','x13'),('bge','x13','x12'),('bltu','x13','x12'),('bgeu','x12','x13')]:
        ok=f'ok_{m}'; a.emit(m,rs1,rs2,ok); a.emit('jal','x0','fail'); a.label(ok)

    # JAL control flow + link nonzero.
    a.emit('jal','x14','jal_target')
    a.emit('jal','x0','fail')
    a.label('jal_target')
    a.emit('beq','x14','x0','fail')

    # JALR: create base+label+1; JALR must clear bit 0.
    a.base_label_addi('x15','jalr_target',1)
    a.emit('jalr','x16','x15',0)
    a.emit('jal','x0','fail')
    a.label('jalr_target')
    a.emit('beq','x16','x0','fail')

    # Store/load family at BASE+0x200 using x17.
    a.emit('addi','x17','x1',0x200)
    a.emit('addi','x18','x0',0x7f); a.emit('sb','x18',0,'x17')
    a.emit('addi','x18','x0',-1);   a.emit('sb','x18',1,'x17')
    a.li('x18',0x12345678);         a.emit('sw','x18',4,'x17')
    a.emit('addi','x18','x0',-128); a.emit('sh','x18',8,'x17')

    a.emit('lb','x19',0,'x17'); a.emit('addi','x20','x0',127); a.emit('bne','x19','x20','fail')
    a.emit('lb','x19',1,'x17'); a.emit('addi','x20','x0',-1); a.emit('bne','x19','x20','fail')
    a.emit('lbu','x19',1,'x17'); a.emit('addi','x20','x0',255); a.emit('bne','x19','x20','fail')
    a.emit('lh','x19',8,'x17'); a.emit('addi','x20','x0',-128); a.emit('bne','x19','x20','fail')
    a.emit('lhu','x19',8,'x17'); a.li('x20',0xff80); a.emit('bne','x19','x20','fail')
    a.emit('lw','x19',4,'x17'); a.li('x20',0x12345678); a.emit('bne','x19','x20','fail')

    # FENCE is a no-op in the uncached single-hart baseline.
    a.emit('fence')
    a.pass_signature(PASS_MAIN,'ebreak')
    a.fail_signature()
    return a


def build_ecall():
    a=Asm(); a.emit('auipc','x1',0); a.li('x31',PASS_ECALL); a.emit('sw','x31',0x400,'x1'); a.emit('ecall')
    return a


def write_hex(path, words):
    path.write_text('\n'.join(f'{w:08x}' for w in words)+'\n')


def main():
    out=Path(__file__).resolve().parent
    tests={'all40_ebreak':(build_main(),PASS_MAIN,2),'ecall':(build_ecall(),PASS_ECALL,1)}
    manifest={'base_address':f'0x{BASE:08x}','signature_offset':'0x00000400','tests':{},'required_mnemonics':[
        'lui','auipc','jal','jalr','beq','bne','blt','bge','bltu','bgeu',
        'lb','lh','lw','lbu','lhu','sb','sh','sw',
        'addi','slti','sltiu','xori','ori','andi','slli','srli','srai',
        'add','sub','sll','slt','sltu','xor','srl','sra','or','and',
        'fence','ecall','ebreak']}
    allcov=set()
    for name,(asm,expect,haltcode) in tests.items():
        words=asm.assemble(); write_hex(out/f'{name}.hex',words)
        cov=sorted(set(asm.coverage)); allcov.update(cov)
        manifest['tests'][name]={'image':f'{name}.hex','expected_signature':f'0x{expect:08x}','expected_halt_code':haltcode,'words':len(words),'mnemonics':cov}
    manifest['covered_mnemonics']=sorted(allcov)
    missing=sorted(set(manifest['required_mnemonics'])-allcov)
    manifest['missing_mnemonics']=missing
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    if missing: raise SystemExit('Missing coverage: '+', '.join(missing))
    print('Generated directed tests; all 40 required mnemonics are present across the manifest.')

if __name__=='__main__': main()
