from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc, asc
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from ..models.budget import (
    Budget, BudgetCategory, FinancialGoal, GoalMilestone, 
    CashFlowForecast, BudgetAlert, BudgetStatus, GoalStatus, AlertStatus
)
from ..models.transaction import Transaction, TransactionType
from ..models.category import Category
from ..schemas.budget import (
    BudgetCreate, BudgetUpdate, BudgetCategoryCreate, BudgetCategoryUpdate,
    FinancialGoalCreate, FinancialGoalUpdate, GoalMilestoneCreate, GoalMilestoneUpdate,
    CashFlowForecastCreate, BudgetAlertCreate, BudgetAlertUpdate
)


class BudgetCRUD:
    def create_budget(self, db: Session, budget_data: BudgetCreate, user_id: UUID) -> Budget:
        """Create a new budget with categories"""
        # Create the budget
        budget = Budget(
            user_id=user_id,
            name=budget_data.name,
            description=budget_data.description,
            period=budget_data.period,
            start_date=budget_data.start_date,
            end_date=budget_data.end_date,
            total_amount=budget_data.total_amount,
            status=budget_data.status,
            is_template=budget_data.is_template
        )
        db.add(budget)
        db.flush()  # Get the budget ID

        # Create budget categories
        for category_data in budget_data.budget_categories:
            budget_category = BudgetCategory(
                budget_id=budget.id,
                category_id=category_data.category_id,
                allocated_amount=category_data.allocated_amount,
                warning_threshold=category_data.warning_threshold,
                notes=category_data.notes
            )
            db.add(budget_category)

        db.commit()
        db.refresh(budget)
        return budget

    def get_budget(self, db: Session, budget_id: UUID, user_id: UUID) -> Optional[Budget]:
        """Get a budget by ID for a specific user"""
        return db.query(Budget).options(
            joinedload(Budget.budget_categories).joinedload(BudgetCategory.category)
        ).filter(
            and_(Budget.id == budget_id, Budget.user_id == user_id)
        ).first()

    def get_budgets(
        self, 
        db: Session, 
        user_id: UUID, 
        skip: int = 0, 
        limit: int = 100,
        status: Optional[BudgetStatus] = None,
        is_template: Optional[bool] = None
    ) -> List[Budget]:
        """Get budgets for a user with optional filtering"""
        query = db.query(Budget).options(
            joinedload(Budget.budget_categories).joinedload(BudgetCategory.category)
        ).filter(Budget.user_id == user_id)

        if status:
            query = query.filter(Budget.status == status)
        if is_template is not None:
            query = query.filter(Budget.is_template == is_template)

        return query.order_by(desc(Budget.created_at)).offset(skip).limit(limit).all()

    def update_budget(self, db: Session, budget_id: UUID, user_id: UUID, budget_data: BudgetUpdate) -> Optional[Budget]:
        """Update a budget"""
        budget = self.get_budget(db, budget_id, user_id)
        if not budget:
            return None

        update_data = budget_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(budget, field, value)

        db.commit()
        db.refresh(budget)
        return budget

    def delete_budget(self, db: Session, budget_id: UUID, user_id: UUID) -> bool:
        """Delete a budget"""
        budget = self.get_budget(db, budget_id, user_id)
        if not budget:
            return False

        db.delete(budget)
        db.commit()
        return True

    def get_budget_analysis(self, db: Session, budget_id: UUID, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get detailed budget analysis with spending data"""
        budget = self.get_budget(db, budget_id, user_id)
        if not budget:
            return None

        # Calculate spending for each category in the budget period
        analysis = {
            "budget_id": budget_id,
            "period_start": budget.start_date,
            "period_end": budget.end_date or date.today(),
            "total_budgeted": budget.total_amount,
            "categories": [],
            "total_spent": Decimal('0.00'),
            "categories_over_budget": [],
            "categories_near_limit": []
        }

        for budget_category in budget.budget_categories:
            # Get actual spending for this category in the budget period
            spent_query = db.query(func.sum(Transaction.amount)).filter(
                and_(
                    Transaction.category_id == budget_category.category_id,
                    Transaction.transaction_type == TransactionType.EXPENSE,
                    Transaction.date >= budget.start_date,
                    Transaction.date <= (budget.end_date or date.today())
                )
            ).join(Transaction.account).filter(
                Transaction.account.has(user_id=user_id)
            )

            spent_amount = spent_query.scalar() or Decimal('0.00')
            analysis["total_spent"] += spent_amount

            remaining = budget_category.allocated_amount - spent_amount
            percentage_used = (spent_amount / budget_category.allocated_amount * 100) if budget_category.allocated_amount > 0 else 0

            category_analysis = {
                "category_id": budget_category.category_id,
                "category_name": budget_category.category.name,
                "allocated_amount": budget_category.allocated_amount,
                "spent_amount": spent_amount,
                "remaining_amount": remaining,
                "percentage_used": percentage_used,
                "warning_threshold": budget_category.warning_threshold
            }

            analysis["categories"].append(category_analysis)

            # Check for over-budget or near-limit categories
            if spent_amount > budget_category.allocated_amount:
                analysis["categories_over_budget"].append(budget_category.category_id)
            elif percentage_used >= budget_category.warning_threshold:
                analysis["categories_near_limit"].append(budget_category.category_id)

        analysis["total_remaining"] = budget.total_amount - analysis["total_spent"]
        analysis["percentage_used"] = (analysis["total_spent"] / budget.total_amount * 100) if budget.total_amount > 0 else 0

        return analysis

    def add_budget_category(self, db: Session, budget_id: UUID, user_id: UUID, category_data: BudgetCategoryCreate) -> Optional[BudgetCategory]:
        """Add a category to an existing budget"""
        budget = self.get_budget(db, budget_id, user_id)
        if not budget:
            return None

        budget_category = BudgetCategory(
            budget_id=budget_id,
            category_id=category_data.category_id,
            allocated_amount=category_data.allocated_amount,
            warning_threshold=category_data.warning_threshold,
            notes=category_data.notes
        )
        db.add(budget_category)
        db.commit()
        db.refresh(budget_category)
        return budget_category

    def update_budget_category(self, db: Session, category_id: UUID, user_id: UUID, category_data: BudgetCategoryUpdate) -> Optional[BudgetCategory]:
        """Update a budget category"""
        budget_category = db.query(BudgetCategory).join(Budget).filter(
            and_(
                BudgetCategory.id == category_id,
                Budget.user_id == user_id
            )
        ).first()

        if not budget_category:
            return None

        update_data = category_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(budget_category, field, value)

        db.commit()
        db.refresh(budget_category)
        return budget_category

    def remove_budget_category(self, db: Session, category_id: UUID, user_id: UUID) -> bool:
        """Remove a category from a budget"""
        budget_category = db.query(BudgetCategory).join(Budget).filter(
            and_(
                BudgetCategory.id == category_id,
                Budget.user_id == user_id
            )
        ).first()

        if not budget_category:
            return False

        db.delete(budget_category)
        db.commit()
        return True


class FinancialGoalCRUD:
    def create_goal(self, db: Session, goal_data: FinancialGoalCreate, user_id: UUID) -> FinancialGoal:
        """Create a new financial goal with milestones"""
        goal = FinancialGoal(
            user_id=user_id,
            name=goal_data.name,
            description=goal_data.description,
            goal_type=goal_data.goal_type,
            target_amount=goal_data.target_amount,
            target_date=goal_data.target_date,
            category_id=goal_data.category_id,
            status=goal_data.status,
            priority=goal_data.priority,
            auto_contribute=goal_data.auto_contribute,
            contribution_amount=goal_data.contribution_amount,
            contribution_frequency=goal_data.contribution_frequency
        )
        db.add(goal)
        db.flush()

        # Create milestones
        for milestone_data in goal_data.goal_milestones:
            milestone = GoalMilestone(
                goal_id=goal.id,
                name=milestone_data.name,
                target_amount=milestone_data.target_amount,
                target_date=milestone_data.target_date,
                notes=milestone_data.notes
            )
            db.add(milestone)

        db.commit()
        db.refresh(goal)
        return goal

    def get_goal(self, db: Session, goal_id: UUID, user_id: UUID) -> Optional[FinancialGoal]:
        """Get a financial goal by ID"""
        return db.query(FinancialGoal).options(
            joinedload(FinancialGoal.goal_milestones),
            joinedload(FinancialGoal.category)
        ).filter(
            and_(FinancialGoal.id == goal_id, FinancialGoal.user_id == user_id)
        ).first()

    def get_goals(
        self, 
        db: Session, 
        user_id: UUID, 
        skip: int = 0, 
        limit: int = 100,
        status: Optional[GoalStatus] = None,
        goal_type: Optional[str] = None
    ) -> List[FinancialGoal]:
        """Get financial goals for a user"""
        query = db.query(FinancialGoal).options(
            joinedload(FinancialGoal.goal_milestones),
            joinedload(FinancialGoal.category)
        ).filter(FinancialGoal.user_id == user_id)

        if status:
            query = query.filter(FinancialGoal.status == status)
        if goal_type:
            query = query.filter(FinancialGoal.goal_type == goal_type)

        return query.order_by(asc(FinancialGoal.priority), desc(FinancialGoal.created_at)).offset(skip).limit(limit).all()

    def update_goal(self, db: Session, goal_id: UUID, user_id: UUID, goal_data: FinancialGoalUpdate) -> Optional[FinancialGoal]:
        """Update a financial goal"""
        goal = self.get_goal(db, goal_id, user_id)
        if not goal:
            return None

        update_data = goal_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(goal, field, value)

        db.commit()
        db.refresh(goal)
        return goal

    def delete_goal(self, db: Session, goal_id: UUID, user_id: UUID) -> bool:
        """Delete a financial goal"""
        goal = self.get_goal(db, goal_id, user_id)
        if not goal:
            return False

        db.delete(goal)
        db.commit()
        return True

    def update_goal_progress(self, db: Session, goal_id: UUID, user_id: UUID, amount: Decimal) -> Optional[FinancialGoal]:
        """Update goal progress by adding to current amount"""
        goal = self.get_goal(db, goal_id, user_id)
        if not goal:
            return None

        goal.current_amount += amount
        
        # Check if goal is completed
        if goal.current_amount >= goal.target_amount and goal.status == GoalStatus.ACTIVE:
            goal.status = GoalStatus.COMPLETED

        db.commit()
        db.refresh(goal)
        return goal

    def add_milestone(self, db: Session, goal_id: UUID, user_id: UUID, milestone_data: GoalMilestoneCreate) -> Optional[GoalMilestone]:
        """Add a milestone to a goal"""
        goal = self.get_goal(db, goal_id, user_id)
        if not goal:
            return None

        milestone = GoalMilestone(
            goal_id=goal_id,
            name=milestone_data.name,
            target_amount=milestone_data.target_amount,
            target_date=milestone_data.target_date,
            notes=milestone_data.notes
        )
        db.add(milestone)
        db.commit()
        db.refresh(milestone)
        return milestone

    def update_milestone(self, db: Session, milestone_id: UUID, user_id: UUID, milestone_data: GoalMilestoneUpdate) -> Optional[GoalMilestone]:
        """Update a goal milestone"""
        milestone = db.query(GoalMilestone).join(FinancialGoal).filter(
            and_(
                GoalMilestone.id == milestone_id,
                FinancialGoal.user_id == user_id
            )
        ).first()

        if not milestone:
            return None

        update_data = milestone_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(milestone, field, value)

        # Set achieved date if marking as achieved
        if milestone_data.is_achieved and not milestone.achieved_date:
            milestone.achieved_date = date.today()

        db.commit()
        db.refresh(milestone)
        return milestone


class CashFlowForecastCRUD:
    def create_forecast(self, db: Session, forecast_data: CashFlowForecastCreate, user_id: UUID) -> CashFlowForecast:
        """Create a cash flow forecast"""
        forecast = CashFlowForecast(
            user_id=user_id,
            forecast_date=forecast_data.forecast_date,
            predicted_income=forecast_data.predicted_income,
            predicted_expenses=forecast_data.predicted_expenses,
            predicted_balance=forecast_data.predicted_balance,
            confidence_score=forecast_data.confidence_score,
            model_version=forecast_data.model_version
        )
        db.add(forecast)
        db.commit()
        db.refresh(forecast)
        return forecast

    def get_forecasts(
        self, 
        db: Session, 
        user_id: UUID, 
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100
    ) -> List[CashFlowForecast]:
        """Get cash flow forecasts for a user"""
        query = db.query(CashFlowForecast).filter(CashFlowForecast.user_id == user_id)

        if start_date:
            query = query.filter(CashFlowForecast.forecast_date >= start_date)
        if end_date:
            query = query.filter(CashFlowForecast.forecast_date <= end_date)

        return query.order_by(asc(CashFlowForecast.forecast_date)).limit(limit).all()

    def delete_old_forecasts(self, db: Session, user_id: UUID, older_than_days: int = 90) -> int:
        """Delete old forecasts to keep the table clean"""
        cutoff_date = date.today() - timedelta(days=older_than_days)
        deleted_count = db.query(CashFlowForecast).filter(
            and_(
                CashFlowForecast.user_id == user_id,
                CashFlowForecast.forecast_date < cutoff_date
            )
        ).delete()
        db.commit()
        return deleted_count


class BudgetAlertCRUD:
    def create_alert(self, db: Session, alert_data: BudgetAlertCreate, user_id: UUID) -> BudgetAlert:
        """Create a budget alert"""
        alert = BudgetAlert(
            user_id=user_id,
            budget_id=alert_data.budget_id,
            goal_id=alert_data.goal_id,
            alert_type=alert_data.alert_type,
            title=alert_data.title,
            message=alert_data.message,
            severity=alert_data.severity
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert

    def get_alerts(
        self, 
        db: Session, 
        user_id: UUID, 
        skip: int = 0, 
        limit: int = 100,
        status: Optional[AlertStatus] = None,
        unread_only: bool = False
    ) -> List[BudgetAlert]:
        """Get budget alerts for a user"""
        query = db.query(BudgetAlert).filter(BudgetAlert.user_id == user_id)

        if status:
            query = query.filter(BudgetAlert.status == status)
        if unread_only:
            query = query.filter(BudgetAlert.read_at.is_(None))

        return query.order_by(desc(BudgetAlert.triggered_at)).offset(skip).limit(limit).all()

    def update_alert(self, db: Session, alert_id: UUID, user_id: UUID, alert_data: BudgetAlertUpdate) -> Optional[BudgetAlert]:
        """Update a budget alert"""
        alert = db.query(BudgetAlert).filter(
            and_(BudgetAlert.id == alert_id, BudgetAlert.user_id == user_id)
        ).first()

        if not alert:
            return None

        if alert_data.status == AlertStatus.READ and not alert.read_at:
            alert.read_at = datetime.utcnow()

        alert.status = alert_data.status
        db.commit()
        db.refresh(alert)
        return alert

    def mark_alerts_as_read(self, db: Session, user_id: UUID, alert_ids: List[UUID]) -> int:
        """Mark multiple alerts as read"""
        updated_count = db.query(BudgetAlert).filter(
            and_(
                BudgetAlert.user_id == user_id,
                BudgetAlert.id.in_(alert_ids),
                BudgetAlert.read_at.is_(None)
            )
        ).update({
            BudgetAlert.status: AlertStatus.READ,
            BudgetAlert.read_at: datetime.utcnow()
        }, synchronize_session=False)
        
        db.commit()
        return updated_count

    def get_unread_count(self, db: Session, user_id: UUID) -> int:
        """Get count of unread alerts"""
        return db.query(BudgetAlert).filter(
            and_(
                BudgetAlert.user_id == user_id,
                BudgetAlert.read_at.is_(None)
            )
        ).count()


# Create instances
budget_crud = BudgetCRUD()
goal_crud = FinancialGoalCRUD()
forecast_crud = CashFlowForecastCRUD()
alert_crud = BudgetAlertCRUD()