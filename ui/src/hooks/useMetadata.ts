import { useQuery, UseQueryResult } from 'react-query';
import { actionsApi } from '../services/api';
import { AccountMetadata } from '../types/api';

export const useAccountMetadata = (
  accountId: number,
  maxRetries: number = 0,
  enabled: boolean = true
): UseQueryResult<AccountMetadata, Error> => {
  return useQuery(
    ['accountMetadata', accountId, maxRetries],
    () => actionsApi.getAccountMetadata(accountId, maxRetries),
    {
      enabled: enabled && !!accountId,
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000, // 5 minutes
    }
  );
};
