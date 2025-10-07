import { useState, useEffect, useRef } from 'react';
import { favoriteJobsApi } from '../services/api';
import { FavoriteJobResponse, FavoriteJobCreateRequest } from '../types/api';
import { getCurrentTimestamp } from '../utils/dateUtils';

export const useFavoriteJobs = () => {
  const [favoriteJobs, setFavoriteJobs] = useState<FavoriteJobResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const hasFetched = useRef(false);

  const fetchFavoriteJobs = async (force = false) => {
    // Prevent multiple simultaneous requests
    if (loading && !force) return;
    
    setLoading(true);
    setError(null);
    try {
      const response = await favoriteJobsApi.list();
      setFavoriteJobs(response.favorite_jobs);
      hasFetched.current = true;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch favorite jobs');
    } finally {
      setLoading(false);
    }
  };

  const createFavoriteJob = async (data: FavoriteJobCreateRequest): Promise<FavoriteJobResponse | null> => {
    try {
      const newFavorite = await favoriteJobsApi.create(data);
      setFavoriteJobs(prev => [newFavorite, ...prev]);
      return newFavorite;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create favorite job');
      return null;
    }
  };

  const updateFavoriteJob = async (id: number, data: FavoriteJobCreateRequest): Promise<FavoriteJobResponse | null> => {
    try {
      const updatedFavorite = await favoriteJobsApi.update(id, data);
      setFavoriteJobs(prev => 
        prev.map(fav => fav.id === id ? updatedFavorite : fav)
      );
      return updatedFavorite;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update favorite job');
      return null;
    }
  };

  const deleteFavoriteJob = async (id: number): Promise<boolean> => {
    try {
      await favoriteJobsApi.delete(id);
      setFavoriteJobs(prev => prev.filter(fav => fav.id !== id));
      return true;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete favorite job');
      return false;
    }
  };

  const markFavoriteJobAsUsed = async (id: number): Promise<boolean> => {
    try {
      await favoriteJobsApi.markAsUsed(id);
      // Update the usage count and last used time in the local state
      setFavoriteJobs(prev => 
        prev.map(fav => 
          fav.id === id 
            ? { 
                ...fav, 
                usage_count: fav.usage_count + 1, 
                last_used_at: getCurrentTimestamp() 
              }
            : fav
        )
      );
      return true;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to mark favorite job as used');
      return false;
    }
  };

  useEffect(() => {
    if (!hasFetched.current) {
      fetchFavoriteJobs();
    }
  }, []);

  return {
    favoriteJobs,
    loading,
    error,
    fetchFavoriteJobs,
    createFavoriteJob,
    updateFavoriteJob,
    deleteFavoriteJob,
    markFavoriteJobAsUsed,
  };
};
