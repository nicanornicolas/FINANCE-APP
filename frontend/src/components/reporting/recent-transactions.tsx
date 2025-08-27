'use client';

import React from 'react';
import { ArrowUpRight, ArrowDownLeft, ArrowRightLeft } from 'lucide-react';

interface Transaction {
  id: string;
  date: string;
  description: string;
  amount: number;
  transaction_type: string;
  category_name?: string;
}

interface RecentTransactionsProps {
  transactions: Transaction[];
  className?: string;
}

export const RecentTransactions: React.FC<RecentTransactionsProps> = ({ 
  transactions, 
  className = '' 
}) => {
  const getTransactionIcon = (type: string) => {
    switch (type) {
      case 'income':
        return <ArrowUpRight className="h-4 w-4 text-green-600" />;
      case 'expense':
        return <ArrowDownLeft className="h-4 w-4 text-red-600" />;
      case 'transfer':
        return <ArrowRightLeft className="h-4 w-4 text-blue-600" />;
      default:
        return <ArrowRightLeft className="h-4 w-4 text-gray-600" />;
    }
  };

  const getAmountColor = (type: string) => {
    switch (type) {
      case 'income':
        return 'text-green-600';
      case 'expense':
        return 'text-red-600';
      case 'transfer':
        return 'text-blue-600';
      default:
        return 'text-gray-600';
    }
  };

  const formatAmount = (amount: number, type: string) => {
    const formattedAmount = Math.abs(amount).toLocaleString();
    switch (type) {
      case 'income':
        return `+$${formattedAmount}`;
      case 'expense':
        return `-$${formattedAmount}`;
      default:
        return `$${formattedAmount}`;
    }
  };

  if (!transactions || transactions.length === 0) {
    return (
      <div className={`text-gray-500 text-center py-8 ${className}`}>
        No recent transactions
      </div>
    );
  }

  return (
    <div className={`space-y-3 ${className}`}>
      {transactions.map((transaction) => (
        <div 
          key={transaction.id} 
          className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
        >
          <div className="flex items-center space-x-3">
            <div className="flex-shrink-0">
              {getTransactionIcon(transaction.transaction_type)}
            </div>
            
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">
                {transaction.description}
              </p>
              <div className="flex items-center space-x-2 text-xs text-gray-500">
                <span>{new Date(transaction.date).toLocaleDateString()}</span>
                {transaction.category_name && (
                  <>
                    <span>•</span>
                    <span className="bg-gray-200 px-2 py-1 rounded-full">
                      {transaction.category_name}
                    </span>
                  </>
                )}
              </div>
            </div>
          </div>
          
          <div className="flex-shrink-0 text-right">
            <p className={`text-sm font-semibold ${getAmountColor(transaction.transaction_type)}`}>
              {formatAmount(transaction.amount, transaction.transaction_type)}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
};