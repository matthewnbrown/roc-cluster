import React from 'react';
import { ScheduledJobResponse } from '../types/api';

interface ScheduledJobCardProps {
  job: ScheduledJobResponse;
  onEdit: (job: ScheduledJobResponse) => void;
  onDelete: (id: number) => void;
  onStatusChange: (id: number, status: string) => void;
}

export const ScheduledJobCard: React.FC<ScheduledJobCardProps> = ({
  job,
  onEdit,
  onDelete,
  onStatusChange
}) => {
  const formatDateTime = (dateString?: string) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleString();
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-800';
      case 'paused': return 'bg-yellow-100 text-yellow-800';
      case 'completed': return 'bg-blue-100 text-blue-800';
      case 'cancelled': return 'bg-gray-100 text-gray-800';
      case 'failed': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getScheduleTypeDisplay = (type: string) => {
    switch (type) {
      case 'once': return 'One-time';
      case 'cron': return 'Cron Schedule';
      case 'daily': return 'Daily Schedule';
      default: return type;
    }
  };

  const getScheduleDescription = () => {
    const config = job.schedule_config;
    switch (job.schedule_type) {
      case 'once':
        return `Runs once at ${formatDateTime(config.execution_time)}`;
      case 'cron':
        return `Cron: ${config.cron_expression}`;
      case 'daily':
        const ranges = config.ranges || [];
        return `Daily: ${ranges.length} time range(s)`;
      default:
        return 'Unknown schedule type';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200 hover:shadow-lg transition-shadow">
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900 mb-1">{job.name}</h3>
          {job.description && (
            <p className="text-sm text-gray-600 mb-2">{job.description}</p>
          )}
        </div>
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(job.status)}`}>
          {job.status}
        </span>
      </div>

      {/* Schedule Info */}
      <div className="mb-4">
        <div className="text-sm text-gray-600 mb-1">
          <span className="font-medium">Type:</span> {getScheduleTypeDisplay(job.schedule_type)}
        </div>
        <div className="text-sm text-gray-600 mb-1">
          <span className="font-medium">Schedule:</span> {getScheduleDescription()}
        </div>
        {job.next_execution_at && (
          <div className="text-sm text-gray-600">
            <span className="font-medium">Next Run:</span> {formatDateTime(job.next_execution_at)}
          </div>
        )}
      </div>

      {/* Execution Stats */}
      <div className="mb-4 p-3 bg-gray-50 rounded-lg">
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div>
            <span className="font-medium text-gray-700">Executions:</span>
            <span className="ml-1 text-gray-600">{job.execution_count}</span>
          </div>
          <div>
            <span className="font-medium text-gray-700">Failures:</span>
            <span className="ml-1 text-gray-600">{job.failure_count}</span>
          </div>
          {job.last_executed_at && (
            <div className="col-span-2">
              <span className="font-medium text-gray-700">Last Run:</span>
              <span className="ml-1 text-gray-600">{formatDateTime(job.last_executed_at)}</span>
            </div>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        {job.status === 'completed' ? (
          <button
            onClick={() => onEdit(job)}
            className="flex-1 bg-green-600 hover:bg-green-700 text-white px-3 py-2 rounded text-sm font-medium"
            title="Create a new scheduled job based on this completed job"
          >
            Recreate
          </button>
        ) : job.status === 'cancelled' || job.status === 'failed' ? (
          <button
            onClick={() => onEdit(job)}
            className="flex-1 bg-orange-600 hover:bg-orange-700 text-white px-3 py-2 rounded text-sm font-medium"
            title="Create a new scheduled job based on this job"
          >
            Clone
          </button>
        ) : (
          <button
            onClick={() => onEdit(job)}
            className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-3 py-2 rounded text-sm font-medium"
          >
            Edit
          </button>
        )}
        
        {job.status === 'active' ? (
          <button
            onClick={() => onStatusChange(job.id, 'paused')}
            className="flex-1 bg-yellow-600 hover:bg-yellow-700 text-white px-3 py-2 rounded text-sm font-medium"
          >
            Pause
          </button>
        ) : job.status === 'paused' ? (
          <button
            onClick={() => onStatusChange(job.id, 'active')}
            className="flex-1 bg-green-600 hover:bg-green-700 text-white px-3 py-2 rounded text-sm font-medium"
          >
            Resume
          </button>
        ) : null}
        
        <button
          onClick={() => onDelete(job.id)}
          className="bg-red-600 hover:bg-red-700 text-white px-3 py-2 rounded text-sm font-medium"
        >
          Delete
        </button>
      </div>
    </div>
  );
};
