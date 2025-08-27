import { api } from '../api';

export interface Transaction {
  id: string;
  account_id: string;
  date: string;
  description: string;
  amount: number;
  transaction_type: 'income' | 'expense' | 'transfer';
  category_id?: string;
  subcategory_id?: string;
  tags: string[];
  is_tax_deductible: boolean;
  confidence_score?: number;
  notes?: string;
  reference_number?: string;
  created_at: string;
  updated_at: string;
}

export interface TransactionCreate {
  account_id: string;
  date: string;
  description: string;
  amount: number;
  transaction_type: 'income' | 'expense' | 'transfer';
  category_id?: string;
  subcategory_id?: string;
  tags?: string[];
  is_tax_deductible?: boolean;
  notes?: string;
  reference_number?: string;
}

export interface TransactionUpdate {
  account_id?: string;
  date?: string;
  description?: string;
  amount?: number;
  transaction_type?: 'income' | 'expense' | 'transfer';
  category_id?: string;
  subcategory_id?: string;
  tags?: string[];
  is_tax_deductible?: boolean;
  notes?: string;
  reference_number?: string;
}

export interface TransactionFilters {
  account_id?: string;
  category_id?: string;
  transaction_type?: 'income' | 'expense' | 'transfer';
  start_date?: string;
  end_date?: string;
  min_amount?: number;
  max_amount?: number;
  search?: string;
  is_tax_deductible?: boolean;
}

export interface TransactionListResponse {
  transactions: Transaction[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export const transactionApi = {
  // Get transactions with pagination and filtering
  getTransactions: async (
    page: number = 1,
    size: number = 50,
    filters?: TransactionFilters
  ): Promise<TransactionListResponse> => {
    const params = new URLSearchParams({
      skip: ((page - 1) * size).toString(),
      limit: size.toString(),
    });

    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.append(key, value.toString());
        }
      });
    }

    const response = await api.get(`/transactions?${params}`);
    return response.data;
  },

  // Get single transaction
  getTransaction: async (id: string): Promise<Transaction> => {
    const response = await api.get(`/transactions/${id}`);
    return response.data;
  },

  // Create transaction
  createTransaction: async (transaction: TransactionCreate): Promise<Transaction> => {
    const response = await api.post('/transactions', transaction);
    return response.data;
  },

  // Update transaction
  updateTransaction: async (id: string, transaction: TransactionUpdate): Promise<Transaction> => {
    const response = await api.put(`/transactions/${id}`, transaction);
    return response.data;
  },

  // Delete transaction
  deleteTransaction: async (id: string): Promise<void> => {
    await api.delete(`/transactions/${id}`);
  },

  // Bulk update transactions
  bulkUpdateTransactions: async (
    transactionIds: string[],
    updates: TransactionUpdate
  ): Promise<Transaction[]> => {
    const response = await api.put('/transactions/bulk', {
      transaction_ids: transactionIds,
      updates,
    });
    return response.data;
  },

  // Bulk delete transactions
  bulkDeleteTransactions: async (transactionIds: string[]): Promise<void> => {
    await api.delete('/transactions/bulk', {
      data: { transaction_ids: transactionIds },
    });
  },

  // Import transactions from file
  importTransactions: async (file: File, accountId: string): Promise<{ 
    imported: number; 
    duplicates: number; 
    errors: string[] 
  }> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('account_id', accountId);

    const response = await api.post('/transactions/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Search transactions
  searchTransactions: async (
    query: string,
    page: number = 1,
    size: number = 50
  ): Promise<TransactionListResponse> => {
    const params = new URLSearchParams({
      q: query,
      skip: ((page - 1) * size).toString(),
      limit: size.toString(),
    });

    const response = await api.get(`/transactions/search?${params}`);
    return response.data;
  },
};