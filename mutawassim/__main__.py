"""
تشغيل موقع متوسّم بأمر واحد:

    python -m mutawassim              # http://localhost:8000 ويفتح المتصفح تلقائيًا
    python -m mutawassim --port 8080  # منفذ آخر
    python -m mutawassim --no-browser

للتطوير على الجهاز فقط (127.0.0.1) مع إعادة التحميل عند تعديل الكود.
للنشر العام انظروا قسم Deployment في README.
"""
from __future__ import annotations

import argparse
import pathlib
import sys
import threading
import webbrowser

ROOT = pathlib.Path(__file__).resolve().parents[1]  # مجلد المشروع
sys.path.insert(0, str(ROOT))  # يعمل حتى لو شُغّل الملف مباشرة أو من مجلد آخر


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m mutawassim", description="تشغيل موقع متوسّم")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true", help="لا تفتح المتصفح تلقائيًا")
    args = parser.parse_args()

    import uvicorn

    url = f"http://localhost:{args.port}"
    print(f"\n  متوسّم يعمل على {url}  (Ctrl+C للإيقاف)\n")
    if not args.no_browser:
        threading.Timer(2.0, lambda: webbrowser.open(url)).start()
    uvicorn.run("mutawassim.api.main:app", host="127.0.0.1", port=args.port, reload=True,
                app_dir=str(ROOT), reload_dirs=[str(ROOT / "mutawassim")], log_level="warning")


if __name__ == "__main__":
    main()
