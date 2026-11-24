#!/usr/bin/env python3
from pathlib import Path
import sys, json
BASE=0x80000000
MASK=0xffffffff

def sx(v,b):
    v &= (1<<b)-1
    return v-(1<<b) if v&(1<<(b-1)) else v

def u32(x): return x & MASK

def load_words(path):
    return [int(x,16) for x in Path(path).read_text().split()]

def run(path,max_steps=10000):
    words=load_words(path)
    mem=bytearray(65536)
    for i,w in enumerate(words): mem[4*i:4*i+4]=w.to_bytes(4,'little')
    x=[0]*32; pc=BASE; halt=0; illegal=False; used=[]
    def rd8(a): return mem[a-BASE]
    def rd16(a): return int.from_bytes(mem[a-BASE:a-BASE+2],'little')
    def rd32(a): return int.from_bytes(mem[a-BASE:a-BASE+4],'little')
    def wr8(a,v): mem[a-BASE]=v&0xff
    def wr16(a,v): mem[a-BASE:a-BASE+2]=(v&0xffff).to_bytes(2,'little')
    def wr32(a,v): mem[a-BASE:a-BASE+4]=(v&MASK).to_bytes(4,'little')
    steps=0
    while steps<max_steps and not halt:
        ins=rd32(pc); opc=ins&0x7f; rd=(ins>>7)&31; f3=(ins>>12)&7; rs1=(ins>>15)&31; rs2=(ins>>20)&31; f7=(ins>>25)&0x7f
        npc=u32(pc+4); val=None; m='?'
        ii=sx(ins>>20,12); ss=sx(((ins>>25)<<5)|((ins>>7)&31),12)
        bi=sx((((ins>>31)&1)<<12)|(((ins>>7)&1)<<11)|(((ins>>25)&0x3f)<<5)|(((ins>>8)&0xf)<<1),13)
        ui=ins&0xfffff000
        ji=sx((((ins>>31)&1)<<20)|(((ins>>12)&0xff)<<12)|(((ins>>20)&1)<<11)|(((ins>>21)&0x3ff)<<1),21)
        a=x[rs1]; b=x[rs2]
        if opc==0x37: m='lui'; val=ui
        elif opc==0x17: m='auipc'; val=u32(pc+ui)
        elif opc==0x6f: m='jal'; val=npc; npc=u32(pc+ji)
        elif opc==0x67 and f3==0: m='jalr'; val=npc; npc=u32((a+ii)&~1)
        elif opc==0x63:
            names={0:'beq',1:'bne',4:'blt',5:'bge',6:'bltu',7:'bgeu'}
            if f3 not in names: illegal=True; halt=3
            else:
                m=names[f3]; taken={0:a==b,1:a!=b,4:sx(a,32)<sx(b,32),5:sx(a,32)>=sx(b,32),6:a<b,7:a>=b}[f3]
                if taken: npc=u32(pc+bi)
        elif opc==0x03:
            addr=u32(a+ii); names={0:'lb',1:'lh',2:'lw',4:'lbu',5:'lhu'}
            if f3 not in names: illegal=True; halt=3
            else:
                m=names[f3]
                if f3==0: val=u32(sx(rd8(addr),8))
                elif f3==1: val=u32(sx(rd16(addr),16))
                elif f3==2: val=rd32(addr)
                elif f3==4: val=rd8(addr)
                else: val=rd16(addr)
        elif opc==0x23:
            addr=u32(a+ss); names={0:'sb',1:'sh',2:'sw'}
            if f3 not in names: illegal=True; halt=3
            else:
                m=names[f3]
                if f3==0: wr8(addr,b)
                elif f3==1: wr16(addr,b)
                else: wr32(addr,b)
        elif opc==0x13:
            names={0:'addi',2:'slti',3:'sltiu',4:'xori',6:'ori',7:'andi'}
            if f3 in names:
                m=names[f3]
                val={0:u32(a+ii),2:int(sx(a,32)<ii),3:int(a<u32(ii)),4:a^u32(ii),6:a|u32(ii),7:a&u32(ii)}[f3]
            elif f3==1 and f7==0: m='slli'; val=u32(a<<((ins>>20)&31))
            elif f3==5 and f7==0: m='srli'; val=a>>((ins>>20)&31)
            elif f3==5 and f7==0x20: m='srai'; val=u32(sx(a,32)>>((ins>>20)&31))
            else: illegal=True; halt=3
        elif opc==0x33:
            if f3==0 and f7==0: m='add'; val=u32(a+b)
            elif f3==0 and f7==0x20: m='sub'; val=u32(a-b)
            elif f3==1 and f7==0: m='sll'; val=u32(a<<(b&31))
            elif f3==2 and f7==0: m='slt'; val=int(sx(a,32)<sx(b,32))
            elif f3==3 and f7==0: m='sltu'; val=int(a<b)
            elif f3==4 and f7==0: m='xor'; val=a^b
            elif f3==5 and f7==0: m='srl'; val=a>>(b&31)
            elif f3==5 and f7==0x20: m='sra'; val=u32(sx(a,32)>>(b&31))
            elif f3==6 and f7==0: m='or'; val=a|b
            elif f3==7 and f7==0: m='and'; val=a&b
            else: illegal=True; halt=3
        elif opc==0x0f and f3==0: m='fence'
        elif opc==0x73 and f3==0 and rs1==0 and rd==0:
            imm=(ins>>20)&0xfff
            if imm==0: m='ecall'; halt=1
            elif imm==1: m='ebreak'; halt=2
            else: illegal=True; halt=3
        else: illegal=True; halt=3
        used.append(m)
        if val is not None and rd!=0: x[rd]=u32(val)
        x[0]=0; pc=npc; steps+=1
    return {'halt_code':halt,'illegal':illegal,'steps':steps,'pc':pc,'used':sorted(set(used)),'mem':mem}

if __name__=='__main__':
    manifest=json.loads((Path(__file__).parents[1]/'tests/manifest.json').read_text())
    sigoff=int(manifest['signature_offset'],16)
    ok=True
    for name,t in manifest['tests'].items():
        r=run(Path(__file__).parents[1]/'tests'/t['image'])
        sig=int.from_bytes(r['mem'][sigoff:sigoff+4],'little')
        exp=int(t['expected_signature'],16)
        passed=(not r['illegal'] and r['halt_code']==t['expected_halt_code'] and sig==exp)
        print(f"{name}: {'PASS' if passed else 'FAIL'} steps={r['steps']} halt={r['halt_code']} signature=0x{sig:08x}")
        if not passed: ok=False
    sys.exit(0 if ok else 1)
