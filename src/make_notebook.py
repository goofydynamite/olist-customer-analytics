"""Convert src/analysis.py (# %% cells) into notebooks/olist_analysis.ipynb and run it."""
from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "analysis.py"
NB = ROOT / "notebooks" / "olist_analysis.ipynb"


def to_cells(text: str):
    cells = []
    for block in text.split("# %%")[1:]:
        if block.startswith(" [markdown]"):
            body = block.split("\n", 1)[1]
            md = "\n".join(line[2:] if line.startswith("# ") else line.lstrip("#")
                           for line in body.strip().splitlines())
            cells.append(nbformat.v4.new_markdown_cell(md))
        else:
            cells.append(nbformat.v4.new_code_cell(block.split("\n", 1)[1].strip()))
    return cells


def main():
    nb = nbformat.v4.new_notebook()
    nb.cells = to_cells(SRC.read_text(encoding="utf-8"))
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    NB.parent.mkdir(exist_ok=True)
    NotebookClient(nb, timeout=900, kernel_name="python3",
                   resources={"metadata": {"path": str(NB.parent)}}).execute()
    with open(NB, "w", encoding="utf-8", newline="\n") as f:
        nbformat.write(nb, f)
    print("Saved", NB.relative_to(ROOT))


if __name__ == "__main__":
    main()
