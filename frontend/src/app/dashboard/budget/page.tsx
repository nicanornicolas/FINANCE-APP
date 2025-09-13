'use client';

import React, { useEffect, useState } from 'react';
import { budgetApi, BudgetSummary, BudgetVsActualComparison } from '@/lib/api/budget';
import { ChartComponent } from '@/components/reporting';

export default function BudgetPage() {
  const [summary, setSummary] = useState<BudgetSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const run = async () => {
      try {
        const s = await budgetApi.getSummary();
        setSummary(s);
      } catch (e: any) {
        setError(e?.message || 'Failed to load budget summary');
      } finally {
        setLoading(false);
      }
    };
    run();
  }, []);

  if (loading) {
    return <div className="p-6">Loading budget dashboard...</div>;
  }

  if (error) {
    return <div className="p-6 text-red-600">{error}</div>;
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Budget & Goals</h1>

      {/* Budgets Summary */}
      <section className="bg-white rounded-lg shadow p-4">
        <h2 className="text-lg font-medium mb-4">Budgets</h2>
        <pre className="text-sm bg-gray-50 p-3 rounded overflow-auto">{JSON.stringify(summary?.budgets, null, 2)}</pre>
      </section>

      {/* Goals Summary */}
      <section className="bg-white rounded-lg shadow p-4">
        <h2 className="text-lg font-medium mb-4">Goals</h2>
        <pre className="text-sm bg-gray-50 p-3 rounded overflow-auto">{JSON.stringify(summary?.goals, null, 2)}</pre>
      </section>
    </div>
  );
}

