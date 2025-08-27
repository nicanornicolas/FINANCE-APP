'use client';

import { useState, useEffect } from 'react';
import { Transaction, TransactionFilters, transactionApi } from '@/lib/api/transactions';
import { TransactionFilters as FilterComponent } from './transaction-filters';
import { TransactionTable } from './transaction-table';
import { TransactionImport } from './transaction-import';
import { Pagination } from '../ui/pagination';
import { LoadingSpinner } from '../ui/loading-spinner';

interface TransactionListProps {
  accountId?: string;
}

export function TransactionList({ accountId }: TransactionListProps) {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTransactions, setSelectedTransactions] = useState<string[]>([]);
  const [showImport, setShowImport] = useState(false);
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalTransactions, setTotalTransactions] = useState(0);
  const [pageSize] = useState(50);
  
  // Filter state
  const [filters, setFilters] = useState<TransactionFilters>({
    account_id: accountId,
  });

  const loadTransactions = async (page: number = currentPage, newFilters?: TransactionFilters) => {
    try {
      setLoading(true);
      setError(null);
      
      const filtersToUse = newFilters || filters;
      const response = await transactionApi.getTransactions(page, pageSize, filtersToUse);
      
      setTransactions(response.transactions);
      setTotalPages(response.pages);
      setTotalTransactions(response.total);
      setCurrentPage(page);
    } catch (err) {
      setError('Failed to load transactions');
      console.error('Error loading transactions:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTransactions(1);
  }, []);

  const handleFilterChange = (newFilters: TransactionFilters) => {
    setFilters(newFilters);
    setCurrentPage(1);
    loadTransactions(1, newFilters);
  };

  const handlePageChange = (page: number) => {
    loadTransactions(page);
  };

  const handleTransactionUpdate = async (id: string, updates: Partial<Transaction>) => {
    try {
      await transactionApi.updateTransaction(id, updates);
      await loadTransactions(); // Reload to get updated data
    } catch (err) {
      console.error('Error updating transaction:', err);
      setError('Failed to update transaction');
    }
  };

  const handleTransactionDelete = async (id: string) => {
    try {
      await transactionApi.deleteTransaction(id);
      await loadTransactions(); // Reload to get updated data
    } catch (err) {
      console.error('Error deleting transaction:', err);
      setError('Failed to delete transaction');
    }
  };

  const handleBulkUpdate = async (updates: Partial<Transaction>) => {
    if (selectedTransactions.length === 0) return;
    
    try {
      await transactionApi.bulkUpdateTransactions(selectedTransactions, updates);
      setSelectedTransactions([]);
      await loadTransactions(); // Reload to get updated data
    } catch (err) {
      console.error('Error bulk updating transactions:', err);
      setError('Failed to update transactions');
    }
  };

  const handleBulkDelete = async () => {
    if (selectedTransactions.length === 0) return;
    
    if (!confirm(`Are you sure you want to delete ${selectedTransactions.length} transactions?`)) {
      return;
    }
    
    try {
      await transactionApi.bulkDeleteTransactions(selectedTransactions);
      setSelectedTransactions([]);
      await loadTransactions(); // Reload to get updated data
    } catch (err) {
      console.error('Error bulk deleting transactions:', err);
      setError('Failed to delete transactions');
    }
  };

  const handleImportSuccess = () => {
    setShowImport(false);
    loadTransactions(); // Reload to show imported transactions
  };

  if (loading && transactions.length === 0) {
    return (
      <div className="flex justify-center items-center h-64">
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Transactions</h1>
          <p className="mt-1 text-sm text-gray-600">
            {totalTransactions} transactions total
          </p>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={() => setShowImport(true)}
            className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <svg className="-ml-1 mr-2 h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            Import
          </button>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <FilterComponent
        filters={filters}
        onFiltersChange={handleFilterChange}
      />

      {/* Bulk Actions */}
      {selectedTransactions.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <span className="text-sm text-blue-800">
                {selectedTransactions.length} transactions selected
              </span>
            </div>
            <div className="flex space-x-2">
              <button
                onClick={handleBulkDelete}
                className="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded text-red-700 bg-red-100 hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
              >
                Delete
              </button>
              <button
                onClick={() => {/* TODO: Open bulk edit modal */}}
                className="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded text-blue-700 bg-blue-100 hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Edit
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Transaction Table */}
      <TransactionTable
        transactions={transactions}
        selectedTransactions={selectedTransactions}
        onSelectionChange={setSelectedTransactions}
        onTransactionUpdate={handleTransactionUpdate}
        onTransactionDelete={handleTransactionDelete}
        loading={loading}
      />

      {/* Pagination */}
      {totalPages > 1 && (
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={handlePageChange}
        />
      )}

      {/* Import Modal */}
      {showImport && (
        <TransactionImport
          onClose={() => setShowImport(false)}
          onSuccess={handleImportSuccess}
          defaultAccountId={accountId}
        />
      )}
    </div>
  );
}