import argparse
import shutil
from backend.shared.chroma_client import get_collection, _client
from backend.shared.chroma_init import seed_from_csv

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="reset collections before seeding")
    args = ap.parse_args()

    if args.reset:
        try:
            for name in ("menus", "prefs", "commits"):
                _client.delete_collection(name)
            print("Collections reset.")
        except Exception:
            pass
    seed_from_csv()