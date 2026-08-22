
import re
from dataclasses import dataclass
from openpyxl.utils import column_index_from_string, get_column_letter


CELL_REF_RE = re.compile(r"(\$?)([A-Z]{1,3})(\$?)(\d+)")


@dataclass
class ParsedCell:
    sheet: str
    row: int
    col: int
    address: str
    formula: str


def _rel_token(is_abs: bool, delta: int) -> str:
    """Render a single row or column offset in R1C1-ish style."""
    if is_abs:
        return "A" 
    if delta == 0:
        return "R0"
    sign = "+" if delta > 0 else ""
    return f"R{sign}{delta}"


def formula_to_signature(formula: str, base_row: int, base_col: int) -> str:

    def replace(match: re.Match) -> str:
        col_abs, col_letters, row_abs, row_digits = match.groups()
        col_idx = column_index_from_string(col_letters)
        row_idx = int(row_digits)

        col_delta = col_idx - base_col
        row_delta = row_idx - base_row

        col_token = _rel_token(bool(col_abs), col_delta)
        row_token = _rel_token(bool(row_abs), row_delta)
        return f"[{row_token},{col_token}]"

    # get rid of the leading "=" if present, uppercase for consistent matching.
    body = formula[1:] if formula.startswith("=") else formula
    return CELL_REF_RE.sub(replace, body.upper())


def example_signature_to_formula(example_formula: str) -> str:
    return example_formula
