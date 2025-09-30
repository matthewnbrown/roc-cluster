import { useQuery, useMutation, useQueryClient } from 'react-query';
import { jobsApi } from '../services/api';
import { JobListResponse, JobResponse, JobCreateRequest, JobStatus } from '../types/api';

// Query keys for jobs
export const jobKeys = {
  all: ['jobs'] as const,
  lists: () => [...jobKeys.all, 'list'] as const,
  list: (filters: Record<string, any>) => [...jobKeys.lists(), filters] as const,
  details: () => [...jobKeys.all, 'detail'] as const,
  detail: (id: number) => [...jobKeys.details(), id] as const,
  status: (id: number) => [...jobKeys.all, 'status', id] as const,
  actionTypes: () => [...jobKeys.all, 'actionTypes'] as const,
};

// Get all jobs with pagination and filtering
export const useJobs = (page: number = 1, perPage: number = 20, status?: string, includeSteps: boolean = true) => {
  return useQuery<JobListResponse, Error>(
    jobKeys.list({ page, perPage, status, includeSteps }),
    () => jobsApi.getJobs(page, perPage, status, includeSteps),
    {
      keepPreviousData: true,
      refetchInterval: (data) => {
        // Only auto-refresh if there are running or pending jobs on the current page
        if (data?.jobs && data.jobs.some(job => job.status === 'running' || job.status === 'pending')) {
          return 1000; // Refetch every 5 seconds if there are active jobs
        }
        return false; // Don't refetch if no active jobs
      },
    }
  );
};

// Get job by ID
export const useJob = (id: number, includeSteps: boolean = false) => {
  return useQuery<JobResponse, Error>(
    jobKeys.detail(id),
    () => jobsApi.getJob(id, includeSteps),
    {
      enabled: !!id,
      refetchInterval: (data) => {
        // Refetch every 3 seconds if job is running or pending
        if (data && (data.status === 'running' || data.status === 'pending')) {
          return 3000; // Refetch every 3 seconds
        }
        return false; // Don't refetch if completed, failed, or cancelled
      },
    }
  );
};

// Get job status (lightweight)
export const useJobStatus = (id: number) => {
  return useQuery(
    jobKeys.status(id),
    () => jobsApi.getJobStatus(id),
    {
      enabled: !!id,
      refetchInterval: (data) => {
        // Refetch every 3 seconds if job is running
        if (data?.status === 'running' || data?.status === 'pending') {
          return 3000;
        }
        return false;
      },
    }
  );
};

// Get job progress with step details (lightweight)
export const useJobProgress = (id: number) => {
  return useQuery(
    [...jobKeys.all, 'progress', id],
    () => jobsApi.getJobProgress(id),
    {
      enabled: !!id,
      refetchInterval: (data) => {
        // Refetch every 2 seconds if job is running or pending, or if no data yet
        if (!data || data?.status === 'running' || data?.status === 'pending') {
          return 2000;
        }
        return false;
      },
    }
  );
};

// Get valid action types
export const useValidActionTypes = () => {
  return useQuery(
    jobKeys.actionTypes(),
    () => jobsApi.getValidActionTypes(),
    {
      staleTime: 5 * 60 * 1000, // 5 minutes
    }
  );
};

// Create job mutation
export const useCreateJob = () => {
  const queryClient = useQueryClient();
  
  return useMutation(
    (jobData: JobCreateRequest) => jobsApi.createJob(jobData),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(jobKeys.lists());
      },
    }
  );
};

// Cancel job mutation
export const useCancelJob = () => {
  const queryClient = useQueryClient();
  
  return useMutation(
    ({ id, reason }: { id: number; reason?: string }) => jobsApi.cancelJob(id, reason),
    {
      onSuccess: (_, { id }) => {
        queryClient.invalidateQueries(jobKeys.detail(id));
        queryClient.invalidateQueries(jobKeys.status(id));
        queryClient.invalidateQueries(jobKeys.lists());
      },
    }
  );
};
