from pathlib import Path

p = Path('project/src/components/TgpBottomBar.tsx')
s = p.read_text()
s = s.replace('justify-around h-16 px-3', 'justify-start gap-1 h-16 px-3 overflow-x-auto')
s = s.replace('justify-center flex-1 h-full relative', 'justify-center flex-none min-w-[56px] px-1 h-full relative')
p.write_text(s)
print('FNB cashier bottom navigation layout fixed')
