"""
reporting.py
------------
Export & reporting helpers.

Generates:
  * CSV export of any dataframe
  * Excel (.xlsx) workbook export
  * A styled PDF executive summary report
"""
from __future__ import annotations

import io

import pandas as pd
from fpdf import FPDF

# Dark palette accents reused in the PDF
ACCENT = (124, 92, 255)
DARK = (11, 15, 30)
SURFACE = (21, 27, 46)
TEXT_LT = (232, 236, 248)
MUTED = (140, 150, 180)


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Return UTF-8 CSV bytes for download."""
    return df.to_csv(index=False).encode("utf-8")


def to_excel_bytes(dfs: dict[str, pd.DataFrame]) -> bytes:
    """
    Write multiple dataframes into one Excel workbook (a sheet per key).
    Missing openpyxl/xlsxwriter are handled gracefully.
    """
    buf = io.BytesIO()
    try:
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            for name, df in dfs.items():
                sheet = _safe_sheet_name(name)
                df.to_excel(writer, sheet_name=sheet, index=False)
    except Exception:
        # Fallback: single sheet
        buf = io.BytesIO()
        buf.write(dfs[list(dfs.keys())[0]].to_csv(index=False).encode("utf-8"))
        buf.seek(0)
        return buf.getvalue()
    buf.seek(0)
    return buf.getvalue()


def _safe_sheet_name(name: str) -> str:
    cleaned = "".join(ch for ch in str(name) if ch not in r"[]*?/\\")
    return (cleaned or "Sheet")[:31]


class PdfReport(FPDF):
    """Minimal branded PDF for the executive summary report."""

    def header(self):
        self.set_fill_color(*SURFACE)
        self.rect(0, 0, 210, 16, "F")
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*ACCENT)
        self.cell(0, 16, "SaaS Business Analytics - Executive Report", ln=True, align="L")
        self.set_draw_color(*ACCENT)
        self.line(10, 18, 200, 18)
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 10, f"Generated {self.generated}  |  Page {self.page_no()}", align="C")


def build_pdf_exec_summary(kpis: dict[str, str], generated: str) -> bytes:
    """Build and return a PDF executive summary from a KPI dict."""
    pdf = PdfReport()
    pdf.generated = generated
    pdf.add_page()
    pdf.set_left_margin(12)
    pdf.set_right_margin(12)

    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*TEXT_LT)
    pdf.cell(0, 10, "Executive Summary", ln=True)

    pdf.ln(4)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(
        0, 6,
        "Interactive dashboard generated from the end-to-end SaaS analytics "
        "pipeline. The figures below summarise overall business performance.",
    )
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*ACCENT)
    pdf.cell(0, 8, "Key Performance Indicators", ln=True)
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 11)
    for label, value in kpis.items():
        pdf.set_text_color(*MUTED)
        pdf.cell(90, 9, f"  {label}", border=1)
        pdf.set_text_color(*TEXT_LT)
        pdf.cell(80, 9, f"{value}", border=1, ln=True)

    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(0, 5, "Report generated automatically. KPIs reflect the active "
                        "global filters applied in the dashboard.")

    # fpdf.output() writes to a file path; use a temp file to capture bytes.
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        pdf.output(tmp_path)
        with open(tmp_path, "rb") as fh:
            return fh.read()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
