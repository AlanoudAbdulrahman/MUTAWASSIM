import re
import torch
import torch.nn.functional as F
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------
# إعداد الطبقة الثانية: نموذج الذكاء الاصطناعي (AI Model)
# ---------------------------------------------------------
try:
    print("جاري تحميل نموذج الذكاء الاصطناعي للفلترة الهجينة...")
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    labels = ["محتوى ديني، أحاديث، فقه، فتاوى إسلامية، قرآن", "محتوى عام، ترفيه، طبخ، أخبار، يوميات"]
    label_embeddings = model.encode(labels, convert_to_tensor=True)
except Exception as e:
    model = None
    print("ملاحظة: نموذج AI لم يُحمل، سيتم الاعتماد على الكلمات المفتاحية فقط.")

# ---------------------------------------------------------
# إعداد الطبقة الأولى: الكلمات المفتاحية (Keywords)
# ---------------------------------------------------------
RELIGIOUS_KEYWORDS = [
    "حديث", "رسول الله", "صلى الله عليه وسلم", "قال الله", "قرآن",
    "آية", "سورة", "صحابي", "فقه", "سنة", "فتاوى", "فتوى", "حكم الشرع",
    "حلال", "حرام", "يجوز", "لا يجوز", "رواه", "أخرجه", "أخرج", "إسناد",
    "بدعة", "وضوء", "عذاب القبر", "يوم القيامة", "صيام", "زكاة"
]

def is_religious(text: str) -> bool:
    """
    يفصل المحتوى الديني باستخدام فلتر متعدد الطبقات (Hybrid Filter):
    - الطبقة 1 (Rule-based): الكلمات المفتاحية الدقيقة (سريعة جداً وتلتقط الحالات الواضحة).
    - الطبقة 2 (AI Semantic): الفهم الدلالي عبر SBERT (لالتقاط السياق المخفي الذي لا يحتوي كلمات مفتاحية).
    """
    text_clean = text.lower()
    
    # --- الطبقة 1: الفلترة بالكلمات المفتاحية ---
    for word in RELIGIOUS_KEYWORDS:
        if re.search(r'\b' + word + r'\b', text_clean):
            return True # تم الالتقاط فوراً بواسطة الكلمات المفتاحية
            
    # --- الطبقة 2: الفلترة بالذكاء الاصطناعي ---
    if model is not None:
        text_embedding = model.encode(text, convert_to_tensor=True)
        cosine_scores = F.cosine_similarity(text_embedding.unsqueeze(0), label_embeddings)
        
        score_religious = cosine_scores[0].item()
        score_general = cosine_scores[1].item()
        
        # إذا كان المعنى السياقي أقرب للمحتوى الديني
        if score_religious > score_general:
            return True
            
    return False

if __name__ == "__main__":
    # أمثلة للاختبار توضح قوة الطبقتين معاً
    examples = [
        ("هل حديث إنما الأعمال بالنيات صحيح؟", True), # ستلتقطها الطبقة 1 لوجود كلمة "حديث"
        ("كيف أسوي مكرونة بالبشاميل؟", False), 
        ("سمعت الشيخ يتكلم عن الصبر والابتلاء والأجر", True), # ستلتقطها الطبقة 2 (لأنها لا تحتوي كلمات مفتاحية صريحة من القائمة)
        ("الجو اليوم مرة حلو نطلع نتمشى؟", False)
    ]
    
    print("\n--- نتائج اختبار الفلتر الهجين (الكلمات + الذكاء الاصطناعي) ---")
    for text, expected in examples:
        result = is_religious(text)
        status = "✅" if result == expected else "❌"
        print(f"{status} | النص: {text[:35]:<35} | النتيجة: {result}")
