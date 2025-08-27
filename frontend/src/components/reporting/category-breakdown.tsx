'use client';

import React from 'react';
import { CategorySummary } from '../../lib/api/reporting';

interface CategoryBreakdownProps {
  categories: CategorySummary[];
  className?: string;
}

export const CategoryBreakdown: React.FC<CategoryBreakdownProps> = ({ 
  categories, 
  className = '' 
}) => {
  const getColorForCategory = (index: number) => {
    const colors = [
      'bg-blue-500',
      'bg-green-500',
      'bg-yellow-500',
      'bg-red-500',
      'bg-purple-500',
      'bg-pink-500',
      'bg-indigo-500',
      'bg-gray-500'
    ];
    return colors[index % colors.length];
  };

  if (!categories || categories.length === 0) {
    return (
      <div className={`text-gray-500 text-center py-8 ${className}`}>
        No category data available
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {categories.slice(0, 8).map((category, index) => (
        <div key={category.category_id || index} className="space-y-2">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-3">
              <div className={`w-3 h-3 rounded-full ${getColorForCategory(index)}`}></div>
              <span className="text-sm font-medium text-gray-900">
                {category.category_name}
              </span>
            </div>
            <div className="text-right">
              <div className="text-sm font-semibold text-gray-900">
                ${Math.abs(category.total_amount).toLocaleString()}
              </div>
              <div className="text-xs text-gray-500">
                {category.percentage.toFixed(1)}%
              </div>
            </div>
          </div>
          
          {/* Progress bar */}
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full ${getColorForCategory(index)}`}
              style={{ width: `${Math.min(category.percentage, 100)}%` }}
            ></div>
          </div>
          
          {/* Transaction count */}
          <div className="text-xs text-gray-500 ml-6">
            {category.transaction_count} transaction{category.transaction_count !== 1 ? 's' : ''}
          </div>
        </div>
      ))}
      
      {categories.length > 8 && (
        <div className="text-sm text-gray-500 text-center pt-2">
          And {categories.length - 8} more categories...
        </div>
      )}
    </div>
  );
};