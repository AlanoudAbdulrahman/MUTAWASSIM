import json
import urllib.request
from urllib.error import URLError, HTTPError
import concurrent.futures

def verify_url(url, doc_id):
    """
    يقوم بإرسال طلب HTTP من نوع HEAD لفحص حالة الرابط دون تحميل محتواه كاملاً.
    """
    # نستخدم User-Agent لتجنب حظر بعض المواقع للسكربتات
    req = urllib.request.Request(
        url, 
        method='HEAD', 
        headers={'User-Agent': 'Mozilla/5.0'}
    )
    
    try:
        urllib.request.urlopen(req, timeout=5)
        return None  # الرابط صالح
    except HTTPError as e:
        if e.code == 404:
            return (doc_id, url, f"مكسور (404 Not Found)")
        elif e.code in [403, 401]:
            # بعض المواقع تحظر روبوتات الفحص (403 Forbidden)، لذا نعتبرها صالحة مبدئياً
            return None
        return (doc_id, url, f"خطأ HTTP {e.code}")
    except URLError as e:
        # إذا كان الرابط الوهمي الذي أنشأناه بغرض الاختبار (fake)
        if "fake" in url:
             return (doc_id, url, "رابط وهمي/مكسور (كما هو متوقع للاختبار)")
        return (doc_id, url, "فشل الاتصال بالموقع")
    except Exception as e:
        return (doc_id, url, f"خطأ غير معروف: {str(e)}")

def check_links(sources_file="sources.json"):
    print(f"--- جاري فحص صحة روابط الإسناد في ملف {sources_file}... ---\n")
    print("قد يستغرق الفحص دقيقة واحدة بناءً على عدد الروابط وسرعة الإنترنت.\n")
    
    try:
        with open(sources_file, 'r', encoding='utf-8') as f:
            sources = json.load(f)
    except FileNotFoundError:
        print(f"الملف {sources_file} غير موجود.")
        return
        
    broken_links = []
    
    # نستخدم ThreadPoolExecutor لتسريع الفحص بفحص عدة روابط في نفس الوقت
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # إنشاء المهام
        futures = {executor.submit(verify_url, src["url"], src["id"]): src for src in sources if "url" in src}
        
        # جمع النتائج
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                broken_links.append(result)
                
    if broken_links:
        print(f"تم اكتشاف {len(broken_links)} رابط مكسور أو غير متاح:")
        for doc_id, url, error in broken_links:
            print(f" - المرجع [{doc_id}]: {url} ({error})")
    else:
        print("جميع الروابط صالحة وتعمل بشكل سليم!")

if __name__ == "__main__":
    check_links()
