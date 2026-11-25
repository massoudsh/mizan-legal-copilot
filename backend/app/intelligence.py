"""Deterministic contract intelligence: playbook checks, redlines, Persian field extraction."""

import re

from app.schemas import ClauseDeviation, ExtractedField, RedlineSuggestion, RiskLevel

_DIGIT_TRANSLATION = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "012345678901234567890123456789"[:20])
_SEVERITY_ORDER = {RiskLevel.LOW: 5, RiskLevel.MEDIUM: 10, RiskLevel.HIGH: 20, RiskLevel.CRITICAL: 30}


def normalize(text: str) -> str:
    """Fold Persian/Arabic digits and separators so matching ignores typography."""
    text = text.translate(_DIGIT_TRANSLATION).replace("‌", " ").replace("‏", "").replace("‎", "")
    return re.sub(r"[ \t]+", " ", text).casefold()


def _lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _find_line(lines: list[str], terms: list[str]) -> tuple[int, str] | None:
    normalized_terms = [normalize(term) for term in terms if term.strip()]
    for number, line in enumerate(lines, start=1):
        haystack = normalize(line)
        if any(term in haystack for term in normalized_terms):
            return number, line
    return None


def check_playbook(text: str, rules) -> tuple[list[ClauseDeviation], list[RedlineSuggestion]]:
    """Compare a contract against tenant rules; return deviations and first-pass redlines."""
    lines, deviations, redlines = _lines(text), [], []
    for rule in rules:
        found = _find_line(lines, rule.forbidden_terms) if rule.forbidden_terms else None
        if found:
            line_number, evidence = found
            deviations.append(ClauseDeviation(
                clause_key=rule.clause_key, label=rule.label, kind="forbidden",
                severity=rule.severity, line=line_number, evidence=evidence,
                message=f"«{rule.label}» شامل عبارتی است که ترجیح سازمان نیست.",
            ))
            redlines.append(RedlineSuggestion(
                clause_key=rule.clause_key, label=rule.label,
                action="replace" if rule.preferred_text else "delete", line=line_number,
                original=evidence, replacement=rule.preferred_text or "",
                reason="جایگزینی عبارت نامطلوب با موضع ترجیحی سازمان.",
            ))
            continue
        if not rule.required_terms:
            continue
        if _find_line(lines, rule.required_terms) is None:
            deviations.append(ClauseDeviation(
                clause_key=rule.clause_key, label=rule.label, kind="missing",
                severity=rule.severity, line=None, evidence=None,
                message=f"بند «{rule.label}» در قرارداد پیدا نشد.",
            ))
            if rule.preferred_text:
                redlines.append(RedlineSuggestion(
                    clause_key=rule.clause_key, label=rule.label, action="insert", line=None,
                    original=None, replacement=rule.preferred_text,
                    reason="افزودن بند لازم بر اساس playbook سازمان.",
                ))
    return deviations, redlines


def risk_score(deviations: list[ClauseDeviation]) -> int:
    penalty = sum(_SEVERITY_ORDER[item.severity] for item in deviations)
    return max(0, 100 - penalty)


_AMOUNT = re.compile(r"([\d][\d,٬.]*)\s*(هزار|میلیون|میلیارد)?\s*(ریال|تومان|دلار|یورو)")
_DATE = re.compile(r"\b(1[34]\d{2}|20\d{2})[/.:-](0?[1-9]|1[0-2])[/.:-](0?[1-9]|[12]\d|3[01])\b")
_NATIONAL_ID = re.compile(r"(?<!\d)\d{10}(?!\d)")
_CONTRACT_NO = re.compile(r"(?:شماره|شمارهٔ)\s*(?:قرارداد|قرارداد:|سند)?\s*[:؛]?\s*([0-9]{2,}(?:[-/][0-9]+)*)")
_DURATION = re.compile(r"(\d{1,2}|یک|دو|سه|شش)\s*(ماه|ماهه|سال|روز)")
_AMOUNT_MULTIPLIERS = {"هزار": 1_000, "میلیون": 1_000_000, "میلیارد": 1_000_000_000}
_PARTY_LABELS = ("طرف اول", "طرف دوم", "کارفرما", "پیمانکار", "خریدار", "فروشنده", "کارمند", "کارآفرین")
_GOVERNING = ("قانون حاکم", "قانون قابل اعمال", "قوانین ایران", "قوانین جمهوری اسلامی")
_EXPIRY = ("تاریخ پایان", "انقضا", "تمدید", "پایان مدت")


def _field(key: str, label: str, value: str, confidence: float, line: int) -> ExtractedField:
    return ExtractedField(key=key, label=label, value=value.strip(), confidence=round(confidence, 2), line=line)


def extract_fields(text: str) -> list[ExtractedField]:
    """Extract Persian contract fields with explicit confidence; never invents values."""
    fields: list[ExtractedField] = []
    lines = _lines(text)
    normalized = normalize(text)

    for label in _PARTY_LABELS:
        match = _find_line(lines, [label + ":"])
        if match:
            line_number, line = match
            value = line.split(":", 1)[1].strip() if ":" in line else line
            if value:
                fields.append(_field("party", label, value, 0.8, line_number))

    for line_number, line in enumerate(lines, start=1):
        normalized_line = normalize(line)
        if not any(word in normalized_line for word in ("مبلغ", "مبلغ کل", "جمع مبلغ", "قیمت")):
            continue
        match = _AMOUNT.search(normalized_line)
        if match:
            number = float(match.group(1).replace(",", "").replace("٬", ""))
            amount = int(number * _AMOUNT_MULTIPLIERS.get(match.group(2) or "", 1))
            fields.append(_field("amount", "مبلغ قرارداد", f"{amount} {match.group(3)}", 0.75, line_number))
            break

    for line_number, line in enumerate(lines, start=1):
        dates = list(_DATE.finditer(normalize(line)))
        if not dates:
            continue
        value = dates[0].group(0)
        is_expiry = any(word in normalize(line) for word in _EXPIRY)
        fields.append(_field("end_date" if is_expiry else "date", "تاریخ پایان" if is_expiry else "تاریخ", value, 0.85, line_number))
        if is_expiry:
            break

    for line_number, line in enumerate(lines, start=1):
        if "کد ملی" in normalize(line):
            match = _NATIONAL_ID.search(normalize(line))
            if match:
                fields.append(_field("national_id", "کد ملی", match.group(0), 0.95, line_number))
                break

    contract_match = _CONTRACT_NO.search(normalized)
    if contract_match:
        line = next((index for index, item in enumerate(lines, start=1) if normalize(contract_match.group(1)) in normalize(item)), 1)
        fields.append(_field("contract_number", "شمارهٔ قرارداد", contract_match.group(1), 0.7, line))

    duration = _DURATION.search(normalized)
    if duration:
        fields.append(_field("duration", "مدت قرارداد", duration.group(0), 0.7, 1))

    governing = _find_line(lines, list(_GOVERNING))
    if governing:
        fields.append(_field("governing_law", "قانون حاکم", governing[1], 0.8, governing[0]))

    return fields[:20]
