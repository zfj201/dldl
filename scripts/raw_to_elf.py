#!/usr/bin/env python3
"""Wrap an AArch64 byte range in an analysis-only ELF for llvm-objdump."""
import pathlib,struct,sys
source,out,addr=sys.argv[1:];addr=int(addr,0)
code=pathlib.Path(source).read_bytes();names=b'\0.text\0.shstrtab\0'
offset=64;str_offset=offset+len(code);shoff=(str_offset+len(names)+7)&~7
hdr=struct.pack('<16sHHIQQQIHHHHHH',b'\x7fELF\x02\x01\x01'+b'\0'*9,1,183,1,0,0,shoff,0,64,0,0,64,3,2)
sections=b'\0'*64+struct.pack('<IIQQQQIIQQ',1,1,6,addr,offset,len(code),0,0,4,0)+struct.pack('<IIQQQQIIQQ',7,3,0,0,str_offset,len(names),0,0,1,0)
pathlib.Path(out).write_bytes((hdr+code+names).ljust(shoff,b'\0')+sections)
