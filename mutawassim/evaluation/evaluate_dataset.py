import json
import time

try:
    import torch
    import torch.nn.functional as F
    from sentence_transformers import SentenceTransformer
    HAS_AI_MODEL = True
except ImportError:
    HAS_AI_MODEL = False
    print("تنبيه: مكتبة sentence-transformers غير مثبتة، سيتم استخدام محاكاة مبسطة (MOCK) للتقييم.")

def map_ruling_to_status(ruling: str) -> str:
    """يحول الحكم الشرعي في المصدر إلى حالة تقنية."""
    ruling_lower = ruling.lower() if ruling else ""
    if "موضوع" in ruling_lower or "باطل" in ruling_lower or "لا أصل له" in ruling_lower:
        return "fabricated"
    if "ضعيف" in ruling_lower:
        return "weak"
    if "صحيح" in ruling_lower or "حسن" in ruling_lower or "نص قرآني" in ruling_lower:
        return "confirmed"
    return "needs_review"

def run_evaluation(test_file="mutawassim/data/test_set/test_set.json", sources_file="mutawassim/data/sources/sources.json", threshold=0.4):
    print("جاري تحميل بيانات الاختبار والمصادر...")
    with open(test_file, 'r', encoding='utf-8') as f:
        test_set = json.load(f)
        
    with open(sources_file, 'r', encoding='utf-8') as f:
        sources = json.load(f)

    print(f"تم تحميل {len(test_set)} سجل اختبار، و {len(sources)} مصدر معتمد.")
    
    if HAS_AI_MODEL:
        print("جاري تحميل النموذج لحساب المطابقة (قد يستغرق بضع ثوانٍ)...")
        model = SentenceTransformer('intfloat/multilingual-e5-base')
        source_texts = [s["text"] for s in sources]
        source_embeddings = model.encode(source_texts, convert_to_tensor=True)
    else:
        # إذا لم يكن النموذج مثبتاً، نستخدم المطابقة النصية البسيطة كمحاكاة
        source_texts = [s["text"] for s in sources]

    # مقاييس التقييم
    results = {
        "total": len(test_set),
        "correct": 0,
        "true_positives_fake": 0,  # اكتشف المغلوط وهو فعلاً مغلوط
        "false_positives_fake": 0, # قال مغلوط وهو في الحقيقة سليم أو يحتاج مراجعة
        "false_negatives_fake": 0, # لم يكتشف المغلوط (قال سليم أو needs_review وهو مغلوط)
        "needs_review_correct": 0
    }
    
    print("\nبدء عملية التحقق والمطابقة...\n")
    
    start_time = time.time()
    
    for item in test_set:
        claim = item["claim_text"]
        expected = item["expected_status"]
        predicted = "needs_review" # القيمة الافتراضية إذا لم نجد دليلاً
        
        if HAS_AI_MODEL:
            claim_emb = model.encode(claim, convert_to_tensor=True)
            cosine_scores = F.cosine_similarity(claim_emb.unsqueeze(0), source_embeddings)
            best_score, best_idx = torch.max(cosine_scores, dim=0)
            
            if best_score.item() >= threshold:
                best_source = sources[best_idx.item()]
                predicted = map_ruling_to_status(best_source["ruling"])
        else:
            # محاكاة بسيطة جداً (بحث بكلمات مشتركة)
            best_match = None
            best_overlap = 0
            claim_words = set(claim.split())
            for src in sources:
                src_words = set(src["text"].split())
                overlap = len(claim_words.intersection(src_words))
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_match = src
            if best_overlap >= 2 and best_match: # عتبة بسيطة
                predicted = map_ruling_to_status(best_match["ruling"])
                
        # حساب الأرقام
        if predicted == expected:
            results["correct"] += 1
            if expected in ["fabricated", "weak"]:
                results["true_positives_fake"] += 1
            if expected == "needs_review":
                results["needs_review_correct"] += 1
        else:
            if expected in ["fabricated", "weak"]:
                results["false_negatives_fake"] += 1
            if predicted in ["fabricated", "weak"]:
                results["false_positives_fake"] += 1

    exec_time = time.time() - start_time
    
    # حساب Precision و Recall للكشف عن المحتوى المغلوط
    tp = results["true_positives_fake"]
    fp = results["false_positives_fake"]
    fn = results["false_negatives_fake"]
    
    precision = (tp / (tp + fp)) * 100 if (tp + fp) > 0 else 0.0
    recall = (tp / (tp + fn)) * 100 if (tp + fn) > 0 else 0.0
    accuracy = (results["correct"] / results["total"]) * 100
    
    # طباعة التقرير النهائي
    print("=" * 50)
    print("--- تقرير أداء نظام متوسم (القياس النهائي) ---")
    print("=" * 50)
    print(f"إجمالي العينات المختبرة: {results['total']}")
    print(f"زمن التنفيذ: {exec_time:.2f} ثانية\n")
    print("--- مؤشرات كشف المحتوى المغلوط (Precision / Recall) ---")
    print(f"الدقة (Precision): {precision:.2f}% (إذا قال النظام مغلوط، بنسبة {precision:.1f}% هو فعلاً مغلوط)")
    print(f"الاستدعاء (Recall): {recall:.2f}% (من إجمالي المغلوط، استطاع النظام كشف {recall:.1f}%)")
    print("\n--- مؤشرات المطابقة العامة ---")
    print(f"دقة درجة الحكم الإجمالية (Accuracy): {accuracy:.2f}%")
    print(f"نسبة صحة الإحالة (Needs Review): {(results['needs_review_correct'] / 20 * 100) if 20 else 0:.2f}%")
    print("=" * 50)

if __name__ == "__main__":
    run_evaluation()
