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

export interface AccountMetadata {
  rank: number;
  turns: number;
  next_turn: string;
  gold: number;
  last_hit: string;
  last_sabbed: string;
  mail: string;
  credits: number;
  username: string;
  lastclicked: string;
  saving: string;
  gets: number;
  credits_given: number;
  credits_received: number;
  userid: string;
  allianceid: string;
  servertime: string;
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
  account_count: number; // Number of accounts in this step (instead of full list)
  original_cluster_ids?: number[]; // Original cluster IDs for cloning
  original_account_ids?: number[]; // Original direct account IDs for cloning
  target_id?: string;
  parameters?: Record<string, any>;
  max_retries: number;
  is_async: boolean;
  status: JobStatus;
  result?: Record<string, any>;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
  total_accounts: number;
  processed_accounts: number;
  successful_accounts: number;
  failed_accounts: number;
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

// Favorite Job Types
export interface FavoriteJobCreateRequest {
  name: string;
  description?: string;
  job_config: Record<string, any>;
}

export interface FavoriteJobResponse {
  id: number;
  name: string;
  description?: string;
  job_config: Record<string, any>;
  created_at: string;
  updated_at?: string;
  usage_count: number;
  last_used_at?: string;
}

export interface FavoriteJobListResponse {
  favorite_jobs: FavoriteJobResponse[];
  total: number;
}

// System Types
export interface SystemNotification {
  id: number;
  timestamp: string;
  success: boolean;
  message: string;
  type: string;
  details: any;
}

export interface SystemNotificationsResponse {
  success: boolean;
  data: {
    notifications: SystemNotification[];
    total: number;
    since: string;
  };
}

export interface PruningStats {
  total_jobs: number;
  jobs_beyond_10th: number;
  total_steps_to_prune: number;
  pruned_jobs_count: number;
  service_running: boolean;
  last_checked: string;
}

export interface PruningStatsResponse {
  success: boolean;
  data: PruningStats;
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

// Action Request Types
export interface AccountIdentifier {
  id_type: 'id' | 'username' | 'email';
  id: string;
}

export interface SetCreditSavingRequest {
  acting_user: AccountIdentifier;
  max_retries?: number;
  value: 'on' | 'off';
}

export interface ActionResponse {
  success: boolean;
  message?: string;
  error?: string;
  data?: Record<string, number>; // weapon_id -> purchase_amount for armory purchases
  timestamp: string;
}

// Additional Action Requests
export interface SabotageRequest {
  acting_user: AccountIdentifier;
  max_retries?: number;
  target_id: string; // enemy user id
  spy_count: number;
  enemy_weapon: number; // weapon id to target
}

export interface BuyUpgradeRequest {
  acting_user: AccountIdentifier;
  max_retries?: number;
  upgrade_option: 'siege' | 'fortification' | 'covert' | 'recruiter';
}

export interface TrainingPurchaseRequest {
  acting_user: AccountIdentifier;
  max_retries?: number;
  // Map of soldier_type_name -> quantity or structured orders
  training_orders: Record<string, any>;
}

// Weapon Types
export interface Weapon {
  id: number;
  roc_weapon_id: number;
  name: string;
  display_name: string;
  created_at: string;
}

// Armory Preferences Types
export interface ArmoryWeaponPreference {
  weapon_id: number;
  weapon_name: string;
  weapon_display_name: string;
  percentage: number;
}

export interface ArmoryPreferences {
  id: number;
  account_id: number;
  created_at: string;
  updated_at?: string;
  weapon_preferences: ArmoryWeaponPreference[];
}

export interface ArmoryPreferencesCreate {
  account_id: number;
  weapon_percentages: Record<string, number>; // weapon_name -> percentage
}

export interface ArmoryPreferencesUpdate {
  weapon_percentages: Record<string, number>; // weapon_name -> percentage
}

// Soldier Types
export interface SoldierType {
  id: number;
  roc_soldier_type_id: string;
  name: string;
  display_name: string;
  costs_soldiers: boolean;
  created_at: string;
}

// Training Preferences Types
export interface TrainingSoldierTypePreference {
  soldier_type_id: number;
  soldier_type_name: string;
  soldier_type_display_name: string;
  soldier_type_costs_soldiers: boolean;
  percentage: number;
}

export interface TrainingPreferences {
  id: number;
  account_id: number;
  created_at: string;
  updated_at?: string;
  soldier_type_preferences: TrainingSoldierTypePreference[];
}

export interface TrainingPreferencesCreate {
  account_id: number;
  soldier_type_percentages: Record<string, number>; // soldier_type_name -> percentage
}

export interface TrainingPreferencesUpdate {
  soldier_type_percentages: Record<string, number>; // soldier_type_name -> percentage
}