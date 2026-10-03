# Index

## Overview
- [[overview]] — یک‌نگاه کلی پروژه، وضعیت فعلی، نقاط ریسک فنی

## Entities (۶ صفحه)
- [[entities/api-main]] — FastAPI app، endpoint های `/health` و `/analyze`
- [[entities/document-parser]] — استخراج متن از PDF/DOCX/TXT/MD
- [[entities/llm-client]] — کلاینت سبک LLM، قابل‌تعویض از طریق env
- [[entities/risk-engine]] — پرامپت‌سازی + fallback قاعده‌محور
- [[entities/schemas]] — مدل‌های Pydantic ورودی/خروجی
- [[entities/landing-page]] — صفحه معرفی محصول (استاتیک RTL)

## Concepts (۲ صفحه)
- [[concepts/risk-analysis-flow]] — جریان کامل آپلود تا خروجی ریسک
- [[concepts/llm-fallback-pattern]] — چرا و چطور MVP بدون کلید API کار می‌کند

## منابع بیرونی
- `docs/PRD.md` — سند محصول کامل (پرسونا‌ها، مدل ریسک، KPI، نقشه‌راه)
- `docs/ARCHITECTURE.md` — معماری فنی کامل (شامل فازهای آینده: RAG، Decision Log، Dashboard)
- بک‌لاگ تسک سطح-پرتفولیو: آیتم‌های `mizan-legal-copilot` در `TASKS.md` — P1-11 و P2-8 و بخش عمدهٔ P3-6 انجام شد؛ باقی‌مانده: جایگزینی ایمیل placeholder در لندینگ (منتظر تصمیم صاحب پروژه)
- بک‌لاگ آینده به‌صورت ۱۰ ایشوی GitHub ثبت شد: `github.com/massoudsh/mizan-legal-copilot/issues` (#1 CI blocked، #2 mailto، #3–#5 roadmap v1، #6–#8 roadmap v2، #9 OCR، #10 rate limiting)
