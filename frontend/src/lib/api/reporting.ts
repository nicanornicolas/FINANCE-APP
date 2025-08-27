import { api } from '../api';

export interface DateRangeFilter {
  start_date: string;
  end_date: string;
  period?: string;
}

export interface ReportFilters {
  date_range: DateRangeFilter;
  account_ids?: string[];
  category_ids?: string[];
  transaction_types?: string[];
  tags?: string[];
  min_amount?: number;
  max_amount?: number;
}

export interface CategorySummary {
  category_id?: string;
  category_name: string;
  total_amount: number;
  transaction_count: number;
  percentage: number;
  subcategories?: CategorySummary[];
}

export interface ExpenseSummary {
  total_expenses: number;
  total_income: number;
  net_income: number;
  transaction_count: number;
  average_transaction: number;
  categories: CategorySummary[];
}

export interface TrendDataPoint {
  period: string;
  date: string;
  income: number;
  expenses: number;
  net: number;
}

export interface FinancialMetrics {
  total_balance: number;
  monthly_income: number;
  monthly_expenses: number;
  monthly_savings: number;
  savings_rate: number;
  top_expense_category?: string;
  expense_trend: TrendDataPoint[];
  income_trend: TrendDataPoint[];
}

export interface DashboardData {
  metrics: FinancialMetrics;
  recent_transactions: any[];
  category_breakdown: CategorySummary[];
  monthly_comparison: Record<string, number>;
}

export interface ChartData {
  labels: string[];
  datasets: any[];
  chart_type: string;
  title: string;
  options?: any;
}

export type ExportFormat = 'pdf' | 'csv' | 'excel' | 'json';

export const reportingApi = {
  // Get dashboard data
  getDashboardData: async (startDate?: string, endDate?: string): Promise<DashboardData> => {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    
    const response = await api.get(`/api/reporting/dashboard?${params.toString()}`);
    return response.data;
  },

  // Get financial metrics
  getFinancialMetrics: async (
    startDate: string,
    endDate: string,
    accountIds?: string[],
    categoryIds?: string[]
  ): Promise<FinancialMetrics> => {
    const params = new URLSearchParams();
    params.append('start_date', startDate);
    params.append('end_date', endDate);
    
    if (accountIds) {
      accountIds.forEach(id => params.append('account_ids', id));
    }
    if (categoryIds) {
      categoryIds.forEach(id => params.append('category_ids', id));
    }
    
    const response = await api.get(`/api/reporting/metrics?${params.toString()}`);
    return response.data;
  },

  // Get expense summary
  getExpenseSummary: async (
    startDate: string,
    endDate: string,
    accountIds?: string[],
    categoryIds?: string[],
    transactionTypes?: string[]
  ): Promise<ExpenseSummary> => {
    const params = new URLSearchParams();
    params.append('start_date', startDate);
    params.append('end_date', endDate);
    
    if (accountIds) {
      accountIds.forEach(id => params.append('account_ids', id));
    }
    if (categoryIds) {
      categoryIds.forEach(id => params.append('category_ids', id));
    }
    if (transactionTypes) {
      transactionTypes.forEach(type => params.append('transaction_types', type));
    }
    
    const response = await api.get(`/api/reporting/expense-summary?${params.toString()}`);
    return response.data;
  },

  // Get chart data
  getChartData: async (
    chartType: string,
    startDate: string,
    endDate: string,
    accountIds?: string[],
    categoryIds?: string[]
  ): Promise<ChartData> => {
    const params = new URLSearchParams();
    params.append('start_date', startDate);
    params.append('end_date', endDate);
    
    if (accountIds) {
      accountIds.forEach(id => params.append('account_ids', id));
    }
    if (categoryIds) {
      categoryIds.forEach(id => params.append('category_ids', id));
    }
    
    const response = await api.get(`/api/reporting/chart-data/${chartType}?${params.toString()}`);
    return response.data;
  },

  // Export expense summary
  exportExpenseSummary: async (
    format: ExportFormat,
    startDate: string,
    endDate: string,
    accountIds?: string[],
    categoryIds?: string[]
  ): Promise<Blob> => {
    const params = new URLSearchParams();
    params.append('format', format);
    params.append('start_date', startDate);
    params.append('end_date', endDate);
    
    if (accountIds) {
      accountIds.forEach(id => params.append('account_ids', id));
    }
    if (categoryIds) {
      categoryIds.forEach(id => params.append('category_ids', id));
    }
    
    const response = await api.post(`/api/reporting/export/expense-summary?${params.toString()}`, {}, {
      responseType: 'blob'
    });
    return response.data;
  },

  // Export financial metrics
  exportFinancialMetrics: async (
    format: ExportFormat,
    startDate: string,
    endDate: string,
    accountIds?: string[],
    categoryIds?: string[]
  ): Promise<Blob> => {
    const params = new URLSearchParams();
    params.append('format', format);
    params.append('start_date', startDate);
    params.append('end_date', endDate);
    
    if (accountIds) {
      accountIds.forEach(id => params.append('account_ids', id));
    }
    if (categoryIds) {
      categoryIds.forEach(id => params.append('category_ids', id));
    }
    
    const response = await api.post(`/api/reporting/export/financial-metrics?${params.toString()}`, {}, {
      responseType: 'blob'
    });
    return response.data;
  },

  // Export transactions
  exportTransactions: async (
    format: ExportFormat,
    startDate: string,
    endDate: string,
    accountIds?: string[],
    categoryIds?: string[],
    transactionTypes?: string[]
  ): Promise<Blob> => {
    const params = new URLSearchParams();
    params.append('format', format);
    params.append('start_date', startDate);
    params.append('end_date', endDate);
    
    if (accountIds) {
      accountIds.forEach(id => params.append('account_ids', id));
    }
    if (categoryIds) {
      categoryIds.forEach(id => params.append('category_ids', id));
    }
    if (transactionTypes) {
      transactionTypes.forEach(type => params.append('transaction_types', type));
    }
    
    const response = await api.post(`/api/reporting/export/transactions?${params.toString()}`, {}, {
      responseType: 'blob'
    });
    return response.data;
  },

  // Get monthly comparison
  getMonthlyComparison: async (): Promise<Record<string, number>> => {
    const response = await api.get('/api/reporting/monthly-comparison');
    return response.data;
  },

  // Get recent transactions
  getRecentTransactions: async (limit: number = 10): Promise<{ transactions: any[] }> => {
    const response = await api.get(`/api/reporting/recent-transactions?limit=${limit}`);
    return response.data;
  }
};