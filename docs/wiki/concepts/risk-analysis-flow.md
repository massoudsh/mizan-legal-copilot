# Concept: جریان تحلیل ریسک (MVP)

> مسیر کامل یک درخواست از آپلود تا خروجی ریسک.

## جریان
```
کاربر POST /analyze (فایل + فیلدهای اختیاری پروفایل سازمان)
  → main.py: فایل خوانده می‌شود (await file.read()) — چک خالی‌بودن
  → document_parser.extract_text() بر اساس پسوند dispatch می‌کند
  → متن خالی؟ → 422 (احتمالاً اسکن بدون OCR)
  → OrgProfile از فرم ساخته می‌شود
  → risk_engine.analyze_document(document_name, text, org_profile)
      → LLMClient.is_configured()?
          بله → پرامپت ساخته می‌شود (متن تا ۱۲۰۰۰ کاراکتر) → LLM فراخوانی می‌شود
                 موفق → RiskAnalysisResult(analysis_mode="llm")
                 خطا/JSON نامعتبر → fallback
          خیر → fallback مستقیم
      → fallback: ۵ الگوی regex روی متن اجرا می‌شود → RiskAnalysisResult(analysis_mode="rule_fallback")
  → پاسخ JSON به کاربر
```

## وابستگی‌ها
- [[entities/api-main]]
- [[entities/document-parser]]
- [[entities/risk-engine]]
- [[entities/llm-client]]
- [[entities/schemas]]

## تصمیم‌ها
- تحلیل **همیشه** یک نتیجه برمی‌گرداند (هرگز 500 برای شکست LLM) — fallback تضمین‌شده است.
- سطح ریسک نهایی fallback = بالاترین سطح بین findings یافته‌شده (نه میانگین).

## فازهای آینده (طبق PRD/ARCHITECTURE، هنوز پیاده‌سازی نشده)
- پایگاه دانش قانونی با RAG (retrieval قبل از پرامپت LLM)
- Decision Log برای مستندسازی تصمیم‌های حساس
- Escalation workflow واقعی (فعلاً فقط فیلد `requires_human_advisor` روی هر finding است، بدون routing عملیاتی)
