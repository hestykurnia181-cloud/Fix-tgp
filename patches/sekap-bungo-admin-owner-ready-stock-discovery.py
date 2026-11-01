from pathlib import Path
import re
ROOT=Path('project')
def dump(path, ranges=None, patterns=None, radius=8):
    p=ROOT/path
    lines=p.read_text(encoding='utf-8').splitlines()
    print(f'\\n######## {path} ({len(lines)} lines) ########')
    if ranges:
        for a,b in ranges:
            print(f'--- lines {a}-{b} ---')
            for i in range(a-1,min(b,len(lines))): print(f'{i+1}: {lines[i]}')
    if patterns:
        for pat in patterns:
            hits=[i for i,x in enumerate(lines) if re.search(pat,x,re.I)]
            for i in hits:
                print(f'--- pattern {pat}, around {i+1} ---')
                for j in range(max(0,i-radius),min(len(lines),i+radius+1)): print(f'{j+1}: {lines[j]}')
dump('src/screens/InventoryScreen.tsx',ranges=[(1,420)])
dump('src/types.ts',patterns=[r'interface InventoryItem',r'type InventoryItem',r'interface Item',r'stockQuantity',r'interface OutletStock',r'type OutletStock'])
dump('src/context/TgpContext.tsx',patterns=[r'update.*Item',r'update.*Stock',r'stockQuantity',r'finishedGoods',r'InventoryItem'])
