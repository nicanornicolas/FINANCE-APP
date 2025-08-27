from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date, datetime, timedelta
from uuid import UUID
import io

from ...db.database import get_db
from ...services.reporting import ReportingService
from ...services.export import ExportService
from ...schemas.reporting import (
    ReportFilters, DateRangeFilter, ReportPeriod, ExpenseSummary,
    FinancialMetrics, DashboardData, ChartData, ExportFormat,
    ReportRequest, ReportResponse
)
from ...schemas.user import User
from ..dependencies import get_current_user

router = APIRouter(prefix="/reporting", tags=["reporting"])


@router.get("/dashboard", response_model=DashboardData)
async def get_dashboard_data(
    start_date: Optional[date] = Query(None, description="Start date for dashboard data"),
    end_date: Optional[date] = Query(None, description="End date for dashboard data"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive dashboard data for the current user."""
    reporting_service = ReportingService(db)
    
    # Set default date range if not provided (last 30 days)
    if not start_date or not end_date:
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
    
    filters = ReportFilters(
        date_range=DateRangeFilter(
            start_date=start_date,
            end_date=end_date,
            period=ReportPeriod.CUSTOM
        )
    )
    
    try:
        dashboard_data = reporting_service.get_dashboard_data(current_user.id, filters)
        return dashboard_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating dashboard data: {str(e)}")


@router.get("/metrics", response_model=FinancialMetrics)
async def get_financial_metrics(
    start_date: date = Query(..., description="Start date for metrics calculation"),
    end_date: date = Query(..., description="End date for metrics calculation"),
    account_ids: Optional[List[UUID]] = Query(None, description="Filter by specific account IDs"),
    category_ids: Optional[List[UUID]] = Query(None, description="Filter by specific category IDs"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get financial metrics for a specific date range."""
    reporting_service = ReportingService(db)
    
    filters = ReportFilters(
        date_range=DateRangeFilter(
            start_date=start_date,
            end_date=end_date,
            period=ReportPeriod.CUSTOM
        ),
        account_ids=account_ids,
        category_ids=category_ids
    )
    
    try:
        metrics = reporting_service.get_financial_metrics(current_user.id, filters)
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating financial metrics: {str(e)}")


@router.get("/expense-summary", response_model=ExpenseSummary)
async def get_expense_summary(
    start_date: date = Query(..., description="Start date for expense summary"),
    end_date: date = Query(..., description="End date for expense summary"),
    account_ids: Optional[List[UUID]] = Query(None, description="Filter by specific account IDs"),
    category_ids: Optional[List[UUID]] = Query(None, description="Filter by specific category IDs"),
    transaction_types: Optional[List[str]] = Query(None, description="Filter by transaction types"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get expense summary with category breakdown."""
    reporting_service = ReportingService(db)
    
    filters = ReportFilters(
        date_range=DateRangeFilter(
            start_date=start_date,
            end_date=end_date,
            period=ReportPeriod.CUSTOM
        ),
        account_ids=account_ids,
        category_ids=category_ids,
        transaction_types=transaction_types
    )
    
    try:
        summary = reporting_service.get_expense_summary(current_user.id, filters)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating expense summary: {str(e)}")


@router.get("/chart-data/{chart_type}", response_model=ChartData)
async def get_chart_data(
    chart_type: str,
    start_date: date = Query(..., description="Start date for chart data"),
    end_date: date = Query(..., description="End date for chart data"),
    account_ids: Optional[List[UUID]] = Query(None, description="Filter by specific account IDs"),
    category_ids: Optional[List[UUID]] = Query(None, description="Filter by specific category IDs"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get chart data for various chart types."""
    reporting_service = ReportingService(db)
    
    # Validate chart type
    valid_chart_types = ["category_pie", "expense_trend", "income_trend", "monthly_comparison"]
    if chart_type not in valid_chart_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid chart type. Must be one of: {', '.join(valid_chart_types)}"
        )
    
    filters = ReportFilters(
        date_range=DateRangeFilter(
            start_date=start_date,
            end_date=end_date,
            period=ReportPeriod.CUSTOM
        ),
        account_ids=account_ids,
        category_ids=category_ids
    )
    
    try:
        chart_data = reporting_service.generate_chart_data(current_user.id, chart_type, filters)
        return chart_data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating chart data: {str(e)}")


@router.post("/export/expense-summary")
async def export_expense_summary(
    format: ExportFormat,
    start_date: date = Query(..., description="Start date for expense summary"),
    end_date: date = Query(..., description="End date for expense summary"),
    account_ids: Optional[List[UUID]] = Query(None, description="Filter by specific account IDs"),
    category_ids: Optional[List[UUID]] = Query(None, description="Filter by specific category IDs"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export expense summary in the specified format."""
    reporting_service = ReportingService(db)
    export_service = ExportService()
    
    filters = ReportFilters(
        date_range=DateRangeFilter(
            start_date=start_date,
            end_date=end_date,
            period=ReportPeriod.CUSTOM
        ),
        account_ids=account_ids,
        category_ids=category_ids
    )
    
    try:
        # Generate the expense summary
        summary = reporting_service.get_expense_summary(current_user.id, filters)
        
        # Export in the requested format
        file_content, filename, content_type = export_service.export_expense_summary(
            summary, format, "expense_summary"
        )
        
        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except ImportError as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Export format not supported: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting expense summary: {str(e)}")


@router.post("/export/financial-metrics")
async def export_financial_metrics(
    format: ExportFormat,
    start_date: date = Query(..., description="Start date for financial metrics"),
    end_date: date = Query(..., description="End date for financial metrics"),
    account_ids: Optional[List[UUID]] = Query(None, description="Filter by specific account IDs"),
    category_ids: Optional[List[UUID]] = Query(None, description="Filter by specific category IDs"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export financial metrics in the specified format."""
    reporting_service = ReportingService(db)
    export_service = ExportService()
    
    filters = ReportFilters(
        date_range=DateRangeFilter(
            start_date=start_date,
            end_date=end_date,
            period=ReportPeriod.CUSTOM
        ),
        account_ids=account_ids,
        category_ids=category_ids
    )
    
    try:
        # Generate the financial metrics
        metrics = reporting_service.get_financial_metrics(current_user.id, filters)
        
        # Export in the requested format
        file_content, filename, content_type = export_service.export_financial_metrics(
            metrics, format, "financial_metrics"
        )
        
        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except ImportError as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Export format not supported: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting financial metrics: {str(e)}")


@router.post("/export/transactions")
async def export_transactions(
    format: ExportFormat,
    start_date: date = Query(..., description="Start date for transactions"),
    end_date: date = Query(..., description="End date for transactions"),
    account_ids: Optional[List[UUID]] = Query(None, description="Filter by specific account IDs"),
    category_ids: Optional[List[UUID]] = Query(None, description="Filter by specific category IDs"),
    transaction_types: Optional[List[str]] = Query(None, description="Filter by transaction types"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export transaction data in the specified format."""
    reporting_service = ReportingService(db)
    export_service = ExportService()
    
    filters = ReportFilters(
        date_range=DateRangeFilter(
            start_date=start_date,
            end_date=end_date,
            period=ReportPeriod.CUSTOM
        ),
        account_ids=account_ids,
        category_ids=category_ids,
        transaction_types=transaction_types
    )
    
    try:
        # Get transactions data
        transactions = reporting_service.get_recent_transactions(current_user.id, limit=1000)
        
        # Export in the requested format
        file_content, filename, content_type = export_service.export_transactions(
            transactions, format, "transactions"
        )
        
        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except ImportError as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Export format not supported: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting transactions: {str(e)}")


@router.get("/monthly-comparison")
async def get_monthly_comparison(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get monthly comparison data (current vs previous month)."""
    reporting_service = ReportingService(db)
    
    try:
        comparison = reporting_service.get_monthly_comparison(current_user.id)
        return comparison
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating monthly comparison: {str(e)}")


@router.get("/recent-transactions")
async def get_recent_transactions(
    limit: int = Query(10, ge=1, le=100, description="Number of recent transactions to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get recent transactions for the current user."""
    reporting_service = ReportingService(db)
    
    try:
        transactions = reporting_service.get_recent_transactions(current_user.id, limit)
        return {"transactions": transactions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching recent transactions: {str(e)}")