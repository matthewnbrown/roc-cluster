import { useQuery } from 'react-query';
import { creditLogsApi } from '../services/api';
import { SentCreditLog, PaginatedResponse } from '../types/api';

// Query keys
export const creditLogsKeys = {
  all: ['creditLogs'] as const,
  byAccount: (accountId: number, page: number, perPage: number) =>
    [...creditLogsKeys.all, 'account', accountId, { page, perPage }] as const,
  allLogs: (page: number, perPage: number) => [...creditLogsKeys.all, 'all', { page, perPage }] as const,
};

// Hooks for credit logs
export const useAccountCreditLogs = (
  accountId: number,
  page: number = 1,
  perPage: number = 100
) => {
  return useQuery(
    creditLogsKeys.byAccount(accountId, page, perPage),
    () => creditLogsApi.getAccountCreditLogs(accountId, page, perPage),
    {
      enabled: !!accountId,
      keepPreviousData: true,
      staleTime: 2 * 60 * 1000, // 2 minutes
    }
  );
};

export const useAllCreditLogs = (page: number = 1, perPage: number = 100) => {
  return useQuery(
    creditLogsKeys.allLogs(page, perPage),
    () => creditLogsApi.getAllCreditLogs(page, perPage),
    {
      keepPreviousData: true,
      staleTime: 2 * 60 * 1000, // 2 minutes
    }
  );
};
