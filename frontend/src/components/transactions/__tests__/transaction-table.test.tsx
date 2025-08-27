/**
 * @jest-environment jsdom
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { TransactionTable } from '../transaction-table';

// Mock the edit modal
jest.mock('../transaction-edit-modal', () => ({
  TransactionEditModal: ({ transaction, onClose, onSave }: any) => (
    <div data-testid="edit-modal">
      <span>Editing: {transaction.description}</span>
      <button onClick={onClose}>Close</button>
      <button onClick={() => onSave({ description: 'Updated' })}>Save</button>
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
  {
    id: '2',
    account_id: 'acc1',
    date: '2024-01-16',
    description: 'Another Transaction',
    amount: 50.00,
    transaction_type: 'income' as const,
    category_id: null,
    subcategory_id: null,
    tags: [],
    is_tax_deductible: true,
    confidence_score: 0.85,
    notes: null,
    reference_number: null,
    created_at: '2024-01-16T10:00:00Z',
    updated_at: '2024-01-16T10:00:00Z',
  },
];

describe('TransactionTable', () => {
  const defaultProps = {
    transactions: mockTransactions,
    selectedTransactions: [],
    onSelectionChange: jest.fn(),
    onTransactionUpdate: jest.fn(),
    onTransactionDelete: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders transactions in table format', () => {
    render(<TransactionTable {...defaultProps} />);

    expect(screen.getByText('Test Transaction')).toBeInTheDocument();
    expect(screen.getByText('Another Transaction')).toBeInTheDocument();
    expect(screen.getByText('-$100.00')).toBeInTheDocument();
    expect(screen.getByText('$50.00')).toBeInTheDocument();
  });

  it('shows empty state when no transactions', () => {
    render(<TransactionTable {...defaultProps} transactions={[]} />);

    expect(screen.getByText('No transactions')).toBeInTheDocument();
    expect(screen.getByText('Get started by importing your financial data.')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    render(<TransactionTable {...defaultProps} transactions={[]} loading={true} />);

    expect(screen.getByText('Loading transactions...')).toBeInTheDocument();
  });

  it('handles transaction selection', () => {
    render(<TransactionTable {...defaultProps} />);

    const checkbox = screen.getAllByRole('checkbox')[1]; // First transaction checkbox
    fireEvent.click(checkbox);

    expect(defaultProps.onSelectionChange).toHaveBeenCalledWith(['1']);
  });

  it('handles select all', () => {
    render(<TransactionTable {...defaultProps} />);

    const selectAllCheckbox = screen.getAllByRole('checkbox')[0];
    fireEvent.click(selectAllCheckbox);

    expect(defaultProps.onSelectionChange).toHaveBeenCalledWith(['1', '2']);
  });

  it('opens edit modal when edit button clicked', () => {
    render(<TransactionTable {...defaultProps} />);

    const editButton = screen.getAllByText('Edit')[0];
    fireEvent.click(editButton);

    expect(screen.getByTestId('edit-modal')).toBeInTheDocument();
    expect(screen.getByText('Editing: Test Transaction')).toBeInTheDocument();
  });

  it('handles transaction deletion with confirmation', () => {
    // Mock window.confirm
    const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true);

    render(<TransactionTable {...defaultProps} />);

    const deleteButton = screen.getAllByText('Delete')[0];
    fireEvent.click(deleteButton);

    expect(confirmSpy).toHaveBeenCalledWith('Are you sure you want to delete this transaction?');
    expect(defaultProps.onTransactionDelete).toHaveBeenCalledWith('1');

    confirmSpy.mockRestore();
  });

  it('does not delete when confirmation is cancelled', () => {
    const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(false);

    render(<TransactionTable {...defaultProps} />);

    const deleteButton = screen.getAllByText('Delete')[0];
    fireEvent.click(deleteButton);

    expect(confirmSpy).toHaveBeenCalled();
    expect(defaultProps.onTransactionDelete).not.toHaveBeenCalled();

    confirmSpy.mockRestore();
  });
});