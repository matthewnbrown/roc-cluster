// API Types based on the FastAPI schemas

export interface Account {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
  last_login?: string;
}

export interface AccountCreate {
  username: string;
  email: string;
  password: string;
}

export interface AccountUpdate {
  username?: string;
  email?: string;
  password?: string;
  is_active?: boolean;
}

export interface UserCookies {
  id: number;
  account_id: number;
  cookies: string;
  created_at: string;
  updated_at?: string;
}

export interface UserCookiesCreate {
  account_id: number;
  cookies: string;
}

export interface UserCookiesUpdate {
  cookies: string;
}

export interface SentCreditLog {
  id: number;
  sender_account_id: number;
  target_user_id: string;
  amount: number;
  success: boolean;
  error_message?: string;
  timestamp: string;
}

export interface PaginationMeta {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
  next_page?: number;
  prev_page?: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: PaginationMeta;
}

export interface ApiError {
  detail: string;
}

export interface ApiResponse<T> {
  data?: T;
  error?: string;
}

// Cluster Types
export interface Cluster {
  id: number;
  name: string;
  description?: string;
  created_at: string;
  updated_at?: string;
  user_count?: number;
}

export interface ClusterUser {
  id: number;
  account_id: number;
  username: string;
  email: string;
  added_at: string;
}

export interface ClusterResponse extends Cluster {
  users: ClusterUser[];
  user_count: number;
}

export interface ClusterListResponse extends Cluster {
  user_count: number;
}

export interface AccountCluster {
  id: number;
  name: string;
  description?: string;
  added_at?: string;
}

// Job-related types
export type JobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface JobStepRequest {
  account_ids?: number[];
  cluster_ids?: number[];
  action_type: string;
  parameters?: Record<string, any>;
  max_retries: number;
  is_async?: boolean;
}

export interface JobCreateRequest {
  name: string;
  description?: string;
  parallel_execution: boolean;
  steps: JobStepRequest[];
}

export interface JobStepResponse {
  id: number;
  step_order: number;
  action_type: string;
  account_id: number;
  target_id?: string;
  parameters?: Record<string, any>;
  max_retries: number;
  is_async: boolean;
  status: JobStatus;
  result?: Record<string, any>;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
}

export interface JobResponse {
  id: number;
  name: string;
  description?: string;
  status: JobStatus;
  parallel_execution: boolean;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  total_steps: number;
  completed_steps: number;
  failed_steps: number;
  error_message?: string;
  steps?: JobStepResponse[];
}

export interface JobListResponse {
  jobs: JobResponse[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface JobCancelRequest {
  reason?: string;
}

export interface ActionType {
  action_type: string;
  description: string;
  category: string;
  parameter_details?: Record<string, any>;
  required_parameters?: string[];
  optional_parameters?: string[];
  output?: Record<string, any>;
}
