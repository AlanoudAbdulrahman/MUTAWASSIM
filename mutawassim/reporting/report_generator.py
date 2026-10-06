"""
report_generator.py — توليد بطاقة الرد الموثّقة.
المالك: العنود (الرد).

التصحيح من الأدلة المسترجَعة فقط: يعرض حكم المصدر ونصه واسمه، ولا يعرض
ملاحظات التحقق الداخلية (note) لأنها تقنية وليست موجّهة للمستخدم.

الإجراء:
- سؤال عن حكم شرعي                          -> إحالة لمختص (النظام لا يُفتي)
- confirmed                                  -> رد
- needs_review (لا دليل كافٍ)                 -> إحالة لمختص
- weak/fabricated في موضوع حسّاس (عقيدة/شبهة) -> إحالة لمختص
- weak/fabricated في غيره                    -> رد
"""
from __future__ import annotations

from ..schemas import (
    Action, Claim, Evidence, ResponseCard, RiskScore, VerificationResult, STATUS_LABEL_AR,
)
from ..verification.verifier import _status_from_ruling

# أنواع لا يُرد عليها آليًا إلا إذا ثبتت صحتها؛ غير ذلك يراجعه مختص
_SENSITIVE_TYPES = frozenset({"aqeedah", "shubha"})

# المستخرِج يكتب الأسئلة التي تُحال لمختص بهذه البدايات (انظر claim_extractor._SYSTEM_PROMPT)،
# ولكل نوع جملته في البطاقة
QUESTION_NOTES = {
    "سؤال عن حكم": "سؤال يطلب حكمًا شرعيًا، والنظام لا يُصدر فتاوى؛ يُحال إلى مختص.",
}

# أسماء المصادر المعتمدة كما تُعرض للمستخدم
_SOURCE_NAMES = {
    "dorar.net": "الدرر السنية",
    "quranpedia.net": "قرآنبيديا",
    "shamela.ws": "المكتبة الشاملة",
}

_SNIPPET_MAX = 200


def _question_note(claim: Claim) -> str | None:
    text = claim.text.strip()
    return next((note for prefix, note in QUESTION_NOTES.items() if text.startswith(prefix)), None)


def is_question(claim: Claim) -> bool:
    return _question_note(claim) is not None


def _source_name(e: Evidence) -> str:
    domain = e.source.split("/", 1)[0]
    return _SOURCE_NAMES.get(domain, e.source)


def _quote(e: Evidence) -> str:
    """نص الدليل مختصرًا بين علامتي تنصيص."""
    text = " ".join(e.snippet.split())
    if len(text) > _SNIPPET_MAX:
        text = text[:_SNIPPET_MAX].rsplit(" ", 1)[0] + "…"
    return f"«{text}»"


def _action(claim: Claim, result: VerificationResult) -> Action:
    if is_question(claim):
        return "إحالة لمختص"
    if result.status == "confirmed":
        return "رد"
    if result.status == "needs_review" or claim.type in _SENSITIVE_TYPES:
        return "إحالة لمختص"
    return "رد"


def _supporting_evidence(result: VerificationResult) -> Evidence | None:
    """الدليل الذي يوافق الحكم. حين يحكم النموذج من دليل غير الأول، لا نعرض
    دليلًا يناقض الشارة (مثل شارة «ضعيف» مع نص «صحيح»)."""
    for e in result.evidence:
        if _status_from_ruling(e.ruling) == result.status:
            return e
    return result.evidence[0] if result.evidence else None


def _correction(claim: Claim, result: VerificationResult, action: Action) -> str:
    top = _supporting_evidence(result)
    has_quote = top is not None and top.snippet.strip()

    if is_question(claim):
        text = _question_note(claim)
        if has_quote:
            text += f" ومن المصادر القريبة التي قد تفيد المختص، في {_source_name(top)}: {_quote(top)}."
        return text

    if top is None:
        return "لا يوجد دليل كافٍ في المصادر المعتمدة؛ يُحال للمختص قبل أي حكم."

    name = _source_name(top)
    quote = f" ونصّه هناك: {_quote(top)}." if has_quote else ""

    if result.status == "needs_review":
        # وُجد مصدر قريب لكنه لا يكفي للحكم؛ نعرضه للمختص
        return f"وُجد نص قريب في {name} لكنه لا يكفي لإصدار حكم؛ يُحال للمختص.{quote}"

    if _status_from_ruling(top.ruling) != result.status:
        # حكم النموذج لا يوافق درجة أي دليل: لا ننسب الحكم للمصدر
        near = f" وأقرب نص في {name}: {_quote(top)}." if has_quote else ""
        text = f"الحكم: {STATUS_LABEL_AR[result.status]}.{near}"
    elif result.status == "confirmed":
        body = f" بنصّه: {_quote(top)}." if has_quote else "."
        return f"ورد في {name}{body}"
    else:  # weak | fabricated
        text = f"حكمه في {name}: {top.ruling}.{quote}"
    if action == "إحالة لمختص":
        text += " موضوع حسّاس؛ يراجعه مختص قبل نشر الرد."
    return text


def build_card(claim: Claim, result: VerificationResult, risk: RiskScore) -> ResponseCard:
    """يرجّع ResponseCard نهائية."""
    action = _action(claim, result)
    return ResponseCard(
        claim_id=claim.claim_id,
        verdict_label=STATUS_LABEL_AR.get(result.status, result.status),
        correction=_correction(claim, result, action),
        # روابط فريدة بترتيب قوة الدليل
        sources=list(dict.fromkeys(e.url for e in result.evidence if e.url)),
        action=action,
        risk=risk.risk,
    )
