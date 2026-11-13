"""Run everything: cleaning, SQL, notebook, Excel."""
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STEPS = ["src/etl.py", "src/run_sql.py", "src/make_notebook.py", "src/build_excel.py"]

for step in STEPS:
    print(f"\n=== {step} ===")
    subprocess.run([sys.executable, str(ROOT / step)], check=True, cwd=ROOT)

if platform.system() == "Windows" and shutil.which("powershell"):
    print("\n=== src/excel_recalc.ps1 ===")
    r = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "src/excel_recalc.ps1"),
                        "-Png", "reports/figures/10_excel_dashboard.png"], cwd=ROOT)
    if r.returncode:
        print("Excel not available - open the workbook in Excel and it will calculate on load.")
print("\nDone.")
