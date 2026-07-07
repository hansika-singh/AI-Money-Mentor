"""
Year-End Tax Summary PDF Generator

Generates a comprehensive PDF report with:
- Total income by source
- Deductions claimed (80C, 80D, HRA, etc.)
- Estimated tax liability (Old vs New regime)
- Tax Loss Harvesting (TLH) events
- Capital gains summary
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from fpdf import FPDF


class TaxSummaryPDF(FPDF):
    """Custom PDF class for tax summary reports."""

    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, "AI Money Mentor - Year-End Tax Summary", new_x="LMARGIN", new_y="NEXT", align="C")
        self.set_font("Helvetica", size=9)
        self.cell(0, 6, f"Generated on {datetime.now().strftime('%d %b %Y %I:%M %p')}", new_x="LMARGIN", new_y="NEXT", align="C")
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def section_title(self, title: str):
        self.set_font("Helvetica", "B", 12)
        self.set_fill_color(240, 240, 240)
        self.cell(0, 8, f"  {title}", new_x="LMARGIN", new_y="NEXT", fill=True)
        self.ln(3)

    def add_row(self, label: str, value: str, bold_value: bool = False):
        self.set_font("Helvetica", size=10)
        self.cell(90, 7, label, new_x="END")
        style = "B" if bold_value else ""
        self.set_font("Helvetica", style, 10)
        self.cell(0, 7, value, new_x="LMARGIN", new_y="NEXT")

    def add_table_header(self, cols: List[str], widths: List[int]):
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(50, 50, 50)
        self.set_text_color(255, 255, 255)
        for i, col in enumerate(cols):
            self.cell(widths[i], 7, col, border=1, fill=True, align="C")
        self.ln()
        self.set_text_color(0, 0, 0)

    def add_table_row(self, values: List[str], widths: List[int], aligns: List[str] | None = None):
        self.set_font("Helvetica", size=9)
        if aligns is None:
            aligns = ["L"] * len(values)
        for i, val in enumerate(values):
            self.cell(widths[i], 6, val, border=1, align=aligns[i])
        self.ln()


def _fmt(amount: float) -> str:
    """Format amount in Indian Rupee style."""
    if amount >= 10000000:
        return f"Rs. {amount / 10000000:.2f} Cr"
    if amount >= 100000:
        return f"Rs. {amount / 100000:.2f} L"
    return f"Rs. {amount:,.0f}"


def generate_tax_summary_pdf(data: Dict[str, Any]) -> bytes:
    """Generate a year-end tax summary PDF.

    Args:
        data: Dictionary containing:
            - income: Dict with source-wise income breakdown
            - deductions: Dict with deduction amounts
            - tax_result: Dict with tax calculation (old/new regime)
            - capital_gains: List of capital gains entries
            - tlh_events: List of tax loss harvesting events
            - fy: Financial year string (e.g. "2025-26")

    Returns:
        PDF file bytes.
    """
    pdf = TaxSummaryPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    fy = data.get("fy", f"{datetime.now().year - 1}-{str(datetime.now().year)[-2:]}")

    # ── Section 1: Income Summary ──
    pdf.section_title(f"Income Summary (FY {fy})")
    income = data.get("income", {})
    income_sources = [
        ("Salary / Business Income", income.get("salary", 0) + income.get("business", 0)),
        ("Capital Gains", income.get("capital_gains", 0)),
        ("Rental Income", income.get("house_property", 0)),
        ("Interest / Dividends", income.get("interest", 0) + income.get("dividends", 0)),
        ("Other Income", income.get("other", 0)),
    ]
    total_income = sum(v for _, v in income_sources)
    for label, val in income_sources:
        if val > 0:
            pdf.add_row(label, _fmt(val))
    pdf.add_row("Gross Total Income", _fmt(total_income), bold_value=True)
    pdf.ln(3)

    # ── Section 2: Deductions ──
    pdf.section_title("Deductions Claimed")
    deductions = data.get("deductions", {})
    deduction_items = [
        ("Section 80C (PPF, ELSS, EPF)", deductions.get("80c", 0), 150000),
        ("Section 80CCD(1B) - NPS", deductions.get("80ccd_1b", 0), 50000),
        ("Section 80D - Health Insurance", deductions.get("80d", 0), 25000),
        ("HRA Exemption (Sec 10(13A))", deductions.get("hra", 0), None),
        ("Standard Deduction", deductions.get("standard", 50000), 50000),
        ("Other Deductions", deductions.get("other", 0), None),
    ]
    total_deductions = 0
    for label, val, cap in deduction_items:
        if val > 0:
            display = _fmt(val)
            if cap:
                display += f" (cap: {_fmt(cap)})"
            pdf.add_row(label, display)
            total_deductions += val
    pdf.add_row("Total Deductions", _fmt(total_deductions), bold_value=True)
    pdf.ln(3)

    # ── Section 3: Tax Liability ──
    pdf.section_title("Estimated Tax Liability")
    tax_result = data.get("tax_result", {})
    if tax_result:
        old_regime = tax_result.get("old_regime", {})
        new_regime = tax_result.get("new_regime", {})
        pdf.add_row("Old Regime Tax", _fmt(old_regime.get("total_tax", 0)))
        pdf.add_row("New Regime Tax", _fmt(new_regime.get("total_tax", 0)))
        recommended = tax_result.get("recommended", "New Regime")
        pdf.add_row("Recommended Regime", recommended, bold_value=True)
    else:
        pdf.add_row("Tax Data", "Not available")
    pdf.ln(3)

    # ── Section 4: Capital Gains Summary ──
    capital_gains = data.get("capital_gains", [])
    if capital_gains:
        pdf.section_title("Capital Gains Summary")
        cols = ["Asset", "Type", "Buy Value", "Sell Value", "Gain/Loss"]
        widths = [40, 30, 35, 35, 40]
        aligns = ["L", "C", "R", "R", "R"]
        pdf.add_table_header(cols, widths)
        total_gain = 0
        for cg in capital_gains:
            gain = cg.get("gain", 0)
            total_gain += gain
            pdf.add_table_row(
                [
                    str(cg.get("asset", "N/A"))[:20],
                    str(cg.get("type", "N/A"))[:15],
                    _fmt(cg.get("buy_value", 0)),
                    _fmt(cg.get("sell_value", 0)),
                    _fmt(gain),
                ],
                widths,
                aligns,
            )
        pdf.add_row("Net Capital Gain", _fmt(total_gain), bold_value=True)
        pdf.ln(3)

    # ── Section 5: Tax Loss Harvesting ──
    tlh_events = data.get("tlh_events", [])
    if tlh_events:
        pdf.section_title("Tax Loss Harvesting (TLH) Events")
        cols = ["Date", "Asset", "Loss Booked", "Saved Tax"]
        widths = [35, 50, 45, 50]
        aligns = ["C", "L", "R", "R"]
        pdf.add_table_header(cols, widths)
        total_saved = 0
        for evt in tlh_events:
            saved = evt.get("saved_tax", 0)
            total_saved += saved
            pdf.add_table_row(
                [
                    str(evt.get("date", "N/A")),
                    str(evt.get("asset", "N/A"))[:25],
                    _fmt(evt.get("loss", 0)),
                    _fmt(saved),
                ],
                widths,
                aligns,
            )
        pdf.add_row("Total Tax Saved via TLH", _fmt(total_saved), bold_value=True)
        pdf.ln(3)

    # ── Section 6: Summary ──
    pdf.section_title("Tax Planning Summary")
    net_tax = 0
    if tax_result:
        recommended = tax_result.get("recommended", "New Regime")
        regime_key = "old_regime" if "Old" in recommended else "new_regime"
        net_tax = tax_result.get(regime_key, {}).get("total_tax", 0)

    pdf.add_row("Gross Total Income", _fmt(total_income))
    pdf.add_row("Total Deductions", _fmt(total_deductions))
    pdf.add_row("Net Tax Liability", _fmt(net_tax), bold_value=True)

    effective_rate = (net_tax / total_income * 100) if total_income > 0 else 0
    pdf.add_row("Effective Tax Rate", f"{effective_rate:.1f}%")
    pdf.ln(5)

    # Disclaimer
    pdf.set_font("Helvetica", "I", 8)
    pdf.multi_cell(
        0,
        4,
        "Disclaimer: This report is generated for informational purposes only and does not "
        "constitute professional tax advice. Please consult a qualified tax advisor for filing.",
    )

    return bytes(pdf.output())
