import { useQuery, useMutation, useQueryClient } from 'react-query';
import { clusterApi, accountApi } from '../services/api';
import { Cluster, ClusterResponse, ClusterListResponse, AccountCluster } from '../types/api';

// Query keys
export const clusterKeys = {
  all: ['clusters'] as const,
  lists: () => [...clusterKeys.all, 'list'] as const,
  list: (page: number, perPage: number, search?: string) => [...clusterKeys.lists(), { page, perPage, search }] as const,
  details: () => [...clusterKeys.all, 'detail'] as const,
  detail: (id: number) => [...clusterKeys.details(), id] as const,
  accountClusters: (accountId: number) => [...clusterKeys.all, 'account', accountId] as const,
};

// Hooks for clusters
export const useClusters = (page: number = 1, perPage: number = 100, search?: string) => {
  return useQuery(
    clusterKeys.list(page, perPage, search),
    () => clusterApi.getClusters(page, perPage, search),
    {
      keepPreviousData: true,
      staleTime: 5 * 60 * 1000, // 5 minutes
    }
  );
};

export const useCluster = (id: number) => {
  return useQuery(
    clusterKeys.detail(id),
    () => clusterApi.getCluster(id),
    {
      enabled: !!id,
      staleTime: 5 * 60 * 1000, // 5 minutes
    }
  );
};

export const useAccountClusters = (accountId: number) => {
  return useQuery(
    clusterKeys.accountClusters(accountId),
    () => accountApi.getAccountClusters(accountId),
    {
      enabled: !!accountId,
      staleTime: 5 * 60 * 1000, // 5 minutes
    }
  );
};

export const useCreateCluster = () => {
  const queryClient = useQueryClient();

  return useMutation(
    (clusterData: { name: string; description?: string }) => clusterApi.createCluster(clusterData),
    {
      onSuccess: () => {
        // Invalidate and refetch clusters list
        queryClient.invalidateQueries(clusterKeys.lists());
      },
    }
  );
};

export const useUpdateCluster = () => {
  const queryClient = useQueryClient();

  return useMutation(
    ({ id, data }: { id: number; data: { name?: string; description?: string } }) => 
      clusterApi.updateCluster(id, data),
    {
      onSuccess: (updatedCluster) => {
        // Update the specific cluster in cache
        queryClient.setQueryData(clusterKeys.detail(updatedCluster.id), updatedCluster);
        // Invalidate clusters list to refetch
        queryClient.invalidateQueries(clusterKeys.lists());
      },
    }
  );
};

export const useDeleteCluster = () => {
  const queryClient = useQueryClient();

  return useMutation(
    (id: number) => clusterApi.deleteCluster(id),
    {
      onSuccess: (_, deletedId) => {
        // Remove the cluster from cache
        queryClient.removeQueries(clusterKeys.detail(deletedId));
        // Invalidate clusters list to refetch
        queryClient.invalidateQueries(clusterKeys.lists());
        // Invalidate all account clusters queries since they might be affected
        queryClient.invalidateQueries([...clusterKeys.all, 'account']);
      },
    }
  );
};

export const useAddUsersToCluster = () => {
  const queryClient = useQueryClient();

  return useMutation(
    ({ clusterId, accountIds }: { clusterId: number; accountIds: number[] }) =>
      clusterApi.addUsersToCluster(clusterId, accountIds),
    {
      onSuccess: (_, { clusterId }) => {
        // Invalidate cluster details and account clusters
        queryClient.invalidateQueries(clusterKeys.detail(clusterId));
        queryClient.invalidateQueries([...clusterKeys.all, 'account']);
        queryClient.invalidateQueries(clusterKeys.lists());
      },
    }
  );
};

export const useRemoveUserFromCluster = () => {
  const queryClient = useQueryClient();

  return useMutation(
    ({ clusterId, accountId }: { clusterId: number; accountId: number }) =>
      clusterApi.removeUserFromCluster(clusterId, accountId),
    {
      onSuccess: (_, { clusterId, accountId }) => {
        // Invalidate cluster details and account clusters
        queryClient.invalidateQueries(clusterKeys.detail(clusterId));
        queryClient.invalidateQueries(clusterKeys.accountClusters(accountId));
        queryClient.invalidateQueries([...clusterKeys.all, 'account']);
        queryClient.invalidateQueries(clusterKeys.lists());
      },
    }
  );
};

export const useCloneCluster = () => {
  const queryClient = useQueryClient();

  return useMutation(
    ({ clusterId, cloneData }: { clusterId: number; cloneData: { name: string; description?: string; include_users: boolean } }) =>
      clusterApi.cloneCluster(clusterId, cloneData),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(clusterKeys.lists());
      },
    }
  );
};
