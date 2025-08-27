import { api } from '../api';

export interface Account {
  id: string;
  user_id: string;
  name: string;
  account_type: 'checking' | 'savings' | 'credit_card' | 'investment' | 'loan' | 'cash' | 'other';
  institution: string;
  account_number?: string;
  balance: number;
  currency: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AccountCreate {
  name: string;
  account_type: 'checking' | 'savings' | 'credit_card' | 'investment' | 'loan' | 'cash' | 'other';
  institution: string;
  account_number?: string;
  balance?: number;
  currency?: string;
}

export interface AccountUpdate {
  name?: string;
  account_type?: 'checking' | 'savings' | 'credit_card' | 'investment' | 'loan' | 'cash' | 'other';
  institution?: string;
  account_number?: string;
  balance?: number;
  currency?: string;
  is_active?: boolean;
}

export const accountApi = {
  // Get all accounts
  getAccounts: async (): Promise<Account[]> => {
    const response = await api.get('/accounts');
    return response.data;
  },

  // Get single account
  getAccount: async (id: string): Promise<Account> => {
    const response = await api.get(`/accounts/${id}`);
    return response.data;
  },

  // Create account
  createAccount: async (account: AccountCreate): Promise<Account> => {
    const response = await api.post('/accounts', account);
    return response.data;
  },

  // Update account
  updateAccount: async (id: string, account: AccountUpdate): Promise<Account> => {
    const response = await api.put(`/accounts/${id}`, account);
    return response.data;
  },

  // Delete account
  deleteAccount: async (id: string): Promise<void> => {
    await api.delete(`/accounts/${id}`);
  },
};