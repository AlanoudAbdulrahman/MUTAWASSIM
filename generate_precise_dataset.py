import json
import random

# قائمة البيانات الدقيقة (100 عينة)
# تحتوي على:
# 1. claim: كيف يكتب الناس الادعاء (يذهب لملف الاختبار)
# 2. text: النص الأصلي الصحيح من المصدر (يذهب لملف المصادر)
# 3. ruling: حكم المحدثين (يذهب لملف المصادر)
# 4. status: الحالة المتوقعة للنظام (يذهب لملف الاختبار)
# 5. url: رابط المصدر 
# 6. src: اسم المصدر
# 7. type: نوع المحتوى

dataset = [
    # ---- أحاديث صحيحة (Confirmed) - 30 عينة ----
    {"claim": "هل حديث إنما الأعمال بالنيات صحيح؟", "text": "إنما الأعمال بالنيات، وإنما لكل امرئ ما نوى", "ruling": "صحيح", "status": "confirmed", "url": "https://dorar.net/hadith/1", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "سمعت أن بني الإسلام على خمس، صح؟", "text": "بني الإسلام على خمس: شهادة أن لا إله إلا الله وأن محمدا رسول الله، وإقام الصلاة...", "ruling": "صحيح", "status": "confirmed", "url": "https://dorar.net/hadith/2", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "حديث لا يؤمن أحدكم حتى يحب لأخيه", "text": "لا يؤمن أحدكم حتى يحب لأخيه ما يحب لنفسه", "ruling": "صحيح", "status": "confirmed", "url": "https://dorar.net/hadith/3", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "الدين النصيحة لمن؟", "text": "الدين النصيحة. قلنا: لمن؟ قال: لله ولكتابه ولرسوله ولأئمة المسلمين وعامتهم", "ruling": "صحيح", "status": "confirmed", "url": "https://dorar.net/hadith/4", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "الكلمة الطيبة صدقة صح؟", "text": "والكلمة الطيبة صدقة", "ruling": "صحيح", "status": "confirmed", "url": "https://dorar.net/hadith/5", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "إن الله لا ينظر إلى صوركم وأموالكم", "text": "إن الله لا ينظر إلى صوركم وأموالكم، ولكن ينظر إلى قلوبكم وأعمالكم", "ruling": "صحيح", "status": "confirmed", "url": "https://dorar.net/hadith/6", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "من سلك طريقا يلتمس فيه علما", "text": "من سلك طريقا يلتمس فيه علما سهل الله له به طريقا إلى الجنة", "ruling": "صحيح", "status": "confirmed", "url": "https://dorar.net/hadith/7", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "تبسمك في وجه أخيك لك صدقة", "text": "تبسمك في وجه أخيك لك صدقة", "ruling": "صحيح", "status": "confirmed", "url": "https://dorar.net/hadith/8", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "لا ضرر ولا ضرار في الإسلام", "text": "لا ضرر ولا ضرار", "ruling": "صحيح", "status": "confirmed", "url": "https://dorar.net/hadith/9", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "الظلم ظلمات يوم القيامة", "text": "اتقوا الظلم، فإن الظلم ظلمات يوم القيامة", "ruling": "صحيح", "status": "confirmed", "url": "https://dorar.net/hadith/10", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "المسلم من سلم المسلمون من لسانه", "text": "المسلم من سلم المسلمون من لسانه ويده", "ruling": "صحيح", "status": "confirmed", "url": "https://dorar.net/hadith/11", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "كلكم راع وكلكم مسؤول عن رعيته", "text": "كلكم راع وكلكم مسؤول عن رعيته", "ruling": "صحيح", "status": "confirmed", "url": "https://dorar.net/hadith/12", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "من رأى منكم منكرا فليغيره بيده", "text": "من رأى منكم منكرا فليغيره بيده، فإن لم يستطع فبلسانه...", "ruling": "صحيح", "status": "confirmed", "url": "https://dorar.net/hadith/13", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "الطهور شطر الإيمان", "text": "الطهور شطر الإيمان، والحمد لله تملا الميزان", "ruling": "صحيح", "status": "confirmed", "url": "https://dorar.net/hadith/14", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "آية المنافق ثلاث", "text": "آية المنافق ثلاث: إذا حدث كذب، وإذا وعد أخلف، وإذا اؤتمن خان", "ruling": "صحيح", "status": "confirmed", "url": "https://dorar.net/hadith/15", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "خيركم من تعلم القرآن وعلمه", "text": "خيركم من تعلم القرآن وعلمه", "ruling": "صحيح", "status": "confirmed", "url": "https://dorar.net/hadith/16", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "لا يدخل الجنة من كان في قلبه مثقال ذرة من كبر", "text": "لا يدخل الجنة من كان في قلبه مثقال ذرة من كبر", "ruling": "صحيح", "status": "confirmed", "url": "https://dorar.net/hadith/17", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "من صام رمضان إيمانا واحتسابا غفر له", "text": "من صام رمضان إيمانا واحتسابا غفر له ما تقدم من ذنبه", "ruling": "صحيح", "status": "confirmed", "url": "https://dorar.net/hadith/18", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "العمرة إلى العمرة كفارة لما بينهما", "text": "العمرة إلى العمرة كفارة لما بينهما، والحج المبرور ليس له جزاء إلا الجنة", "ruling": "صحيح", "status": "confirmed", "url": "https://dorar.net/hadith/19", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "من غشنا فليس منا صحيح؟", "text": "من غشنا فليس منا", "ruling": "صحيح", "status": "confirmed", "url": "https://dorar.net/hadith/20", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "المرء مع من أحب", "text": "المرء مع من أحب يوم القيامة", "ruling": "صحيح", "status": "confirmed", "url": "https://dorar.net/hadith/21", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "اتقوا النار ولو بشق تمرة", "text": "اتقوا النار ولو بشق تمرة، فمن لم يجد فبكلمة طيبة", "ruling": "صحيح", "status": "confirmed", "url": "https://dorar.net/hadith/22", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "ما نقصت صدقة من مال", "text": "ما نقصت صدقة من مال، وما زاد الله عبدا بعفو إلا عزا", "ruling": "صحيح", "status": "confirmed", "url": "https://dorar.net/hadith/23", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "الدال على الخير كفاعله", "text": "من دل على خير فله مثل أجر فاعله", "ruling": "صحيح", "status": "confirmed", "url": "https://dorar.net/hadith/24", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "المؤمن القوي خير وأحب إلى الله", "text": "المؤمن القوي خير وأحب إلى الله من المؤمن الضعيف", "ruling": "صحيح", "status": "confirmed", "url": "https://dorar.net/hadith/25", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "حق المسلم على المسلم خمس", "text": "حق المسلم على المسلم خمس: رد السلام، وعيادة المريض...", "ruling": "صحيح", "status": "confirmed", "url": "https://dorar.net/hadith/26", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "الصيام جنة", "text": "الصيام جنة، فإذا كان يوم صوم أحدكم فلا يرفث ولا يصخب", "ruling": "صحيح", "status": "confirmed", "url": "https://dorar.net/hadith/27", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "من يرد الله به خيرا يفقهه في الدين", "text": "من يرد الله به خيرا يفقهه في الدين", "ruling": "صحيح", "status": "confirmed", "url": "https://dorar.net/hadith/28", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "إنما الصبر عند الصدمة الأولى", "text": "إنما الصبر عند الصدمة الأولى", "ruling": "صحيح", "status": "confirmed", "url": "https://dorar.net/hadith/29", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "ليس الشديد بالصرعة", "text": "ليس الشديد بالصرعة، إنما الشديد الذي يملك نفسه عند الغضب", "ruling": "صحيح", "status": "confirmed", "url": "https://dorar.net/hadith/30", "src": "dorar.net/hadith", "type": "hadith"},

    # ---- أحاديث ضعيفة أو موضوعة (Fabricated / Weak) - 30 عينة ----
    {"claim": "اختلاف أمتي رحمة", "text": "اختلاف أمتي رحمة", "ruling": "لا أصل له (موضوع)", "status": "fabricated", "url": "https://dorar.net/fake/1", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "من نام بعد العصر فاختلس عقله", "text": "من نام بعد العصر فاختلس عقله فلا يلومن إلا نفسه", "ruling": "ضعيف جدا", "status": "weak", "url": "https://dorar.net/fake/2", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "النظافة من الإيمان", "text": "النظافة من الإيمان", "ruling": "موضوع", "status": "fabricated", "url": "https://dorar.net/fake/3", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "صوموا تصحوا", "text": "صوموا تصحوا", "ruling": "ضعيف", "status": "weak", "url": "https://dorar.net/fake/4", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "من حج فلم يزرني فقد جفاني", "text": "من حج فلم يزرني فقد جفاني", "ruling": "موضوع", "status": "fabricated", "url": "https://dorar.net/fake/5", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "لو أحسن أحدكم ظنه بحجر لنفعه", "text": "لو أحسن أحدكم ظنه بحجر لنفعه", "ruling": "موضوع", "status": "fabricated", "url": "https://dorar.net/fake/6", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "من عرف نفسه فقد عرف ربه", "text": "من عرف نفسه فقد عرف ربه", "ruling": "لا أصل له", "status": "fabricated", "url": "https://dorar.net/fake/7", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "حب الوطن من الإيمان", "text": "حب الوطن من الإيمان", "ruling": "موضوع", "status": "fabricated", "url": "https://dorar.net/fake/8", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "المعدة بيت الداء", "text": "المعدة بيت الداء والحمية رأس الدواء", "ruling": "ليس بحديث (كلام أطباء)", "status": "fabricated", "url": "https://dorar.net/fake/9", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "أبغض الحلال إلى الله الطلاق", "text": "أبغض الحلال إلى الله الطلاق", "ruling": "ضعيف", "status": "weak", "url": "https://dorar.net/fake/10", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "اطلبوا العلم ولو في الصين", "text": "اطلبوا العلم ولو بالصين", "ruling": "موضوع", "status": "fabricated", "url": "https://dorar.net/fake/11", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "إياكم وخضراء الدمن", "text": "إياكم وخضراء الدمن. قيل: وما خضراء الدمن؟ قال: المرأة الحسناء في المنبت السوء", "ruling": "ضعيف جدا", "status": "weak", "url": "https://dorar.net/fake/12", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "الجنة تحت أقدام الأمهات", "text": "الجنة تحت أقدام الأمهات", "ruling": "موضوع بهذا اللفظ", "status": "fabricated", "url": "https://dorar.net/fake/13", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "خير الأسماء ما حمد وما عبد", "text": "خير الأسماء ما حمد وعبد", "ruling": "لا أصل له", "status": "fabricated", "url": "https://dorar.net/fake/14", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "الدين المعاملة", "text": "الدين المعاملة", "ruling": "لا أصل له", "status": "fabricated", "url": "https://dorar.net/fake/15", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "الساكت عن الحق شيطان أخرس", "text": "الساكت عن الحق شيطان أخرس", "ruling": "ليس بحديث (مقولة لأبي علي الدقاق)", "status": "fabricated", "url": "https://dorar.net/fake/16", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "من لم يهتم بأمر المسلمين فليس منهم", "text": "من لم يهتم بأمر المسلمين فليس منهم", "ruling": "ضعيف", "status": "weak", "url": "https://dorar.net/fake/17", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "لا صلاة لجار المسجد إلا في المسجد", "text": "لا صلاة لجار المسجد إلا في المسجد", "ruling": "ضعيف", "status": "weak", "url": "https://dorar.net/fake/18", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "الأقربون أولى بالمعروف", "text": "الأقربون أولى بالمعروف", "ruling": "ليس بحديث", "status": "fabricated", "url": "https://dorar.net/fake/19", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "من كثر ضحكه قلت هيبته", "text": "من كثر ضحكه قلت هيبته", "ruling": "ليس بحديث (من أقوال عمر بن الخطاب)", "status": "fabricated", "url": "https://dorar.net/fake/20", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "لا تتمارضوا فتمرضوا", "text": "لا تتمارضوا فتمرضوا، ولا تحفروا قبوركم فتموتوا", "ruling": "لا أصل له", "status": "fabricated", "url": "https://dorar.net/fake/21", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "الباذنجان لما أكل له", "text": "الباذنجان لما أكل له", "ruling": "موضوع", "status": "fabricated", "url": "https://dorar.net/fake/22", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "من قلد عالما لقي الله سالما", "text": "من قلد عالما لقي الله سالما", "ruling": "لا أصل له", "status": "fabricated", "url": "https://dorar.net/fake/23", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "تفكر ساعة خير من عبادة سنة", "text": "تفكر ساعة خير من عبادة ستين سنة", "ruling": "موضوع", "status": "fabricated", "url": "https://dorar.net/fake/24", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "أنا مدينة العلم وعلي بابها", "text": "أنا مدينة العلم وعلي بابها", "ruling": "موضوع", "status": "fabricated", "url": "https://dorar.net/fake/25", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "العمل عبادة", "text": "العمل عبادة", "ruling": "ليس بحديث", "status": "fabricated", "url": "https://dorar.net/fake/26", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "كما تدين تدان", "text": "البر لا يبلى، والإثم لا ينسى، والديان لا يموت، فكن كما شئت، كما تدين تدان", "ruling": "ضعيف", "status": "weak", "url": "https://dorar.net/fake/27", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "النظافة نصف الدين", "text": "النظافة نصف الدين", "ruling": "موضوع", "status": "fabricated", "url": "https://dorar.net/fake/28", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "من تعلم لغة قوم أمن مكرهم", "text": "من تعلم لغة قوم أمن مكرهم", "ruling": "لا أصل له", "status": "fabricated", "url": "https://dorar.net/fake/29", "src": "dorar.net/hadith", "type": "hadith"},
    {"claim": "الضرورات تبيح المحظورات كحديث", "text": "الضرورات تبيح المحظورات", "ruling": "ليس بحديث بل قاعدة فقهية", "status": "fabricated", "url": "https://dorar.net/fake/30", "src": "dorar.net/hadith", "type": "hadith"},

    # ---- نصوص قرآنية (Quran) - 20 عينة ----
    {"claim": "قوله تعالى إياك نعبد وإياك نستعين", "text": "إياك نعبد وإياك نستعين", "ruling": "نص قرآني (سورة الفاتحة)", "status": "confirmed", "url": "https://quranpedia.net/surah/1/5", "src": "quranpedia.net", "type": "quran"},
    {"claim": "إن مع العسر يسرا", "text": "إن مع العسر يسرا", "ruling": "نص قرآني (سورة الشرح)", "status": "confirmed", "url": "https://quranpedia.net/surah/94/6", "src": "quranpedia.net", "type": "quran"},
    {"claim": "قل هو الله أحد", "text": "قل هو الله أحد", "ruling": "نص قرآني (سورة الإخلاص)", "status": "confirmed", "url": "https://quranpedia.net/surah/112/1", "src": "quranpedia.net", "type": "quran"},
    {"claim": "وبالوالدين إحسانا", "text": "وقضى ربك ألا تعبدوا إلا إياه وبالوالدين إحسانا", "ruling": "نص قرآني (سورة الإسراء)", "status": "confirmed", "url": "https://quranpedia.net/surah/17/23", "src": "quranpedia.net", "type": "quran"},
    {"claim": "إن الله مع الصابرين", "text": "يا أيها الذين آمنوا استعينوا بالصبر والصلاة إن الله مع الصابرين", "ruling": "نص قرآني (سورة البقرة)", "status": "confirmed", "url": "https://quranpedia.net/surah/2/153", "src": "quranpedia.net", "type": "quran"},
    {"claim": "فمن يعمل مثقال ذرة خيرا يره", "text": "فمن يعمل مثقال ذرة خيرا يره", "ruling": "نص قرآني (سورة الزلزلة)", "status": "confirmed", "url": "https://quranpedia.net/surah/99/7", "src": "quranpedia.net", "type": "quran"},
    {"claim": "وما خلقت الجن والإنس إلا ليعبدون", "text": "وما خلقت الجن والإنس إلا ليعبدون", "ruling": "نص قرآني (سورة الذاريات)", "status": "confirmed", "url": "https://quranpedia.net/surah/51/56", "src": "quranpedia.net", "type": "quran"},
    {"claim": "ولا تقربوا الزنا", "text": "ولا تقربوا الزنا إنه كان فاحشة وساء سبيلا", "ruling": "نص قرآني (سورة الإسراء)", "status": "confirmed", "url": "https://quranpedia.net/surah/17/32", "src": "quranpedia.net", "type": "quran"},
    {"claim": "إن الدين عند الله الإسلام", "text": "إن الدين عند الله الإسلام", "ruling": "نص قرآني (سورة آل عمران)", "status": "confirmed", "url": "https://quranpedia.net/surah/3/19", "src": "quranpedia.net", "type": "quran"},
    {"claim": "اقرأ باسم ربك الذي خلق", "text": "اقرأ باسم ربك الذي خلق", "ruling": "نص قرآني (سورة العلق)", "status": "confirmed", "url": "https://quranpedia.net/surah/96/1", "src": "quranpedia.net", "type": "quran"},
    {"claim": "إن الله وملائكته يصلون على النبي", "text": "إن الله وملائكته يصلون على النبي يا أيها الذين آمنوا صلوا عليه وسلموا تسليما", "ruling": "نص قرآني (سورة الأحزاب)", "status": "confirmed", "url": "https://quranpedia.net/surah/33/56", "src": "quranpedia.net", "type": "quran"},
    {"claim": "لا يكلف الله نفسا إلا وسعها", "text": "لا يكلف الله نفسا إلا وسعها لها ما كسبت وعليها ما اكتسبت", "ruling": "نص قرآني (سورة البقرة)", "status": "confirmed", "url": "https://quranpedia.net/surah/2/286", "src": "quranpedia.net", "type": "quran"},
    {"claim": "ويقولون متى هذا الوعد", "text": "ويقولون متى هذا الوعد إن كنتم صادقين", "ruling": "نص قرآني (سورة الملك وغيرها)", "status": "confirmed", "url": "https://quranpedia.net/surah/67/25", "src": "quranpedia.net", "type": "quran"},
    {"claim": "كل نفس ذائقة الموت", "text": "كل نفس ذائقة الموت وإنما توفون أجوركم يوم القيامة", "ruling": "نص قرآني (سورة آل عمران)", "status": "confirmed", "url": "https://quranpedia.net/surah/3/185", "src": "quranpedia.net", "type": "quran"},
    {"claim": "وإذا سألك عبادي عني فإني قريب", "text": "وإذا سألك عبادي عني فإني قريب أجيب دعوة الداع إذا دعان", "ruling": "نص قرآني (سورة البقرة)", "status": "confirmed", "url": "https://quranpedia.net/surah/2/186", "src": "quranpedia.net", "type": "quran"},
    {"claim": "يا أيها الذين آمنوا اتقوا الله وقولوا قولا سديدا", "text": "يا أيها الذين آمنوا اتقوا الله وقولوا قولا سديدا", "ruling": "نص قرآني (سورة الأحزاب)", "status": "confirmed", "url": "https://quranpedia.net/surah/33/70", "src": "quranpedia.net", "type": "quran"},
    {"claim": "ألا بذكر الله تطمئن القلوب", "text": "الذين آمنوا وتطمئن قلوبهم بذكر الله ألا بذكر الله تطمئن القلوب", "ruling": "نص قرآني (سورة الرعد)", "status": "confirmed", "url": "https://quranpedia.net/surah/13/28", "src": "quranpedia.net", "type": "quran"},
    {"claim": "ومن يتق الله يجعل له مخرجا", "text": "ومن يتق الله يجعل له مخرجا ويرزقه من حيث لا يحتسب", "ruling": "نص قرآني (سورة الطلاق)", "status": "confirmed", "url": "https://quranpedia.net/surah/65/2", "src": "quranpedia.net", "type": "quran"},
    {"claim": "إن الصلاة تنهى عن الفحشاء والمنكر", "text": "وأقم الصلاة إن الصلاة تنهى عن الفحشاء والمنكر", "ruling": "نص قرآني (سورة العنكبوت)", "status": "confirmed", "url": "https://quranpedia.net/surah/29/45", "src": "quranpedia.net", "type": "quran"},
    {"claim": "ولسوف يعطيك ربك فترضى", "text": "ولسوف يعطيك ربك فترضى", "ruling": "نص قرآني (سورة الضحى)", "status": "confirmed", "url": "https://quranpedia.net/surah/93/5", "src": "quranpedia.net", "type": "quran"},

    # ---- أسئلة وأحكام غير موجودة (Needs Review / Out of Scope) - 20 عينة ----
    {"claim": "هل الاحتفال بالمولد النبوي جائز؟", "status": "needs_review"},
    {"claim": "ما حكم الاستثمار في البيتكوين والعملات الرقمية؟", "status": "needs_review"},
    {"claim": "هل تارك الصلاة كافر؟", "status": "needs_review"},
    {"claim": "حكم المقاطعة للمنتجات الأجنبية؟", "status": "needs_review"},
    {"claim": "ما حكم زراعة الشعر للرجال؟", "status": "needs_review"},
    {"claim": "هل يجوز سفر المرأة بدون محرم بالطائرة؟", "status": "needs_review"},
    {"claim": "ما حكم العمل في البنوك والمصارف الحالية؟", "status": "needs_review"},
    {"claim": "هل المطر الخفيف يبيح جمع الصلاة؟", "status": "needs_review"},
    {"claim": "ما حكم استخدام البطاقات الائتمانية؟", "status": "needs_review"},
    {"claim": "حكم التصوير بالهاتف الجوال؟", "status": "needs_review"},
    {"claim": "هل التدخين مكروه أم محرم؟", "status": "needs_review"},
    {"claim": "رأيت في المنام سقوط أسناني، ما التفسير؟", "status": "needs_review"},
    {"claim": "ما حكم التداول بالهامش في الأسهم؟", "status": "needs_review"},
    {"claim": "هل قطرة العين تفطر الصائم؟", "status": "needs_review"},
    {"claim": "حكم بخاخ الربو في نهار رمضان؟", "status": "needs_review"},
    {"claim": "هل النقاب فرض أم فضل؟", "status": "needs_review"},
    {"claim": "ما حكم الأناشيد بوجود مؤثرات صوتية؟", "status": "needs_review"},
    {"claim": "هل يجوز مس المصحف للمرأة الحائض؟", "status": "needs_review"},
    {"claim": "حكم دفع الرشوة لتخليص معاملة معطلة ظلما؟", "status": "needs_review"},
    {"claim": "ما حكم الاستماع للموسيقى؟", "status": "needs_review"}
]

def main():
    test_set = []
    sources = []
    
    # تفريغ البيانات إلى ملفين: واحد للاختبار وآخر لقاعدة المعرفة
    for i, item in enumerate(dataset):
        # 1. إعداد عينة الاختبار
        test_set.append({
            "claim_text": item["claim"],
            "expected_status": item["status"]
        })
        
        # 2. إعداد المصدر (إن وجد النص) - الأسئلة الفقهية لا توضع في المصادر هنا لأن النظام يجب أن لا يجدها فيرد needs_review
        if "text" in item:
            sources.append({
                "id": f"s{i+1}",
                "text": item["text"],
                "url": item["url"],
                "ruling": item["ruling"],
                "source": item["src"],
                "type": item["type"]
            })
            
    # خلط ملف الاختبار
    random.shuffle(test_set)
    
    # حفظ الملفات
    with open("test_set.json", "w", encoding="utf-8") as f:
        json.dump(test_set, f, ensure_ascii=False, indent=2)
        
    with open("sources.json", "w", encoding="utf-8") as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)
        
    print(f"Generated {len(test_set)} records in test_set.json")
    print(f"Generated {len(sources)} verified sources in sources.json")

if __name__ == "__main__":
    main()
