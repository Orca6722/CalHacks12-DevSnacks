import csv
import os
from .chroma_client import ensure_collections, add_menus
from .settings import DATA_DIR


def seed_from_csv():
    ensure_collections()
    path = os.path.join(DATA_DIR, "menus.csv")
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)
    add_menus(rows)
    print(f"Seeded {len(rows)} menu items into ChromaDB")


if __name__ == "__main__":
    seed_from_csv()