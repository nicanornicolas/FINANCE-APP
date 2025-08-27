'use client';

import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  PieChart, 
  BarChart3,
  Download,
  Calendar,
  Filter
} from 'lucide-react';
import { reportingApi, DashboardData, ExportFormat } from '../../lib/api/reporting';
import { ChartComponent, ChartSkeleton } from './chart-components';
import { MetricCard } from './metric-card';
import { RecentTransactions } from './recent-transactions';
import { CategoryBreakdown } from './category-breakdown';
import { ExportModal } from './export-modal';

interface DashboardProps {
  className?: string;
}

export const Dashboard: React.FC<DashboardProps> = ({ className = '' }) => {
  const [dateRange, setDateRange] = useState({
    startDate: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], // 30 days ago
    endDate: new Date().toISOString().split('T')[0] // today
  });
  const [showExportModal, setShowExportModal] = useState(false);
  const [selectedChartType, setSelectedChartType] = useState<string>('category_pie');

  // Fetch dashboard data
  const { 
    data: dashboardData, 
    isLoading: isDashboardLoading, 
    error: dashboardError,
    refetch: refetchDashboard
  } = useQuery({
    queryKey: ['dashboard', dateRange.startDate, dateRange.endDate],
    queryFn: () => reportingApi.getDashboardData(dateRange.startDate, dateRange.endDate),
  });

  // Fetch chart data
  const { 
    data: chartData, 
    isLoading: isChartLoading 
  } = useQuery({
    queryKey: ['chart', selectedChartType, dateRange.startDate, dateRange.endDate],
    queryFn: () => reportingApi.getChartData(
      selectedChartType, 
      dateRange.startDate, 
      dateRange.endDate
    ),
    enabled: !!selectedChartType,
  });

  const handleDateRangeChange = (start: string, end: string) => {
    setDateRange({ startDate: start, endDate: end });
  };

  const handleExport = async (format: ExportFormat, type: string) => {
    try {
      let blob: Blob;
      let filename: string;

      switch (type) {
        case 'expense-summary':
          blob = await reportingApi.exportExpenseSummary(
            format, 
            dateRange.startDate, 
            dateRange.endDate
          );
          filename = `expense-summary.${format}`;
          break;
        case 'financial-metrics':
          blob = await reportingApi.exportFinancialMetrics(
            format, 
            dateRange.startDate, 
            dateRange.endDate
          );
          filename = `financial-metrics.${format}`;
          break;
        case 'transactions':
          blob = await reportingApi.exportTransactions(
            format, 
            dateRange.startDate, 
            dateRange.endDate
          );
          filename = `transactions.${format}`;
          break;
        default:
          throw new Error('Invalid export type');
      }

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export failed:', error);
      // You might want to show a toast notification here
    }
  };

  if (dashboardError) {
    return (
      <div className="p-6 text-center">
        <div className="text-red-600 mb-4">Error loading dashboard data</div>
        <button 
          onClick={() => refetchDashboard()}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className={`p-6 space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <h1 className="text-2xl font-bold text-gray-900">Financial Dashboard</h1>
        
        <div className="flex flex-col sm:flex-row gap-2">
          {/* Date Range Selector */}
          <div className="flex gap-2">
            <input
              type="date"
              value={dateRange.startDate}
              onChange={(e) => handleDateRangeChange(e.target.value, dateRange.endDate)}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm"
            />
            <input
              type="date"
              value={dateRange.endDate}
              onChange={(e) => handleDateRangeChange(dateRange.startDate, e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm"
            />
          </div>
          
          {/* Export Button */}
          <button
            onClick={() => setShowExportModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 text-sm"
          >
            <Download size={16} />
            Export
          </button>
        </div>
      </div>

      {/* Key Metrics */}
      {isDashboardLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-white p-6 rounded-lg shadow animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
              <div className="h-8 bg-gray-200 rounded w-1/2"></div>
            </div>
          ))}
        </div>
      ) : dashboardData ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <MetricCard
            title="Total Balance"
            value={`$${dashboardData.metrics.total_balance.toLocaleString()}`}
            icon={<DollarSign className="h-6 w-6" />}
            trend={dashboardData.metrics.total_balance > 0 ? 'up' : 'down'}
            className="bg-blue-50 border-blue-200"
          />
          
          <MetricCard
            title="Monthly Income"
            value={`$${dashboardData.metrics.monthly_income.toLocaleString()}`}
            icon={<TrendingUp className="h-6 w-6 text-green-600" />}
            trend="up"
            className="bg-green-50 border-green-200"
          />
          
          <MetricCard
            title="Monthly Expenses"
            value={`$${dashboardData.metrics.monthly_expenses.toLocaleString()}`}
            icon={<TrendingDown className="h-6 w-6 text-red-600" />}
            trend="down"
            className="bg-red-50 border-red-200"
          />
          
          <MetricCard
            title="Savings Rate"
            value={`${dashboardData.metrics.savings_rate.toFixed(1)}%`}
            icon={<PieChart className="h-6 w-6 text-purple-600" />}
            trend={dashboardData.metrics.savings_rate > 20 ? 'up' : 'down'}
            className="bg-purple-50 border-purple-200"
          />
        </div>
      ) : null}

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Main Chart */}
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Financial Overview</h2>
            <select
              value={selectedChartType}
              onChange={(e) => setSelectedChartType(e.target.value)}
              className="px-3 py-1 border border-gray-300 rounded text-sm"
            >
              <option value="category_pie">Category Breakdown</option>
              <option value="expense_trend">Expense Trend</option>
              <option value="income_trend">Income Trend</option>
              <option value="monthly_comparison">Monthly Comparison</option>
            </select>
          </div>
          
          {isChartLoading ? (
            <ChartSkeleton height={300} />
          ) : chartData ? (
            <ChartComponent data={chartData} height={300} />
          ) : (
            <div className="h-[300px] flex items-center justify-center text-gray-500">
              No chart data available
            </div>
          )}
        </div>

        {/* Category Breakdown */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Category Breakdown</h2>
          {isDashboardLoading ? (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="animate-pulse">
                  <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                  <div className="h-2 bg-gray-200 rounded"></div>
                </div>
              ))}
            </div>
          ) : dashboardData ? (
            <CategoryBreakdown categories={dashboardData.category_breakdown} />
          ) : (
            <div className="text-gray-500">No category data available</div>
          )}
        </div>
      </div>

      {/* Recent Transactions */}
      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Transactions</h2>
        {isDashboardLoading ? (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="animate-pulse flex justify-between">
                <div className="h-4 bg-gray-200 rounded w-1/3"></div>
                <div className="h-4 bg-gray-200 rounded w-1/4"></div>
              </div>
            ))}
          </div>
        ) : dashboardData ? (
          <RecentTransactions transactions={dashboardData.recent_transactions} />
        ) : (
          <div className="text-gray-500">No recent transactions</div>
        )}
      </div>

      {/* Export Modal */}
      {showExportModal && (
        <ExportModal
          onClose={() => setShowExportModal(false)}
          onExport={handleExport}
        />
      )}
    </div>
  );
};