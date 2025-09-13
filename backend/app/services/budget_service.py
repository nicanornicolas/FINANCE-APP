from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Tuple
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID
import logging
from statistics import mean, stdev

from ..crud.budget import budget_crud, goal_crud, forecast_crud, alert_crud
from ..models.budget import BudgetPeriod, AlertType, AlertStatus, GoalStatus
from ..models.transaction import Transaction, TransactionType
from ..models.account import Account
from ..schemas.budget import (
    BudgetCreate, BudgetUpdate, FinancialGoalCreate, FinancialGoalUpdate,
    BudgetAlertCreate, CashFlowForecastCreate, BudgetAnalysis, CashFlowProjection
)

logger = logging.getLogger(__name__)


class BudgetService:
    """Service for budget management and financial planning"""

    def __init__(self):
        self.budget_crud = budget_crud
        self.goal_crud = goal_crud
        self.forecast_crud = forecast_crud
        self.alert_crud = alert_crud

    # Budget Management
    def create_budget(self, db: Session, budget_data: BudgetCreate, user_id: UUID):
        """Create a new budget with validation"""
        # Validate that total allocated amount doesn't exceed budget total
        total_allocated = sum(cat.allocated_amount for cat in budget_data.budget_categories)
        if total_allocated > budget_data.total_amount:
            raise ValueError("Total allocated amount cannot exceed budget total")

        return self.budget_crud.create_budget(db, budget_data, user_id)

    def get_budget_with_analysis(self, db: Session, budget_id: UUID, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get budget with detailed analysis"""
        budget = self.budget_crud.get_budget(db, budget_id, user_id)
        if not budget:
            return None

        analysis = self.budget_crud.get_budget_analysis(db, budget_id, user_id)
        return {
            "budget": budget,
            "analysis": analysis
        }

    def get_budget_vs_actual_comparison(self, db: Session, budget_id: UUID, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Compare budget vs actual spending with insights"""
        analysis = self.budget_crud.get_budget_analysis(db, budget_id, user_id)
        if not analysis:
            return None

        insights = []
        total_variance = analysis["total_budgeted"] - analysis["total_spent"]
        variance_percentage = (total_variance / analysis["total_budgeted"] * 100) if analysis["total_budgeted"] > 0 else 0

        # Generate insights
        if variance_percentage > 20:
            insights.append("You're significantly under budget - consider reallocating funds or increasing savings")
        elif variance_percentage < -10:
            insights.append("You're over budget - review spending in over-budget categories")
        elif abs(variance_percentage) <= 5:
            insights.append("Your spending is well-aligned with your budget")

        # Category-specific insights
        for category in analysis["categories"]:
            if category["percentage_used"] > 100:
                insights.append(f"'{category['category_name']}' is over budget by {category['percentage_used'] - 100:.1f}%")
            elif category["percentage_used"] > category["warning_threshold"]:
                insights.append(f"'{category['category_name']}' is approaching its limit at {category['percentage_used']:.1f}%")

        return {
            "budget_id": budget_id,
            "comparison_period": f"{analysis['period_start']} to {analysis['period_end']}",
            "categories": analysis["categories"],
            "total_variance": total_variance,
            "variance_percentage": variance_percentage,
            "insights": insights
        }

    def check_budget_alerts(self, db: Session, user_id: UUID) -> List[Dict[str, Any]]:
        """Check for budget alerts and create notifications"""
        alerts_created = []
        budgets = self.budget_crud.get_budgets(db, user_id, status=None)

        for budget in budgets:
            analysis = self.budget_crud.get_budget_analysis(db, budget.id, user_id)
            if not analysis:
                continue

            # Check for over-budget categories
            for category_id in analysis["categories_over_budget"]:
                category_info = next((cat for cat in analysis["categories"] if cat["category_id"] == category_id), None)
                if category_info:
                    alert = BudgetAlertCreate(
                        budget_id=budget.id,
                        alert_type=AlertType.BUDGET_EXCEEDED,
                        title=f"Budget Exceeded: {category_info['category_name']}",
                        message=f"You've exceeded your budget for {category_info['category_name']} by {category_info['spent_amount'] - category_info['allocated_amount']:.2f}",
                        severity="error"
                    )
                    created_alert = self.alert_crud.create_alert(db, alert, user_id)
                    alerts_created.append(created_alert)

            # Check for categories near limit
            for category_id in analysis["categories_near_limit"]:
                category_info = next((cat for cat in analysis["categories"] if cat["category_id"] == category_id), None)
                if category_info:
                    alert = BudgetAlertCreate(
                        budget_id=budget.id,
                        alert_type=AlertType.BUDGET_WARNING,
                        title=f"Budget Warning: {category_info['category_name']}",
                        message=f"You've used {category_info['percentage_used']:.1f}% of your budget for {category_info['category_name']}",
                        severity="warning"
                    )
                    created_alert = self.alert_crud.create_alert(db, alert, user_id)
                    alerts_created.append(created_alert)

        return alerts_created

    # Financial Goal Management
    def create_financial_goal(self, db: Session, goal_data: FinancialGoalCreate, user_id: UUID):
        """Create a financial goal with validation"""
        # Validate milestone amounts don't exceed target
        if goal_data.goal_milestones:
            max_milestone = max(milestone.target_amount for milestone in goal_data.goal_milestones)
            if max_milestone > goal_data.target_amount:
                raise ValueError("Milestone target cannot exceed goal target")

        return self.goal_crud.create_goal(db, goal_data, user_id)

    def get_goal_progress_analysis(self, db: Session, goal_id: UUID, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get detailed goal progress analysis"""
        goal = self.goal_crud.get_goal(db, goal_id, user_id)
        if not goal:
            return None

        progress_percentage = (goal.current_amount / goal.target_amount * 100) if goal.target_amount > 0 else 0
        remaining_amount = goal.target_amount - goal.current_amount

        analysis = {
            "goal": goal,
            "progress_percentage": progress_percentage,
            "remaining_amount": remaining_amount,
            "is_on_track": True,
            "days_remaining": None,
            "monthly_required_contribution": None,
            "recommendations": []
        }

        if goal.target_date:
            days_remaining = (goal.target_date - date.today()).days
            analysis["days_remaining"] = days_remaining

            if days_remaining > 0:
                months_remaining = days_remaining / 30.44  # Average days per month
                if months_remaining > 0:
                    analysis["monthly_required_contribution"] = remaining_amount / Decimal(str(months_remaining))

                # Check if on track
                expected_progress = (1 - (days_remaining / ((goal.target_date - goal.created_at.date()).days))) * 100
                analysis["is_on_track"] = progress_percentage >= expected_progress * 0.9  # 10% tolerance

                if not analysis["is_on_track"]:
                    analysis["recommendations"].append(
                        f"Consider increasing contributions to {analysis['monthly_required_contribution']:.2f} per month to stay on track"
                    )

        # Check milestones
        achieved_milestones = sum(1 for milestone in goal.goal_milestones if milestone.is_achieved)
        total_milestones = len(goal.goal_milestones)
        if total_milestones > 0:
            milestone_progress = (achieved_milestones / total_milestones) * 100
            if milestone_progress < progress_percentage * 0.8:
                analysis["recommendations"].append("Update your milestone progress to better track your goal")

        return analysis

    def check_goal_milestones(self, db: Session, user_id: UUID) -> List[Dict[str, Any]]:
        """Check for achieved goal milestones and create alerts"""
        alerts_created = []
        goals = self.goal_crud.get_goals(db, user_id, status=GoalStatus.ACTIVE)

        for goal in goals:
            for milestone in goal.goal_milestones:
                if not milestone.is_achieved and goal.current_amount >= milestone.target_amount:
                    # Mark milestone as achieved
                    milestone.is_achieved = True
                    milestone.achieved_date = date.today()
                    db.commit()

                    # Create alert
                    alert = BudgetAlertCreate(
                        goal_id=goal.id,
                        alert_type=AlertType.GOAL_MILESTONE,
                        title=f"Milestone Achieved: {milestone.name}",
                        message=f"Congratulations! You've reached the milestone '{milestone.name}' for your goal '{goal.name}'",
                        severity="info"
                    )
                    created_alert = self.alert_crud.create_alert(db, alert, user_id)
                    alerts_created.append(created_alert)

        return alerts_created

    # Cash Flow Forecasting
    def generate_cash_flow_forecast(self, db: Session, user_id: UUID, months_ahead: int = 6) -> CashFlowProjection:
        """Generate cash flow forecast using historical data"""
        # Get historical transaction data (last 12 months for better prediction)
        end_date = date.today()
        start_date = end_date - timedelta(days=365)

        # Get user's accounts
        accounts = db.query(Account).filter(Account.user_id == user_id).all()
        account_ids = [account.id for account in accounts]

        if not account_ids:
            return CashFlowProjection(
                user_id=user_id,
                projection_months=months_ahead,
                starting_balance=Decimal('0.00'),
                monthly_forecasts=[],
                projected_end_balance=Decimal('0.00'),
                cash_flow_warnings=[],
                recommendations=[]
            )

        # Get historical transactions
        transactions = db.query(Transaction).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_date,
            Transaction.date <= end_date
        ).all()

        # Calculate monthly averages
        monthly_income = []
        monthly_expenses = []

        for i in range(12):
            month_start = end_date - timedelta(days=30 * (i + 1))
            month_end = end_date - timedelta(days=30 * i)

            month_income = sum(
                t.amount for t in transactions 
                if t.transaction_type == TransactionType.INCOME and month_start <= t.date <= month_end
            )
            month_expenses = sum(
                t.amount for t in transactions 
                if t.transaction_type == TransactionType.EXPENSE and month_start <= t.date <= month_end
            )

            monthly_income.append(month_income)
            monthly_expenses.append(month_expenses)

        # Calculate averages and trends
        avg_income = Decimal(str(mean(monthly_income))) if monthly_income else Decimal('0.00')
        avg_expenses = Decimal(str(mean(monthly_expenses))) if monthly_expenses else Decimal('0.00')

        # Calculate current balance
        current_balance = sum(account.balance for account in accounts)

        # Generate forecasts
        forecasts = []
        running_balance = current_balance
        warnings = []
        recommendations = []

        for month in range(1, months_ahead + 1):
            forecast_date = end_date + timedelta(days=30 * month)
            
            # Apply some variability (±10% for more realistic forecasting)
            income_variance = avg_income * Decimal('0.1')
            expense_variance = avg_expenses * Decimal('0.1')
            
            predicted_income = avg_income
            predicted_expenses = avg_expenses
            predicted_balance = running_balance + predicted_income - predicted_expenses

            # Create forecast record
            forecast = CashFlowForecastCreate(
                forecast_date=forecast_date,
                predicted_income=predicted_income,
                predicted_expenses=predicted_expenses,
                predicted_balance=predicted_balance,
                confidence_score=Decimal('75.0'),  # Base confidence
                model_version="historical_average_v1"
            )

            forecast_record = self.forecast_crud.create_forecast(db, forecast, user_id)
            forecasts.append(forecast_record)

            # Check for warnings
            if predicted_balance < Decimal('0.00'):
                warnings.append(f"Projected negative balance in {forecast_date.strftime('%B %Y')}: {predicted_balance:.2f}")
            elif predicted_balance < avg_expenses * Decimal('0.5'):  # Less than half a month's expenses
                warnings.append(f"Low cash reserves projected for {forecast_date.strftime('%B %Y')}")

            running_balance = predicted_balance

        # Generate recommendations
        if running_balance < current_balance:
            recommendations.append("Consider reducing expenses or increasing income to improve cash flow")
        
        if any(balance < Decimal('0.00') for balance in [f.predicted_balance for f in forecasts]):
            recommendations.append("Build an emergency fund to avoid cash flow shortfalls")

        avg_monthly_savings = avg_income - avg_expenses
        if avg_monthly_savings > Decimal('0.00'):
            recommendations.append(f"You save an average of {avg_monthly_savings:.2f} per month - consider setting up automatic investments")

        return CashFlowProjection(
            user_id=user_id,
            projection_months=months_ahead,
            starting_balance=current_balance,
            monthly_forecasts=forecasts,
            projected_end_balance=running_balance,
            cash_flow_warnings=warnings,
            recommendations=recommendations
        )

    def check_cash_flow_warnings(self, db: Session, user_id: UUID) -> List[Dict[str, Any]]:
        """Check for cash flow warnings and create alerts"""
        alerts_created = []
        
        # Get recent forecasts
        forecasts = self.forecast_crud.get_forecasts(
            db, user_id, 
            start_date=date.today(),
            end_date=date.today() + timedelta(days=90),
            limit=3
        )

        for forecast in forecasts:
            if forecast.predicted_balance < Decimal('0.00'):
                alert = BudgetAlertCreate(
                    alert_type=AlertType.CASH_FLOW_WARNING,
                    title="Cash Flow Warning",
                    message=f"Projected negative balance of {forecast.predicted_balance:.2f} on {forecast.forecast_date}",
                    severity="warning"
                )
                created_alert = self.alert_crud.create_alert(db, alert, user_id)
                alerts_created.append(created_alert)

        return alerts_created

    # Notification and Alert Management
    def process_all_alerts(self, db: Session, user_id: UUID) -> Dict[str, List]:
        """Process all types of alerts for a user"""
        all_alerts = {
            "budget_alerts": self.check_budget_alerts(db, user_id),
            "goal_alerts": self.check_goal_milestones(db, user_id),
            "cash_flow_alerts": self.check_cash_flow_warnings(db, user_id)
        }
        
        total_alerts = sum(len(alerts) for alerts in all_alerts.values())
        logger.info(f"Processed {total_alerts} alerts for user {user_id}")
        
        return all_alerts

    # Utility Methods
    def get_budget_summary(self, db: Session, user_id: UUID) -> Dict[str, Any]:
        """Get a summary of all budgets for a user"""
        budgets = self.budget_crud.get_budgets(db, user_id)
        
        summary = {
            "total_budgets": len(budgets),
            "active_budgets": len([b for b in budgets if b.status.value == "active"]),
            "total_budgeted": sum(b.total_amount for b in budgets if b.status.value == "active"),
            "budgets_over_limit": 0,
            "budgets_near_limit": 0
        }

        for budget in budgets:
            if budget.status.value == "active":
                analysis = self.budget_crud.get_budget_analysis(db, budget.id, user_id)
                if analysis:
                    if analysis["percentage_used"] > 100:
                        summary["budgets_over_limit"] += 1
                    elif analysis["percentage_used"] > 80:
                        summary["budgets_near_limit"] += 1

        return summary

    def get_goals_summary(self, db: Session, user_id: UUID) -> Dict[str, Any]:
        """Get a summary of all financial goals for a user"""
        goals = self.goal_crud.get_goals(db, user_id)
        
        summary = {
            "total_goals": len(goals),
            "active_goals": len([g for g in goals if g.status == GoalStatus.ACTIVE]),
            "completed_goals": len([g for g in goals if g.status == GoalStatus.COMPLETED]),
            "total_target_amount": sum(g.target_amount for g in goals if g.status == GoalStatus.ACTIVE),
            "total_current_amount": sum(g.current_amount for g in goals if g.status == GoalStatus.ACTIVE),
            "goals_on_track": 0,
            "goals_behind": 0
        }

        for goal in goals:
            if goal.status == GoalStatus.ACTIVE and goal.target_date:
                analysis = self.get_goal_progress_analysis(db, goal.id, user_id)
                if analysis:
                    if analysis["is_on_track"]:
                        summary["goals_on_track"] += 1
                    else:
                        summary["goals_behind"] += 1

        return summary


# Create service instance
budget_service = BudgetService()