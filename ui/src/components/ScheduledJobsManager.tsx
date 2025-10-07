import React, { useState } from 'react';
import { useScheduledJobs } from '../hooks/useScheduledJobs';
import { ScheduledJobResponse } from '../types/api';
import { ScheduledJobForm } from './ScheduledJobForm';
import { ScheduledJobCard } from './ScheduledJobCard';

export const ScheduledJobsManager: React.FC = () => {
  const {
    scheduledJobs,
    loading,
    error,
    fetchScheduledJobs,
    deleteScheduledJob,
    updateScheduledJobStatus,
    clearError
  } = useScheduledJobs();

  const [showForm, setShowForm] = useState(false);
  const [editingJob, setEditingJob] = useState<ScheduledJobResponse | null>(null);
  const [filterStatuses, setFilterStatuses] = useState<string[]>([]);

  const handleCreateJob = () => {
    setEditingJob(null);
    setShowForm(true);
  };

  const handleEditJob = (job: ScheduledJobResponse) => {
    // For completed, cancelled, or failed jobs, we're recreating/cloning
    // For active or paused jobs, we're actually editing
    if (job.status === 'completed' || job.status === 'cancelled' || job.status === 'failed') {
      // Create a new job based on the existing one (clone/recreate)
      setEditingJob({
        ...job,
        id: 0, // Reset ID to indicate this is a new job
        name: `${job.name} (Copy)`, // Add suffix to indicate it's a copy
        status: 'active', // Start as active
        execution_count: 0, // Reset counters
        failure_count: 0,
        last_executed_at: undefined,
        next_execution_at: undefined,
        created_at: new Date().toISOString(),
        updated_at: undefined
      });
    } else {
      // Regular edit for active/paused jobs
      setEditingJob(job);
    }
    setShowForm(true);
  };

  const handleCloseForm = () => {
    setShowForm(false);
    setEditingJob(null);
  };

  const handleDeleteJob = async (id: number) => {
    if (window.confirm('Are you sure you want to delete this scheduled job?')) {
      await deleteScheduledJob(id);
    }
  };

  const handleStatusChange = async (id: number, newStatus: string) => {
    await updateScheduledJobStatus(id, newStatus);
  };

  const filteredJobs = filterStatuses.length > 0 
    ? scheduledJobs.filter(job => filterStatuses.includes(job.status))
    : scheduledJobs;

  // Sort jobs with active ones first, then by creation date (newest first)
  const sortedJobs = [...filteredJobs].sort((a, b) => {
    // Priority order for status
    const statusPriority: Record<string, number> = {
      'active': 0,
      'paused': 1,
      'completed': 2,
      'cancelled': 3,
      'failed': 4
    };
    
    const aPriority = statusPriority[a.status] ?? 5;
    const bPriority = statusPriority[b.status] ?? 5;
    
    // First sort by status priority
    if (aPriority !== bPriority) {
      return aPriority - bPriority;
    }
    
    // Then sort by creation date (newest first)
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });

  if (showForm) {
    return (
      <ScheduledJobForm
        editingJob={editingJob}
        onClose={handleCloseForm}
        onSuccess={() => {
          handleCloseForm();
          fetchScheduledJobs();
        }}
      />
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Scheduled Jobs</h1>
        <button
          onClick={handleCreateJob}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium"
        >
          Create Scheduled Job
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
          {error}
          <button
            onClick={clearError}
            className="ml-2 text-red-500 hover:text-red-700"
          >
            ×
          </button>
        </div>
      )}

      {/* Filter Controls */}
      <div className="mb-6 bg-gray-50 p-4 rounded-lg">
        <div className="space-y-4">
          {/* Header with counts and refresh */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <label className="text-sm font-medium text-gray-700">Filter by Status:</label>
            <div className="flex items-center justify-between sm:justify-end gap-2">
              <span className="text-sm text-gray-600">
                Showing {filteredJobs.length} of {scheduledJobs.length} jobs
                {filterStatuses.length > 0 && (
                  <span className="ml-2 text-xs text-gray-500">
                    ({filterStatuses.join(', ')})
                  </span>
                )}
              </span>
              <button
                onClick={() => fetchScheduledJobs()}
                className="bg-gray-600 hover:bg-gray-700 text-white px-3 py-2 rounded-lg text-sm whitespace-nowrap"
              >
                Refresh
              </button>
            </div>
          </div>

          {/* Filter options - responsive grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
            {[
              { value: 'active', label: 'Active', color: 'green' },
              { value: 'paused', label: 'Paused', color: 'yellow' },
              { value: 'completed', label: 'Completed', color: 'blue' },
              { value: 'cancelled', label: 'Cancelled', color: 'gray' },
              { value: 'failed', label: 'Failed', color: 'red' }
            ].map(({ value, label, color }) => {
              const count = scheduledJobs.filter(job => job.status === value).length;
              const isSelected = filterStatuses.includes(value);
              
              return (
                <label
                  key={value}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg border-2 cursor-pointer transition-colors text-sm ${
                    isSelected 
                      ? `border-${color}-500 bg-${color}-50 text-${color}-700` 
                      : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setFilterStatuses(prev => [...prev, value]);
                      } else {
                        setFilterStatuses(prev => prev.filter(s => s !== value));
                      }
                    }}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="font-medium truncate">
                    {label} ({count})
                  </span>
                </label>
              );
            })}
          </div>

          {/* Clear all button */}
          {filterStatuses.length > 0 && (
            <div className="flex justify-center">
              <button
                onClick={() => setFilterStatuses([])}
                className="text-sm text-gray-500 hover:text-gray-700 underline"
              >
                Clear all filters
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Jobs List */}
      {loading ? (
        <div className="flex justify-center items-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      ) : sortedJobs.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <p className="text-lg">
            {filterStatuses.length > 0 
              ? `No scheduled jobs found with status: ${filterStatuses.join(', ')}` 
              : 'No scheduled jobs found'
            }
          </p>
          <p className="text-sm mt-2">
            {filterStatuses.length > 0 ? (
              <>
                Try changing the filter to see other jobs or{' '}
                <button
                  onClick={() => setFilterStatuses([])}
                  className="text-blue-600 hover:text-blue-800 underline"
                >
                  view all jobs
                </button>
              </>
            ) : (
              'Create your first scheduled job to get started.'
            )}
          </p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {sortedJobs.map((job) => (
            <ScheduledJobCard
              key={job.id}
              job={job}
              onEdit={handleEditJob}
              onDelete={handleDeleteJob}
              onStatusChange={handleStatusChange}
            />
          ))}
        </div>
      )}
    </div>
  );
};
