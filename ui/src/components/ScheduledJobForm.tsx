import React, { useState, useEffect } from 'react';
import { ScheduledJobResponse, ScheduledJobCreateRequest, DailyScheduleRange } from '../types/api';
import { useFavoriteJobs } from '../hooks/useFavoriteJobs';
import { useScheduledJobs } from '../hooks/useScheduledJobs';
import JobForm from './JobForm';

interface ScheduledJobFormProps {
  editingJob?: ScheduledJobResponse | null;
  onClose: () => void;
  onSuccess: () => void;
}

export const ScheduledJobForm: React.FC<ScheduledJobFormProps> = ({
  editingJob,
  onClose,
  onSuccess
}) => {
  const { favoriteJobs, fetchFavoriteJobs } = useFavoriteJobs();
  const { createScheduledJob, updateScheduledJob } = useScheduledJobs();

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    schedule_type: 'once' as 'once' | 'cron' | 'daily',
    job_source: 'favorite' as 'favorite' | 'new',
    favorite_job_id: '',
    job_config: null as any, // Will be set when job is created
    once_config: {
      execution_time: ''
    },
    cron_config: {
      cron_expression: ''
    },
    daily_config: {
      ranges: [] as DailyScheduleRange[],
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone // Default to user's timezone
    }
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showJobForm, setShowJobForm] = useState(false);
  const [timeValidationError, setTimeValidationError] = useState<string | null>(null);

  // Function to validate scheduled time
  const validateScheduledTime = (executionTime: string | null): string | null => {
    if (!executionTime) return null;
    
    const scheduledDate = new Date(executionTime);
    const now = new Date();
    
    // Add a small buffer (30 seconds) to account for form submission time
    const buffer = new Date(now.getTime() + 30 * 1000);
    
    if (scheduledDate < buffer) {
      return 'Scheduled time cannot be in the past. Please select a future date and time.';
    }
    
    return null;
  };

  useEffect(() => {
    if (editingJob) {
      setFormData({
        name: editingJob.name,
        description: editingJob.description || '',
        schedule_type: editingJob.schedule_type as 'once' | 'cron' | 'daily',
        job_source: 'new', // When editing, we'll show the job config
        favorite_job_id: '',
        job_config: editingJob.job_config,
        once_config: {
          execution_time: editingJob.schedule_config?.execution_time || ''
        },
        cron_config: {
          cron_expression: editingJob.schedule_config?.cron_expression || ''
        },
        daily_config: {
          ranges: editingJob.schedule_config?.ranges || [],
          timezone: editingJob.schedule_config?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone
        }
      });
    }
  }, [editingJob]);

  // Validate time whenever execution_time changes
  useEffect(() => {
    if (formData.schedule_type === 'once' && formData.once_config.execution_time) {
      const validationError = validateScheduledTime(formData.once_config.execution_time);
      setTimeValidationError(validationError);
    } else {
      setTimeValidationError(null);
    }
  }, [formData.once_config.execution_time, formData.schedule_type]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      // Validate scheduled time before submission
      if (formData.schedule_type === 'once' && formData.once_config.execution_time) {
        const timeError = validateScheduledTime(formData.once_config.execution_time);
        if (timeError) {
          setError(timeError);
          setLoading(false);
          return;
        }
      }
      let jobConfig;

      if (formData.job_source === 'favorite') {
        const selectedFavorite = favoriteJobs.find(f => f.id.toString() === formData.favorite_job_id);
        if (!selectedFavorite) {
          throw new Error('Please select a favorite job');
        }
        jobConfig = selectedFavorite.job_config;
      } else {
        // Use the job configuration from JobForm
        if (!formData.job_config) {
          throw new Error('Please create a job configuration first');
        }
        jobConfig = formData.job_config;
      }

      const requestData: ScheduledJobCreateRequest = {
        name: formData.name,
        description: formData.description || undefined,
        job_config: jobConfig,
        schedule_type: formData.schedule_type,
        once_config: formData.schedule_type === 'once' ? formData.once_config : undefined,
        cron_config: formData.schedule_type === 'cron' ? formData.cron_config : undefined,
        daily_config: formData.schedule_type === 'daily' ? formData.daily_config : undefined
      };

      let result;
      if (editingJob && editingJob.id > 0) {
        // Update existing job
        result = await updateScheduledJob(editingJob.id, requestData);
      } else {
        // Create new job
        result = await createScheduledJob(requestData);
      }
      
      if (result) {
        onSuccess();
      }
    } catch (err: any) {
      setError(err.message || 'Failed to create scheduled job');
    } finally {
      setLoading(false);
    }
  };

  const addDailyRange = () => {
    setFormData(prev => ({
      ...prev,
      daily_config: {
        ...prev.daily_config,
        ranges: [
          ...prev.daily_config.ranges,
          { start_time: '09:00', end_time: '17:00', interval_minutes: 60, random_noise_minutes: 0 }
        ]
      }
    }));
  };

  const removeDailyRange = (index: number) => {
    setFormData(prev => ({
      ...prev,
      daily_config: {
        ...prev.daily_config,
        ranges: prev.daily_config.ranges.filter((_, i) => i !== index)
      }
    }));
  };

  const updateDailyRange = (index: number, field: keyof DailyScheduleRange, value: string | number) => {
    setFormData(prev => ({
      ...prev,
      daily_config: {
        ...prev.daily_config,
        ranges: prev.daily_config.ranges.map((range, i) => 
          i === index ? { ...range, [field]: value } : range
        )
      }
    }));
  };

  const handleJobCreated = (jobConfig: any) => {
    setFormData(prev => ({
      ...prev,
      job_config: jobConfig
    }));
    setShowJobForm(false);
  };

  // If we're showing the JobForm, render it instead
  if (showJobForm) {
    return (
      <JobForm
        onClose={() => setShowJobForm(false)}
        onSuccess={(jobConfig) => handleJobCreated(jobConfig)}
        isScheduledJobMode={true}
        jobToClone={formData.job_config ? {
          id: 0,
          name: 'Scheduled Job Configuration',
          description: '',
          status: 'pending' as any,
          parallel_execution: formData.job_config.parallel_execution || false,
          created_at: new Date().toISOString(),
          started_at: undefined,
          completed_at: undefined,
          total_steps: formData.job_config.steps?.length || 0,
          completed_steps: 0,
          failed_steps: 0,
          error_message: undefined,
          steps: formData.job_config.steps || []
        } : null}
      />
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-gray-900">
              {editingJob ? (
                editingJob.id === 0 ? 'Recreate Scheduled Job' : 'Edit Scheduled Job'
              ) : 'Create Scheduled Job'}
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-2xl"
            >
              ×
            </button>
          </div>

          {error && (
            <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Basic Info */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Name *
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Description
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={3}
              />
            </div>

            {/* Job Source Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Job Configuration *
              </label>
              <div className="space-y-3">
                <div className="flex space-x-4">
                  <label className="flex items-center">
                    <input
                      type="radio"
                      name="job_source"
                      value="favorite"
                      checked={formData.job_source === 'favorite'}
                      onChange={(e) => setFormData(prev => ({ ...prev, job_source: e.target.value as 'favorite' | 'new' }))}
                      className="mr-2"
                    />
                    Use Favorite Job
                  </label>
                  <label className="flex items-center">
                    <input
                      type="radio"
                      name="job_source"
                      value="new"
                      checked={formData.job_source === 'new'}
                      onChange={(e) => setFormData(prev => ({ ...prev, job_source: e.target.value as 'favorite' | 'new' }))}
                      className="mr-2"
                    />
                    Create New Job
                  </label>
                </div>

                {formData.job_source === 'favorite' && (
                  <select
                    value={formData.favorite_job_id}
                    onChange={(e) => setFormData(prev => ({ ...prev, favorite_job_id: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    required={formData.job_source === 'favorite'}
                  >
                    <option value="">Select a favorite job</option>
                    {favoriteJobs.map(fav => (
                      <option key={fav.id} value={fav.id}>
                        {fav.name} {fav.description && `- ${fav.description}`}
                      </option>
                    ))}
                  </select>
                )}

                {formData.job_source === 'new' && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-700">Job Configuration</span>
                      <button
                        type="button"
                        onClick={() => setShowJobForm(true)}
                        className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm font-medium"
                      >
                        {formData.job_config ? 'Edit Job Configuration' : 'Create Job Configuration'}
                      </button>
                    </div>
                    
                    {formData.job_config ? (
                      <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-sm font-medium text-gray-700">Job Configuration Created</p>
                            <p className="text-xs text-gray-500">
                              {formData.job_config.steps?.length || 0} steps configured
                            </p>
                          </div>
                          <button
                            type="button"
                            onClick={() => setFormData(prev => ({ ...prev, job_config: null }))}
                            className="text-red-600 hover:text-red-800 text-sm"
                          >
                            Clear
                          </button>
                        </div>
                      </div>
                    ) : (
                      <p className="text-sm text-gray-500 italic">
                        No job configuration created yet. Click "Create Job Configuration" to build your job.
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Schedule Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Schedule Type *
              </label>
              <select
                value={formData.schedule_type}
                onChange={(e) => setFormData(prev => ({ 
                  ...prev, 
                  schedule_type: e.target.value as 'once' | 'cron' | 'daily' 
                }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              >
                <option value="once">Run Once at Specific Time</option>
                <option value="cron">Cron Schedule</option>
                <option value="daily">Daily Schedule with Time Ranges</option>
              </select>
            </div>

            {/* Schedule Configuration */}
            {formData.schedule_type === 'once' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Execution Date & Time *
                </label>
                
                <div className="space-y-4">
                  {/* Date and Time Inputs */}
                  <div className="grid grid-cols-2 gap-4">
                    {/* Date Input */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Date</label>
                      <input
                        type="date"
                        value={formData.once_config.execution_time ? 
                          (() => {
                            const date = new Date(formData.once_config.execution_time);
                            const year = date.getFullYear();
                            const month = String(date.getMonth() + 1).padStart(2, '0');
                            const day = String(date.getDate()).padStart(2, '0');
                            return `${year}-${month}-${day}`;
                          })() : 
                          ''
                        }
                        onChange={(e) => {
                          const selectedDate = e.target.value;
                          if (selectedDate) {
                            const existingTime = formData.once_config.execution_time ? 
                              new Date(formData.once_config.execution_time) : 
                              new Date();
                            const [year, month, day] = selectedDate.split('-');
                            existingTime.setFullYear(parseInt(year), parseInt(month) - 1, parseInt(day));
                            setFormData(prev => ({
                              ...prev,
                              once_config: { ...prev.once_config, execution_time: existingTime.toISOString() }
                            }));
                          }
                        }}
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        required
                        min={(() => {
                          const today = new Date();
                          const year = today.getFullYear();
                          const month = String(today.getMonth() + 1).padStart(2, '0');
                          const day = String(today.getDate()).padStart(2, '0');
                          return `${year}-${month}-${day}`;
                        })()}
                      />
                    </div>

                    {/* Time Input */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">Time</label>
                      <input
                        type="time"
                        value={formData.once_config.execution_time ? 
                          new Date(formData.once_config.execution_time).toTimeString().slice(0, 5) : 
                          ''
                        }
                        onChange={(e) => {
                          const selectedTime = e.target.value;
                          if (selectedTime) {
                            const [hours, minutes] = selectedTime.split(':');
                            const existingDate = formData.once_config.execution_time ? 
                              new Date(formData.once_config.execution_time) : 
                              new Date();
                            existingDate.setHours(parseInt(hours), parseInt(minutes), 0, 0);
                            setFormData(prev => ({
                              ...prev,
                              once_config: { ...prev.once_config, execution_time: existingDate.toISOString() }
                            }));
                          }
                        }}
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        required
                      />
                    </div>
                  </div>

                  {/* Quick Time Presets */}
                  <div>
                    <label className="block text-xs text-gray-600 mb-2">Quick Time Presets</label>
                    <div className="flex flex-wrap gap-2">
                      {[
                        { label: 'Now', hours: new Date().getHours(), minutes: new Date().getMinutes() },
                        { label: '9:00 AM', hours: 9, minutes: 0 },
                        { label: '12:00 PM', hours: 12, minutes: 0 },
                        { label: '3:00 PM', hours: 15, minutes: 0 },
                        { label: '6:00 PM', hours: 18, minutes: 0 },
                        { label: '9:00 PM', hours: 21, minutes: 0 },
                        { label: 'Midnight', hours: 0, minutes: 0 },
                      ].map((preset) => (
                        <button
                          key={preset.label}
                          type="button"
                          onClick={() => {
                            const today = new Date();
                            today.setHours(preset.hours, preset.minutes, 0, 0);
                            setFormData(prev => ({
                              ...prev,
                              once_config: { ...prev.once_config, execution_time: today.toISOString() }
                            }));
                          }}
                          className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 rounded border transition-colors"
                        >
                          {preset.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Current Selection Display */}
                  {formData.once_config.execution_time && (
                    <div className={`p-2 border rounded-lg ${
                      timeValidationError 
                        ? 'bg-red-50 border-red-200' 
                        : 'bg-blue-50 border-blue-200'
                    }`}>
                      <p className={`text-sm ${
                        timeValidationError ? 'text-red-800' : 'text-blue-800'
                      }`}>
                        <strong>Scheduled for:</strong> {new Date(formData.once_config.execution_time).toLocaleString()}
                      </p>
                      <p className={`text-xs mt-1 ${
                        timeValidationError ? 'text-red-600' : 'text-blue-600'
                      }`}>
                        {timeValidationError || 'Time will be interpreted in your local timezone'}
                      </p>
                    </div>
                  )}

                  {/* Time Validation Error */}
                  {timeValidationError && (
                    <div className="p-3 bg-red-100 border border-red-400 text-red-700 rounded-lg">
                      <div className="flex items-center">
                        <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                        </svg>
                        <span className="font-medium">Invalid Scheduled Time</span>
                      </div>
                      <p className="mt-1 text-sm">{timeValidationError}</p>
                    </div>
                  )}

                  <p className="text-xs text-gray-500">
                    Use the calendar and time picker above, or click a quick preset button
                  </p>
                </div>
              </div>
            )}

            {formData.schedule_type === 'cron' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Cron Expression *
                </label>
                <input
                  type="text"
                  value={formData.cron_config.cron_expression}
                  onChange={(e) => setFormData(prev => ({
                    ...prev,
                    cron_config: { ...prev.cron_config, cron_expression: e.target.value }
                  }))}
                  placeholder="0 0 * * *"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
                <p className="text-sm text-gray-500 mt-1">
                  Format: minute hour day month day-of-week (e.g., "0 0 * * *" for daily at midnight)
                </p>
              </div>
            )}

            {formData.schedule_type === 'daily' && (
              <div>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Timezone
                  </label>
                  <select
                    value={formData.daily_config.timezone}
                    onChange={(e) => setFormData(prev => ({
                      ...prev,
                      daily_config: { ...prev.daily_config, timezone: e.target.value }
                    }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="America/New_York">Eastern Time (ET)</option>
                    <option value="America/Chicago">Central Time (CT)</option>
                    <option value="America/Denver">Mountain Time (MT)</option>
                    <option value="America/Los_Angeles">Pacific Time (PT)</option>
                    <option value="Europe/London">London (GMT/BST)</option>
                    <option value="Europe/Paris">Paris (CET/CEST)</option>
                    <option value="Asia/Tokyo">Tokyo (JST)</option>
                    <option value="UTC">UTC</option>
                  </select>
                  <p className="text-xs text-gray-500 mt-1">
                    All times below will be interpreted in this timezone
                  </p>
                </div>
                
                <div className="flex justify-between items-center mb-2">
                  <label className="block text-sm font-medium text-gray-700">
                    Daily Time Ranges *
                  </label>
                  <button
                    type="button"
                    onClick={addDailyRange}
                    className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm"
                  >
                    Add Range
                  </button>
                </div>
                
                <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <h4 className="text-sm font-medium text-blue-900 mb-1">Random Intervals</h4>
                  <p className="text-xs text-blue-700">
                    Use the "Random Noise" field to add variation to your intervals. For example, with a 10-minute base interval and 2-minute noise, 
                    executions will occur between 8-12 minutes apart (using Gaussian distribution). This helps avoid predictable patterns.
                  </p>
                </div>
                
                {formData.daily_config.ranges.map((range, index) => (
                  <div key={index} className="border border-gray-200 rounded-lg p-4 mb-3">
                    <div className="flex justify-between items-center mb-3">
                      <span className="text-sm font-medium text-gray-700">Range {index + 1}</span>
                      <button
                        type="button"
                        onClick={() => removeDailyRange(index)}
                        className="text-red-600 hover:text-red-800 text-sm"
                      >
                        Remove
                      </button>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs text-gray-600 mb-1">Start Time</label>
                        <input
                          type="time"
                          value={range.start_time}
                          onChange={(e) => updateDailyRange(index, 'start_time', e.target.value)}
                          className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-600 mb-1">End Time</label>
                        <input
                          type="time"
                          value={range.end_time}
                          onChange={(e) => updateDailyRange(index, 'end_time', e.target.value)}
                          className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
                          required
                        />
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-3 mt-3">
                      <div>
                        <label className="block text-xs text-gray-600 mb-1">Base Interval (minutes)</label>
                        <input
                          type="number"
                          value={range.interval_minutes}
                          onChange={(e) => updateDailyRange(index, 'interval_minutes', parseInt(e.target.value))}
                          min="1"
                          className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
                          required
                        />
                        <p className="text-xs text-gray-500 mt-1">Average time between executions</p>
                      </div>
                      <div>
                        <label className="block text-xs text-gray-600 mb-1">Random Noise (minutes)</label>
                        <input
                          type="number"
                          value={range.random_noise_minutes || 0}
                          onChange={(e) => updateDailyRange(index, 'random_noise_minutes', parseInt(e.target.value) || 0)}
                          min="0"
                          className="w-full border border-gray-300 rounded px-2 py-1 text-sm"
                        />
                        <p className="text-xs text-gray-500 mt-1">Random variation using Gaussian distribution</p>
                      </div>
                    </div>
                  </div>
                ))}
                
                {formData.daily_config.ranges.length === 0 && (
                  <p className="text-sm text-gray-500 italic">
                    No time ranges defined. Click "Add Range" to create one.
                  </p>
                )}
              </div>
            )}

            {/* Form Actions */}
            <div className="flex gap-3 pt-4">
              <button
                type="submit"
                disabled={loading || !!timeValidationError}
                className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white px-4 py-2 rounded-lg font-medium"
              >
                {loading ? (
                  editingJob?.id === 0 ? 'Recreating...' : 
                  editingJob ? 'Updating...' : 'Creating...'
                ) : (
                  editingJob?.id === 0 ? 'Recreate' : 
                  editingJob ? 'Update' : 'Create'
                )}
              </button>
              <button
                type="button"
                onClick={onClose}
                className="flex-1 bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-lg font-medium"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
