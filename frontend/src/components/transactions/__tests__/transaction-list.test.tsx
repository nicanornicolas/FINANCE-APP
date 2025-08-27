/**
 * @jest-environment jsdom
 */

import { render, screen, waitFor } from '@testing-library/react';
import { TransactionList } from '../transaction-list';
import { transactionApi } from '@/lib/api/transactions';

// Mock the API
jest.mock('@/lib/api/transactions', () => ({
  transactionApi: {
    getTransactions: jest.fn(),
    updateTransaction: jest.fn(),
    deleteTransaction: jest.fn(),
    bulkUpdateTransactions: jest.fn(),
    bulkDeleteTransactions: jest.fn(),
  },
}));

// Mock the child components
jest.mock('../transaction-filters', () => ({
  TransactionFilters: ({ onFiltersChange }: any) => (
    <div data-testid="transaction-filters">
      <button onClick={() => onFiltersChange({})}>Apply Filters</button>
    </div>
  ),
}));

jest.mock('../transaction-table', () => ({
  TransactionTable: ({ transactions, loading }: any) => (
    <div data-testid="transaction-table">
      {loading ? 'Loading...' : `${transactions.length} transactions`}
    </div>
  ),
}));

jest.mock('../transaction-import', () => ({
  TransactionImport: ({ onClose, onSuccess }: any) => (
    <div data-testid="transaction-import">
      <button onClick={onClose}>Close</button>
      <button onClick={onSuccess}>Success</button>
    </div>
  ),
}));

jest.mock('../../ui/pagination', () => ({
  Pagination: ({ currentPage, totalPages }: any) => (
    <div data-testid="pagination">
      Page {currentPage} of {totalPages}
    </div>
  ),
}));

const mockTransactions = [
  {
    id: '1',
    account_id: 'acc1',
    date: '2024-01-15',
    description: 'Test Transaction',
    amount: 100.00,
    transaction_type: 'expense' as const,
    category_id: 'cat1',
    subcategory_id: null,
    tags: ['test'],
    is_tax_deductible: false,
    confidence_score: 0.95,
    notes: 'Test note',
    reference_number: 'REF123',
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-15T10:00:00Z',
  },
];

describe('TransactionList', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders loading state initially', () => {
    (transactionApi.getTransactions as jest.Mock).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    render(<TransactionList />);
    
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('renders transactions after loading', async () => {
    (transactionApi.getTransactions as jest.Mock).mockResolvedValue({
      transactions: mockTransactions,
      total: 1,
      page: 1,
      size: 50,
      pages: 1,
    });

    render(<TransactionList />);

    await waitFor(() => {
      expect(screen.getByText('1 transactions total')).toBeInTheDocument();
    });

    expect(screen.getByText('1 transactions')).toBeInTheDocument();
  });

  it('shows import button', async () => {
    (transactionApi.getTransactions as jest.Mock).mockResolvedValue({
      transactions: [],
      total: 0,
      page: 1,
      size: 50,
      pages: 1,
    });

    render(<TransactionList />);

    await waitFor(() => {
      expect(screen.getByText('Import')).toBeInTheDocument();
    });
  });

  it('handles error state', async () => {
    (transactionApi.getTransactions as jest.Mock).mockRejectedValue(
      new Error('API Error')
    );

    render(<TransactionList />);

    await waitFor(() => {
      expect(screen.getByText('Failed to load transactions')).toBeInTheDocument();
    });
  });
});