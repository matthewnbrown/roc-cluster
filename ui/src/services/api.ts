import axios, { AxiosResponse } from 'axios';
import {
  Account,
  AccountCreate,
  AccountUpdate,
  UserCookies,
  UserCookiesCreate,
  UserCookiesUpdate,
  SentCreditLog,
  PaginatedResponse,
  ApiError,
  Cluster,
  ClusterResponse,
  ClusterListResponse,
  AccountCluster,
} from '../types/api';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`Making ${config.method?.toUpperCase()} request to ${config.url}`);
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.data?.detail) {
      console.error('API Error:', error.response.data.detail);
    } else {
      console.error('API Error:', error.message);
    }
    return Promise.reject(error);
  }
);

// Account API functions
export const accountApi = {
  // Get all accounts with pagination
  getAccounts: async (page: number = 1, perPage: number = 100): Promise<PaginatedResponse<Account>> => {
    const response: AxiosResponse<PaginatedResponse<Account>> = await api.get('/accounts', {
      params: { page, per_page: perPage },
    });
    return response.data;
  },

  // Get account by ID
  getAccount: async (id: number): Promise<Account> => {
    const response: AxiosResponse<Account> = await api.get(`/accounts/${id}`);
    return response.data;
  },

  // Create new account
  createAccount: async (accountData: AccountCreate): Promise<Account> => {
    const response: AxiosResponse<Account> = await api.post('/accounts', accountData);
    return response.data;
  },

  // Update account
  updateAccount: async (id: number, accountData: AccountUpdate): Promise<Account> => {
    const response: AxiosResponse<Account> = await api.put(`/accounts/${id}`, accountData);
    return response.data;
  },

  // Delete account
  deleteAccount: async (id: number): Promise<void> => {
    await api.delete(`/accounts/${id}`);
  },

  // Get clusters for account
  getAccountClusters: async (accountId: number): Promise<AccountCluster[]> => {
    const response: AxiosResponse<AccountCluster[]> = await api.get(`/accounts/${accountId}/clusters`);
    return response.data;
  },
};

// User Cookies API functions
export const cookiesApi = {
  // Get cookies for account
  getCookies: async (accountId: number): Promise<UserCookies> => {
    const response: AxiosResponse<UserCookies> = await api.get(`/accounts/${accountId}/cookies`);
    return response.data;
  },

  // Create or update cookies
  upsertCookies: async (accountId: number, cookiesData: UserCookiesCreate): Promise<UserCookies> => {
    const response: AxiosResponse<UserCookies> = await api.post(`/accounts/${accountId}/cookies`, cookiesData);
    return response.data;
  },

  // Update cookies
  updateCookies: async (accountId: number, cookiesData: UserCookiesUpdate): Promise<UserCookies> => {
    const response: AxiosResponse<UserCookies> = await api.put(`/accounts/${accountId}/cookies`, cookiesData);
    return response.data;
  },

  // Delete cookies
  deleteCookies: async (accountId: number): Promise<void> => {
    await api.delete(`/accounts/${accountId}/cookies`);
  },
};

// Credit Logs API functions
export const creditLogsApi = {
  // Get credit logs for specific account
  getAccountCreditLogs: async (
    accountId: number,
    page: number = 1,
    perPage: number = 100
  ): Promise<PaginatedResponse<SentCreditLog>> => {
    const response: AxiosResponse<PaginatedResponse<SentCreditLog>> = await api.get(
      `/accounts/${accountId}/credit-logs`,
      {
        params: { page, per_page: perPage },
      }
    );
    return response.data;
  },

  // Get all credit logs
  getAllCreditLogs: async (page: number = 1, perPage: number = 100): Promise<PaginatedResponse<SentCreditLog>> => {
    const response: AxiosResponse<PaginatedResponse<SentCreditLog>> = await api.get('/accounts/credit-logs', {
      params: { page, per_page: perPage },
    });
    return response.data;
  },
};

// Cluster API functions
export const clusterApi = {
  // Get all clusters with pagination
  getClusters: async (page: number = 1, perPage: number = 100, search?: string): Promise<PaginatedResponse<ClusterListResponse>> => {
    const response: AxiosResponse<PaginatedResponse<ClusterListResponse>> = await api.get('/clusters', {
      params: { page, per_page: perPage, search },
    });
    return response.data;
  },

  // Get cluster by ID
  getCluster: async (id: number): Promise<ClusterResponse> => {
    const response: AxiosResponse<ClusterResponse> = await api.get(`/clusters/${id}`);
    return response.data;
  },

  // Create new cluster
  createCluster: async (clusterData: { name: string; description?: string }): Promise<ClusterResponse> => {
    const response: AxiosResponse<ClusterResponse> = await api.post('/clusters', clusterData);
    return response.data;
  },

  // Update cluster
  updateCluster: async (id: number, clusterData: { name?: string; description?: string }): Promise<ClusterResponse> => {
    const response: AxiosResponse<ClusterResponse> = await api.put(`/clusters/${id}`, clusterData);
    return response.data;
  },

  // Delete cluster
  deleteCluster: async (id: number): Promise<void> => {
    await api.delete(`/clusters/${id}`);
  },

  // Add users to cluster
  addUsersToCluster: async (clusterId: number, accountIds: number[]): Promise<{ message: string; added_count: number; skipped_count: number }> => {
    const response: AxiosResponse<{ message: string; added_count: number; skipped_count: number }> = await api.post(`/clusters/${clusterId}/users`, {
      account_ids: accountIds,
    });
    return response.data;
  },

  // Remove user from cluster
  removeUserFromCluster: async (clusterId: number, accountId: number): Promise<void> => {
    await api.delete(`/clusters/${clusterId}/users/${accountId}`);
  },

  // Clone cluster
  cloneCluster: async (clusterId: number, cloneData: { name: string; description?: string; include_users: boolean }): Promise<ClusterResponse> => {
    console.log('API cloneCluster called with:', { clusterId, cloneData });
    const response: AxiosResponse<ClusterResponse> = await api.post(`/clusters/${clusterId}/clone`, cloneData);
    return response.data;
  },
};

export default api;
