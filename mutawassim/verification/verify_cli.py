"""
verify_cli.py — تجربة تفاعلية لوحدة التحقق.
المالك: غيداء (التحقق).

استخدام:
  python -m mutawassim.verification.verify_cli "النظافة من الإيمان"
  أو بدون وسيط للوضع التفاعلي (اكتبي ادعاءً كل سطر، وسطر فارغ للخروج).
"""
from __future__ import annotations

import sys

from ..schemas import Post, STATUS_LABEL_AR
from ..extraction.claim_extractor import extract_claims
from ..verification.verifier import verify


def check(text: str) -> None:
    post = Post(post_id="cli", text=text)
    claims = extract_claims(post)
    if not claims:
        print("  (لا يوجد ادعاء قابل للتحقق)")
        return
    for c in claims:
        r = verify(c)
        label = STATUS_LABEL_AR.get(r.status, r.status)
        print(f"  • {c.text}")
        print(f"    الحالة: {label} ({r.status}) | ثقة: {r.confidence}")
        for e in r.evidence:
            print(f"      - [{e.ruling}] {e.url}")
        if not r.evidence:
            print("      - لا دليل كافٍ -> إحالة لمختص")


def main() -> None:
    if len(sys.argv) > 1:
        check(" ".join(sys.argv[1:]))
        return
    print("اكتبي ادعاءً (سطر فارغ للخروج):")
    while True:
        try:
            t = input("ادعاء> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not t:
            break
        check(t)


if __name__ == "__main__":
    main()
