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
- بک‌لاگ تسک سطح-پرتفولیو: آیتم‌های `mizan-legal-copilot` در `TASKS.md` (P1-11 CI/tests/upload guard، P2-8 license، P3-6 polish)
