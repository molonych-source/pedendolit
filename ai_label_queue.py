"""
AI labeling, step 1 of 2: queue the next batch of articles that have no AI label yet.

Writes ai_labels/queue.json with only the fields the labeler may see (pmid, title,
journal, pub_types, abstract). Existing topics and other classifier output are left
out on purpose, so the AI judges each article independently.

Order is by PMID, so repeated runs walk the store deterministically and never skip or
repeat an article. Articles already in ai_labels/labels.json are not queued again.

Usage:
  python3 ai_label_queue.py --next 500
  python3 ai_label_queue.py --status
"""
import json, os, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
LABELS = os.path.join(HERE, "ai_labels", "labels.json")
QUEUE = os.path.join(HERE, "ai_labels", "queue.json")


def load_labels():
    try:
        return json.load(open(LABELS)).get("labels", {})
    except (OSError, ValueError):
        return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--next", type=int, default=500)
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    store = json.load(open(os.path.join(HERE, "pedendolit-data.json")))["articles"]
    done = load_labels()
    todo = sorted((x for x in store if str(x["pmid"]) not in done), key=lambda x: int(x["pmid"]))
    print(f"store {len(store)} | labeled {sum(1 for x in store if str(x['pmid']) in done)} | remaining {len(todo)}")
    if a.status:
        return
    batch = [{"pmid": str(x["pmid"]), "title": x.get("title") or "", "journal": x.get("journal") or "",
              "pub_types": x.get("pub_types") or [], "abstract": x.get("abstract") or ""}
             for x in todo[:a.next]]
    json.dump(batch, open(QUEUE, "w"), ensure_ascii=False, indent=0)
    print(f"queued {len(batch)} -> {os.path.relpath(QUEUE, HERE)}")


if __name__ == "__main__":
    main()
