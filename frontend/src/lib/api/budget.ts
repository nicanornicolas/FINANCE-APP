import { api } from '../api';

export type UUID = string;

export interface BudgetSummary {
  budgets: any;
  goals: any;
}

export interface BudgetListResponse {
  budgets: any[];
  total_count: number;
  page: number;
  page_size: number;
}

export interface GoalListResponse {
  goals: any[];
  total_count: number;
  page: number;
  page_size: number;
}

export interface BudgetVsActualComparison {
  categories: Array<{
    category_id?: UUID;
    category_name: string;
    allocated: number;
    actual: number;
    variance: number;
    variance_pct: number;
  }>;
  totals: { allocated: number; actual: number; variance: number; variance_pct: number };
  insights?: string[];
}

export interface BudgetAlertListResponse {
  alerts: any[];
  total_count: number;
  unread_count: number;
  page: number;
  page_size: number;
}

export const budgetApi = {
  getSummary: async (): Promise<BudgetSummary> => {
    const res = await api.get('/api/budget/summary');
    return res.data;
  },

  listBudgets: async (params?: { skip?: number; limit?: number; status?: string; is_template?: boolean }): Promise<BudgetListResponse> => {
    const search = new URLSearchParams();
    if (params?.skip != null) search.append('skip', String(params.skip));
    if (params?.limit != null) search.append('limit', String(params.limit));
    if (params?.status) search.append('status', params.status);
    if (params?.is_template != null) search.append('is_template', String(params.is_template));
    const res = await api.get(`/api/budget/budgets?${search.toString()}`);
    return res.data;
  },

  getBudgetComparison: async (budgetId: UUID): Promise<BudgetVsActualComparison> => {
    const res = await api.get(`/api/budget/budgets/${budgetId}/comparison`);
    return res.data;
  },

  listGoals: async (params?: { skip?: number; limit?: number; status?: string; goal_type?: string }): Promise<GoalListResponse> => {
    const search = new URLSearchParams();
    if (params?.skip != null) search.append('skip', String(params.skip));
    if (params?.limit != null) search.append('limit', String(params.limit));
    if (params?.status) search.append('status', params.status);
    if (params?.goal_type) search.append('goal_type', params.goal_type);
    const res = await api.get(`/api/budget/goals?${search.toString()}`);
    return res.data;
  },

  listAlerts: async (params?: { skip?: number; limit?: number; status?: string; unread_only?: boolean }): Promise<BudgetAlertListResponse> => {
    const search = new URLSearchParams();
    if (params?.skip != null) search.append('skip', String(params.skip));
    if (params?.limit != null) search.append('limit', String(params.limit));
    if (params?.status) search.append('status', params.status);
    if (params?.unread_only != null) search.append('unread_only', String(params.unread_only));
    const res = await api.get(`/api/budget/alerts?${search.toString()}`);
    return res.data;
  },

  processAlerts: async (): Promise<{ message: string; alerts: Record<string, any[]> }> => {
    const res = await api.post('/api/budget/alerts/process', {});
    return res.data;
  },

  markAlertsRead: async (alertIds: UUID[]): Promise<{ message: string }> => {
    const res = await api.post('/api/budget/alerts/mark-read', alertIds);
    return res.data;
  },
};

