import io
import csv
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID
import json

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

from ..schemas.reporting import ExportFormat, ExpenseSummary, FinancialMetrics


class ExportService:
    """Service for exporting reports in various formats."""

    def export_expense_summary(
        self, 
        summary: ExpenseSummary, 
        format: ExportFormat,
        filename_prefix: str = "expense_summary"
    ) -> tuple[bytes, str, str]:
        """
        Export expense summary in the specified format.
        Returns: (file_content, filename, content_type)
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == ExportFormat.CSV:
            return self._export_csv(summary, f"{filename_prefix}_{timestamp}.csv")
        elif format == ExportFormat.EXCEL:
            return self._export_excel(summary, f"{filename_prefix}_{timestamp}.xlsx")
        elif format == ExportFormat.PDF:
            return self._export_pdf(summary, f"{filename_prefix}_{timestamp}.pdf")
        elif format == ExportFormat.JSON:
            return self._export_json(summary, f"{filename_prefix}_{timestamp}.json")
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def export_financial_metrics(
        self,
        metrics: FinancialMetrics,
        format: ExportFormat,
        filename_prefix: str = "financial_metrics"
    ) -> tuple[bytes, str, str]:
        """Export financial metrics in the specified format."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == ExportFormat.CSV:
            return self._export_metrics_csv(metrics, f"{filename_prefix}_{timestamp}.csv")
        elif format == ExportFormat.EXCEL:
            return self._export_metrics_excel(metrics, f"{filename_prefix}_{timestamp}.xlsx")
        elif format == ExportFormat.PDF:
            return self._export_metrics_pdf(metrics, f"{filename_prefix}_{timestamp}.pdf")
        elif format == ExportFormat.JSON:
            return self._export_json(metrics, f"{filename_prefix}_{timestamp}.json")
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def export_transactions(
        self,
        transactions: List[Dict[str, Any]],
        format: ExportFormat,
        filename_prefix: str = "transactions"
    ) -> tuple[bytes, str, str]:
        """Export transaction data in the specified format."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == ExportFormat.CSV:
            return self._export_transactions_csv(transactions, f"{filename_prefix}_{timestamp}.csv")
        elif format == ExportFormat.EXCEL:
            return self._export_transactions_excel(transactions, f"{filename_prefix}_{timestamp}.xlsx")
        elif format == ExportFormat.PDF:
            return self._export_transactions_pdf(transactions, f"{filename_prefix}_{timestamp}.pdf")
        elif format == ExportFormat.JSON:
            return self._export_json(transactions, f"{filename_prefix}_{timestamp}.json")
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _export_csv(self, summary: ExpenseSummary, filename: str) -> tuple[bytes, str, str]:
        """Export expense summary as CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write summary data
        writer.writerow(["Expense Summary"])
        writer.writerow(["Total Expenses", float(summary.total_expenses)])
        writer.writerow(["Total Income", float(summary.total_income)])
        writer.writerow(["Net Income", float(summary.net_income)])
        writer.writerow(["Transaction Count", summary.transaction_count])
        writer.writerow(["Average Transaction", float(summary.average_transaction)])
        writer.writerow([])  # Empty row
        
        # Write category breakdown
        writer.writerow(["Category Breakdown"])
        writer.writerow(["Category", "Amount", "Transaction Count", "Percentage"])
        
        for category in summary.categories:
            writer.writerow([
                category.category_name,
                float(category.total_amount),
                category.transaction_count,
                f"{category.percentage:.2f}%"
            ])
        
        content = output.getvalue().encode('utf-8')
        return content, filename, "text/csv"

    def _export_excel(self, summary: ExpenseSummary, filename: str) -> tuple[bytes, str, str]:
        """Export expense summary as Excel."""
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas is required for Excel export")
        
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Summary sheet
            summary_data = {
                'Metric': ['Total Expenses', 'Total Income', 'Net Income', 'Transaction Count', 'Average Transaction'],
                'Value': [
                    float(summary.total_expenses),
                    float(summary.total_income),
                    float(summary.net_income),
                    summary.transaction_count,
                    float(summary.average_transaction)
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
            
            # Category breakdown sheet
            category_data = {
                'Category': [cat.category_name for cat in summary.categories],
                'Amount': [float(cat.total_amount) for cat in summary.categories],
                'Transaction Count': [cat.transaction_count for cat in summary.categories],
                'Percentage': [f"{cat.percentage:.2f}%" for cat in summary.categories]
            }
            pd.DataFrame(category_data).to_excel(writer, sheet_name='Categories', index=False)
        
        content = output.getvalue()
        return content, filename, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    def _export_pdf(self, summary: ExpenseSummary, filename: str) -> tuple[bytes, str, str]:
        """Export expense summary as PDF."""
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab is required for PDF export")
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
        )
        story.append(Paragraph("Expense Summary Report", title_style))
        story.append(Spacer(1, 12))
        
        # Summary table
        summary_data = [
            ['Metric', 'Value'],
            ['Total Expenses', f"${float(summary.total_expenses):,.2f}"],
            ['Total Income', f"${float(summary.total_income):,.2f}"],
            ['Net Income', f"${float(summary.net_income):,.2f}"],
            ['Transaction Count', str(summary.transaction_count)],
            ['Average Transaction', f"${float(summary.average_transaction):,.2f}"]
        ]
        
        summary_table = Table(summary_data)
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 24))
        
        # Category breakdown
        story.append(Paragraph("Category Breakdown", styles['Heading2']))
        story.append(Spacer(1, 12))
        
        category_data = [['Category', 'Amount', 'Count', 'Percentage']]
        for category in summary.categories:
            category_data.append([
                category.category_name,
                f"${float(category.total_amount):,.2f}",
                str(category.transaction_count),
                f"{category.percentage:.2f}%"
            ])
        
        category_table = Table(category_data)
        category_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(category_table)
        
        doc.build(story)
        content = buffer.getvalue()
        return content, filename, "application/pdf"

    def _export_json(self, data: Any, filename: str) -> tuple[bytes, str, str]:
        """Export data as JSON."""
        if hasattr(data, 'model_dump'):
            # Pydantic model
            json_data = data.model_dump()
        elif hasattr(data, 'dict'):
            # Pydantic model (older version)
            json_data = data.dict()
        else:
            # Regular data
            json_data = data
        
        content = json.dumps(json_data, indent=2, default=str).encode('utf-8')
        return content, filename, "application/json"

    def _export_metrics_csv(self, metrics: FinancialMetrics, filename: str) -> tuple[bytes, str, str]:
        """Export financial metrics as CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(["Financial Metrics"])
        writer.writerow(["Total Balance", float(metrics.total_balance)])
        writer.writerow(["Monthly Income", float(metrics.monthly_income)])
        writer.writerow(["Monthly Expenses", float(metrics.monthly_expenses)])
        writer.writerow(["Monthly Savings", float(metrics.monthly_savings)])
        writer.writerow(["Savings Rate", f"{metrics.savings_rate:.2f}%"])
        writer.writerow(["Top Expense Category", metrics.top_expense_category or "N/A"])
        writer.writerow([])
        
        # Expense trend
        writer.writerow(["Expense Trend"])
        writer.writerow(["Period", "Amount"])
        for trend in metrics.expense_trend:
            writer.writerow([trend.period, float(trend.expenses)])
        
        content = output.getvalue().encode('utf-8')
        return content, filename, "text/csv"

    def _export_metrics_excel(self, metrics: FinancialMetrics, filename: str) -> tuple[bytes, str, str]:
        """Export financial metrics as Excel."""
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas is required for Excel export")
        
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Metrics sheet
            metrics_data = {
                'Metric': ['Total Balance', 'Monthly Income', 'Monthly Expenses', 'Monthly Savings', 'Savings Rate', 'Top Expense Category'],
                'Value': [
                    float(metrics.total_balance),
                    float(metrics.monthly_income),
                    float(metrics.monthly_expenses),
                    float(metrics.monthly_savings),
                    f"{metrics.savings_rate:.2f}%",
                    metrics.top_expense_category or "N/A"
                ]
            }
            pd.DataFrame(metrics_data).to_excel(writer, sheet_name='Metrics', index=False)
            
            # Trends sheet
            if metrics.expense_trend:
                trend_data = {
                    'Period': [trend.period for trend in metrics.expense_trend],
                    'Expenses': [float(trend.expenses) for trend in metrics.expense_trend],
                    'Income': [float(trend.income) for trend in metrics.income_trend] if metrics.income_trend else [0] * len(metrics.expense_trend)
                }
                pd.DataFrame(trend_data).to_excel(writer, sheet_name='Trends', index=False)
        
        content = output.getvalue()
        return content, filename, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    def _export_metrics_pdf(self, metrics: FinancialMetrics, filename: str) -> tuple[bytes, str, str]:
        """Export financial metrics as PDF."""
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab is required for PDF export")
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
        )
        story.append(Paragraph("Financial Metrics Report", title_style))
        story.append(Spacer(1, 12))
        
        # Metrics table
        metrics_data = [
            ['Metric', 'Value'],
            ['Total Balance', f"${float(metrics.total_balance):,.2f}"],
            ['Monthly Income', f"${float(metrics.monthly_income):,.2f}"],
            ['Monthly Expenses', f"${float(metrics.monthly_expenses):,.2f}"],
            ['Monthly Savings', f"${float(metrics.monthly_savings):,.2f}"],
            ['Savings Rate', f"{metrics.savings_rate:.2f}%"],
            ['Top Expense Category', metrics.top_expense_category or "N/A"]
        ]
        
        metrics_table = Table(metrics_data)
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(metrics_table)
        
        doc.build(story)
        content = buffer.getvalue()
        return content, filename, "application/pdf"

    def _export_transactions_csv(self, transactions: List[Dict[str, Any]], filename: str) -> tuple[bytes, str, str]:
        """Export transactions as CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        if transactions:
            # Write header
            headers = list(transactions[0].keys())
            writer.writerow(headers)
            
            # Write data
            for transaction in transactions:
                writer.writerow([transaction.get(header, '') for header in headers])
        
        content = output.getvalue().encode('utf-8')
        return content, filename, "text/csv"

    def _export_transactions_excel(self, transactions: List[Dict[str, Any]], filename: str) -> tuple[bytes, str, str]:
        """Export transactions as Excel."""
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas is required for Excel export")
        
        output = io.BytesIO()
        
        if transactions:
            df = pd.DataFrame(transactions)
            df.to_excel(output, index=False, engine='openpyxl')
        else:
            # Create empty Excel file
            pd.DataFrame().to_excel(output, index=False, engine='openpyxl')
        
        content = output.getvalue()
        return content, filename, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    def _export_transactions_pdf(self, transactions: List[Dict[str, Any]], filename: str) -> tuple[bytes, str, str]:
        """Export transactions as PDF."""
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab is required for PDF export")
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
        )
        story.append(Paragraph("Transaction Report", title_style))
        story.append(Spacer(1, 12))
        
        if transactions:
            # Create table data
            headers = ['Date', 'Description', 'Amount', 'Type', 'Category']
            table_data = [headers]
            
            for transaction in transactions:
                table_data.append([
                    transaction.get('date', ''),
                    transaction.get('description', '')[:30] + '...' if len(transaction.get('description', '')) > 30 else transaction.get('description', ''),
                    f"${float(transaction.get('amount', 0)):,.2f}",
                    transaction.get('transaction_type', ''),
                    transaction.get('category_name', '')
                ])
            
            # Create table
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(table)
        else:
            story.append(Paragraph("No transactions found.", styles['Normal']))
        
        doc.build(story)
        content = buffer.getvalue()
        return content, filename, "application/pdf"