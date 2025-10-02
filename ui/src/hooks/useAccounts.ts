import { useQuery, useMutation, useQueryClient } from 'react-query';
import { useState, useEffect } from 'react';
import { accountApi } from '../services/api';
import { Account, AccountCreate, AccountUpdate } from '../types/api';

// Query keys
export const accountKeys = {
  all: ['accounts'] as const,
  lists: () => [...accountKeys.all, 'list'] as const,
  list: (page: number, perPage: number, search?: string) => [...accountKeys.lists(), { page, perPage, search }] as const,
  details: () => [...accountKeys.all, 'detail'] as const,
  detail: (id: number) => [...accountKeys.details(), id] as const,
};

// Hooks for accounts
export const useAccounts = (page: number = 1, perPage: number = 100, search?: string) => {
  return useQuery(
    accountKeys.list(page, perPage, search),
    () => accountApi.getAccounts(page, perPage, search),
    {
      keepPreviousData: true,
      staleTime: 5 * 60 * 1000, // 5 minutes
    }
  );
};

export const useAccount = (id: number) => {
  return useQuery(
    accountKeys.detail(id),
    () => accountApi.getAccount(id),
    {
      enabled: !!id,
      staleTime: 5 * 60 * 1000, // 5 minutes
    }
  );
};

export const useCreateAccount = () => {
  const queryClient = useQueryClient();

  return useMutation(
    (accountData: AccountCreate) => accountApi.createAccount(accountData),
    {
      onSuccess: () => {
        // Invalidate and refetch accounts list
        queryClient.invalidateQueries(accountKeys.lists());
      },
    }
  );
};

export const useUpdateAccount = () => {
  const queryClient = useQueryClient();

  return useMutation(
    ({ id, data }: { id: number; data: AccountUpdate }) => accountApi.updateAccount(id, data),
    {
      onSuccess: (updatedAccount) => {
        // Update the specific account in cache
        queryClient.setQueryData(accountKeys.detail(updatedAccount.id), updatedAccount);
        // Invalidate accounts list to refetch
        queryClient.invalidateQueries(accountKeys.lists());
      },
    }
  );
};

export const useDeleteAccount = () => {
  const queryClient = useQueryClient();

  return useMutation(
    (id: number) => accountApi.deleteAccount(id),
    {
      onSuccess: (_, deletedId) => {
        // Remove the account from cache
        queryClient.removeQueries(accountKeys.detail(deletedId));
        // Invalidate accounts list to refetch
        queryClient.invalidateQueries(accountKeys.lists());
      },
    }
  );
};

// Hook for account search/autocomplete with debouncing
export const useAccountSearch = (searchTerm: string, debounceMs: number = 300) => {
  const [debouncedSearchTerm, setDebouncedSearchTerm] = useState(searchTerm);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchTerm(searchTerm);
    }, debounceMs);

    return () => clearTimeout(timer);
  }, [searchTerm, debounceMs]);

  return useQuery(
    accountKeys.list(1, 50, debouncedSearchTerm), // Limit to 50 results for autocomplete
    () => accountApi.getAccounts(1, 50, debouncedSearchTerm),
    {
      enabled: debouncedSearchTerm.length >= 2, // Only search when at least 2 characters
      keepPreviousData: true,
      staleTime: 30 * 1000, // 30 seconds for autocomplete
    }
  );
};
