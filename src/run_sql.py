"""
Step 2 - run every SQL file in sql/ against data/olist.db.

    python src/run_sql.py

Files are executed in name order. A statement preceded by a line
"-- name: <query_name>" is a SELECT whose result is saved to
outputs/sql_results/<query_name>.csv. Everything else (views, DDL) is just executed.
"""
from __future__ import annotations

import re
import sqlite3
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "olist.db"
SQL_DIR = ROOT / "sql"
OUT = ROOT / "outputs" / "sql_results"

NAME_RE = re.compile(r"^--\s*name:\s*(\w+)", re.M)


def split_named(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Return (ddl_prefix, [(name, select_sql), ...])."""
    parts = NAME_RE.split(text)
    ddl, named = parts[0], []
    for i in range(1, len(parts), 2):
        named.append((parts[i], parts[i + 1].strip().rstrip(";")))
    return ddl, named


def run_all(con: sqlite3.Connection) -> dict[str, pd.DataFrame]:
    OUT.mkdir(parents=True, exist_ok=True)
    results = {}
    for f in sorted(SQL_DIR.glob("*.sql")):
        ddl, named = split_named(f.read_text(encoding="utf-8"))
        if ddl.strip():
            con.executescript(ddl)
        for name, sql in named:
            t0 = time.perf_counter()
            df = pd.read_sql_query(sql, con)
            df.to_csv(OUT / f"{name}.csv", index=False, lineterminator="\n")
            results[name] = df
            print(f"  {f.name:<30} {name:<30} {len(df):>7,} rows  {time.perf_counter() - t0:5.1f}s")
    return results


def main() -> None:
    con = sqlite3.connect(DB)
    run_all(con)
    con.close()
    print(f"\nResults saved to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
