"""
Category management API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from ...db.database import get_db
from ...crud import category as crud_category
from ...schemas.category import CategoryCreate, CategoryUpdate, CategoryInDB
from ...models.user import User
from ..dependencies import get_current_user

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=List[CategoryInDB])
async def get_categories(
    skip: int = 0,
    limit: int = 100,
    parent_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get categories for the current user
    """
    if parent_id:
        categories = crud_category.category.get_subcategories(
            db, user_id=current_user.id, parent_id=parent_id
        )
    else:
        categories = crud_category.category.get_by_user(
            db, user_id=current_user.id, skip=skip, limit=limit
        )
    return categories


@router.get("/root", response_model=List[CategoryInDB])
async def get_root_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get root categories (categories without parent) for the current user
    """
    categories = crud_category.category.get_root_categories(
        db, user_id=current_user.id
    )
    return categories


@router.get("/{category_id}", response_model=CategoryInDB)
async def get_category(
    category_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific category by ID
    """
    category = crud_category.category.get_by_user_and_id(
        db, user_id=current_user.id, category_id=category_id
    )
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    return category


@router.post("/", response_model=CategoryInDB)
async def create_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new category
    """
    # Validate parent category if specified
    if category_data.parent_id:
        parent_category = crud_category.category.get_by_user_and_id(
            db, user_id=current_user.id, category_id=category_data.parent_id
        )
        if not parent_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent category not found"
            )
    
    # Check if category name already exists for this user
    existing_categories = crud_category.category.get_by_user(db, user_id=current_user.id)
    if any(cat.name.lower() == category_data.name.lower() for cat in existing_categories):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists"
        )
    
    category = crud_category.category.create_with_user(
        db, obj_in=category_data, user_id=current_user.id
    )
    return category


@router.put("/{category_id}", response_model=CategoryInDB)
async def update_category(
    category_id: UUID,
    category_data: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a category
    """
    category = crud_category.category.get_by_user_and_id(
        db, user_id=current_user.id, category_id=category_id
    )
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # Validate parent category if being updated
    if category_data.parent_id:
        parent_category = crud_category.category.get_by_user_and_id(
            db, user_id=current_user.id, category_id=category_data.parent_id
        )
        if not parent_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent category not found"
            )
        
        # Prevent circular references
        if category_data.parent_id == category_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category cannot be its own parent"
            )
    
    # Check for name conflicts if name is being updated
    if category_data.name:
        existing_categories = crud_category.category.get_by_user(db, user_id=current_user.id)
        if any(cat.name.lower() == category_data.name.lower() and cat.id != category_id 
               for cat in existing_categories):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category with this name already exists"
            )
    
    updated_category = crud_category.category.update(
        db, db_obj=category, obj_in=category_data
    )
    return updated_category


@router.delete("/{category_id}")
async def delete_category(
    category_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a category
    """
    category = crud_category.category.get_by_user_and_id(
        db, user_id=current_user.id, category_id=category_id
    )
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # Check if category has subcategories
    subcategories = crud_category.category.get_subcategories(
        db, user_id=current_user.id, parent_id=category_id
    )
    if subcategories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete category with subcategories. Delete subcategories first."
        )
    
    # Check if category is used by transactions
    from ...models.transaction import Transaction
    transactions_count = db.query(Transaction).filter(
        Transaction.category_id == category_id
    ).count()
    
    if transactions_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete category. It is used by {transactions_count} transactions."
        )
    
    crud_category.category.remove(db, id=category_id)
    return {"message": "Category deleted successfully"}


@router.get("/{category_id}/subcategories", response_model=List[CategoryInDB])
async def get_subcategories(
    category_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get subcategories of a specific category
    """
    # Verify parent category exists and belongs to user
    parent_category = crud_category.category.get_by_user_and_id(
        db, user_id=current_user.id, category_id=category_id
    )
    if not parent_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent category not found"
        )
    
    subcategories = crud_category.category.get_subcategories(
        db, user_id=current_user.id, parent_id=category_id
    )
    return subcategories


@router.post("/bulk", response_model=List[CategoryInDB])
async def create_default_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a set of default categories for new users
    """
    default_categories = [
        {"name": "Food & Dining", "color": "#FF6B6B", "icon": "utensils"},
        {"name": "Transportation", "color": "#4ECDC4", "icon": "car"},
        {"name": "Shopping", "color": "#45B7D1", "icon": "shopping-bag"},
        {"name": "Entertainment", "color": "#96CEB4", "icon": "film"},
        {"name": "Bills & Utilities", "color": "#FFEAA7", "icon": "file-text"},
        {"name": "Healthcare", "color": "#DDA0DD", "icon": "heart"},
        {"name": "Income", "color": "#98D8C8", "icon": "dollar-sign"},
        {"name": "Investments", "color": "#F7DC6F", "icon": "trending-up"},
        {"name": "Education", "color": "#BB8FCE", "icon": "book"},
        {"name": "Travel", "color": "#85C1E9", "icon": "map-pin"},
    ]
    
    created_categories = []
    for cat_data in default_categories:
        # Check if category already exists
        existing_categories = crud_category.category.get_by_user(db, user_id=current_user.id)
        if not any(cat.name.lower() == cat_data["name"].lower() for cat in existing_categories):
            category_create = CategoryCreate(**cat_data)
            category = crud_category.category.create_with_user(
                db, obj_in=category_create, user_id=current_user.id
            )
            created_categories.append(category)
    
    return created_categories
