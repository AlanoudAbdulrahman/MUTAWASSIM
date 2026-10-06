/* متوسّم — موقع React بلا خطوة بناء (htm بدل JSX).
   كل الأرقام والأحكام من الـ API؛ لا منطق تحقق في الواجهة. */
const { useState, useEffect, useMemo } = React;
const html = htm.bind(React.createElement);

const STATUS = {
  fabricated:   { label: "موضوع",       icon: "✕", color: "var(--fabricated)" },
  weak:         { label: "ضعيف",        icon: "!", color: "var(--weak)" },
  needs_review: { label: "يحتاج تحقق",  icon: "؟", color: "var(--needs_review)" },
  confirmed:    { label: "مؤكد",        icon: "✓", color: "var(--confirmed)" },
};
const STATUS_ORDER = ["fabricated", "weak", "needs_review", "confirmed"];

const pct = (v) => `${Math.round((v || 0) * 100)}%`;
const safeUrl = (u) => (/^https?:\/\//i.test(String(u || "")) ? u : null);
const fix2 = (v) => (v ?? 0).toFixed(2);

/* مفتاح OpenAI الخاص بالزائر: في متصفحه فقط (الجلسة، أو الجهاز إن اختار التذكّر)،
   ويُرسل مع طلبات التحقق وحدها. الخادم لا يحفظه. */
const KEY_NAME = "mw_llm_key";
const keyStore = {
  get() {
    try { return sessionStorage.getItem(KEY_NAME) || localStorage.getItem(KEY_NAME) || ""; }
    catch (_) { return ""; }
  },
  set(key, remember) {
    try {
      this.clear();
      (remember ? localStorage : sessionStorage).setItem(KEY_NAME, key);
    } catch (_) {}
  },
  clear() {
    try { sessionStorage.removeItem(KEY_NAME); localStorage.removeItem(KEY_NAME); } catch (_) {}
  },
};

async function api(path, body, method, withKey) {
  const headers = { "Content-Type": "application/json" };
  const key = withKey ? keyStore.get() : "";
  if (key) headers["X-LLM-Key"] = key;
  const res = await fetch(path, body === undefined ? { method: method || "GET", headers } : {
    method: method || "POST", headers, body: JSON.stringify(body),
  });
  if (!res.ok) {
    let msg = `خطأ ${res.status}`;
    try { msg = (await res.json()).detail || msg; } catch (_) {}
    throw new Error(msg);
  }
  return res;
}
const getJSON = async (path, body, withKey) => (await api(path, body, undefined, withKey)).json();

function download(blob, name) {
  const url = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/* ================= مكوّنات عامة ================= */

function Badge({ status, label }) {
  const s = STATUS[status] || STATUS.needs_review;
  return html`<span className="badge" style=${{ "--c": s.color }}>
    <span className="icon" aria-hidden="true">${s.icon}</span>${label || s.label}</span>`;
}

function Kpi({ label, value, hint, color, icon }) {
  return html`<div className="kpi" style=${{ "--kpi-color": color || "var(--navy)" }}>
    <div className="value">${value}</div>
    <div className="label">${icon && html`<span aria-hidden="true">${icon}</span>`}${label}</div>
    ${hint && html`<div className="hint">${hint}</div>`}
  </div>`;
}

/* حلقة نسبة لمقياس واحد (مقدار واحد = لون واحد) */
function Ring({ value, label, hint }) {
  const r = 30, c = 2 * Math.PI * r, v = Math.max(0, Math.min(1, value || 0));
  return html`<div className="ring-tile">
    <svg viewBox="0 0 80 80" className="ring" role="img" aria-label=${`${label}: ${pct(v)}`}>
      <circle cx="40" cy="40" r=${r} className="ring-track" />
      <circle cx="40" cy="40" r=${r} className="ring-fill"
        style=${{ strokeDasharray: `${c * v} ${c}` }} transform="rotate(-90 40 40)" />
      <text x="40" y="45" textAnchor="middle" className="ring-text">${pct(v)}</text>
    </svg>
    <div><div className="ring-label">${label}</div><div className="small muted">${hint}</div></div>
  </div>`;
}

/* حلقة توزيع الأحكام: كل قطعة بلون حالتها، والنسبة والعدد مكتوبان في الدليل */
function Donut({ rows, total }) {
  const r = 52, c = 2 * Math.PI * r, gap = rows.filter((x) => x.value).length > 1 ? 2 : 0;
  let offset = 0;
  return html`<div className="donut-wrap">
    <svg viewBox="0 0 140 140" className="donut" role="img" aria-label="توزيع الأحكام">
      <circle cx="70" cy="70" r=${r} className="ring-track" style=${{ strokeWidth: 16 }} />
      ${rows.filter((x) => x.value).map((x) => {
        const len = (x.value / total) * c;
        const el = html`<circle key=${x.label} cx="70" cy="70" r=${r} fill="none"
          style=${{ stroke: x.color, strokeWidth: 16, strokeDasharray: `${Math.max(len - gap, 0)} ${c}`, strokeDashoffset: -offset }}
          transform="rotate(-90 70 70)"><title>${x.label}: ${x.value} (${pct(x.value / total)})</title></circle>`;
        offset += len;
        return el;
      })}
      <text x="70" y="68" textAnchor="middle" className="donut-total">${total}</text>
      <text x="70" y="88" textAnchor="middle" className="donut-sub">ادعاء</text>
    </svg>
    <ul className="legend">
      ${rows.map((x) => html`<li key=${x.label}><span className="sw" style=${{ "--c": x.color }}></span>
        <span>${x.label}</span><b>${x.value}</b><span className="muted">${pct(total ? x.value / total : 0)}</span></li>`)}
    </ul>
  </div>`;
}

/* أعمدة أفقية بتلميح عند المرور (القيمة مكتوبة دائمًا، واللون لا يحمل المعنى وحده) */
function BarChart({ rows, max, format = (v) => v, empty = "لا بيانات" }) {
  const [tip, setTip] = useState(null);
  const top = max ?? Math.max(1, ...rows.map((r) => r.value));
  if (!rows.length) return html`<div className="empty">${empty}</div>`;
  return html`<div className="chart" onMouseLeave=${() => setTip(null)}>
    ${rows.map((r, i) => html`
      <div key=${i} className="bar-row"
           onMouseMove=${(e) => setTip({ x: e.clientX, y: e.clientY, body: r.tip || `${r.label}: ${format(r.value)}` })}>
        <div className="bar-label" title=${r.label}>${r.label}</div>
        <div className="bar-track"><div className="bar-fill"
             style=${{ width: `${(r.value / top) * 100}%`, "--c": r.color }}></div></div>
        <div className="bar-value">${format(r.value)}</div>
      </div>`)}
    ${tip && html`<div className="tooltip" style=${{ left: tip.x + 14, top: tip.y + 14 }}>${tip.body}</div>`}
  </div>`;
}

function Header({ tab, setTab, mode, onAbout, onKey, hasKey }) {
  const real = mode && !mode.mock_mode;
  const tabs = [["verify", "التحقق"], ["performance", "أداء النظام"], ["history", "السجل"], ["sources", "المصادر المعتمدة"]];
  return html`<header className="hero">
    <div className="hero-pattern"></div>
    <div className="hero-inner">
      <div className="brand">
        <h1><button className="brand-link" onClick=${() => setTab("verify")} title="الصفحة الرئيسية">متوسم</button></h1>
        <p>الإنذار المبكر للمحتوى الديني المضلِّل — تحقق مسند إلى المصادر المعتمدة</p>
      </div>
      <div className="hero-actions">
        ${mode && html`<div className=${"mode-chip" + (!real || (mode.needs_user_key && !hasKey) ? " mock" : "")}>
          <span className="dot"></span>
          ${!real ? "وضع تجريبي (بلا نموذج)"
            : mode.needs_user_key && !hasKey ? "أدخلي مفتاحك لبدء التحقق"
            : `${mode.model} · ${hasKey ? "بمفتاحك" : "بمفتاح الخادم"}`}
        </div>`}
        ${real && html`<button className="about-btn ghost-btn" onClick=${onKey}>${hasKey ? "🔑 مفتاحي" : "🔑 أدخلي مفتاحك"}</button>`}
        <button className="about-btn" onClick=${onAbout}>من نحن</button>
      </div>
    </div>
    <nav className="tabs">
      ${tabs.map(([k, t]) => html`<button key=${k} className=${"tab" + (tab === k ? " active" : "")}
          onClick=${() => setTab(k)}>${t}</button>`)}
    </nav>
  </header>`;
}

/* ================= صفحة التحقق ================= */

function HowItWorks() {
  const steps = [
    ["١", "استخراج الادعاء", "النموذج يقرأ المنشور ولو كان عاميًا، ويستخرج النص المنقول ونوعه"],
    ["٢", "البحث في المصادر", "بالكلمات ثم بالمعنى في المصادر المعتمدة (الدرر السنية وقرآنبيديا)"],
    ["٣", "الحكم من الدليل", "الحكم من درجة المصدر فقط؛ ما لا يسنده مصدر يُحال إلى مختص"],
    ["٤", "الخطورة والتقرير", "ترتيب الادعاءات بالخطورة، وبطاقة موثّقة لكل ادعاء وتقرير PDF"],
  ];
  return html`<section className="steps section">
    ${steps.map(([n, t, d]) => html`<div key=${n} className="step">
      <span className="step-num">${n}</span><div><b>${t}</b><div className="small muted">${d}</div></div></div>`)}
  </section>`;
}

function InputPanel({ demos, limits, onAnalyze, loading, blocked }) {
  const [source, setSource] = useState(demos[0]?.key || "text");
  const [posts, setPosts] = useState([]);
  const [text, setText] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    setError("");
    if (source === "text") { setPosts(lines(text)); return; }
    if (source === "file") { setPosts([]); return; }
    getJSON(`/api/demo/${source}`).then(setPosts).catch((e) => setError(e.message));
  }, [source]);

  function lines(t) {
    return t.split("\n").map((s) => s.trim()).filter(Boolean).map((s, i) => ({ post_id: `p${i + 1}`, text: s }));
  }

  async function onFile(e) {
    const f = e.target.files?.[0];
    if (!f) return;
    setError("");
    try { setPosts(await getJSON("/api/parse", { filename: f.name, content: await f.text() })); }
    catch (err) { setError(err.message); setPosts([]); }
  }

  const options = [...demos.map((d) => [d.key, d.title]), ["text", "لصق نص"], ["file", "رفع ملف"]];
  const tooMany = limits && posts.length > limits.max_posts;
  return html`<section className="panel">
    <h2>المنشورات</h2>
    <div className="segmented">
      ${options.map(([k, t]) => html`<button key=${k} className=${"seg" + (source === k ? " active" : "")}
          onClick=${() => setSource(k)}>${t}</button>`)}
    </div>
    ${source === "text" && html`<textarea placeholder="منشور واحد في كل سطر…" value=${text}
        onInput=${(e) => { setText(e.target.value); setPosts(lines(e.target.value)); }}></textarea>`}
    ${source === "file" && html`<label className="file-drop">
        <input type="file" accept=".json,.csv,.md" onChange=${onFile} />
        اختاري ملف JSON بصيغة [{post_id, text}]، أو CSV بعمود text، أو ملف ديمو .md
      </label>`}
    ${posts.length > 0 && source !== "text" && html`<ol className="preview">
        ${posts.slice(0, 12).map((p) => html`<li key=${p.post_id}>${p.text}</li>`)}
        ${posts.length > 12 && html`<li className="muted">… و${posts.length - 12} منشورات أخرى</li>`}
      </ol>`}
    <div className="row spread" style=${{ marginTop: 14 }}>
      <span className=${"small " + (tooMany ? "warn-text" : "muted")}>${posts.length} منشور جاهز للتحقق
        ${limits && ` · الحد ${limits.max_posts} في الدفعة`}</span>
      <button className="btn" disabled=${loading || !posts.length || tooMany || blocked} onClick=${() => onAnalyze(posts)}>
        ${loading ? html`<span className="spinner"></span> جارِ التحقق…` : "تحقّق"}
      </button>
    </div>
    ${loading && html`<div className="notice">مع النموذج الحقيقي قد يستغرق التحقق دقيقة أو أكثر حسب عدد المنشورات.</div>`}
    ${error && html`<div className="notice error">${error}</div>`}
  </section>`;
}

function Summary({ summary }) {
  const count = (s) => summary.by_status.find((x) => x.status === s)?.count ?? 0;
  return html`<div className="grid kpis section">
    <${Kpi} label="ادعاء مستخرج" value=${summary.total_claims}
        hint=${`من ${summary.posts_with_claims} منشور من أصل ${summary.posts_in}`} />
    ${STATUS_ORDER.map((s) => html`<${Kpi} key=${s} label=${STATUS[s].label} value=${count(s)}
        color=${STATUS[s].color} icon=${STATUS[s].icon} />`)}
    <${Kpi} label="إحالة لمختص" value=${summary.referrals} color="var(--mauve)"
        hint=${`أعلى خطورة ${fix2(summary.max_risk)}`} />
  </div>`;
}

function Charts({ summary, items }) {
  const statusRows = summary.by_status.map((s) => ({
    label: s.label, value: s.count, color: STATUS[s.status].color,
    tip: `${s.label}: ${s.count} من ${summary.total_claims} ادعاء`,
  }));
  const riskRows = items.filter((i) => i.risk > 0).slice(0, 8).map((i) => ({
    label: i.claim_text, value: i.risk, color: STATUS[i.status].color,
    tip: html`<div><b>${i.verdict_label}</b> · ${i.claim_type_ar}</div><div>${i.claim_text}</div>
      <div className="formula">${fix2(i.factors.spread)} × ${fix2(i.factors.severity)} × ${fix2(i.factors.sensitivity)} = ${fix2(i.risk)}</div>`,
  }));
  const typeRows = summary.by_type.map((t) => ({ label: t.label, value: t.count, color: "var(--navy)" }));
  return html`<div className="grid charts section">
    <div className="panel"><h2>توزيع الأحكام</h2><${Donut} rows=${statusRows} total=${summary.total_claims} /></div>
    <div className="panel"><h2>الأعلى خطورة</h2>
      <${BarChart} rows=${riskRows} max=${1} format=${fix2} empty="لا يوجد ادعاء خطِر في هذه الدفعة" />
      <div className="muted small">الخطورة = الانتشار × البطلان × الحساسية</div></div>
    <div className="panel"><h2>أنواع الادعاءات</h2><${BarChart} rows=${typeRows} /></div>
  </div>`;
}

function ClaimCard({ item, index }) {
  const [open, setOpen] = useState(false);
  const s = STATUS[item.status];
  const referral = item.action === "إحالة لمختص";
  return html`<article className="card" style=${{ "--c": s.color }}>
    <div className="card-head">
      <div className="left">
        <span className="num">${index}</span>
        <${Badge} status=${item.status} label=${item.verdict_label} />
        <span className=${"pill" + (referral ? " ref" : "")}>${item.action}</span>
        <span className="type-chip">${item.claim_type_ar}</span>
      </div>
      <div className="risk" title="الخطورة = الانتشار × البطلان × الحساسية">
        <span className="small muted">الخطورة</span>
        <div className="bar-track"><div className="bar-fill" style=${{ width: pct(item.risk), "--c": s.color }}></div></div>
        <span className="val">${fix2(item.risk)}</span>
      </div>
    </div>
    <div className="claim">«${item.claim_text}»</div>
    <div className="post-ref">من المنشور ${item.post_id}</div>
    <p className="correction">${item.correction}</p>
    ${item.sources.length > 0 && html`<div className="sources">
      ${item.sources.filter(safeUrl).map((u, i) => html`<a key=${i} href=${u} target="_blank" rel="noopener noreferrer">المصدر ${i + 1} ↗</a>`)}
    </div>`}
    <button className="details-toggle" onClick=${() => setOpen(!open)}>${open ? "إخفاء التفاصيل ▲" : "عرض التفاصيل ▼"}</button>
    ${open && html`<dl className="details">
      <dt>المنشور الأصلي</dt><dd>${item.post_text}</dd>
      <dt>حساب الخطورة</dt>
      <dd className="formula">الانتشار ${fix2(item.factors.spread)} × البطلان ${fix2(item.factors.severity)} × الحساسية ${fix2(item.factors.sensitivity)} = ${fix2(item.risk)}</dd>
      ${item.evidence.length > 0 && html`<dt>الأدلة المسترجعة</dt>
        ${item.evidence.map((e, i) => html`<dd key=${i}>${e.source_name} · ${e.ruling || "بلا درجة"} — «${e.snippet}»</dd>`)}`}
    </dl>`}
  </article>`;
}

function Results({ result }) {
  const [statuses, setStatuses] = useState(new Set());
  const [action, setAction] = useState("");
  const [busy, setBusy] = useState(false);
  const items = result.items.filter((i) =>
    (!statuses.size || statuses.has(i.status)) && (!action || i.action === action));

  function toggle(s) {
    const next = new Set(statuses);
    next.has(s) ? next.delete(s) : next.add(s);
    setStatuses(next);
  }
  async function pdf() {
    setBusy(true);
    try { download(await (await api("/api/report", { items: result.items })).blob(), "mutawassim_report.pdf"); }
    finally { setBusy(false); }
  }
  const json = () => download(new Blob([JSON.stringify(result, null, 2)], { type: "application/json" }), "mutawassim_results.json");

  return html`<div>
    <${Summary} summary=${result.summary} />
    <${Charts} summary=${result.summary} items=${result.items} />
    <div className="toolbar">
      <div className="filters">
        ${STATUS_ORDER.map((s) => html`<button key=${s} className=${"chip" + (statuses.has(s) ? " on" : "")}
            onClick=${() => toggle(s)}><span className="sw" style=${{ "--c": STATUS[s].color }}></span>${STATUS[s].label}</button>`)}
        <select className="chip" value=${action} onChange=${(e) => setAction(e.target.value)}>
          <option value="">كل الإجراءات</option><option value="رد">رد</option><option value="إحالة لمختص">إحالة لمختص</option>
        </select>
      </div>
      <div className="row">
        <button className="btn ghost" onClick=${json}>تحميل JSON</button>
        <button className="btn" onClick=${pdf} disabled=${busy}>${busy ? html`<span className="spinner"></span>` : "تحميل التقرير PDF"}</button>
      </div>
    </div>
    <h2 className="section-title">البطاقات (${items.length}) — مرتبة حسب الخطورة</h2>
    <div className="cards">
      ${items.map((i) => html`<${ClaimCard} key=${i.claim_id} item=${i} index=${result.items.indexOf(i) + 1} />`)}
      ${!items.length && html`<div className="empty">لا توجد بطاقات تطابق التصفية.</div>`}
    </div>
  </div>`;
}

function VerifyPage({ demos, limits, needsKey, onKey }) {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  async function analyze(posts) {
    setLoading(true); setError("");
    try { setResult(await getJSON("/api/analyze", { posts }, true)); }
    catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }
  return html`<div>
    ${needsKey && html`<div className="notice key-needed">
        🔑 لاستخدام التحقق أدخلي مفتاح OpenAI الخاص بك؛ يبقى في متصفحك وتكون التكلفة على حسابك.
        <button className="btn small-btn" onClick=${onKey}>أدخلي المفتاح</button></div>`}
    <${InputPanel} demos=${demos} limits=${limits} onAnalyze=${analyze} loading=${loading} blocked=${needsKey} />
    ${!result && !loading && html`<${HowItWorks} />`}
    ${error && html`<div className="notice error">${error}</div>`}
    ${result && html`<div className="notice ok-note">
        ✓ حُفظت النتائج في سجلّك الخاص (عملية #${result.batch_id})، وتدخل في إحصائياتك وحساب الانتشار.
        ${result.errors.length > 0 && html`<div>تعذّر إكمال ${result.errors.length} عنصر فأُحيل للمختص أو تُخطّي: ${result.errors.map((e) => e.post_id).join("، ")}</div>`}
      </div>`}
    ${result && (result.items.length
      ? html`<${Results} result=${result} />`
      : html`<div className="panel section empty">لم يُستخرج ادعاء قابل للتحقق من هذه المنشورات.</div>`)}
  </div>`;
}

/* ================= صفحة أداء النظام ================= */

const METRICS = {
  verification: {
    title: "التحقق من الأحكام", cases: "مجموعة اختبار من 100 ادعاء أحكامها معروفة مسبقًا",
    tiles: [
      ["status_accuracy", "دقة الحكم", "الحكم يطابق المتوقع"],
      ["citation_accuracy", "دقة الاستشهاد", "المصدر يوافق الحكم فعلًا"],
      ["detection_precision", "دقة كشف المغلوط", "إذا قال مغلوط فهو مغلوط"],
      ["detection_recall", "شمول كشف المغلوط", "كم من المغلوط اكتشف"],
      ["detection_f1", "F1 كشف المغلوط", "توازن الدقة والشمول"],
      ["citation_rate", "الأحكام المسندة برابط", "من الأحكام الصادرة"],
    ],
  },
  extraction: {
    title: "استخراج الادعاءات", cases: "منشورات اختبار ادعاءاتها الصحيحة معروفة مسبقًا",
    tiles: [
      ["claim_f1", "F1 الاستخراج", "توازن الدقة والشمول"],
      ["claim_precision", "دقة الاستخراج", "ما استُخرج ادعاء فعلًا"],
      ["claim_recall", "شمول الاستخراج", "ما فات من الادعاءات"],
      ["type_accuracy", "دقة نوع الادعاء", "حديث/قرآن/عقيدة…"],
      ["no_claim_accuracy", "تجاهل غير الادعاءات", "الدعاء والرأي وأسئلة المعلومات"],
    ],
  },
};

/* حالة متوقعة/ناتجة: رمز حالة، أو قائمة ادعاءات (الاستخراج)، أو no_claim */
function describe(v) {
  if (Array.isArray(v)) return v.length ? v.join("، ") : "لا ادعاء";
  if (v === "no_claim") return "لم يُستخرج ادعاء";
  if (typeof v === "string" && v.startsWith("error:")) return `خطأ: ${v.slice(6)}`;
  return STATUS[v]?.label || v || "";
}

function EvalPanel({ kind, data, stale }) {
  const meta = METRICS[kind];
  const failures = data?.failures || [];
  return html`<div className="eval-block">
    <div className="row spread">
      <h3>${meta.title}</h3>
      ${data && html`<span className="muted small">${meta.cases} · آخر قياس ${data.ran_at.replace("T", " ")}${data.model ? ` · ${data.model}` : ""}</span>`}
    </div>
    ${!data && html`<div className="empty">لم يُقس بعد.</div>`}
    ${data && html`<div className=${"grid rings" + (stale ? " dim" : "")}>
      ${meta.tiles.map(([k, label, hint]) => html`<${Ring} key=${k} label=${label} value=${data[k]} hint=${hint} />`)}
    </div>`}
    ${data && failures.length > 0 && html`<details style=${{ marginTop: 12 }}>
      <summary>حالات للمراجعة (${failures.length})</summary>
      <div className="table-wrap"><table><thead><tr>
        <th>الحالة</th><th>المتوقع</th><th>الناتج</th></tr></thead><tbody>
        ${failures.map((f, i) => html`<tr key=${i}>
          <td>${f.claim || f.post_id}</td>
          <td>${describe(f.expected)}</td>
          <td>${f.error ? `خطأ: ${f.error}` : describe(f.got ?? f.predicted)}</td></tr>`)}
      </tbody></table></div>
    </details>`}
  </div>`;
}

function BenchmarkBox() {
  const [st, setSt] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let alive = true, timer;
    const load = () => getJSON("/api/evaluation").then((d) => {
      if (!alive) return;
      setSt(d);
      if (d.running) timer = setTimeout(load, 4000);  // يتابع حتى ينتهي القياس التلقائي
    }).catch((e) => setError(e.message));
    load();
    return () => { alive = false; clearTimeout(timer); };
  }, []);
  if (error) return html`<div className="notice error">${error}</div>`;
  if (!st) return html`<section className="panel"><div className="empty">جارِ التحميل…</div></section>`;
  const stale = st.stale.length > 0;
  const chip = st.running ? html`<span className="status-chip busy"><span className="spinner dark"></span>يتم التحديث تلقائيًا بعد تعديل الكود…</span>`
    : st.error ? html`<span className="status-chip err">تعذّر التحديث التلقائي</span>`
    : stale ? html`<span className="status-chip warn">بحاجة إلى تحديث</span>`
    : html`<span className="status-chip ok">✓ مطابق لآخر نسخة</span>`;
  return html`<section className="panel">
    <div className="row spread">
      <h2 style=${{ margin: 0 }}>الأداء على مجموعات الاختبار</h2>${chip}
    </div>
    <p className="muted small">مشتركة بين كل المستخدمين: ثابتة لنفس الكود، وتُعاد تلقائيًا عند أي تعديل في الكود أو المصادر أو الإعدادات.
      ${st.mode === "mock" ? " (الوضع التجريبي: النتائج تقيس البديل بلا نموذج.)" : ""}</p>
    ${["verification", "extraction"].map((k) => html`<${EvalPanel} key=${k} kind=${k}
        data=${st.results[k]} stale=${st.stale.includes(k)} />`)}
  </section>`;
}

function UsageBox() {
  const [u, setU] = useState(null);
  useEffect(() => { getJSON("/api/usage").then(setU).catch(() => setU(false)); }, []);
  if (u === null) return html`<section className="panel section"><div className="empty">جارِ التحميل…</div></section>`;
  if (u === false) return html`<div className="notice error">تعذّر تحميل الإحصائيات.</div>`;
  const rows = u.by_status.map((s) => ({ label: s.label, value: s.count, color: STATUS[s.status].color }));
  const top = u.top_misleading.map((t) => ({
    label: t.claim_text, value: t.posts, color: STATUS[t.status]?.color || "var(--navy)",
    tip: `${t.claim_text} — ورد في ${t.posts} منشور`,
  }));
  return html`<section className="panel section">
    <div className="row spread">
      <h2 style=${{ margin: 0 }}>إحصائيات استخدامي</h2>
      <span className="status-chip ok">يتحدث مع كل تحقق</span>
    </div>
    <p className="muted small">كل ما فحصتِه من هذا المتصفح منذ البداية. خاصة بك، ولا تشمل ما يفحصه الآخرون.</p>
    ${u.claims === 0 ? html`<div className="empty">لا توجد عمليات تحقق محفوظة بعد. جرّبي صفحة التحقق.</div>` : html`
      <div className="grid kpis">
        <${Kpi} label="عملية تحقق" value=${u.batches} />
        <${Kpi} label="منشور فُحص" value=${u.posts} />
        <${Kpi} label="ادعاء مستخرج" value=${u.claims} />
        <${Kpi} label="ادعاء مغلوط" value=${u.misleading} color="var(--fabricated)" />
        <${Kpi} label="إحالة لمختص" value=${u.referrals} color="var(--mauve)" />
      </div>
      <div className="grid two section">
        <div className="panel inner"><h2>توزيع كل الأحكام</h2><${Donut} rows=${rows} total=${u.claims} /></div>
        <div className="panel inner"><h2>أكثر الادعاءات المغلوطة انتشارًا</h2>
          <${BarChart} rows=${top} empty="لا توجد ادعاءات مغلوطة بعد" />
          <div className="muted small">الرقم = عدد المنشورات التي ورد فيها الادعاء</div></div>
      </div>`}
  </section>`;
}

function PerformancePage() {
  return html`<div>
    <section className="explain">
      <h2>كيف نقيس الأداء؟</h2>
      <p>في الصفحة جزآن: <b>الأداء على مجموعات الاختبار</b> يمرّر النظام كاملًا على ادعاءات
        <b>أجوبتها الصحيحة معروفة مسبقًا</b> ويحسب نسبة الصواب؛ فهو ثابت لنفس الكود ويُعاد تلقائيًا
        عند أي تعديل، وهو نفسه لكل المستخدمين. و<b>إحصائيات استخدامي</b> تجمع ما فحصتِه أنتِ فقط، وتتحدث مع كل تحقق.</p>
      <ul>
        <li><b>قياس التحقق:</b> 100 ادعاء، لكل واحد حكمه الصحيح (مؤكد/ضعيف/موضوع/يحتاج تحقق).</li>
        <li><b>قياس الاستخراج:</b> منشورات نعرف ما فيها من ادعاءات، لنتأكد أن النظام يلتقطها ولا يخترع غيرها.</li>
      </ul>
    </section>
    <${BenchmarkBox} />
    <${UsageBox} />
  </div>`;
}

/* ================= صفحة السجل ================= */

function HistoryPage() {
  const [rows, setRows] = useState(null);
  const [open, setOpen] = useState(null);
  const [confirm, setConfirm] = useState(null);
  const [error, setError] = useState("");
  const load = () => getJSON("/api/history").then(setRows).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  async function show(id) {
    setError("");
    try {
      const d = await getJSON(`/api/history/${id}`);
      setOpen({ id, created_at: d.batch.created_at, result: { summary: d.summary, items: d.items } });
    } catch (e) { setError(e.message); }
  }
  async function remove(id) {
    try { await api(`/api/history/${id}`, undefined, "DELETE"); setConfirm(null); load(); }
    catch (e) { setError(e.message); }
  }

  if (open) return html`<div>
    <div className="row spread">
      <button className="btn ghost" onClick=${() => setOpen(null)}>→ العودة إلى السجل</button>
      <span className="muted">عملية #${open.id} · ${open.created_at.replace("T", " ")}</span>
    </div>
    <${Results} result=${open.result} />
  </div>`;

  return html`<div>
    <div className="notice privacy">🔒 سجلّك خاص بهذا المتصفح: لا يراه غيرك، ولا يُضاف إليه ما يفحصه الآخرون.
      يُحفظ تلقائيًا ويُستفاد منه في حساب انتشار الادعاءات عبر الزمن، ويختفي إذا مسحتِ بيانات الموقع من المتصفح.</div>
    ${error && html`<div className="notice error">${error}</div>`}
    ${rows === null && !error && html`<div className="empty">جارِ التحميل…</div>`}
    ${rows && rows.length === 0 && html`<section className="panel empty">لا توجد عمليات تحقق محفوظة بعد.</section>`}
    ${rows && rows.length > 0 && html`<section className="panel"><div className="table-wrap"><table>
      <thead><tr><th>#</th><th>التاريخ</th><th>المنشورات</th><th>الادعاءات</th><th>مغلوط</th>
        <th>إحالات</th><th>أعلى خطورة</th><th></th></tr></thead>
      <tbody>${rows.map((b) => html`<tr key=${b.id}>
        <td>${b.id}</td><td>${b.created_at.replace("T", " ")}</td><td>${b.posts_in}</td>
        <td>${b.total_claims}</td><td>${b.misleading}</td><td>${b.referrals}</td><td>${fix2(b.max_risk)}</td>
        <td className="actions">
          <button className="btn ghost small-btn" onClick=${() => show(b.id)}>عرض</button>
          ${confirm === b.id
            ? html`<button className="btn danger small-btn" onClick=${() => remove(b.id)}>تأكيد الحذف</button>
                   <button className="btn ghost small-btn" onClick=${() => setConfirm(null)}>إلغاء</button>`
            : html`<button className="btn ghost small-btn" onClick=${() => setConfirm(b.id)}>حذف</button>`}
        </td></tr>`)}</tbody></table></div></section>`}
  </div>`;
}

/* ================= صفحة المصادر ================= */

function SourcesPage() {
  const [data, setData] = useState(null);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  useEffect(() => { getJSON("/api/sources").then(setData).catch((e) => setError(e.message)); }, []);
  const rows = useMemo(() => (data?.items || []).filter((r) =>
    (!status || r.status === status) && (!q || r.text.includes(q) || (r.ruling || "").includes(q))), [data, q, status]);
  if (error) return html`<div className="notice error">${error}</div>`;
  if (!data) return html`<div className="empty">جارِ التحميل…</div>`;
  const typeCount = (t) => data.by_type.find((x) => x.type === t)?.count ?? 0;
  return html`<div>
    <p className="muted">قاعدة المعرفة التي يستند إليها كل حكم. النظام لا يحكم إلا بما في هذه المصادر.</p>
    <div className="grid kpis">
      <${Kpi} label="مصدر معتمد" value=${data.total} />
      <${Kpi} label="حديث" value=${typeCount("hadith")} hint="الدرر السنية" />
      <${Kpi} label="آية" value=${typeCount("quran")} hint="قرآنبيديا" />
    </div>
    <div className="grid two section">
      <div className="panel"><h2>المصادر حسب الحكم</h2>
        <${BarChart} rows=${data.by_status.map((s) => ({ label: s.label, value: s.count, color: STATUS[s.status].color }))} /></div>
      <div className="panel"><h2>المصادر حسب الجهة</h2>
        <${BarChart} rows=${data.by_source.map((s) => ({ label: s.label, value: s.count, color: "var(--navy)" }))} /></div>
    </div>
    <section className="panel section">
      <div className="row spread" style=${{ marginBottom: 10 }}>
        <h2 style=${{ margin: 0 }}>كل المصادر (${rows.length})</h2>
        <div className="row">
          <select className="search" value=${status} onChange=${(e) => setStatus(e.target.value)}>
            <option value="">كل الأحكام</option>
            ${STATUS_ORDER.map((s) => html`<option key=${s} value=${s}>${STATUS[s].label}</option>`)}
          </select>
          <input className="search" placeholder="ابحثي في النصوص والأحكام…" value=${q} onInput=${(e) => setQ(e.target.value)} />
        </div>
      </div>
      <div className="table-wrap"><table><thead><tr>
        <th>النص</th><th>الحكم</th><th>الدرجة في المصدر</th><th>المصدر</th></tr></thead><tbody>
        ${rows.map((r) => html`<tr key=${r.id}>
          <td className="text">${r.text}</td>
          <td><${Badge} status=${r.status} label=${r.label} /></td>
          <td>${r.ruling}</td>
          <td>${safeUrl(r.url) ? html`<a href=${r.url} target="_blank" rel="noopener noreferrer">${r.source_name} ↗</a>` : r.source_name}</td></tr>`)}
      </tbody></table></div>
    </section>
  </div>`;
}

/* ================= مفتاح الزائر ================= */

function KeyModal({ onClose, onChange }) {
  const [key, setKey] = useState(keyStore.get());
  const [show, setShow] = useState(false);
  const [remember, setRemember] = useState(() => { try { return !!localStorage.getItem(KEY_NAME); } catch (_) { return false; } });
  const [error, setError] = useState("");
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);
  function save() {
    const k = key.trim();
    if (!/^sk-[A-Za-z0-9_\-]{16,}$/.test(k)) { setError("المفتاح يبدأ بـ sk- ويتكون من حروف وأرقام."); return; }
    keyStore.set(k, remember); onChange(true); onClose();
  }
  function remove() { keyStore.clear(); setKey(""); onChange(false); onClose(); }
  return html`<div className="modal-backdrop" onClick=${onClose}>
    <div className="modal" role="dialog" aria-modal="true" aria-labelledby="key-title" onClick=${(e) => e.stopPropagation()}>
      <button className="modal-close" onClick=${onClose} aria-label="إغلاق">×</button>
      <div className="modal-head">
        <h2 id="key-title">مفتاح OpenAI الخاص بك</h2>
        <p className="tagline-dark">التحقق يستخدم مفتاحك، فتكون التكلفة على حسابك أنتِ.</p>
      </div>
      <label className="field-label" htmlFor="llm-key">المفتاح</label>
      <div className="key-row">
        <input id="llm-key" className="search key-input" type=${show ? "text" : "password"} dir="ltr"
          autoComplete="off" spellCheck="false" placeholder="sk-..." value=${key}
          onInput=${(e) => { setKey(e.target.value); setError(""); }} />
        <button className="btn ghost small-btn" onClick=${() => setShow(!show)}>${show ? "إخفاء" : "إظهار"}</button>
      </div>
      <label className="check"><input type="checkbox" checked=${remember} onChange=${(e) => setRemember(e.target.checked)} />
        تذكّره على هذا الجهاز (وإلا يُنسى عند إغلاق المتصفح)</label>
      ${error && html`<div className="notice error">${error}</div>`}
      <ul className="key-facts small">
        <li>🔒 يبقى في متصفحك فقط، ويُرسل مع طلب التحقق عبر اتصال آمن، ولا يحفظه خادمنا ولا يسجّله.</li>
        <li>💡 الأفضل مفتاح مخصّص لمتوسّم بسقف صرف شهري، من <span dir="ltr">platform.openai.com/api-keys</span></li>
      </ul>
      <div className="row spread">
        ${keyStore.get() ? html`<button className="btn ghost" onClick=${remove}>حذف المفتاح</button>` : html`<span></span>`}
        <button className="btn" onClick=${save}>حفظ</button>
      </div>
    </div>
  </div>`;
}

/* ================= من نحن ================= */

function AboutModal({ onClose }) {
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => { document.removeEventListener("keydown", onKey); document.body.style.overflow = ""; };
  }, []);
  const values = [
    ["✓", "موثوق", "كل حكم مأخوذ من مصدر معتمد ومربوط برابطه، ولا يحكم النموذج من عنده."],
    ["◎", "ذكي", "يفهم المنشورات العامية ويستخرج منها الادعاءات ويبحث عنها بالكلمات والمعنى."],
    ["⚑", "مسؤول", "لا يُصدر فتاوى؛ ما لا دليل عليه أو يحتاج اجتهادًا يُحال إلى مختص."],
  ];
  return html`<div className="modal-backdrop" onClick=${onClose}>
    <div className="modal" role="dialog" aria-modal="true" aria-labelledby="about-title" onClick=${(e) => e.stopPropagation()}>
      <button className="modal-close" onClick=${onClose} aria-label="إغلاق">×</button>
      <div className="modal-head">
        <h2 id="about-title">من نحن</h2>
        <p className="tagline-dark">نرصد المحتوى الديني المضلِّل قبل أن ينتشر، ونردّ عليه بالدليل الموثّق.</p>
      </div>
      <p>متوسم منصة ذكية تساعد الجهات الدعوية والباحثين والفرق الإعلامية على رصد الادعاءات الدينية
        المتداولة، والتحقق منها من المصادر المعتمدة، وترتيبها حسب خطورتها، وإصدار تقارير موثّقة جاهزة للرد.</p>
      <div className="values">
        ${values.map(([icon, title, text]) => html`<div key=${title} className="about-value">
          <span className="value-icon" aria-hidden="true">${icon}</span>
          <div><b>${title}</b><div className="small muted">${text}</div></div></div>`)}
      </div>
    </div>
  </div>`;
}

/* ================= التطبيق ================= */

// لكل صفحة رابطها: /performance و/history و/sources، والتحقق هو الصفحة الرئيسية /
const PAGES = { verify: "/", performance: "/performance", history: "/history", sources: "/sources" };
const pageFromPath = () => Object.keys(PAGES).find((k) => PAGES[k] === location.pathname.replace(/\/+$/, "")) || "verify";

function App() {
  const [tab, setTabState] = useState(pageFromPath);
  const setTab = (k) => {
    if (location.pathname !== PAGES[k]) history.pushState(null, "", PAGES[k]);
    setTabState(k);
    window.scrollTo(0, 0);
  };
  useEffect(() => {
    const onBack = () => setTabState(pageFromPath());
    window.addEventListener("popstate", onBack);
    return () => window.removeEventListener("popstate", onBack);
  }, []);
  const [info, setInfo] = useState(null);
  const [error, setError] = useState("");
  const [about, setAbout] = useState(false);
  const [keyOpen, setKeyOpen] = useState(false);
  const [hasKey, setHasKey] = useState(() => !!keyStore.get());
  useEffect(() => { getJSON("/api/info").then(setInfo).catch((e) => setError(e.message)); }, []);
  return html`<div>
    <${Header} tab=${tab} setTab=${setTab} mode=${info?.mode} onAbout=${() => setAbout(true)}
      onKey=${() => setKeyOpen(true)} hasKey=${hasKey} />
    ${about && html`<${AboutModal} onClose=${() => setAbout(false)} />`}
    ${keyOpen && html`<${KeyModal} onClose=${() => setKeyOpen(false)} onChange=${setHasKey} />`}
    <main>
      ${error && html`<div className="notice error">تعذّر الاتصال بالخادم: ${error}</div>`}
      ${info && tab === "verify" && html`<${VerifyPage} demos=${info.demos} limits=${info.limits}
          needsKey=${info.mode.needs_user_key && !hasKey} onKey=${() => setKeyOpen(true)} />`}
      ${tab === "performance" && html`<${PerformancePage} />`}
      ${tab === "history" && html`<${HistoryPage} />`}
      ${tab === "sources" && html`<${SourcesPage} />`}
    </main>
    <footer>
      <span className="foot-brand">متوسم</span>
      <span className="foot-sep" aria-hidden="true">·</span>
      <span>نرصد المحتوى الديني المضلِّل قبل أن ينتشر، ونردّ عليه بالدليل الموثّق.</span>
    </footer>
  </div>`;
}

ReactDOM.createRoot(document.getElementById("root")).render(html`<${App} />`);
