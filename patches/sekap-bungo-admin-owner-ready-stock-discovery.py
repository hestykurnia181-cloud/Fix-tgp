from pathlib import Path
import re
def show(path, pats, radius=14):
 lines=Path('project',path).read_text(encoding='utf-8').splitlines()
 for pat in pats:
  for i,x in enumerate(lines):
   if re.search(pat,x,re.I):
    print(f'\\n### {path}:{i+1} pattern={pat}')
    for j in range(max(0,i-radius),min(len(lines),i+radius+1)): print(f'{j+1}: {lines[j]}')
show('src/context/TgpContext.tsx',[r'const addItem',r'const restockFinishedGoods',r'const produceFinishedGoods',r'const addAuditLog',r'updateItemRecipe',r'setItems,',r'addItem,'],20)
show('src/services/supabaseSyncService.ts',[r'async syncItem',r'syncItem\s*='],12)
