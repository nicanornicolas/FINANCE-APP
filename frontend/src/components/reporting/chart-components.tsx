'use client';

import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from 'chart.js';
import { Line, Bar, Pie } from 'react-chartjs-2';
import { ChartData } from '../../lib/api/reporting';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
);

interface ChartComponentProps {
  data: ChartData;
  height?: number;
  className?: string;
}

export const ChartComponent: React.FC<ChartComponentProps> = ({ 
  data, 
  height = 300, 
  className = '' 
}) => {
  const chartData = {
    labels: data.labels,
    datasets: data.datasets,
  };

  const defaultOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: data.title,
      },
    },
    ...data.options,
  };

  const renderChart = () => {
    switch (data.chart_type) {
      case 'line':
        return (
          <Line 
            data={chartData} 
            options={defaultOptions} 
            height={height}
          />
        );
      case 'bar':
        return (
          <Bar 
            data={chartData} 
            options={defaultOptions} 
            height={height}
          />
        );
      case 'pie':
        return (
          <Pie 
            data={chartData} 
            options={{
              ...defaultOptions,
              plugins: {
                ...defaultOptions.plugins,
                legend: {
                  position: 'right' as const,
                },
              },
            }} 
            height={height}
          />
        );
      default:
        return <div>Unsupported chart type: {data.chart_type}</div>;
    }
  };

  return (
    <div className={`w-full ${className}`} style={{ height: `${height}px` }}>
      {renderChart()}
    </div>
  );
};

// Specific chart components for common use cases
export const ExpenseTrendChart: React.FC<{ data: ChartData; className?: string }> = ({ 
  data, 
  className 
}) => (
  <ChartComponent 
    data={data} 
    height={250} 
    className={className}
  />
);

export const CategoryPieChart: React.FC<{ data: ChartData; className?: string }> = ({ 
  data, 
  className 
}) => (
  <ChartComponent 
    data={data} 
    height={300} 
    className={className}
  />
);

export const MonthlyComparisonChart: React.FC<{ data: ChartData; className?: string }> = ({ 
  data, 
  className 
}) => (
  <ChartComponent 
    data={data} 
    height={250} 
    className={className}
  />
);

// Loading placeholder for charts
export const ChartSkeleton: React.FC<{ height?: number; className?: string }> = ({ 
  height = 300, 
  className = '' 
}) => (
  <div 
    className={`bg-gray-100 animate-pulse rounded-lg flex items-center justify-center ${className}`}
    style={{ height: `${height}px` }}
  >
    <div className="text-gray-400">Loading chart...</div>
  </div>
);