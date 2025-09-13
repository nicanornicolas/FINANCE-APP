from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from uuid import UUID

from ...db.database import get_db
from ...api.dependencies import get_current_user
from ...models.user import User
from ...models.budget import BudgetStatus, GoalStatus, AlertStatus
from ...schemas.budget import (
    BudgetCreate, BudgetUpdate, BudgetResponse, BudgetListResponse,
    BudgetCategoryCreate, BudgetCategoryUpdate, BudgetCategoryResponse,
    FinancialGoalCreate, FinancialGoalUpdate, FinancialGoalResponse, FinancialGoalListResponse,
    GoalMilestoneCreate, GoalMilestoneUpdate, GoalMilestoneResponse,
    BudgetAlertResponse, BudgetAlertListResponse, BudgetAlertUpdate,
    BudgetAnalysis, BudgetVsActualComparison, CashFlowProjection
)
from ...services.budget_service import budget_service
from ...crud.budget import budget_crud, goal_crud, alert_crud

router = APIRouter(prefix="/budget", tags=["budget"])


# Budget Management Endpoints
@router.post("/budgets", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(
    budget_data: BudgetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new budget"""
    try:
        budget = budget_service.create_budget(db, budget_data, current_user.id)
        return budget
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/budgets", response_model=BudgetListResponse)
async def get_budgets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[BudgetStatus] = None,
    is_template: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's budgets with optional filtering"""
    budgets = budget_crud.get_budgets(
        db, current_user.id, skip=skip, limit=limit, 
        status=status, is_template=is_template
    )
    
    # Get total count for pagination
    total_count = len(budget_crud.get_budgets(db, current_user.id, status=status, is_template=is_template))
    
    return BudgetListResponse(
        budgets=budgets,
        total_count=total_count,
        page=skip // limit + 1,
        page_size=limit
    )


@router.get("/budgets/{budget_id}", response_model=BudgetResponse)
async def get_budget(
    budget_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific budget"""
    budget = budget_crud.get_budget(db, budget_id, current_user.id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    return budget


@router.put("/budgets/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: UUID,
    budget_data: BudgetUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a budget"""
    budget = budget_crud.update_budget(db, budget_id, current_user.id, budget_data)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    return budget


@router.delete("/budgets/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a budget"""
    success = budget_crud.delete_budget(db, budget_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Budget not found")


@router.get("/budgets/{budget_id}/analysis", response_model=BudgetAnalysis)
async def get_budget_analysis(
    budget_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed budget analysis"""
    analysis = budget_crud.get_budget_analysis(db, budget_id, current_user.id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Budget not found")
    return analysis


@router.get("/budgets/{budget_id}/comparison", response_model=BudgetVsActualComparison)
async def get_budget_comparison(
    budget_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get budget vs actual comparison with insights"""
    comparison = budget_service.get_budget_vs_actual_comparison(db, budget_id, current_user.id)
    if not comparison:
        raise HTTPException(status_code=404, detail="Budget not found")
    return comparison


# Budget Category Management
@router.post("/budgets/{budget_id}/categories", response_model=BudgetCategoryResponse, status_code=status.HTTP_201_CREATED)
async def add_budget_category(
    budget_id: UUID,
    category_data: BudgetCategoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a category to a budget"""
    category = budget_crud.add_budget_category(db, budget_id, current_user.id, category_data)
    if not category:
        raise HTTPException(status_code=404, detail="Budget not found")
    return category


@router.put("/budget-categories/{category_id}", response_model=BudgetCategoryResponse)
async def update_budget_category(
    category_id: UUID,
    category_data: BudgetCategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a budget category"""
    category = budget_crud.update_budget_category(db, category_id, current_user.id, category_data)
    if not category:
        raise HTTPException(status_code=404, detail="Budget category not found")
    return category


@router.delete("/budget-categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_budget_category(
    category_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a category from a budget"""
    success = budget_crud.remove_budget_category(db, category_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Budget category not found")


# Financial Goals Management
@router.post("/goals", response_model=FinancialGoalResponse, status_code=status.HTTP_201_CREATED)
async def create_financial_goal(
    goal_data: FinancialGoalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new financial goal"""
    try:
        goal = budget_service.create_financial_goal(db, goal_data, current_user.id)
        return goal
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/goals", response_model=FinancialGoalListResponse)
async def get_financial_goals(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[GoalStatus] = None,
    goal_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's financial goals"""
    goals = goal_crud.get_goals(
        db, current_user.id, skip=skip, limit=limit,
        status=status, goal_type=goal_type
    )
    
    # Get total count for pagination
    total_count = len(goal_crud.get_goals(db, current_user.id, status=status, goal_type=goal_type))
    
    return FinancialGoalListResponse(
        goals=goals,
        total_count=total_count,
        page=skip // limit + 1,
        page_size=limit
    )


@router.get("/goals/{goal_id}", response_model=FinancialGoalResponse)
async def get_financial_goal(
    goal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific financial goal"""
    goal = goal_crud.get_goal(db, goal_id, current_user.id)
    if not goal:
        raise HTTPException(status_code=404, detail="Financial goal not found")
    return goal


@router.put("/goals/{goal_id}", response_model=FinancialGoalResponse)
async def update_financial_goal(
    goal_id: UUID,
    goal_data: FinancialGoalUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a financial goal"""
    goal = goal_crud.update_goal(db, goal_id, current_user.id, goal_data)
    if not goal:
        raise HTTPException(status_code=404, detail="Financial goal not found")
    return goal


@router.delete("/goals/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_financial_goal(
    goal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a financial goal"""
    success = goal_crud.delete_goal(db, goal_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Financial goal not found")


@router.get("/goals/{goal_id}/analysis")
async def get_goal_analysis(
    goal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed goal progress analysis"""
    analysis = budget_service.get_goal_progress_analysis(db, goal_id, current_user.id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Financial goal not found")
    return analysis


@router.post("/goals/{goal_id}/contribute")
async def contribute_to_goal(
    goal_id: UUID,
    amount: float,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a contribution to a financial goal"""
    from decimal import Decimal
    goal = goal_crud.update_goal_progress(db, goal_id, current_user.id, Decimal(str(amount)))
    if not goal:
        raise HTTPException(status_code=404, detail="Financial goal not found")
    return {"message": "Contribution added successfully", "new_amount": goal.current_amount}


# Goal Milestones
@router.post("/goals/{goal_id}/milestones", response_model=GoalMilestoneResponse, status_code=status.HTTP_201_CREATED)
async def add_goal_milestone(
    goal_id: UUID,
    milestone_data: GoalMilestoneCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a milestone to a goal"""
    milestone = goal_crud.add_milestone(db, goal_id, current_user.id, milestone_data)
    if not milestone:
        raise HTTPException(status_code=404, detail="Financial goal not found")
    return milestone


@router.put("/milestones/{milestone_id}", response_model=GoalMilestoneResponse)
async def update_goal_milestone(
    milestone_id: UUID,
    milestone_data: GoalMilestoneUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a goal milestone"""
    milestone = goal_crud.update_milestone(db, milestone_id, current_user.id, milestone_data)
    if not milestone:
        raise HTTPException(status_code=404, detail="Goal milestone not found")
    return milestone


# Cash Flow Forecasting
@router.get("/cash-flow/forecast", response_model=CashFlowProjection)
async def get_cash_flow_forecast(
    months_ahead: int = Query(6, ge=1, le=24),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate cash flow forecast"""
    forecast = budget_service.generate_cash_flow_forecast(db, current_user.id, months_ahead)
    return forecast


# Alerts and Notifications
@router.get("/alerts", response_model=BudgetAlertListResponse)
async def get_budget_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[AlertStatus] = None,
    unread_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get budget alerts"""
    alerts = alert_crud.get_alerts(
        db, current_user.id, skip=skip, limit=limit,
        status=status, unread_only=unread_only
    )
    
    total_count = len(alert_crud.get_alerts(db, current_user.id, status=status, unread_only=unread_only))
    unread_count = alert_crud.get_unread_count(db, current_user.id)
    
    return BudgetAlertListResponse(
        alerts=alerts,
        total_count=total_count,
        unread_count=unread_count,
        page=skip // limit + 1,
        page_size=limit
    )


@router.put("/alerts/{alert_id}", response_model=BudgetAlertResponse)
async def update_budget_alert(
    alert_id: UUID,
    alert_data: BudgetAlertUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a budget alert (mark as read, etc.)"""
    alert = alert_crud.update_alert(db, alert_id, current_user.id, alert_data)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.post("/alerts/mark-read")
async def mark_alerts_as_read(
    alert_ids: List[UUID],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark multiple alerts as read"""
    updated_count = alert_crud.mark_alerts_as_read(db, current_user.id, alert_ids)
    return {"message": f"Marked {updated_count} alerts as read"}


@router.post("/alerts/process")
async def process_all_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Process all types of alerts for the current user"""
    alerts = budget_service.process_all_alerts(db, current_user.id)
    total_alerts = sum(len(alert_list) for alert_list in alerts.values())
    return {
        "message": f"Processed {total_alerts} alerts",
        "alerts": alerts
    }


# Summary and Dashboard Endpoints
@router.get("/summary")
async def get_budget_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get budget and goals summary for dashboard"""
    budget_summary = budget_service.get_budget_summary(db, current_user.id)
    goals_summary = budget_service.get_goals_summary(db, current_user.id)
    
    return {
        "budgets": budget_summary,
        "goals": goals_summary
    }