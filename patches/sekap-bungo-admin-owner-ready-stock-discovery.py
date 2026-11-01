from pathlib import Path
import re

ROOT = Path('project')
terms = re.compile(r'siap\s*jual|stok\s*siap|ready\s*stock|readyToSell|readyStock|availableStock|stockReady', re.I)
for path in sorted((ROOT / 'src').rglob('*')):
    if not path.is_file() or path.suffix not in {'.tsx', '.ts', '.jsx', '.js'}:
        continue
    try:
        lines = path.read_text(encoding='utf-8').splitlines()
    except Exception:
        continue
    hits = [i for i, line in enumerate(lines) if terms.search(line)]
    if hits:
        print(f'\n=== STOCK READY MATCHES: {path} ===')
        shown = set()
        for i in hits:
            for j in range(max(0, i-5), min(len(lines), i+7)):
                if j not in shown:
                    print(f'{j+1}: {lines[j]}')
                    shown.add(j)
