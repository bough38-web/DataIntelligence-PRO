import os
import traceback
import pandas as pd
from PySide6.QtCore import QThread, Signal
from app.utils.common import get_readable_file_path, is_file_locked
from app.core.handlers import load_file_to_df, load_open_excel_sheet_df
from app.core.processors import (
    apply_replacements, apply_advanced_conditions, fill_service_small_from_mid,
    apply_sorting, apply_dedup
)

def export_from_df(df, output_path, selected_columns=None, conditions=None, 
                    replacement_rules=None, fill_service=True, sort_specs=None, 
                    dedup_spec=None):
    if replacement_rules:
        df = apply_replacements(df, replacement_rules)
    if conditions:
        df = apply_advanced_conditions(df, conditions)
    if fill_service:
        df = fill_service_small_from_mid(df)
    if selected_columns:
        keep_cols = [c for c in selected_columns if c in df.columns]
        df = df[keep_cols]
    if sort_specs:
        df = apply_sorting(df, sort_specs)
    if dedup_spec:
        df = apply_dedup(df, dedup_spec)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    return len(df)

class MergeWorker(QThread):
    progress_changed = Signal(int)
    status_changed = Signal(str)
    finished_ok = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, files, output_path, sheet_name=None, selected_columns=None,
                 conditions=None, replacement_rules=None, fill_service=True):
        super().__init__()
        self.files = files
        self.output_path = output_path
        self.sheet_name = sheet_name
        self.selected_columns = selected_columns or []
        self.conditions = conditions or []
        self.replacement_rules = replacement_rules or []
        self.fill_service = fill_service

    def run(self):
        try:
            result_frames = []
            total_files = len(self.files)
            failed = []

            for idx, file_path in enumerate(self.files, start=1):
                base = os.path.basename(file_path)
                try:
                    if is_file_locked(file_path):
                        self.status_changed.emit(f"[열림 감지] {base} / 임시 복사본으로 처리")
                    readable = get_readable_file_path(file_path)
                    df = load_file_to_df(readable, sheet_name=self.sheet_name)
                    
                    if self.replacement_rules:
                        df = apply_replacements(df, self.replacement_rules)
                    if self.conditions:
                        df = apply_advanced_conditions(df, self.conditions)
                    if self.fill_service:
                        df = fill_service_small_from_mid(df)
                    if self.selected_columns:
                        keep = [c for c in self.selected_columns if c in df.columns]
                        df = df[keep]
                        
                    result_frames.append(df)
                    self.status_changed.emit(f"[완료] {base} / {len(df):,}행")
                except Exception as e:
                    failed.append((base, str(e)))
                    self.status_changed.emit(f"[실패] {base} / {e}")
                self.progress_changed.emit(int(idx / total_files * 100) if total_files else 100)

            if result_frames:
                final_df = pd.concat(result_frames, ignore_index=True)
            else:
                final_df = pd.DataFrame(columns=self.selected_columns)
            
            final_df.to_csv(self.output_path, index=False, encoding="utf-8-sig")

            msg = [f"병합 완료: 총 {len(final_df):,}행 저장", f"성공 파일: {len(result_frames)}개", f"실패 파일: {len(failed)}개"]
            if failed:
                msg.append("\n[실패 파일 목록]")
                for name, reason in failed[:20]:
                    msg.append(f"- {name}: {reason}")
            self.finished_ok.emit("\n".join(msg))
        except Exception as e:
            self.error_occurred.emit(f"{e}\n\n{traceback.format_exc()}")

class ExportWorker(QThread):
    progress_changed = Signal(int)
    status_changed = Signal(str)
    finished_ok = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, source_path, output_path, sheet_name=None, selected_columns=None,
                 conditions=None, replacement_rules=None, fill_service=True,
                 sort_specs=None, dedup_spec=None, header_row_idx=None, force_html=False):
        super().__init__()
        self.source_path = source_path
        self.output_path = output_path
        self.sheet_name = sheet_name
        self.selected_columns = selected_columns or []
        self.conditions = conditions or []
        self.replacement_rules = replacement_rules or []
        self.fill_service = fill_service
        self.sort_specs = sort_specs or []
        self.dedup_spec = dedup_spec
        self.header_row_idx = header_row_idx
        self.force_html = force_html

    def run(self):
        try:
            self.progress_changed.emit(10)
            readable = get_readable_file_path(self.source_path)
            self.status_changed.emit(f"[읽기] {os.path.basename(self.source_path)}")
            df = load_file_to_df(
                readable,
                sheet_name=self.sheet_name,
                header_row_idx=self.header_row_idx,
                force_html=self.force_html
            )
            self.progress_changed.emit(50)
            written = export_from_df(
                df=df,
                output_path=self.output_path,
                selected_columns=self.selected_columns,
                conditions=self.conditions,
                replacement_rules=self.replacement_rules,
                fill_service=self.fill_service,
                sort_specs=self.sort_specs,
                dedup_spec=self.dedup_spec,
            )
            self.progress_changed.emit(100)
            self.finished_ok.emit(f"완료: 총 {written:,}행 저장")
        except Exception as e:
            self.error_occurred.emit(f"{e}\n\n{traceback.format_exc()}")

class OpenExcelExportWorker(QThread):
    progress_changed = Signal(int)
    status_changed = Signal(str)
    finished_ok = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, workbook_name, sheet_name, output_path, selected_columns=None,
                 conditions=None, replacement_rules=None, fill_service=True,
                 sort_specs=None, dedup_spec=None, header_row_idx=None):
        super().__init__()
        self.workbook_name = workbook_name
        self.sheet_name = sheet_name
        self.output_path = output_path
        self.selected_columns = selected_columns or []
        self.conditions = conditions or []
        self.replacement_rules = replacement_rules or []
        self.fill_service = fill_service
        self.sort_specs = sort_specs or []
        self.dedup_spec = dedup_spec
        self.header_row_idx = header_row_idx

    def run(self):
        try:
            self.progress_changed.emit(10)
            self.status_changed.emit(f"[읽기] {self.workbook_name} / {self.sheet_name}")
            df = load_open_excel_sheet_df(
                self.workbook_name,
                self.sheet_name,
                max_rows=None,
                header_row_idx=self.header_row_idx
            )
            self.progress_changed.emit(55)
            written = export_from_df(
                df=df,
                output_path=self.output_path,
                selected_columns=self.selected_columns,
                conditions=self.conditions,
                replacement_rules=self.replacement_rules,
                fill_service=self.fill_service,
                sort_specs=self.sort_specs,
                dedup_spec=self.dedup_spec,
            )
            self.progress_changed.emit(100)
            self.finished_ok.emit(f"완료: 총 {written:,}행 저장")
        except Exception as e:
            self.error_occurred.emit(f"{e}\n\n{traceback.format_exc()}")

class MatchingWorker(QThread):
    progress_changed = Signal(int)
    status_changed = Signal(str)
    finished_ok = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, base_path, ref_path, output_path, base_sheet=None, ref_sheet=None,
                 base_key=None, ref_key=None, ref_columns=None):
        super().__init__()
        self.base_path = base_path
        self.ref_path = ref_path
        self.output_path = output_path
        self.base_sheet = base_sheet
        self.ref_sheet = ref_sheet
        self.base_key = base_key
        self.ref_key = ref_key
        self.ref_columns = ref_columns or []

    def run(self):
        try:
            self.progress_changed.emit(10)
            self.status_changed.emit(f"[로드] 원본: {os.path.basename(self.base_path)}")
            base_df = load_file_to_df(get_readable_file_path(self.base_path), sheet_name=self.base_sheet)
            
            if base_df.empty:
                raise ValueError("원본 데이터가 비어 있거나 읽을 수 없습니다.")
            if self.base_key not in base_df.columns:
                raise ValueError(f"원본 데이터에 '{self.base_key}' 컬럼이 없습니다.")

            self.progress_changed.emit(30)
            self.status_changed.emit(f"[로드] 참조: {os.path.basename(self.ref_path)}")
            ref_df = load_file_to_df(get_readable_file_path(self.ref_path), sheet_name=self.ref_sheet)
            
            if ref_df.empty:
                raise ValueError("참조 데이터가 비어 있거나 읽을 수 없습니다.")
            if self.ref_key not in ref_df.columns:
                raise ValueError(f"참조 데이터에 '{self.ref_key}' 컬럼이 없습니다.")

            self.progress_changed.emit(60)
            self.status_changed.emit(f"[매칭 준비] 데이터 정규화 및 중복 제거")
            
            # Key Normalization: convert to string and strip whitespace for robust matching
            base_df[self.base_key] = base_df[self.base_key].astype(str).str.strip()
            ref_df[self.ref_key] = ref_df[self.ref_key].astype(str).str.strip()

            # Prepare ref_df: keep only key and requested columns
            base_cols = set(base_df.columns)
            ref_cols_to_keep = [c for c in self.ref_columns if c not in base_cols or c == self.ref_key]
            
            # Filter columns that actually exist in ref_df
            ref_cols_to_keep = [c for c in ref_cols_to_keep if c in ref_df.columns]
            
            keep_ref = list(set([self.ref_key] + ref_cols_to_keep))
            ref_subset = ref_df[keep_ref].copy()
            
            # Deduplicate Reference Data on the Key to prevent row count explosion (VLOOKUP style)
            before_dedup = len(ref_subset)
            ref_subset.drop_duplicates(subset=[self.ref_key], keep='first', inplace=True)
            after_dedup = len(ref_subset)
            if before_dedup != after_dedup:
                self.status_changed.emit(f"[주의] 참조 데이터 중복 키 제거: {before_dedup - after_dedup}건")

            self.progress_changed.emit(80)
            self.status_changed.emit(f"[매칭 실행] {self.base_key} <=> {self.ref_key}")

            # Perform left join
            result_df = pd.merge(
                base_df, 
                ref_subset, 
                left_on=self.base_key, 
                right_on=self.ref_key, 
                how='left'
            )
            
            # If keys had different names, drop the reference key column
            if self.base_key != self.ref_key and self.ref_key in result_df.columns:
                result_df.drop(columns=[self.ref_key], inplace=True)
            
            self.progress_changed.emit(90)
            self.status_changed.emit(f"[저장] {os.path.basename(self.output_path)}")
            result_df.to_csv(self.output_path, index=False, encoding="utf-8-sig")
            
            self.progress_changed.emit(100)
            self.finished_ok.emit(f"매칭 완료: 총 {len(result_df):,}행 저장")
        except Exception as e:
            self.error_occurred.emit(f"{e}\n\n{traceback.format_exc()}")
