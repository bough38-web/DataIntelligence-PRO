import os
import re
import json
import tempfile
import uuid
import shutil
from pathlib import Path
import pandas as pd

def clean_text(x):
    if x is None:
        return ""
    try:
        if pd.isna(x):
            return ""
    except Exception:
        pass
    s = str(x)
    s = s.replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def make_unique_columns(cols):
    seen = {}
    out = []
    for i, c in enumerate(cols):
        name = clean_text(c) or f"컬럼{i+1}"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        out.append(name)
    return out

def header_score(row):
    score = 0.0
    for v in row:
        t = clean_text(v)
        if not t:
            continue
        if re.fullmatch(r"\d+(\.\d+)?", t):
            score += 0.2
        else:
            score += 1.0
    return score

def detect_header_index_from_rows(rows, max_scan=30):
    best_idx = 0
    best_score = -1.0
    for i, row in enumerate(rows[:max_scan]):
        score = header_score(row)
        if score > best_score:
            best_score = score
            best_idx = i
    return best_idx

def normalize_columns_from_header_row(header_row):
    return make_unique_columns(header_row)

def choose_header_index(rows, header_row_idx=None, max_scan=30):
    if not rows:
        return 0
    if header_row_idx is None:
        return detect_header_index_from_rows(rows, max_scan=max_scan)
    try:
        idx = int(header_row_idx)
    except Exception:
        idx = 0
    if idx < 0:
        idx = 0
    if idx >= len(rows):
        idx = len(rows) - 1
    return idx

def trim_empty_columns_df(df):
    if df.empty:
        return df
    keep_cols = []
    for c in df.columns:
        s = (
            df[c]
            .fillna("")
            .astype(str)
            .str.replace("\xa0", " ", regex=False)
            .str.strip()
        )
        if s.ne("").any():
            keep_cols.append(c)
    return df[keep_cols]

def fill_service_small_from_mid(df):
    cols = list(df.columns)
    mid_col = next((c for c in cols if "서비스" in str(c) and "중" in str(c)), None)
    small_col = next((c for c in cols if "서비스" in str(c) and "소" in str(c)), None)
    if mid_col is None or small_col is None:
        return df
    mid_s = df[mid_col].astype(str).map(clean_text)
    small_s = df[small_col].astype(str).map(clean_text)
    blank_mask = small_s.eq("") | small_s.str.lower().eq("nan")
    df.loc[blank_mask, small_col] = mid_s[blank_mask]
    return df

def is_html_content(file_path):
    try:
        with open(file_path, "rb") as f:
            raw = f.read(65536).lower()
        markers = [
            b"<html", b"<table", b"<!doctype html", b"<head", b"<body",
            b"<meta", b"<tr", b"<td", b"<th"
        ]
        return any(m in raw for m in markers)
    except Exception:
        return False

def is_file_locked(file_path):
    if not os.path.exists(file_path):
        return False
    try:
        # On Windows, opening in 'ab' or 'r+' with exclusive access fails if open in Excel
        f = open(file_path, "r+", encoding="utf-8")
        f.close()
        return False
    except Exception:
        # If open for writing (r+) fails, it's likely locked
        return True

def make_temp_copy(file_path):
    temp_dir = os.path.join(tempfile.gettempdir(), "gui_data_extractor_temp")
    os.makedirs(temp_dir, exist_ok=True)
    ext = os.path.splitext(file_path)[1].lower()
    temp_name = f"{uuid.uuid4().hex}{ext}"
    temp_path = os.path.join(temp_dir, temp_name)
    shutil.copy2(file_path, temp_path)
    return temp_path

def get_readable_file_path(file_path):
    if is_file_locked(file_path):
        return make_temp_copy(file_path)
    return file_path

def to_numeric_series(s):
    s2 = (
        s.astype(str)
        .map(clean_text)
        .str.replace(",", "", regex=False)
        .str.replace("원", "", regex=False)
        .str.replace("%", "", regex=False)
    )
    return pd.to_numeric(s2, errors="coerce")

def to_datetime_series(s):
    s2 = s.astype(str).map(clean_text)
    return pd.to_datetime(s2, errors="coerce")

def preview_text(df, rows=10):
    if df is None or df.empty:
        return "(데이터 없음)"
    return df.head(rows).fillna("").to_string(index=False)

def raw_rows_preview_text(rows, max_rows=20):
    if not rows:
        return "(원본 행 데이터 없음)"
    clipped = rows[:max_rows]
    width = max((len(r) for r in clipped), default=0)
    normalized = []
    for r in clipped:
        vals = list(r)
        if len(vals) < width:
            vals += [None] * (width - len(vals))
        normalized.append(vals)
    df = pd.DataFrame(normalized)
    return df.fillna("").to_string(index=False, header=False)

class JsonStore:
    def __init__(self, filename, default=None):
        self.path = Path(filename)
        self.default = default if default is not None else []

    def load(self):
        try:
            if not self.path.exists():
                return json.loads(json.dumps(self.default, ensure_ascii=False))
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return json.loads(json.dumps(self.default, ensure_ascii=False))

    def save(self, data):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def dataframe_from_rows_with_header(rows, header_row_idx=None, scan_rows=200):
    if not rows:
        return pd.DataFrame()
    trimmed_rows = _trim_rows_to_used_content(rows)
    if not trimmed_rows:
        return pd.DataFrame()
    header_idx = choose_header_index(trimmed_rows, header_row_idx=header_row_idx, max_scan=scan_rows)
    header = normalize_columns_from_header_row(trimmed_rows[header_idx])
    body_rows = trimmed_rows[header_idx + 1:]
    normalized = []
    for r in body_rows:
        vals = list(r)
        if len(vals) < len(header):
            vals += [None] * (len(header) - len(vals))
        elif len(vals) > len(header):
            vals = vals[:len(header)]
        normalized.append(vals)
    body = pd.DataFrame(normalized, columns=header)
    return trim_empty_columns_df(body)

def _normalize_excel_value_matrix(values):
    if values is None:
        return []
    if not isinstance(values, (list, tuple)):
        return [[values]]
    rows = []
    for row in values:
        if isinstance(row, (list, tuple)):
            rows.append(list(row))
        else:
            rows.append([row])
    return rows

def _trim_rows_to_used_content(rows):
    if not rows:
        return rows
    max_len = 0
    for r in rows:
        if not r: continue
        last_nonempty = 0
        for idx, v in enumerate(r, start=1):
            if clean_text(v):
                last_nonempty = idx
        max_len = max(max_len, last_nonempty)
    if max_len <= 0:
        return rows
    return [list(r[:max_len]) for r in rows]
