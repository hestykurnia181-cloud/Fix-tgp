from pathlib import Path

root = Path('project')
dialog = root / 'src/components/Dialogs.tsx'
screen = root / 'src/screens/DamagedGoodsScreen.tsx'

if not dialog.exists() or not screen.exists():
    raise SystemExit('Damaged goods fix: required files missing')

source = dialog.read_text()
old = """  if (!isOpen) return null;

  const currentItem = selectableItems.find((i) => i.itemId === itemId);"""
new = """  // Keep hook order identical whether the dialog is open or closed.
  useEffect(() => {
    if (!selectableItems.some((item) => item.itemId === itemId)) {
      setItemId(selectableItems[0]?.itemId || '');
    }
  }, [isOpen, itemId, selectableItems]);

  if (!isOpen) return null;

  const currentItem = selectableItems.find((i) => i.itemId === itemId);"""
if old not in source:
    raise SystemExit('Damaged goods fix: dialog hook-order insertion point not found')
source = source.replace(old, new, 1)
source = source.replace(
    "  useEffect(() => { if (!selectableItems.some((item) => item.itemId === itemId)) setItemId(selectableItems[0]?.itemId || ''); }, [selectableItems, itemId]);\n",
    "",
    1
)
dialog.write_text(source)

source = screen.read_text()
source = source.replace('color="amber"', 'accentBg="bg-amber-50 border-amber-100" accentColor="text-amber-600"', 1)
source = source.replace('color="rose"', 'accentBg="bg-rose-50 border-rose-100" accentColor="text-rose-600"', 2)
screen.write_text(source)
print('Damaged goods hook order and summary card props fixed')
