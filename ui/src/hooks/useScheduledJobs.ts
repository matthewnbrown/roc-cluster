import { useState, useEffect } from 'react';
import { scheduledJobsApi } from '../services/api';
import { 
  ScheduledJobResponse, 
  ScheduledJobCreateRequest, 
  ScheduledJobExecutionResponse 
} from '../types/api';
import { getCurrentTimestamp } from '../utils/dateUtils';

export const useScheduledJobs = () => {
  const [scheduledJobs, setScheduledJobs] = useState<ScheduledJobResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchScheduledJobs = async (status?: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await scheduledJobsApi.list(status);
      setScheduledJobs(response.scheduled_jobs);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch scheduled jobs');
    } finally {
      setLoading(false);
    }
  };

  const createScheduledJob = async (data: ScheduledJobCreateRequest): Promise<ScheduledJobResponse | null> => {
    try {
      const newScheduledJob = await scheduledJobsApi.create(data);
      setScheduledJobs(prev => [newScheduledJob, ...prev]);
      return newScheduledJob;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create scheduled job');
      return null;
    }
  };

  const updateScheduledJob = async (id: number, data: ScheduledJobCreateRequest): Promise<ScheduledJobResponse | null> => {
    try {
      const updatedScheduledJob = await scheduledJobsApi.update(id, data);
      setScheduledJobs(prev => 
        prev.map(job => job.id === id ? updatedScheduledJob : job)
      );
      return updatedScheduledJob;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update scheduled job');
      return null;
    }
  };

  const updateScheduledJobStatus = async (id: number, status: string): Promise<boolean> => {
    try {
      await scheduledJobsApi.updateStatus(id, status);
      
      // Fetch the updated job to get all fields (like next_execution_at)
      const updatedJob = await scheduledJobsApi.get(id);
      if (updatedJob) {
        setScheduledJobs(prev => 
          prev.map(job => job.id === id ? updatedJob : job)
        );
      } else {
        // Fallback to just updating status if fetch fails
        setScheduledJobs(prev => 
          prev.map(job => job.id === id ? { ...job, status } : job)
        );
      }
      
      return true;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update scheduled job status');
      return false;
    }
  };

  const deleteScheduledJob = async (id: number): Promise<boolean> => {
    try {
      await scheduledJobsApi.delete(id);
      setScheduledJobs(prev => prev.filter(job => job.id !== id));
      return true;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete scheduled job');
      return false;
    }
  };

  const getScheduledJob = async (id: number): Promise<ScheduledJobResponse | null> => {
    try {
      return await scheduledJobsApi.get(id);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch scheduled job');
      return null;
    }
  };

  const getScheduledJobExecutions = async (id: number, limit: number = 50): Promise<ScheduledJobExecutionResponse[]> => {
    try {
      const response = await scheduledJobsApi.getExecutions(id, limit);
      return response.executions;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch scheduled job executions');
      return [];
    }
  };

  // Auto-fetch on mount
  useEffect(() => {
    fetchScheduledJobs();
  }, []);

  return {
    scheduledJobs,
    loading,
    error,
    fetchScheduledJobs,
    createScheduledJob,
    updateScheduledJob,
    updateScheduledJobStatus,
    deleteScheduledJob,
    getScheduledJob,
    getScheduledJobExecutions,
    clearError: () => setError(null)
  };
};

