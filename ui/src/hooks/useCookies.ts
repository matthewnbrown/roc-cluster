import { useQuery, useMutation, useQueryClient } from 'react-query';
import { cookiesApi } from '../services/api';
import { UserCookies, UserCookiesCreate, UserCookiesUpdate } from '../types/api';

// Query keys
export const cookiesKeys = {
  all: ['cookies'] as const,
  byAccount: (accountId: number) => [...cookiesKeys.all, 'account', accountId] as const,
};

// Hooks for cookies
export const useCookies = (accountId: number) => {
  return useQuery(
    cookiesKeys.byAccount(accountId),
    () => cookiesApi.getCookies(accountId),
    {
      enabled: !!accountId,
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: (failureCount, error: any) => {
        // Don't retry on 404 (no cookies found)
        if (error?.response?.status === 404) {
          return false;
        }
        return failureCount < 3;
      },
    }
  );
};

export const useUpsertCookies = () => {
  const queryClient = useQueryClient();

  return useMutation(
    ({ accountId, data }: { accountId: number; data: UserCookiesCreate }) =>
      cookiesApi.upsertCookies(accountId, data),
    {
      onSuccess: (updatedCookies) => {
        // Update the cookies in cache
        queryClient.setQueryData(cookiesKeys.byAccount(updatedCookies.account_id), updatedCookies);
      },
    }
  );
};

export const useUpdateCookies = () => {
  const queryClient = useQueryClient();

  return useMutation(
    ({ accountId, data }: { accountId: number; data: UserCookiesUpdate }) =>
      cookiesApi.updateCookies(accountId, data),
    {
      onSuccess: (updatedCookies) => {
        // Update the cookies in cache
        queryClient.setQueryData(cookiesKeys.byAccount(updatedCookies.account_id), updatedCookies);
      },
    }
  );
};

export const useDeleteCookies = () => {
  const queryClient = useQueryClient();

  return useMutation(
    (accountId: number) => cookiesApi.deleteCookies(accountId),
    {
      onSuccess: (_, accountId) => {
        // Remove the cookies from cache
        queryClient.removeQueries(cookiesKeys.byAccount(accountId));
      },
    }
  );
};
