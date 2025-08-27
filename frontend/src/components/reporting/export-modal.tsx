'use client';

import React, { useState } from 'react';
import { X, Download } from 'lucide-react';
import { ExportFormat } from '../../lib/api/reporting';

interface ExportModalProps {
  onClose: () => void;
  onExport: (format: ExportFormat, type: string) => Promise<void>;
}

export const ExportModal: React.FC<ExportModalProps> = ({ onClose, onExport }) => {
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>('pdf');
  const [selectedType, setSelectedType] = useState<string>('expense-summary');
  const [isExporting, setIsExporting] = useState(false);

  const exportTypes = [
    { value: 'expense-summary', label: 'Expense Summary' },
    { value: 'financial-metrics', label: 'Financial Metrics' },
    { value: 'transactions', label: 'Transaction Data' }
  ];

  const exportFormats = [
    { value: 'pdf' as ExportFormat, label: 'PDF' },
    { value: 'csv' as ExportFormat, label: 'CSV' },
    { value: 'excel' as ExportFormat, label: 'Excel' },
    { value: 'json' as ExportFormat, label: 'JSON' }
  ];

  const handleExport = async () => {
    setIsExporting(true);
    try {
      await onExport(selectedFormat, selectedType);
      onClose();
    } catch (error) {
      console.error('Export failed:', error);
      // You might want to show an error message here
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Export Report</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X size={20} />
          </button>
        </div>

        <div className="space-y-4">
          {/* Export Type Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Report Type
            </label>
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {exportTypes.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>

          {/* Format Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Format
            </label>
            <div className="grid grid-cols-2 gap-2">
              {exportFormats.map((format) => (
                <button
                  key={format.value}
                  onClick={() => setSelectedFormat(format.value)}
                  className={`px-3 py-2 text-sm rounded-md border transition-colors ${
                    selectedFormat === format.value
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  {format.label}
                </button>
              ))}
            </div>
          </div>

          {/* Export Description */}
          <div className="bg-gray-50 p-3 rounded-md">
            <p className="text-sm text-gray-600">
              {selectedType === 'expense-summary' && 
                'Export a detailed breakdown of expenses by category with totals and percentages.'}
              {selectedType === 'financial-metrics' && 
                'Export key financial metrics including income, expenses, savings rate, and trends.'}
              {selectedType === 'transactions' && 
                'Export raw transaction data with all details for the selected date range.'}
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-end space-x-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
            disabled={isExporting}
          >
            Cancel
          </button>
          <button
            onClick={handleExport}
            disabled={isExporting}
            className="flex items-center space-x-2 px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Download size={16} />
            <span>{isExporting ? 'Exporting...' : 'Export'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};