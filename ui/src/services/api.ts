import axios, { AxiosResponse } from 'axios';
import {
  Account,
  AccountCreate,
  AccountUpdate,
  AccountMetadata,
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
  JobListResponse,
  JobResponse,
  JobCreateRequest,
  JobStatus,
  ActionType,
  SetCreditSavingRequest,
  ActionResponse,
  SabotageRequest,
  BuyUpgradeRequest,
  TrainingPurchaseRequest,
  Weapon,
  ArmoryPreferences,
  ArmoryPreferencesCreate,
  ArmoryPreferencesUpdate,
  SoldierType,
  TrainingPreferences,
  TrainingPreferencesCreate,
  TrainingPreferencesUpdate,
  FavoriteJobCreateRequest,
  FavoriteJobResponse,
  FavoriteJobListResponse,
  SystemNotification,
  SystemNotificationsResponse,
  PruningStatsResponse,
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
    const response: AxiosResponse<PaginatedResponse<Account>> = await api.get('/accounts/', {
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
    const response: AxiosResponse<PaginatedResponse<ClusterListResponse>> = await api.get('/clusters/', {
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

// Jobs API
export const jobsApi = {
  // Get all jobs with pagination and filtering
  getJobs: async (page: number = 1, perPage: number = 20, status?: string, includeSteps: boolean = true): Promise<JobListResponse> => {
    const params: any = { page, per_page: perPage, include_steps: includeSteps };
    if (status) params.status = status;
    
    const response: AxiosResponse<JobListResponse> = await api.get('/jobs/', { params });
    return response.data;
  },

  // Get job by ID
  getJob: async (id: number, includeSteps: boolean = false): Promise<JobResponse> => {
    const response: AxiosResponse<JobResponse> = await api.get(`/jobs/${id}`, {
      params: { include_steps: includeSteps },
    });
    return response.data;
  },

  // Create new job
  createJob: async (jobData: JobCreateRequest): Promise<JobResponse> => {
    const response: AxiosResponse<JobResponse> = await api.post('/jobs', jobData);
    return response.data;
  },

  // Cancel job
  cancelJob: async (id: number, reason?: string): Promise<{ message: string }> => {
    const response: AxiosResponse<{ message: string }> = await api.post(`/jobs/${id}/cancel`, {
      reason,
    });
    return response.data;
  },

  // Get job status (lightweight)
  getJobStatus: async (id: number): Promise<{
    job_id: number;
    status: JobStatus;
    progress: {
      total_steps: number;
      completed_steps: number;
      failed_steps: number;
    };
    created_at: string;
    started_at?: string;
    completed_at?: string;
  }> => {
    const response: AxiosResponse<any> = await api.get(`/jobs/${id}/status`);
    return response.data;
  },

  // Get job progress with step details (lightweight)
  getJobProgress: async (id: number): Promise<{
    job_id: number;
    status: JobStatus;
    progress: {
      total_steps: number;
      completed_steps: number;
      failed_steps: number;
      percentage: number;
    };
    steps: Array<{
      id: number;
      step_order: number;
      action_type: string;
      status: string;
      total_accounts: number;
      processed_accounts: number;
      successful_accounts: number;
      failed_accounts: number;
      progress_percentage: number;
    }>;
    updated_at: string;
  }> => {
    const response: AxiosResponse<any> = await api.get(`/jobs/${id}/progress`);
    return response.data;
  },

  // Get valid action types
  getValidActionTypes: async (): Promise<{
    action_types: ActionType[];
    categories: Record<string, ActionType[]>;
    summary: {
      total_action_types: number;
      categories: string[];
      user_actions: number;
      self_actions: number;
      info_actions: number;
    };
  }> => {
    const response: AxiosResponse<any> = await api.get('/jobs/valid-action-types');
    return response.data;
  },
};

// Actions API functions
export const actionsApi = {
  // Set credit saving
  setCreditSaving: async (request: SetCreditSavingRequest): Promise<ActionResponse> => {
    const response: AxiosResponse<ActionResponse> = await api.post('/actions/set-credit-saving', request);
    return response.data;
  },

  // Sabotage action
  sabotage: async (request: SabotageRequest): Promise<ActionResponse> => {
    const response: AxiosResponse<ActionResponse> = await api.post('/actions/sabotage', request);
    return response.data;
  },

  // Buy upgrade action
  buyUpgrade: async (request: BuyUpgradeRequest): Promise<ActionResponse> => {
    const response: AxiosResponse<ActionResponse> = await api.post('/actions/buy-upgrade', request);
    return response.data;
  },

  // Purchase training
  purchaseTraining: async (request: TrainingPurchaseRequest): Promise<ActionResponse> => {
    const response: AxiosResponse<ActionResponse> = await api.post('/actions/training-purchase', request);
    return response.data;
  },

  // Get account metadata
  getAccountMetadata: async (accountId: number, maxRetries: number = 0): Promise<AccountMetadata> => {
    const response: AxiosResponse<AccountMetadata> = await api.get(`/actions/account/${accountId}/metadata`, {
      params: { max_retries: maxRetries },
    });
    return response.data;
  },
};

// Armory API functions
export const armoryApi = {
  // Get all weapons
  getWeapons: async (): Promise<Weapon[]> => {
    const response: AxiosResponse<Weapon[]> = await api.get('/armory/weapons');
    return response.data;
  },

  // Get armory preferences for account
  getArmoryPreferences: async (accountId: number): Promise<ArmoryPreferences> => {
    const response: AxiosResponse<ArmoryPreferences> = await api.get(`/armory/preferences/${accountId}`);
    return response.data;
  },

  // Create armory preferences
  createArmoryPreferences: async (preferencesData: ArmoryPreferencesCreate): Promise<ArmoryPreferences> => {
    const response: AxiosResponse<ArmoryPreferences> = await api.post('/armory/preferences', preferencesData);
    return response.data;
  },

  // Update armory preferences
  updateArmoryPreferences: async (accountId: number, preferencesData: ArmoryPreferencesUpdate): Promise<ArmoryPreferences> => {
    const response: AxiosResponse<ArmoryPreferences> = await api.put(`/armory/preferences/${accountId}`, preferencesData);
    return response.data;
  },

  // Delete armory preferences
  deleteArmoryPreferences: async (accountId: number): Promise<void> => {
    await api.delete(`/armory/preferences/${accountId}`);
  },

  // Purchase armory by preferences
  purchaseArmoryByPreferences: async (accountId: number): Promise<ActionResponse> => {
    const response: AxiosResponse<ActionResponse> = await api.post(`/armory/purchase/${accountId}`);
    return response.data;
  },

  // Get all soldier types
  getSoldierTypes: async (): Promise<SoldierType[]> => {
    const response: AxiosResponse<SoldierType[]> = await api.get('/armory/soldier-types');
    return response.data;
  },

  // Get training preferences for account
  getTrainingPreferences: async (accountId: number): Promise<TrainingPreferences> => {
    const response: AxiosResponse<TrainingPreferences> = await api.get(`/armory/training-preferences/${accountId}`);
    return response.data;
  },

  // Create training preferences
  createTrainingPreferences: async (preferencesData: TrainingPreferencesCreate): Promise<TrainingPreferences> => {
    const response: AxiosResponse<TrainingPreferences> = await api.post('/armory/training-preferences', preferencesData);
    return response.data;
  },

  // Update training preferences
  updateTrainingPreferences: async (accountId: number, preferencesData: TrainingPreferencesUpdate): Promise<TrainingPreferences> => {
    const response: AxiosResponse<TrainingPreferences> = await api.put(`/armory/training-preferences/${accountId}`, preferencesData);
    return response.data;
  },

  // Delete training preferences
  deleteTrainingPreferences: async (accountId: number): Promise<void> => {
    await api.delete(`/armory/training-preferences/${accountId}`);
  },

  // Favorite Jobs API
  favoriteJobs: {
    async list(): Promise<FavoriteJobListResponse> {
      const response: AxiosResponse<FavoriteJobListResponse> = await api.get('/favorite-jobs/');
      return response.data;
    },

    async get(id: number): Promise<FavoriteJobResponse> {
      const response: AxiosResponse<FavoriteJobResponse> = await api.get(`/favorite-jobs/${id}`);
      return response.data;
    },

    async create(data: FavoriteJobCreateRequest): Promise<FavoriteJobResponse> {
      const response: AxiosResponse<FavoriteJobResponse> = await api.post('/favorite-jobs/', data);
      return response.data;
    },

    async update(id: number, data: FavoriteJobCreateRequest): Promise<FavoriteJobResponse> {
      const response: AxiosResponse<FavoriteJobResponse> = await api.put(`/favorite-jobs/${id}`, data);
      return response.data;
    },

    async delete(id: number): Promise<void> {
      await api.delete(`/favorite-jobs/${id}`);
    },

    async markAsUsed(id: number): Promise<void> {
      await api.post(`/favorite-jobs/${id}/use`);
    },
  },
};

// Export individual API objects for use in hooks
export const favoriteJobsApi = {
  async list(): Promise<FavoriteJobListResponse> {
    const response: AxiosResponse<FavoriteJobListResponse> = await api.get('/favorite-jobs/');
    return response.data;
  },

  async get(id: number): Promise<FavoriteJobResponse> {
    const response: AxiosResponse<FavoriteJobResponse> = await api.get(`/favorite-jobs/${id}`);
    return response.data;
  },

  async create(data: FavoriteJobCreateRequest): Promise<FavoriteJobResponse> {
    const response: AxiosResponse<FavoriteJobResponse> = await api.post('/favorite-jobs/', data);
    return response.data;
  },

  async update(id: number, data: FavoriteJobCreateRequest): Promise<FavoriteJobResponse> {
    const response: AxiosResponse<FavoriteJobResponse> = await api.put(`/favorite-jobs/${id}`, data);
    return response.data;
  },

  async delete(id: number): Promise<void> {
    await api.delete(`/favorite-jobs/${id}`);
  },

  async markAsUsed(id: number): Promise<void> {
    await api.post(`/favorite-jobs/${id}/use`);
  },
};

// System API
export const systemApi = {
  async getPruningStats(): Promise<PruningStatsResponse> {
    const response: AxiosResponse<PruningStatsResponse> = await api.get('/system/pruning/stats');
    return response.data;
  },

  async getNotifications(limit: number = 10, notificationType?: string): Promise<SystemNotificationsResponse> {
    const params: any = { limit };
    if (notificationType) {
      params.notification_type = notificationType;
    }
    const response: AxiosResponse<SystemNotificationsResponse> = await api.get('/system/notifications', { params });
    return response.data;
  },

  async triggerManualPruning(): Promise<{ success: boolean; message: string }> {
    const response = await api.post('/system/pruning/trigger');
    return response.data;
  },

  async getDetailedHealthCheck(): Promise<any> {
    const response = await api.get('/system/health/detailed');
    return response.data;
  },

  async getDatabaseStats(): Promise<{ success: boolean; data: any }> {
    const response = await api.get('/system/database/stats');
    return response.data;
  },

  async triggerVacuum(): Promise<{ success: boolean; message: string; details?: any }> {
    const response = await api.post('/system/vacuum');
    return response.data;
  },

  async triggerFullVacuum(): Promise<{ success: boolean; message: string; details?: any }> {
    const response = await api.post('/system/vacuum/full');
    return response.data;
  },
};

export default api;
