from pathlib import Path

screen = Path("project/src/screens/DamagedGoodsScreen.tsx")
if not screen.exists():
    raise SystemExit("Damaged goods dialog mount fix: screen file missing")

source = screen.read_text()
old = """      <ReportDamagedGoodsDialog
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
      />"""
new = """      {isReportModalOpen && (
        <ReportDamagedGoodsDialog
          isOpen={true}
          onClose={() => setIsReportModalOpen(false)}
        />
      )}"""
if old not in source:
    if new in source:
        print("Damaged goods dialog is already conditionally mounted")
    else:
        raise SystemExit("Damaged goods dialog mount fix: expected render block not found")
else:
    source = source.replace(old, new, 1)
    screen.write_text(source)

print("Damaged goods dialog now mounts only when opened")
