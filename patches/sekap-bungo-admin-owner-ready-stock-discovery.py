from pathlib import Path
def dump(path,a,b):
 lines=Path('project',path).read_text(encoding='utf-8').splitlines()
 print(f'\\n### {path}:{a}-{b}')
 for i in range(a-1,min(b,len(lines))): print(f'{i+1}: {lines[i]}')
dump('src/types.ts',285,330)
dump('src/context/TgpContext.tsx',130,170)
dump('src/context/TgpContext.tsx',2040,2145)
dump('src/context/TgpContext.tsx',2318,2375)
dump('src/context/TgpContext.tsx',3518,3568)
dump('src/screens/InventoryScreen.tsx',410,448)
