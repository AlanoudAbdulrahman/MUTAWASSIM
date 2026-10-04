import json
import urllib.request
from urllib.error import URLError, HTTPError
import concurrent.futures
import time

def verify_url(url, doc_id, retries=2):
    """
    يقوم بفحص الرابط بشكل حقيقي وموثوق للإنتاج (Production-ready).
    يحاول إرسال طلب HEAD أولاً لتوفير الموارد، وإذا قوبل برفض أو خطأ (مثل 405 أو 403)
    يحاول إرسال طلب GET كامل. يتضمن أيضاً نظام إعادة المحاولة (Retries) لتجنب أخطاء الشبكة المؤقتة.
    """
    # استخدام ترويسات متصفح حقيقية لتجنب الحظر من خوادم الحماية (مثل Cloudflare)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ar,en-US;q=0.7,en;q=0.3'
    }
    
    for attempt in range(retries):
        try:
            # 1. محاولة بطلب HEAD أولاً (أسرع وأقل استهلاكاً للبيانات)
            req = urllib.request.Request(url, method='HEAD', headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status < 400:
                    return None  # الرابط صالح ويعمل
                    
        except HTTPError as e:
            # 2. بعض الخوادم تمنع طلبات HEAD وترد بـ 405 أو 403، لذا نجرب GET كخطة بديلة
            if e.code in [403, 405, 503]:
                try:
                    req_get = urllib.request.Request(url, method='GET', headers=headers)
                    with urllib.request.urlopen(req_get, timeout=10) as response_get:
                        if response_get.status < 400:
                            return None # الرابط صالح ويعمل
                except HTTPError as e_get:
                    if attempt == retries - 1:
                        return (doc_id, url, f"خطأ HTTP {e_get.code} ({e_get.reason})")
                except Exception as e_get:
                    if attempt == retries - 1:
                        return (doc_id, url, f"فشل الاتصال: {str(e_get)}")
            else:
                if attempt == retries - 1:
                    return (doc_id, url, f"خطأ HTTP {e.code} ({e.reason})")
        
        except URLError as e:
            if attempt == retries - 1:
                return (doc_id, url, f"فشل الوصول للرابط: {e.reason}")
        except Exception as e:
            if attempt == retries - 1:
                return (doc_id, url, f"خطأ غير متوقع: {str(e)}")
                
        # انتظار ثانية واحدة قبل إعادة المحاولة (في حال وجود ضغط على الخادم)
        time.sleep(1)
        
    return (doc_id, url, "فشل الفحص بعد عدة محاولات")

def check_links(sources_file="mutawassim/data/sources/sources.json"):
    print(f"--- جاري فحص صحة الروابط بشكل حقيقي في ملف {sources_file}... ---\n")
    print("نظام الفحص يعمل الآن بقدرات متقدمة (يستخدم HEAD ثم GET مع إعادة المحاولة).")
    print("قد يستغرق الفحص بعض الوقت بناءً على سرعة الاستجابة من الخوادم...\n")
    
    try:
        with open(sources_file, 'r', encoding='utf-8') as f:
            sources = json.load(f)
    except FileNotFoundError:
        print(f"الملف {sources_file} غير موجود.")
        return
        
    broken_links = []
    
    # فحص متزامن لتسريع العملية (Multithreading) بدون إغراق الخوادم بالطلبات
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(verify_url, src["url"], src["id"]): src for src in sources if "url" in src}
        
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
