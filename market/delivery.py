"""Who confirms the delivery happened: evidence, an AI inspector, and an inspection window.

A PayPal hold only proves the buyer paid. Before the money is released, three things answer "was it
really delivered?", following the pattern escrow services and PayPal seller protection use:

1. The seller delivers through the platform, so the platform is the system of record: a digital item
   is a file manifest with its size and SHA-256 hash, a physical item is a shipment with a tracking
   number. When the buyer opens the file, the access (time and IP) is logged, which is the kind of
   proof of delivery PayPal asks for on intangible goods.
2. An AI delivery inspector compares what the listing promised with what actually arrived and says
   whether it matches. Sellers here behave like their record: one whose buyers often return things
   sometimes ships the wrong file, an empty archive, or only a preview.
3. The buyer accepts or rejects. If they say nothing, the hold is released when the inspection window
   ends, but only when the inspector found the delivery matches. A mismatch never auto-releases.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import time

from agent import tap

INSPECTION_SECONDS = 180
# the inspector's call blocks or frees a creator's money, so it runs on the stronger model when one is set
INSPECTOR_MODEL = os.environ.get("HELM_INSPECTOR_MODEL", "gpt-5-mini")          # the live demo's window; a real deal would agree on e.g. 72 hours

_FILES = {
    "presets": lambda t: [("presets/" + t + f" {i + 1:02d}.xmp", 4_800 + 37 * i) for i in range(12)] + [("preview.jpg", 412_000)],
    "beats": lambda t: [(f"stems/{n}.wav", 9_400_000 + 1_000 * i) for i, n in enumerate(["drums", "bass", "melody", "fx"])] + [("license.pdf", 88_000)],
    "prints": lambda t: [(t + " 300dpi.tiff", 61_000_000), (t + " A3.pdf", 14_200_000)],
    "ebooks": lambda t: [(t + ".pdf", 3_100_000), (t + ".epub", 1_400_000)],
    "templates": lambda t: ([(t + " (Canva share link).url", 220)] + [("thumbnails/" + t + f" {i + 1:02d}.png", 640_000) for i in range(3)] + [("how to use.pdf", 380_000)]
                            if "canva" in t.lower() else
                            [(t + " (Notion duplicate link).url", 210), ("setup guide.pdf", 520_000)] if "notion" in t.lower() else
                            [(t + ".psd", 22_000_000), ("fonts.txt", 900), ("guide.pdf", 640_000)]),
}
_WRONG = {"presets": "beats", "beats": "ebooks", "prints": "presets", "ebooks": "templates", "templates": "prints", "merch": "ebooks"}


def _seller_return_rate(acct, seller: str) -> float:
    sold = [o for o in acct.market.orders if o.seller == seller]
    if not sold:
        return 0.05
    return sum(1 for o in sold if o.status in ("returned", "charged_back")) / len(sold)


def deliver(acct, eid: str) -> dict:
    """The seller's delivery, recorded by the platform. Behaviour follows the seller's real record."""
    item = acct.escrows[eid]
    listing = acct.market.listings.get(item.get("listing") or "")
    category = getattr(listing, "category", None) or ("merch" if not item.get("listing") else "presets")
    title = item["title"]
    rng = random.Random(f"{eid}:{time.time()}")
    rate = _seller_return_rate(acct, item["seller"]) if item.get("seller") else 0.04
    roll = rng.random()
    mode = "as listed"
    if roll < rate * 0.6:
        mode = rng.choice(["wrong item", "empty file", "preview only"])
    if not item.get("listing") or category == "merch":
        # a physical item from an outside store or a merch listing: a shipment, not a file
        d = {"kind": "shipment", "carrier": rng.choice(["UPS", "USPS", "DHL"]),
             "tracking": "1Z" + "".join(rng.choice("0123456789ABCDEFGHJKLMNPRSTUVWXYZ") for _ in range(16)),
             "status": "label created" if mode != "as listed" else "out for delivery",
             "contents": title if mode == "as listed" else ("" if mode == "empty file" else "a different item")}
    else:
        make = _FILES.get(category, _FILES["templates"])
        if mode == "wrong item":
            files = _FILES.get(_WRONG.get(category, "ebooks"), _FILES["ebooks"])("untitled pack")
        elif mode == "empty file":
            files = [(title + ".zip", 0)]
        elif mode == "preview only":
            files = [("preview.jpg", 212_000), ("readme.txt", 1_100)]
        else:
            files = make(title)
        manifest = [{"name": n, "bytes": b} for n, b in files]
        d = {"kind": "download", "archive": title + ".zip", "files": manifest,
             "bytes": sum(f["bytes"] for f in manifest),
             "sha256": hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()}
    d.update({"delivered_at": time.time(), "seller": item["merchant"], "listing_title": title,
              "listing_category": category, "price": item["price"], "_mode": mode})
    item["delivery"] = d
    item["accessed"] = []
    return d


def inspect(acct, eid: str, llm=None) -> dict:
    """The buyer's AI delivery inspector reads the listing and the delivery and judges the match."""
    item = acct.escrows[eid]
    d = dict(item.get("delivery") or {})
    # the seller names the files, so the names are untrusted text: scan them before any model reads them
    from market.guard import scan_text
    injected = []
    if d.get("files"):
        clean = []
        for f in d["files"]:
            sc = scan_text(f.get("name", ""))
            if sc["flagged"]:
                injected.append(f.get("name", "")[:80])
            clean.append({**f, "name": sc["redacted"] if sc["flagged"] else f.get("name", "")})
        d["files"] = clean
    for k in ("contents", "archive"):
        if d.get(k) and scan_text(d[k])["flagged"]:
            injected.append(str(d[k])[:80])
            d[k] = scan_text(d[k])["redacted"]
    facts = {"marketplace": "a creator marketplace for digital goods: presets, beats, printable art prints, ebooks and "
                            "templates are delivered as downloadable files (Notion and Canva templates are normally a share or duplicate link plus a guide); merch and outside-store "
                            "items ship physically with tracking",
             "typical_sizes": "a Lightroom preset (.xmp) is 2 to 10 KB each, so a 12-preset pack is well under 1 MB; "
                              "a share or duplicate link file (.url) is a few hundred bytes; WAV stems are 5 to 50 MB "
                              "each; a print-ready TIFF is 20 to 150 MB; an ebook PDF is 1 to 10 MB",
             "promised": {"title": item["title"], "category": d.get("listing_category"), "price": item["price"],
                          "seller": item["merchant"]},
             "delivered": {k: v for k, v in d.items() if not k.startswith("_") and k not in ("listing_title", "listing_category", "price", "seller")}}
    t0 = time.time()
    tap.emit("node_start", node="inspect", graph="buyer")
    verdict, reason, checks, driver, model, err = "unverified", "", [], "llm", None, None
    try:
        if llm is None:
            from agent.llm import LLMClient
            llm = LLMClient()
        with tap.node("inspect"):
            msg = llm.chat(messages=[
                {"role": "system", "content":
                 "You are the buyer's delivery inspector. Compare what the listing promised with what the "
                 "seller actually delivered (file names, sizes, or shipment and tracking). Decide whether a "
                 "reasonable buyer got what they paid for. Judge fairly: if the files are the kind of thing the "
                 "listing describes and of plausible size, it matches. It does not match when the file is empty "
                 "(zero bytes), when only a preview or readme arrived, when the files are for a different kind of "
                 "product, or when a shipment has not moved. Reply ONLY as JSON: "
                 '{"verdict": "matches" | "mismatch" | "incomplete", "reason": "one plain sentence", '
                 '"checks": ["short fact you checked", ...]}'},
                {"role": "user", "content": json.dumps(facts)}], temperature=0.2, max_tokens=900,
                model=INSPECTOR_MODEL or None)
        model = getattr(llm, "last_model", None)
        raw = (msg or {}).get("content") or ""
        j = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
        verdict = j.get("verdict") if j.get("verdict") in ("matches", "mismatch", "incomplete") else "unverified"
        reason = str(j.get("reason") or "")[:300]
        checks = [str(c)[:120] for c in (j.get("checks") or [])][:4]
    except Exception as exc:                          # no silent stand-in: the buyer decides by hand
        driver, err = "error", f"{type(exc).__name__}: {str(exc)[:160]}"
        reason = "the inspector could not reach a model, so nothing is released automatically"
    if injected:
        # a delivery that tries to instruct the inspector never releases on silence, whatever the model said
        if verdict == "matches":
            verdict = "incomplete"
        reason = "a file name tried to give the inspector instructions and was removed; " + (reason or "")
        checks = (["file name with instructions removed before inspection"] + checks)[:4]
    out = {"verdict": verdict, "reason": reason, "checks": checks, "model": model, "at": time.time(),
           "window_ends": time.time() + INSPECTION_SECONDS}
    item["inspection"] = out
    tap.emit("node_end", node="inspect", graph="buyer", ms=int((time.time() - t0) * 1000), driver=driver,
             model=model, error=err, verdict=verdict, reason=reason, checks=checks,
             delivery=public(d), title=item["title"])
    return out


def deliver_and_inspect(acct, eid: str) -> dict:
    t0 = time.time()
    tap.emit("node_start", node="deliver", graph="buyer")
    d = deliver(acct, eid)
    tap.emit("node_end", node="deliver", graph="buyer", ms=int((time.time() - t0) * 1000), driver="sim",
             delivery=public(d), title=acct.escrows[eid]["title"])
    return {"delivery": public(d), "inspection": inspect(acct, eid)}


def public(d: dict) -> dict:
    return {k: v for k, v in (d or {}).items() if not k.startswith("_")}


def record_access(acct, eid: str, ip: str) -> dict:
    item = acct.escrows.get(eid)
    if not item or not item.get("delivery"):
        raise ValueError("nothing has been delivered for that purchase yet")
    parts = (ip or "0.0.0.0").split(".")
    rec = {"at": time.time(), "ip": ".".join(parts[:3]) + ".x" if len(parts) == 4 else ip}
    item.setdefault("accessed", []).append(rec)
    return rec


def hold_view(item: dict) -> dict:
    """What the approval card shows about a hold's delivery."""
    ins = item.get("inspection") or {}
    return {"delivery": public(item.get("delivery")), "accessed": item.get("accessed") or [],
            "inspection": {k: ins.get(k) for k in ("verdict", "reason", "checks", "model", "window_ends")} if ins else None}


def auto_release_ok(item: dict, now: float | None = None) -> tuple:
    ins = item.get("inspection") or {}
    now = now or time.time()
    if not item.get("delivery"):
        return False, "nothing has been delivered yet"
    if ins.get("verdict") != "matches":
        return False, f"the inspector found the delivery {ins.get('verdict') or 'unverified'}, so it waits for you"
    if now < float(ins.get("window_ends") or 0):
        return False, "the inspection window is still open"
    return True, "the inspection window ended with no complaint and the inspector found it matches"
