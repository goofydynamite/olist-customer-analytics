"""
Run the whole pipeline end to end:

    python run_all.py

1. src/etl.py            raw CSVs  -> data/olist.db (SQLite)
2. src/run_sql.py        sql/*.sql -> outputs/sql_results/*.csv
3. src/make_notebook.py  analysis  -> notebooks/olist_analysis.ipynb + reports/figures/*.png
4. src/build_excel.py    results   -> excel/Olist_Customer_Dashboard.xlsx
5. src/excel_recalc.ps1  (Windows + Excel only) recalculates formulas and renders the dashboard PNG
"""
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
