"""
Rule-based categorization service for transactions
"""

import re
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from uuid import UUID

from ..models.category import Category
from ..models.transaction import Transaction, TransactionType


class CategorizationRule:
    """Represents a single categorization rule"""
    
    def __init__(
        self,
        name: str,
        category_name: str,
        keywords: List[str],
        amount_min: Optional[float] = None,
        amount_max: Optional[float] = None,
        transaction_type: Optional[TransactionType] = None,
        priority: int = 1
    ):
        self.name = name
        self.category_name = category_name
        self.keywords = [kw.lower() for kw in keywords]
        self.amount_min = amount_min
        self.amount_max = amount_max
        self.transaction_type = transaction_type
        self.priority = priority
    
    def matches(self, description: str, amount: float, transaction_type: TransactionType) -> bool:
        """Check if this rule matches the given transaction"""
        
        # Check transaction type
        if self.transaction_type and self.transaction_type != transaction_type:
            return False
        
        # Check amount range
        if self.amount_min is not None and amount < self.amount_min:
            return False
        if self.amount_max is not None and amount > self.amount_max:
            return False
        
        # Check keywords
        description_lower = description.lower()
        return any(keyword in description_lower for keyword in self.keywords)


class RuleBasedCategorizationService:
    """Service for rule-based transaction categorization"""
    
    def __init__(self):
        self.default_rules = self._create_default_rules()
    
    def _create_default_rules(self) -> List[CategorizationRule]:
        """Create default categorization rules"""
        return [
            # Food & Dining
            CategorizationRule(
                name="Restaurants",
                category_name="Food & Dining",
                keywords=["restaurant", "cafe", "coffee", "starbucks", "mcdonald", "burger", "pizza", "subway", "kfc", "taco", "chipotle", "panera"],
                transaction_type=TransactionType.EXPENSE,
                priority=2
            ),
            CategorizationRule(
                name="Grocery Stores",
                category_name="Food & Dining",
                keywords=["grocery", "supermarket", "walmart", "target", "kroger", "safeway", "whole foods", "trader joe", "costco", "sam's club"],
                transaction_type=TransactionType.EXPENSE,
                priority=2
            ),
            
            # Transportation
            CategorizationRule(
                name="Gas Stations",
                category_name="Transportation",
                keywords=["shell", "exxon", "bp", "chevron", "mobil", "gas station", "fuel", "gasoline"],
                transaction_type=TransactionType.EXPENSE,
                priority=2
            ),
            CategorizationRule(
                name="Ride Sharing",
                category_name="Transportation",
                keywords=["uber", "lyft", "taxi", "cab"],
                transaction_type=TransactionType.EXPENSE,
                priority=3
            ),
            CategorizationRule(
                name="Public Transit",
                category_name="Transportation",
                keywords=["metro", "subway", "bus", "transit", "mta", "bart"],
                transaction_type=TransactionType.EXPENSE,
                priority=2
            ),
            
            # Bills & Utilities
            CategorizationRule(
                name="Electric/Gas Utilities",
                category_name="Bills & Utilities",
                keywords=["electric", "electricity", "gas company", "utility", "power", "energy"],
                transaction_type=TransactionType.EXPENSE,
                priority=3
            ),
            CategorizationRule(
                name="Internet/Phone",
                category_name="Bills & Utilities",
                keywords=["verizon", "at&t", "comcast", "xfinity", "spectrum", "internet", "phone", "wireless", "cellular"],
                transaction_type=TransactionType.EXPENSE,
                priority=3
            ),
            CategorizationRule(
                name="Streaming Services",
                category_name="Entertainment",
                keywords=["netflix", "hulu", "disney+", "amazon prime", "spotify", "apple music", "youtube premium"],
                transaction_type=TransactionType.EXPENSE,
                priority=3
            ),
            
            # Shopping
            CategorizationRule(
                name="Online Shopping",
                category_name="Shopping",
                keywords=["amazon", "ebay", "etsy", "online", "paypal"],
                transaction_type=TransactionType.EXPENSE,
                priority=1
            ),
            CategorizationRule(
                name="Retail Stores",
                category_name="Shopping",
                keywords=["target", "walmart", "best buy", "home depot", "lowes", "macy", "nordstrom"],
                transaction_type=TransactionType.EXPENSE,
                priority=2
            ),
            
            # Healthcare
            CategorizationRule(
                name="Medical",
                category_name="Healthcare",
                keywords=["doctor", "hospital", "clinic", "medical", "pharmacy", "cvs", "walgreens", "dentist", "dental"],
                transaction_type=TransactionType.EXPENSE,
                priority=3
            ),
            
            # Income
            CategorizationRule(
                name="Salary/Wages",
                category_name="Income",
                keywords=["payroll", "salary", "wages", "direct deposit", "employer"],
                transaction_type=TransactionType.INCOME,
                priority=3
            ),
            CategorizationRule(
                name="Interest/Dividends",
                category_name="Income",
                keywords=["interest", "dividend", "investment", "return"],
                transaction_type=TransactionType.INCOME,
                priority=2
            ),
            
            # Entertainment
            CategorizationRule(
                name="Movies/Theater",
                category_name="Entertainment",
                keywords=["movie", "theater", "cinema", "amc", "regal"],
                transaction_type=TransactionType.EXPENSE,
                priority=2
            ),
            
            # Travel
            CategorizationRule(
                name="Airlines",
                category_name="Travel",
                keywords=["airline", "airways", "delta", "american airlines", "united", "southwest", "jetblue"],
                transaction_type=TransactionType.EXPENSE,
                priority=3
            ),
            CategorizationRule(
                name="Hotels",
                category_name="Travel",
                keywords=["hotel", "motel", "inn", "resort", "marriott", "hilton", "hyatt", "airbnb"],
                transaction_type=TransactionType.EXPENSE,
                priority=3
            ),
        ]
    
    def categorize_transaction(
        self,
        description: str,
        amount: float,
        transaction_type: TransactionType,
        user_rules: Optional[List[CategorizationRule]] = None
    ) -> Optional[Tuple[str, int, str]]:
        """
        Categorize a transaction using rules
        
        Returns:
            Tuple of (category_name, confidence_score, rule_name) or None if no match
        """
        all_rules = (user_rules or []) + self.default_rules
        
        # Sort rules by priority (higher priority first)
        all_rules.sort(key=lambda r: r.priority, reverse=True)
        
        for rule in all_rules:
            if rule.matches(description, amount, transaction_type):
                # Calculate confidence based on priority and keyword match strength
                confidence = min(rule.priority * 20, 80)  # Max 80% for rule-based
                return rule.category_name, confidence, rule.name
        
        return None
    
    def get_category_suggestions(
        self,
        description: str,
        amount: float,
        transaction_type: TransactionType,
        db: Session,
        user_id: UUID,
        limit: int = 3
    ) -> List[Dict]:
        """
        Get category suggestions for a transaction
        """
        suggestions = []
        
        # Try rule-based categorization first
        rule_result = self.categorize_transaction(description, amount, transaction_type)
        if rule_result:
            category_name, confidence, rule_name = rule_result
            
            # Find the actual category object
            category = db.query(Category).filter(
                Category.user_id == user_id,
                Category.name == category_name
            ).first()
            
            if category:
                suggestions.append({
                    "category_id": category.id,
                    "category_name": category.name,
                    "confidence": confidence,
                    "method": "rule_based",
                    "rule_name": rule_name
                })
        
        # Add fuzzy matching suggestions based on similar transactions
        similar_suggestions = self._get_similar_transaction_suggestions(
            description, amount, transaction_type, db, user_id, limit - len(suggestions)
        )
        suggestions.extend(similar_suggestions)
        
        return suggestions[:limit]
    
    def _get_similar_transaction_suggestions(
        self,
        description: str,
        amount: float,
        transaction_type: TransactionType,
        db: Session,
        user_id: UUID,
        limit: int
    ) -> List[Dict]:
        """
        Find suggestions based on similar transactions
        """
        suggestions = []
        
        # Get user's accounts
        from ..models.account import Account
        user_accounts = db.query(Account).filter(Account.user_id == user_id).all()
        account_ids = [acc.id for acc in user_accounts]
        
        if not account_ids:
            return suggestions
        
        # Find similar transactions by description keywords
        description_words = set(re.findall(r'\b\w+\b', description.lower()))
        
        # Get categorized transactions for this user
        categorized_transactions = db.query(Transaction).join(Category).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.category_id.isnot(None),
            Transaction.transaction_type == transaction_type
        ).all()
        
        # Score transactions by similarity
        scored_transactions = []
        for trans in categorized_transactions:
            trans_words = set(re.findall(r'\b\w+\b', trans.description.lower()))
            
            # Calculate word overlap
            common_words = description_words.intersection(trans_words)
            if common_words:
                similarity_score = len(common_words) / len(description_words.union(trans_words))
                
                # Boost score if amounts are similar
                amount_diff = abs(float(trans.amount) - amount)
                if amount_diff < amount * 0.1:  # Within 10%
                    similarity_score *= 1.5
                elif amount_diff < amount * 0.5:  # Within 50%
                    similarity_score *= 1.2
                
                scored_transactions.append((trans, similarity_score))
        
        # Sort by similarity and get top suggestions
        scored_transactions.sort(key=lambda x: x[1], reverse=True)
        
        seen_categories = set()
        for trans, score in scored_transactions[:limit * 2]:  # Get more to filter duplicates
            if trans.category_id not in seen_categories:
                seen_categories.add(trans.category_id)
                
                confidence = min(int(score * 60), 70)  # Max 70% for similarity-based
                suggestions.append({
                    "category_id": trans.category_id,
                    "category_name": trans.category.name,
                    "confidence": confidence,
                    "method": "similarity",
                    "similar_transaction": trans.description
                })
                
                if len(suggestions) >= limit:
                    break
        
        return suggestions
    
    def create_custom_rule(
        self,
        name: str,
        category_name: str,
        keywords: List[str],
        amount_min: Optional[float] = None,
        amount_max: Optional[float] = None,
        transaction_type: Optional[TransactionType] = None,
        priority: int = 5  # Custom rules get higher priority
    ) -> CategorizationRule:
        """
        Create a custom categorization rule
        """
        return CategorizationRule(
            name=name,
            category_name=category_name,
            keywords=keywords,
            amount_min=amount_min,
            amount_max=amount_max,
            transaction_type=transaction_type,
            priority=priority
        )


# Global service instance
rule_based_categorization_service = RuleBasedCategorizationService()
