'use client';

import { MainLayout } from '@/components/layout/main-layout';
import { TransactionList } from '@/components/transactions/transaction-list';

export default function TransactionsPage() {
  return (
    <MainLayout>
      <TransactionList />
    </MainLayout>
  );
}