"""CSV statement parser with auto-detected column names."""

from __future__ import annotations
import csv
import os
from datetime import datetime
from pathlib import Path

from src.models.finance import RawStatement, Transaction


_DATE_ALIASES = {"date", "transaction date", "posted date", "trans date", "posting date"}
_DESC_ALIASES = {"description", "memo", "merchant", "payee", "details", "narrative", "particulars", "transaction description"}
_AMOUNT_ALIASES = {"amount", "transaction amount", "trans amount"}
_DEBIT_ALIASES = {"debit", "debit amount", "withdrawal", "withdrawals", "charge"}
_CREDIT_ALIASES = {"credit", "credit amount", "deposit", "deposits", "payment"}
_BALANCE_ALIASES = {"balance", "running balance", "account balance", "ledger balance"}

_DATE_FORMATS = [
    "%m/%d/%Y", "%m/%d/%y",
    "%d/%m/%Y", "%d/%m/%y",
    "%Y-%m-%d",
    "%m-%d-%Y", "%m-%d-%y",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%b %d, %Y",
    "%d %b %Y",
]


def parse_csv_statement(file_path: str, account_name: str | None = None) -> RawStatement:
    """Parse a bank or credit card CSV export into a RawStatement."""
    path = Path(file_path)
    name = account_name or path.stem.replace("_", " ").replace("-", " ").title()

    with open(file_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"CSV file has no headers: {file_path}")

        col_map = _detect_columns(list(reader.fieldnames))
        rows = list(reader)

    transactions: list[Transaction] = []
    for i, row in enumerate(rows):
        try:
            txn = _parse_row(row, col_map, path.name, i)
            if txn is not None:
                transactions.append(txn)
        except Exception:
            continue

    closing_balance: float | None = None
    if transactions and transactions[-1].balance is not None:
        closing_balance = transactions[-1].balance

    opening_balance: float | None = None
    if transactions and transactions[0].balance is not None:
        opening_balance = transactions[0].balance

    return RawStatement(
        file_path=str(path.resolve()),
        account_name=name,
        transactions=transactions,
        opening_balance=opening_balance,
        closing_balance=closing_balance,
    )


def _detect_columns(headers: list[str]) -> dict[str, str | None]:
    """Map logical field names to actual CSV column names."""
    normalized = {h: h.strip().lower() for h in headers}

    def find(aliases: set[str]) -> str | None:
        for col, norm in normalized.items():
            if norm in aliases:
                return col
        for col, norm in normalized.items():
            for alias in aliases:
                if alias in norm or norm in alias:
                    return col
        return None

    return {
        "date": find(_DATE_ALIASES),
        "description": find(_DESC_ALIASES),
        "amount": find(_AMOUNT_ALIASES),
        "debit": find(_DEBIT_ALIASES),
        "credit": find(_CREDIT_ALIASES),
        "balance": find(_BALANCE_ALIASES),
    }


def _parse_row(row: dict, col_map: dict, source_file: str, index: int) -> Transaction | None:
    date_col = col_map.get("date")
    desc_col = col_map.get("description")

    if not date_col or not desc_col:
        return None

    date_raw = row.get(date_col, "").strip()
    description = row.get(desc_col, "").strip()

    if not date_raw or not description:
        return None

    date_str = _parse_date(date_raw)
    if date_str is None:
        return None

    amount = _parse_amount(
        row.get(col_map.get("amount") or "", ""),
        row.get(col_map.get("debit") or "", ""),
        row.get(col_map.get("credit") or "", ""),
    )

    balance: float | None = None
    bal_col = col_map.get("balance")
    if bal_col and row.get(bal_col, "").strip():
        try:
            balance = _clean_float(row[bal_col])
        except (ValueError, TypeError):
            pass

    return Transaction(
        date=date_str,
        description=description,
        amount=amount,
        balance=balance,
        source_file=source_file,
    )


def _parse_amount(amount_raw: str, debit_raw: str, credit_raw: str) -> float:
    """Return signed float: negative = money out, positive = money in."""
    amount_raw = amount_raw.strip()
    debit_raw = debit_raw.strip()
    credit_raw = credit_raw.strip()

    if amount_raw:
        return _clean_float(amount_raw)

    # Separate debit/credit columns
    debit = _clean_float(debit_raw) if debit_raw else 0.0
    credit = _clean_float(credit_raw) if credit_raw else 0.0

    if debit and not credit:
        return -abs(debit)
    if credit and not debit:
        return abs(credit)
    return credit - debit


def _clean_float(value: str) -> float:
    """Strip currency symbols, commas, and parentheses then parse."""
    s = value.strip().replace(",", "").replace("$", "").replace("£", "").replace("€", "")
    negative = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    result = float(s)
    return -abs(result) if negative else result


def _parse_date(value: str) -> str | None:
    """Normalize a date string to YYYY-MM-DD, trying common formats."""
    value = value.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None
