"""
Business service layer for business logic, reporting, and analytics
"""
from typing import List, Dict, Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, extract, case
from datetime import datetime, date, timedelta
from decimal import Decimal
from calendar import monthrange

from ..models.business import (
    BusinessEntity, Client, Invoice, InvoiceStatus, BusinessAccount
)
from ..models.transaction import Transaction, TransactionType
from ..models.account import Account
from ..crud.business import business_entity, client, invoice
from ..schemas.business import (
    BusinessSummary, ProfitLossReport, CashFlowReport
)


class BusinessService:
    """Service class for business operations and reporting"""

    def get_business_summary(self, db: Session, business_entity_id: UUID) -> BusinessSummary:
        """Get business summary statistics"""
        
        # Get total revenue from invoices
        revenue_query = db.query(func.sum(Invoice.total_amount)).filter(
            and_(
                Invoice.business_entity_id == business_entity_id,
                Invoice.status == InvoiceStatus.PAID
            )
        )
        total_revenue = revenue_query.scalar() or Decimal('0.00')

        # Get total expenses from business transactions
        expense_query = db.query(func.sum(Transaction.amount)).filter(
            and_(
                Transaction.account_id.in_(
                    db.query(BusinessAccount.account_id).filter(
                        BusinessAccount.business_entity_id == business_entity_id
                    )
                ),
                Transaction.transaction_type == TransactionType.EXPENSE
            )
        )
        total_expenses = expense_query.scalar() or Decimal('0.00')

        # Calculate net profit
        net_profit = total_revenue - total_expenses

        # Get outstanding invoices count
        outstanding_count = db.query(func.count(Invoice.id)).filter(
            and_(
                Invoice.business_entity_id == business_entity_id,
                Invoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.VIEWED])
            )
        ).scalar() or 0

        # Get overdue invoices count
        today = datetime.now().date()
        overdue_count = db.query(func.count(Invoice.id)).filter(
            and_(
                Invoice.business_entity_id == business_entity_id,
                Invoice.due_date < today,
                Invoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.VIEWED])
            )
        ).scalar() or 0

        # Get total outstanding amount
        outstanding_amount = db.query(
            func.sum(Invoice.total_amount - Invoice.paid_amount)
        ).filter(
            and_(
                Invoice.business_entity_id == business_entity_id,
                Invoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.VIEWED])
            )
        ).scalar() or Decimal('0.00')

        # Get active clients count
        active_clients = db.query(func.count(Client.id)).filter(
            and_(
                Client.business_entity_id == business_entity_id,
                Client.is_active == True
            )
        ).scalar() or 0

        return BusinessSummary(
            total_revenue=total_revenue,
            total_expenses=total_expenses,
            net_profit=net_profit,
            outstanding_invoices=outstanding_count,
            overdue_invoices=overdue_count,
            total_outstanding_amount=outstanding_amount,
            active_clients=active_clients
        )

    def generate_profit_loss_report(
        self, 
        db: Session, 
        business_entity_id: UUID, 
        start_date: date, 
        end_date: date
    ) -> ProfitLossReport:
        """Generate profit and loss report for a specific period"""
        
        # Get revenue from paid invoices in the period
        revenue = db.query(func.sum(Invoice.total_amount)).filter(
            and_(
                Invoice.business_entity_id == business_entity_id,
                Invoice.status == InvoiceStatus.PAID,
                Invoice.paid_date >= start_date,
                Invoice.paid_date <= end_date
            )
        ).scalar() or Decimal('0.00')

        # Get business account IDs
        business_account_ids = db.query(BusinessAccount.account_id).filter(
            BusinessAccount.business_entity_id == business_entity_id
        ).subquery()

        # Get expenses by category for the period
        expense_query = db.query(
            Transaction.category_id,
            func.sum(Transaction.amount).label('total_amount')
        ).join(
            business_account_ids, Transaction.account_id == business_account_ids.c.account_id
        ).filter(
            and_(
                Transaction.transaction_type == TransactionType.EXPENSE,
                Transaction.date >= start_date,
                Transaction.date <= end_date
            )
        ).group_by(Transaction.category_id).all()

        # Calculate expense breakdown
        expense_breakdown = {}
        total_expenses = Decimal('0.00')
        cost_of_goods_sold = Decimal('0.00')  # This would need category mapping
        
        for category_id, amount in expense_query:
            if category_id:
                # You would need to implement category mapping to determine COGS vs Operating Expenses
                expense_breakdown[str(category_id)] = float(amount)
                total_expenses += amount

        # For now, assume all expenses are operating expenses
        operating_expenses = total_expenses
        gross_profit = revenue - cost_of_goods_sold
        net_profit = gross_profit - operating_expenses

        return ProfitLossReport(
            business_entity_id=business_entity_id,
            period_start=datetime.combine(start_date, datetime.min.time()),
            period_end=datetime.combine(end_date, datetime.max.time()),
            revenue=revenue,
            cost_of_goods_sold=cost_of_goods_sold,
            gross_profit=gross_profit,
            operating_expenses=operating_expenses,
            net_profit=net_profit,
            expense_breakdown=expense_breakdown
        )

    def generate_cash_flow_report(
        self, 
        db: Session, 
        business_entity_id: UUID, 
        start_date: date, 
        end_date: date
    ) -> CashFlowReport:
        """Generate cash flow report for a specific period"""
        
        # Get business account IDs
        business_account_ids = [
            acc.account_id for acc in db.query(BusinessAccount).filter(
                BusinessAccount.business_entity_id == business_entity_id
            ).all()
        ]

        if not business_account_ids:
            return CashFlowReport(
                business_entity_id=business_entity_id,
                period_start=datetime.combine(start_date, datetime.min.time()),
                period_end=datetime.combine(end_date, datetime.max.time()),
                opening_balance=Decimal('0.00'),
                cash_inflows=Decimal('0.00'),
                cash_outflows=Decimal('0.00'),
                closing_balance=Decimal('0.00'),
                monthly_breakdown=[]
            )

        # Get opening balance (balance at start of period)
        opening_balance_query = db.query(func.sum(Account.balance)).filter(
            Account.id.in_(business_account_ids)
        )
        
        # Adjust for transactions before start date
        transactions_before = db.query(
            func.sum(
                case(
                    (Transaction.transaction_type == TransactionType.INCOME, Transaction.amount),
                    else_=-Transaction.amount
                )
            )
        ).filter(
            and_(
                Transaction.account_id.in_(business_account_ids),
                Transaction.date < start_date
            )
        ).scalar() or Decimal('0.00')

        current_balance = opening_balance_query.scalar() or Decimal('0.00')
        opening_balance = current_balance - transactions_before

        # Get cash inflows (income) for the period
        cash_inflows = db.query(func.sum(Transaction.amount)).filter(
            and_(
                Transaction.account_id.in_(business_account_ids),
                Transaction.transaction_type == TransactionType.INCOME,
                Transaction.date >= start_date,
                Transaction.date <= end_date
            )
        ).scalar() or Decimal('0.00')

        # Get cash outflows (expenses) for the period
        cash_outflows = db.query(func.sum(Transaction.amount)).filter(
            and_(
                Transaction.account_id.in_(business_account_ids),
                Transaction.transaction_type == TransactionType.EXPENSE,
                Transaction.date >= start_date,
                Transaction.date <= end_date
            )
        ).scalar() or Decimal('0.00')

        # Calculate closing balance
        closing_balance = opening_balance + cash_inflows - cash_outflows

        # Generate monthly breakdown
        monthly_breakdown = self._generate_monthly_cash_flow(
            db, business_account_ids, start_date, end_date
        )

        return CashFlowReport(
            business_entity_id=business_entity_id,
            period_start=datetime.combine(start_date, datetime.min.time()),
            period_end=datetime.combine(end_date, datetime.max.time()),
            opening_balance=opening_balance,
            cash_inflows=cash_inflows,
            cash_outflows=cash_outflows,
            closing_balance=closing_balance,
            monthly_breakdown=monthly_breakdown
        )

    def _generate_monthly_cash_flow(
        self, 
        db: Session, 
        account_ids: List[UUID], 
        start_date: date, 
        end_date: date
    ) -> List[Dict]:
        """Generate monthly cash flow breakdown"""
        monthly_data = []
        
        current_date = start_date.replace(day=1)  # Start from first day of month
        
        while current_date <= end_date:
            # Get last day of current month
            last_day = monthrange(current_date.year, current_date.month)[1]
            month_end = current_date.replace(day=last_day)
            
            # Don't go beyond end_date
            if month_end > end_date:
                month_end = end_date

            # Get inflows for the month
            inflows = db.query(func.sum(Transaction.amount)).filter(
                and_(
                    Transaction.account_id.in_(account_ids),
                    Transaction.transaction_type == TransactionType.INCOME,
                    Transaction.date >= current_date,
                    Transaction.date <= month_end
                )
            ).scalar() or Decimal('0.00')

            # Get outflows for the month
            outflows = db.query(func.sum(Transaction.amount)).filter(
                and_(
                    Transaction.account_id.in_(account_ids),
                    Transaction.transaction_type == TransactionType.EXPENSE,
                    Transaction.date >= current_date,
                    Transaction.date <= month_end
                )
            ).scalar() or Decimal('0.00')

            monthly_data.append({
                'month': current_date.strftime('%Y-%m'),
                'month_name': current_date.strftime('%B %Y'),
                'inflows': float(inflows),
                'outflows': float(outflows),
                'net_flow': float(inflows - outflows)
            })

            # Move to next month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)

        return monthly_data

    def get_invoice_analytics(self, db: Session, business_entity_id: UUID) -> Dict:
        """Get invoice analytics and metrics"""
        
        # Invoice status distribution
        status_distribution = db.query(
            Invoice.status,
            func.count(Invoice.id).label('count'),
            func.sum(Invoice.total_amount).label('total_amount')
        ).filter(
            Invoice.business_entity_id == business_entity_id
        ).group_by(Invoice.status).all()

        # Average payment time
        avg_payment_time = db.query(
            func.avg(
                func.extract('days', Invoice.paid_date - Invoice.invoice_date)
            )
        ).filter(
            and_(
                Invoice.business_entity_id == business_entity_id,
                Invoice.status == InvoiceStatus.PAID,
                Invoice.paid_date.isnot(None)
            )
        ).scalar()

        # Top clients by revenue
        top_clients = db.query(
            Client.name,
            func.sum(Invoice.total_amount).label('total_revenue'),
            func.count(Invoice.id).label('invoice_count')
        ).join(
            Invoice, Client.id == Invoice.client_id
        ).filter(
            and_(
                Invoice.business_entity_id == business_entity_id,
                Invoice.status == InvoiceStatus.PAID
            )
        ).group_by(Client.id, Client.name).order_by(
            func.sum(Invoice.total_amount).desc()
        ).limit(10).all()

        return {
            'status_distribution': [
                {
                    'status': status.value,
                    'count': count,
                    'total_amount': float(total_amount or 0)
                }
                for status, count, total_amount in status_distribution
            ],
            'average_payment_days': float(avg_payment_time or 0),
            'top_clients': [
                {
                    'name': name,
                    'total_revenue': float(revenue),
                    'invoice_count': count
                }
                for name, revenue, count in top_clients
            ]
        }

    def separate_business_expenses(
        self, 
        db: Session, 
        business_entity_id: UUID, 
        transaction_ids: List[UUID]
    ) -> Dict[str, int]:
        """Mark transactions as business expenses for separation"""
        
        # Get business account IDs
        business_account_ids = [
            acc.account_id for acc in db.query(BusinessAccount).filter(
                BusinessAccount.business_entity_id == business_entity_id
            ).all()
        ]

        # Update transactions to mark them as business expenses
        updated_count = 0
        for transaction_id in transaction_ids:
            transaction = db.query(Transaction).filter(
                and_(
                    Transaction.id == transaction_id,
                    Transaction.account_id.in_(business_account_ids)
                )
            ).first()
            
            if transaction:
                # You might want to add a business_entity_id field to Transaction model
                # or use tags to mark business expenses
                if hasattr(transaction, 'tags'):
                    tags = transaction.tags or []
                    if f"business:{business_entity_id}" not in tags:
                        tags.append(f"business:{business_entity_id}")
                        transaction.tags = tags
                        updated_count += 1

        db.commit()
        
        return {
            'updated_transactions': updated_count,
            'total_requested': len(transaction_ids)
        }


# Create service instance
business_service = BusinessService()