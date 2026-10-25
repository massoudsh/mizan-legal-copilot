# Overview — میزان (Mizan)

میزان یک پلتفرم tenant-scoped برای تحلیل ریسک حقوقی و رگولاتوری سازمان‌های ایرانی است. جریان اصلی شامل تحلیل سند، مقررات نسخه‌دار، پروفایل سازمان، دفتر تصمیم، تعهدات و داشبورد مدیریتی است.

## قابلیت‌های محصول
- تحلیل PDF/DOCX/TXT/تصویر با OCR اختیاری و fallback قاعده‌محور.
- RBAC با نقش‌های owner/admin/analyst/viewer و جداسازی دادهٔ tenant.
- مقایسهٔ نسخه‌های قرارداد، workflow بررسی انسانی و audit export.
- رصد feedهای allowlist‌شدهٔ مقررات با تاریخ اجرا، trust score و هشدار تغییر.
- connectorهای HR/مالی با secret reference و schema production PostgreSQL/pgvector/RLS.

منبع context اجرایی در `.noqte/wiki/` نگه‌داری می‌شود؛ این پوشه نسخهٔ مستنداتی repository است و باید با همان قراردادها همگام بماند.
