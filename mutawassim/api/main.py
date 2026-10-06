"""
api/main.py — واجهة FastAPI وموقع متوسّم.
المالك: لجين (الخلفية/التكامل).

تشغيل:  uvicorn mutawassim.api.main:app --reload
ثم افتحوا http://localhost:8000 (الموقع)، و/docs لتوثيق الـ API.
الحدود والحماية في api/security.py.
"""
from __future__ import annotations

import logging
import pathlib

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .. import benchmark, config, llm, storage
from ..schemas import Claim, Post, ResponseCard
from ..pipeline import is_key_error, process_batch, run_pipeline
from ..reporting.pdf_report import _FONTS, _THEMES, DEFAULT_THEME, load_posts, parse_posts, render_pdf
from ..serialize import item_to_json, summarize
from . import security, views

log = logging.getLogger("mutawassim.api")

app = FastAPI(
    title="MUTAWASSIM API", version="0.3.0",
    docs_url="/docs" if security.EXPOSE_DOCS else None,
    redoc_url=None, openapi_url="/openapi.json" if security.EXPOSE_DOCS else None,
)

_WEB = pathlib.Path(__file__).resolve().parents[1] / "web"


@app.middleware("http")
async def identity_and_headers(request: Request, call_next):
    # هوية مجهولة لكل متصفح: السجل والإحصائيات تُقيَّد بها، فلا يرى زائرٌ بيانات غيره
    token = request.cookies.get(security.COOKIE_NAME)
    fresh = not security.valid_token(token)
    if fresh:
        token = security.new_token()
    request.state.owner = security.owner_of(token)
    response = await call_next(request)
    if fresh:
        response.set_cookie(security.COOKIE_NAME, token, max_age=security.COOKIE_MAX_AGE, httponly=True,
                            samesite="lax", secure=security.cookie_secure(request), path="/")
    response.headers.update(security.SECURITY_HEADERS)
    if request.url.path == "/docs":
        response.headers["Content-Security-Policy"] = security.DOCS_CSP
    return response


class VerifyRequest(BaseModel):
    posts: list[Post]


class ParseRequest(BaseModel):
    filename: str = Field(max_length=200)
    content: str


class ReportRequest(BaseModel):
    items: list[dict] = Field(default_factory=list, max_length=500)
    theme: str = DEFAULT_THEME


class EvaluateRequest(BaseModel):
    kind: str  # "verification" | "extraction"


# ---- واجهات سابقة (المسار والصيغة لا يتغيران) ----
@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/verify", response_model=list[ResponseCard])
def verify_batch(req: VerifyRequest, request: Request) -> list[ResponseCard]:
    security.check_batch(req.posts)
    key, _ = _model_key(request)
    with llm.using_key(key):
        return run_pipeline([p.model_dump() for p in req.posts])


def _model_key(request: Request) -> tuple[str | None, bool]:
    """مفتاح هذا الطلب: مفتاح الزائر، أو مفتاح الخادم إن سُمح. بلا مفتاح لا تحقق حقيقي."""
    key, server = security.resolve_key(request)
    if not config.MOCK_MODE and not key:
        raise HTTPException(401, "أدخلي مفتاح OpenAI الخاص بك من زر «مفتاحي» لبدء التحقق.")
    return key, server


# ---- واجهات الموقع ----
@app.get("/api/info")
def info(request: Request) -> dict:
    if security.is_local(request):
        benchmark.ensure_fresh()  # بعد تعديل الكود يُعاد القياس بمفتاح الخادم؛ لا يطلقه زوار الإنترنت
    return {"mode": views.mode_info(request),
            "demos": [{"key": k, "title": t} for k, (t, _) in views.DEMO_SETS.items()],
            "limits": {"max_posts": security.MAX_POSTS, "max_post_chars": security.MAX_POST_CHARS}}


@app.get("/api/demo/{key}")
def demo_posts(key: str) -> list[dict]:
    if key not in views.DEMO_SETS:  # قائمة مغلقة: لا يُقرأ أي مسار من المستخدم
        raise HTTPException(404, "مجموعة غير معروفة")
    return load_posts(views.DEMO_SETS[key][1])


@app.post("/api/parse")
def parse(req: ParseRequest) -> list[dict]:
    security.check_upload(req.content)
    try:
        posts = parse_posts(req.filename, req.content)
    except Exception:
        raise HTTPException(400, "تعذّرت قراءة الملف. تأكدي أنه JSON بصيغة [{post_id, text}] أو CSV بعمود text أو ملف ديمو .md")
    return [{"post_id": str(p.get("post_id")), "text": str(p.get("text", ""))}
            for p in posts if str(p.get("text", "")).strip()]


@app.post("/api/analyze")
def analyze(req: VerifyRequest, request: Request) -> dict:
    security.check_batch(req.posts)
    key, _ = _model_key(request)
    raw = [p.model_dump() for p in req.posts]
    try:
        with llm.using_key(key):
            batch = process_batch(raw, owner=request.state.owner, save=True, mode=views.mode_label())
    except Exception as e:
        if is_key_error(e):
            msg = ("رصيد مفتاحك انتهى أو تجاوز حدّه لدى OpenAI." if type(e).__name__ == "RateLimitError"
                   else "المفتاح غير صحيح أو غير مفعّل. تأكدي منه من زر «مفتاحي».")
            raise HTTPException(401, msg)
        log.exception("analyze failed")  # التفاصيل في سجل الخادم فقط
        raise HTTPException(502, "تعذّر إكمال التحقق. تأكدي من الاتصال ومفتاح النموذج ثم أعيدي المحاولة.")
    items = [item_to_json(i) for i in batch.items]
    return {"summary": summarize(items, posts_in=len(raw)), "items": items,
            "batch_id": batch.batch_id, "errors": batch.errors, "mode": views.mode_info(request)}


@app.post("/api/report")
def report(req: ReportRequest) -> Response:
    if req.theme not in _THEMES:
        raise HTTPException(400, "ثيم غير معروف")
    try:
        cards = [ResponseCard(**{k: i[k] for k in ResponseCard.model_fields if k in i}) for i in req.items]
        claims = [Claim(claim_id=i["claim_id"], source_post_id=i["post_id"], text=i["claim_text"],
                        type=i.get("claim_type", "other")) for i in req.items]
    except Exception:
        raise HTTPException(400, "بيانات التقرير غير صالحة")
    pdf = render_pdf(cards, claims, theme=req.theme)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="mutawassim_report.pdf"'})


@app.get("/api/sources")
def sources() -> dict:
    return views.sources_overview()


@app.get("/api/usage")
def usage(request: Request) -> dict:
    _claim_local_legacy(request)
    return views.usage(request.state.owner)


# ---- السجل: لكل متصفح سجله الخاص، ولا يصل أحد لسجل غيره ----
def _claim_local_legacy(request: Request) -> None:
    # سجلّ حُفظ قبل إضافة الهويات بلا مالك: يُسند لصاحب الجهاز عند فتحه محليًا فقط
    if security.is_local(request):
        storage.claim_legacy(request.state.owner)


@app.get("/api/history")
def history(request: Request) -> list[dict]:
    _claim_local_legacy(request)
    return storage.list_batches(request.state.owner)


@app.get("/api/history/{batch_id}")
def history_batch(batch_id: int, request: Request) -> dict:
    found = storage.get_batch(batch_id, request.state.owner)
    if not found:
        raise HTTPException(404, "الدفعة غير موجودة")
    found["summary"] = summarize(found["items"], posts_in=found["batch"]["posts_in"])
    return found


@app.delete("/api/history/{batch_id}")
def delete_history_batch(batch_id: int, request: Request) -> dict:
    if not storage.delete_batch(batch_id, request.state.owner):
        raise HTTPException(404, "الدفعة غير موجودة")
    return {"deleted": batch_id}


# ---- قياس الأداء: تلقائي عند تغيّر البصمة، ويدوي للمشرف ----
@app.get("/api/evaluation")
def evaluation_status(request: Request) -> dict:
    if security.is_local(request):
        benchmark.ensure_fresh()
    return benchmark.status()


@app.post("/api/evaluation", dependencies=[Depends(security.require_admin)])
def run_evaluation(req: EvaluateRequest) -> dict:
    if req.kind not in benchmark.KINDS:
        raise HTTPException(400, "نوع قياس غير معروف")
    try:
        return benchmark.run(req.kind)
    except Exception:
        log.exception("evaluation failed")
        raise HTTPException(502, "تعذّر إكمال القياس.")


# صفحات الموقع لها روابط مباشرة؛ كلها تفتح نفس الواجهة وهي تعرض الصفحة المطلوبة
@app.get("/performance", include_in_schema=False)
@app.get("/history", include_in_schema=False)
@app.get("/sources", include_in_schema=False)
def web_page() -> FileResponse:
    return FileResponse(_WEB / "index.html")


# الخطوط (نفس خطوط تقرير PDF) ثم الموقع؛ الموقع أخيرًا حتى لا يحجب مسارات الـ API
app.mount("/fonts", StaticFiles(directory=_FONTS), name="fonts")
if _WEB.exists():
    app.mount("/", StaticFiles(directory=_WEB, html=True), name="web")
