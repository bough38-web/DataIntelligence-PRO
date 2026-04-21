import pandas as pd
import re
from app.utils.common import (
    clean_text, to_numeric_series, to_datetime_series, fill_service_small_from_mid
)

def apply_replacements(df, replacement_rules):
    if df.empty or not replacement_rules:
        return df
    result = df.copy()
    for rule in replacement_rules:
        col = clean_text(rule.get("column"))
        from_val = clean_text(rule.get("from"))
        to_val = clean_text(rule.get("to"))
        if not col or col not in result.columns or from_val == "":
            continue
        s = result[col].astype(str).map(clean_text)
        mask = s.eq(from_val)
        if mask.any():
            result.loc[mask, col] = to_val
    return result

def apply_advanced_conditions(df, conditions):
    result = df
    for cond in conditions:
        col = clean_text(cond.get("column"))
        mode = clean_text(cond.get("mode")).lower() or "eq"
        values = [clean_text(v) for v in cond.get("values", []) if clean_text(v)]

        if not col or col not in result.columns or not values:
            continue

        s = result[col].astype(str).map(clean_text)

        if mode == "eq":
            mask = s.isin(values)
        elif mode == "neq":
            mask = ~s.isin(values)
        elif mode == "contains":
            mask = pd.Series(False, index=result.index)
            for v in values:
                mask = mask | s.str.contains(re.escape(v), na=False, regex=True)
        elif mode == "not_contains":
            mask = pd.Series(True, index=result.index)
            for v in values:
                mask = mask & (~s.str.contains(re.escape(v), na=False, regex=True))
        elif mode == "regex":
            mask = pd.Series(False, index=result.index)
            for pattern in values:
                try:
                    mask = mask | s.str.contains(pattern, na=False, regex=True)
                except re.error:
                    continue
        elif mode in ["gt", "gte", "lt", "lte", "between"]:
            num_s = to_numeric_series(result[col])
            try:
                if mode == "gt":
                    target = float(values[0].replace(",", ""))
                    mask = num_s > target
                elif mode == "gte":
                    target = float(values[0].replace(",", ""))
                    mask = num_s >= target
                elif mode == "lt":
                    target = float(values[0].replace(",", ""))
                    mask = num_s < target
                elif mode == "lte":
                    target = float(values[0].replace(",", ""))
                    mask = num_s <= target
                else:
                    v1 = float(values[0].replace(",", ""))
                    v2 = float(values[1].replace(",", "")) if len(values) > 1 else v1
                    low, high = sorted([v1, v2])
                    mask = num_s.between(low, high, inclusive="both")
            except Exception:
                mask = pd.Series(False, index=result.index)
        elif mode in ["date_eq", "date_before", "date_after", "date_between"]:
            dt_s = to_datetime_series(result[col])
            try:
                if mode == "date_eq":
                    target = pd.to_datetime(values[0], errors="coerce")
                    mask = dt_s.dt.normalize() == target.normalize()
                elif mode == "date_before":
                    target = pd.to_datetime(values[0], errors="coerce")
                    mask = dt_s < target
                elif mode == "date_after":
                    target = pd.to_datetime(values[0], errors="coerce")
                    mask = dt_s > target
                else:
                    d1 = pd.to_datetime(values[0], errors="coerce")
                    d2 = pd.to_datetime(values[1], errors="coerce") if len(values) > 1 else d1
                    low, high = sorted([d1, d2])
                    mask = (dt_s >= low) & (dt_s <= high)
            except Exception:
                mask = pd.Series(False, index=result.index)
        else:
            mask = s.isin(values)

        result = result[mask.fillna(False)]
        if result.empty:
            break
    return result

def apply_sorting(df, sort_specs):
    if df.empty or not sort_specs:
        return df
    by = []
    ascending = []
    for spec in sort_specs:
        col = clean_text(spec.get("column"))
        order = clean_text(spec.get("order")).lower() or "asc"
        if col and col in df.columns:
            by.append(col)
            ascending.append(order != "desc")
    if not by:
        return df
    try:
        return df.sort_values(by=by, ascending=ascending, kind="stable")
    except Exception:
        return df

def apply_dedup(df, dedup_spec):
    if df.empty or not dedup_spec:
        return df
    col = clean_text(dedup_spec.get("column"))
    keep = clean_text(dedup_spec.get("keep")).lower() or "first"
    if col not in df.columns:
        return df
    try:
        return df.drop_duplicates(subset=[col], keep="last" if keep == "last" else "first")
    except Exception:
        return df
