import React, { useState } from 'react';
import { useJob, useCancelJob } from '../hooks/useJobs';
import { JobResponse, JobStatus } from '../types/api';
import Button from './ui/Button';
import { Table, TableHeader, TableBody, TableRow, TableCell } from './ui/Table';
import { ArrowLeft, Clock, CheckCircle, XCircle, AlertCircle, Pause, X, Eye, ChevronDown, ChevronRight } from 'lucide-react';

interface JobDetailsProps {
  jobId: number;
  onBack: () => void;
}

const JobDetails: React.FC<JobDetailsProps> = ({ jobId, onBack }) => {
  const [showSteps, setShowSteps] = useState(true);
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set());
  const { data: job, isLoading, error } = useJob(jobId, true);
  const cancelJobMutation = useCancelJob();

  const handleCancelJob = async () => {
    if (window.confirm(`Are you sure you want to cancel job "${job?.name}"?`)) {
      try {
        await cancelJobMutation.mutateAsync({ id: jobId });
      } catch (error) {
        console.error('Failed to cancel job:', error);
      }
    }
  };

  const toggleStepExpansion = (stepIndex: number) => {
    const newExpanded = new Set(expandedSteps);
    if (newExpanded.has(stepIndex)) {
      newExpanded.delete(stepIndex);
    } else {
      newExpanded.add(stepIndex);
    }
    setExpandedSteps(newExpanded);
  };

  const getStatusIcon = (status: JobStatus) => {
    switch (status) {
      case 'pending':
        return <Clock className="h-5 w-5 text-yellow-500" />;
      case 'running':
        return <AlertCircle className="h-5 w-5 text-blue-500" />;
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />;
      case 'cancelled':
        return <Pause className="h-5 w-5 text-gray-500" />;
      default:
        return <Clock className="h-5 w-5 text-gray-500" />;
    }
  };

  const getStatusColor = (status: JobStatus) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'running':
        return 'bg-blue-100 text-blue-800';
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'cancelled':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStepStatusIcon = (status: JobStatus) => {
    switch (status) {
      case 'pending':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      case 'running':
        return <AlertCircle className="h-4 w-4 text-blue-500" />;
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'cancelled':
        return <Pause className="h-4 w-4 text-gray-500" />;
      default:
        return <Clock className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStepStatusColor = (status: JobStatus) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'running':
        return 'bg-blue-100 text-blue-800';
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'cancelled':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const getProgressPercentage = () => {
    if (!job || job.total_steps === 0) return 0;
    // Include both completed and failed steps as "finished" steps
    const finishedSteps = job.completed_steps + job.failed_steps;
    return Math.round((finishedSteps / job.total_steps) * 100);
  };

  const getDuration = () => {
    if (!job) return null;
    
    if (job.started_at && job.completed_at) {
      // Backend now sends dates with 'Z' suffix, so direct parsing should work
      const startTime = new Date(job.started_at).getTime();
      const endTime = new Date(job.completed_at).getTime();
      
      if (isNaN(startTime) || isNaN(endTime)) return null;
      
      const duration = endTime - startTime;
      return `${Math.round(duration / 1000)}s`;
    } else if (job.started_at) {
      // Backend now sends dates with 'Z' suffix, so direct parsing should work
      const startTime = new Date(job.started_at).getTime();
      const currentTime = new Date().getTime();
      
      if (isNaN(startTime)) {
        console.warn('Invalid start time:', job.started_at);
        return 'Invalid start time';
      }
      
      const duration = currentTime - startTime;
      if (duration < 0) {
        console.warn('Negative duration detected:', duration);
        return '0s (running)'; // Handle negative duration
      }
      
      return `${Math.round(duration / 1000)}s (running)`;
    }
    return null;
  };

  const renderActionSummary = (summary: any) => {
    const actionType = summary.action_type || 'unknown';
    
    // Common summary items
    const commonItems = [
      { key: 'successes', label: 'Completed', value: summary.successes, color: 'text-green-600' },
      { key: 'failed', label: 'Failed', value: summary.failed, color: 'text-red-600' },
      { key: 'total_retries', label: 'Total Retries', value: summary.total_retries, color: 'text-orange-600' }
    ];

    // Action-specific summary items
    const actionSpecificItems = [];
    
    switch (actionType) {
      case 'attack':
        actionSpecificItems.push(
          { key: 'battle_wins', label: 'Battles Won', value: summary.battle_wins, color: 'text-green-600' },
          { key: 'battle_losses', label: 'Battles Lost', value: summary.battle_losses, color: 'text-red-600' },
          { key: 'protection_buffs', label: 'Protection Buffs', value: summary.protection_buffs, color: 'text-blue-600' },
          { key: 'maxed_hits', label: 'Maxed Hits', value: summary.maxed_hits, color: 'text-purple-600' },
          { key: 'runs_away', label: 'Runs Away', value: summary.runs_away, color: 'text-orange-600' },
          { key: 'gold_won', label: 'Gold Won', value: summary.gold_won?.toLocaleString(), color: 'text-yellow-600' },
          { key: 'troops_killed', label: 'Troops Killed', value: summary.troops_killed, color: 'text-red-600' },
          { key: 'troops_lost', label: 'Troops Lost', value: summary.troops_lost, color: 'text-red-600' },
          { key: 'soldiers_killed', label: 'Soldiers Killed', value: summary.soldiers_killed, color: 'text-red-600' },
          { key: 'soldiers_lost', label: 'Soldiers Lost', value: summary.soldiers_lost, color: 'text-red-600' }
        );
        break;
        
      case 'sabotage':
        actionSpecificItems.push(
          { key: 'sabotages_defended', label: 'Defended', value: summary.sabotages_defended, color: 'text-yellow-600' },
          { key: 'maxed_sab_attempts', label: 'Max Attempts', value: summary.maxed_sab_attempts, color: 'text-purple-600' },
          { key: 'sabotages_failed', label: 'Failed', value: summary.sabotages_failed, color: 'text-red-600' },
          { key: 'weapons_destroyed', label: 'Weapons Destroyed', value: summary.weapons_destroyed, color: 'text-red-600' },
          { key: 'total_damage_dealt', label: 'Damage Dealt', value: summary.total_damage_dealt?.toLocaleString(), color: 'text-orange-600' },
          { key: 'weapon_damage_cost', label: 'Weapon Cost', value: summary.weapon_damage_cost?.toLocaleString(), color: 'text-blue-600' }
        );
        break;
        
      case 'spy':
        actionSpecificItems.push(
          { key: 'spies_successful', label: 'Spies Successful', value: summary.spies_successful, color: 'text-green-600' },
          { key: 'spies_successful_data', label: 'Data Collected', value: summary.spies_successful_data, color: 'text-blue-600' },
          { key: 'spies_caught', label: 'Spies Caught', value: summary.spies_caught, color: 'text-red-600' },
          { key: 'spies_failed', label: 'Spies Failed', value: summary.spies_failed, color: 'text-red-600' },
          { key: 'maxed_spy_attempts', label: 'Max Attempts Reached', value: summary.maxed_spy_attempts, color: 'text-purple-600' }
        );
        break;
        
      case 'send_credits':
        actionSpecificItems.push(
          { key: 'credits_sent', label: 'Credits Sent', value: summary.credits_sent?.toLocaleString(), color: 'text-green-600' },
          { key: 'jackpot_credits', label: 'Jackpot Credits', value: summary.jackpot_credits?.toLocaleString(), color: 'text-yellow-600' },
          { key: 'transfers_successful', label: 'Transfers Successful', value: summary.transfers_successful, color: 'text-green-600' },
          { key: 'transfers_failed', label: 'Transfers Failed', value: summary.transfers_failed, color: 'text-red-600' }
        );
        break;
        
      case 'recruit':
        actionSpecificItems.push(
          { key: 'recruitments_successful', label: 'Recruitments Successful', value: summary.recruitments_successful, color: 'text-green-600' },
          { key: 'recruitments_failed', label: 'Recruitments Failed', value: summary.recruitments_failed, color: 'text-red-600' },
          { key: 'recruit_not_needed', label: 'Recruit Not Needed', value: summary.recruit_not_needed, color: 'text-blue-600' },
          { key: 'total_cost', label: 'Total Cost', value: summary.total_cost?.toLocaleString(), color: 'text-yellow-600' }
        );
        break;
        
      case 'purchase_armory':
        actionSpecificItems.push(
          { key: 'weapons_purchased', label: 'Weapons Purchased', value: summary.weapons_purchased, color: 'text-green-600' },
          { key: 'purchases_successful', label: 'Purchases Successful', value: summary.purchases_successful, color: 'text-green-600' },
          { key: 'purchases_failed', label: 'Purchases Failed', value: summary.purchases_failed, color: 'text-red-600' },
          { key: 'total_cost', label: 'Total Cost', value: summary.total_cost?.toLocaleString(), color: 'text-yellow-600' },
          { key: 'weapons_sold', label: 'Weapons Sold', value: summary.weapons_sold, color: 'text-blue-600' },
          { key: 'total_revenue', label: 'Total Revenue', value: summary.total_revenue?.toLocaleString(), color: 'text-green-600' }
        );
        break;
        
      case 'purchase_training':
        actionSpecificItems.push(
          { key: 'purchases_successful', label: 'Purchases Successful', value: summary.purchases_successful, color: 'text-green-600' },
          { key: 'purchases_failed', label: 'Purchases Failed', value: summary.purchases_failed, color: 'text-red-600' },
          { key: 'soldiers_trained', label: 'Soldiers Trained', value: summary.soldiers_trained, color: 'text-blue-600' },
          { key: 'mercs_trained', label: 'Mercs Trained', value: summary.mercs_trained, color: 'text-purple-600' },
          { key: 'soldiers_untrained', label: 'Soldiers Untrained', value: summary.soldiers_untrained, color: 'text-orange-600' },
          { key: 'mercs_untrained', label: 'Mercs Untrained', value: summary.mercs_untrained, color: 'text-orange-600' },
          { key: 'total_cost', label: 'Total Cost', value: summary.total_cost?.toLocaleString(), color: 'text-yellow-600' }
        );
        break;
        
      case 'become_officer':
        actionSpecificItems.push(
          { key: 'officer_applications', label: 'Applications', value: summary.officer_applications, color: 'text-blue-600' },
          { key: 'applications_successful', label: 'Applications Successful', value: summary.applications_successful, color: 'text-green-600' },
          { key: 'applications_failed', label: 'Applications Failed', value: summary.applications_failed, color: 'text-red-600' }
        );
        break;
        
      case 'get_metadata':
        actionSpecificItems.push(
          { key: 'metadata_retrieved', label: 'Metadata Retrieved', value: summary.metadata_retrieved, color: 'text-green-600' },
          { key: 'retrievals_successful', label: 'Retrievals Successful', value: summary.retrievals_successful, color: 'text-green-600' },
          { key: 'retrievals_failed', label: 'Retrievals Failed', value: summary.retrievals_failed, color: 'text-red-600' },
          { key: 'accounts_updated', label: 'Accounts Updated', value: summary.accounts_updated, color: 'text-blue-600' }
        );
        break;
        
      default:
        actionSpecificItems.push(
          { key: 'operations_completed', label: 'Operations Completed', value: summary.operations_completed, color: 'text-green-600' },
          { key: 'operations_failed', label: 'Operations Failed', value: summary.operations_failed, color: 'text-red-600' }
        );
    }

    // Combine all items
    const allItems = [...commonItems, ...actionSpecificItems];
    
    // Filter out items with zero or undefined values for cleaner display
    const displayItems = allItems.filter(item => item.value !== undefined && item.value !== null && item.value !== 0);

    // Show errors if any
    const errorItems = summary.error_list && summary.error_list.length > 0 ? summary.error_list : [];

    return (
      <div className="grid grid-cols-3 gap-6 w-full">
        {/* Action Results Column */}
        <div className="space-y-3">
          <div className="text-sm font-medium text-gray-600 mb-3">Action Results</div>
          <div className="space-y-3">
            {displayItems.map((item) => (
              <div key={item.key} className="flex items-center justify-between">
                <span className="text-sm text-gray-600">{item.label}:</span>
                <span className={`text-lg font-semibold ${item.color}`}>
                  {item.value}
                </span>
              </div>
            ))}
          </div>
        </div>
        
        {/* Messages Column */}
        <div>
          <div className="text-sm font-medium text-blue-600 mb-3">Messages</div>
          {summary.messages && Object.keys(summary.messages).length > 0 ? (
            <div className="max-h-40 overflow-y-auto space-y-2">
              {Object.entries(summary.messages).map(([username, messages]: [string, any]) => (
                <div key={username} className="bg-blue-100 rounded p-2">
                  <div className="text-sm font-medium text-blue-800 mb-1">{username}</div>
                  <div className="space-y-1">
                    {Array.isArray(messages) ? messages.map((message: string, index: number) => (
                      <div key={index} className="text-sm text-blue-700 break-words">
                        {String(message)}
                      </div>
                    )) : (
                      <div className="text-sm text-blue-700 break-words">
                        {String(messages)}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-sm text-gray-500 italic">No messages</div>
          )}
        </div>

        {/* Errors Column */}
        <div>
          <div className="text-sm font-medium text-red-600 mb-3">Errors</div>
          {errorItems && errorItems.length > 0 ? (
            <div className="max-h-40 overflow-y-auto space-y-2">
              {errorItems.map((errorItem: any, index: number) => (
                <div key={index} className="bg-red-100 rounded p-2">
                  <div className="text-sm font-medium text-red-800">
                    {errorItem.username || (errorItem.account_id ? `Account ${errorItem.account_id}` : 'Unknown Account')}
                  </div>
                  <div className="space-y-1">
                    {(errorItem.errors || [errorItem.error]).map((error: string, errorIndex: number) => (
                      <div key={errorIndex} className="text-sm text-red-700 break-words">
                        {error}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-sm text-gray-500 italic">No errors</div>
          )}
        </div>
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <p className="text-red-800">Error loading job: {error.message}</p>
        <Button onClick={onBack} variant="secondary" className="mt-4">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Jobs
        </Button>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-md p-4">
        <p className="text-gray-800">Job not found</p>
        <Button onClick={onBack} variant="secondary" className="mt-4">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Jobs
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button onClick={onBack} variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{job.name}</h1>
            <p className="text-gray-600">Job Details</p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          {(job.status === 'pending' || job.status === 'running') && (
            <Button
              onClick={handleCancelJob}
              variant="secondary"
              className="flex items-center gap-2 text-red-600 hover:text-red-700"
              loading={cancelJobMutation.isLoading}
            >
              <X className="h-4 w-4" />
              Cancel Job
            </Button>
          )}
        </div>
      </div>

      {/* Status and Progress */}
      <div className="bg-white shadow rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            {getStatusIcon(job.status)}
            <span
              className={`inline-flex items-center px-3 py-1 text-sm font-semibold rounded-full ${getStatusColor(job.status)}`}
            >
              {job.status.charAt(0).toUpperCase() + job.status.slice(1)}
            </span>
          </div>
          <div className="text-sm text-gray-500">
            {getProgressPercentage()}% Complete
          </div>
        </div>

        <div className="mb-4">
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>Progress</span>
            <span>{job.completed_steps} / {job.total_steps} steps</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div
              className="bg-primary-600 h-3 rounded-full transition-all duration-300"
              style={{ width: `${getProgressPercentage()}%` }}
            ></div>
          </div>
        </div>

        {job.failed_steps > 0 && (
          <div className="text-sm text-red-600">
            {job.failed_steps} step{job.failed_steps !== 1 ? 's' : ''} failed
          </div>
        )}
      </div>

      {/* Job Information */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Job Information</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <dt className="text-sm font-medium text-gray-500">Created</dt>
            <dd className="text-sm text-gray-900">{formatDate(job.created_at)}</dd>
          </div>
          {job.started_at && (
            <div>
              <dt className="text-sm font-medium text-gray-500">Started</dt>
              <dd className="text-sm text-gray-900">{formatDate(job.started_at)}</dd>
            </div>
          )}
          {job.completed_at && (
            <div>
              <dt className="text-sm font-medium text-gray-500">Completed</dt>
              <dd className="text-sm text-gray-900">{formatDate(job.completed_at)}</dd>
            </div>
          )}
          {getDuration() && (
            <div>
              <dt className="text-sm font-medium text-gray-500">Duration</dt>
              <dd className="text-sm text-gray-900">{getDuration()}</dd>
            </div>
          )}
          <div>
            <dt className="text-sm font-medium text-gray-500">Execution Mode</dt>
            <dd className="text-sm text-gray-900">
              {job.parallel_execution ? 'Parallel' : 'Sequential'}
            </dd>
          </div>
        </div>
        
        {job.description && (
          <div className="mt-4">
            <dt className="text-sm font-medium text-gray-500">Description</dt>
            <dd className="text-sm text-gray-900 mt-1">{job.description}</dd>
          </div>
        )}

        {job.error_message && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
            <dt className="text-sm font-medium text-red-800">Error Message</dt>
            <dd className="text-sm text-red-700 mt-1">{job.error_message}</dd>
          </div>
        )}
      </div>

      {/* Overview Section */}
      <div className="bg-white shadow rounded-lg p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-medium text-gray-900">Job Overview</h3>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowSteps(!showSteps)}
            className="flex items-center gap-2"
          >
            <Eye className="h-6 w-6" />
            {showSteps ? 'Hide Steps' : 'Show Steps'}
          </Button>
        </div>

        {/* Job Summary */}
        <div className="mb-6">
          <h4 className="text-md font-medium text-gray-900 mb-4">Job Summary</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">{job.total_steps}</div>
              <div className="text-sm text-gray-500">Total Steps</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">{job.completed_steps}</div>
              <div className="text-sm text-gray-500">Completed</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">{job.failed_steps}</div>
              <div className="text-sm text-gray-500">Failed</div>
            </div>
          </div>
        </div>

        {/* Steps Section */}
        {showSteps && (
        <div className="border-t border-gray-200 pt-6">
          <h4 className="text-md font-medium text-gray-900 mb-4">Job Steps</h4>
          {job.steps && job.steps.length > 0 ? (
            <div className="space-y-3">
              {job.steps.map((step, index) => (
                <div key={step.id} className="border border-gray-200 rounded-lg">
                  {/* Step Summary Row - Clickable */}
                  <div 
                    className="p-4 cursor-pointer hover:bg-gray-50 transition-colors"
                    onClick={() => toggleStepExpansion(index)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-6 flex-1 min-w-0">
                        <div className="font-mono text-sm text-gray-500 w-8 flex-shrink-0">
                          #{step.step_order}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-gray-900 truncate">{step.action_type}</div>
                          {step.parameters && Object.keys(step.parameters).length > 0 && (
                            <div className="text-sm text-gray-500 truncate">
                              {Object.entries(step.parameters).slice(0, 2).map(([key, value]) => (
                                <span key={key} className="mr-2">
                                  {key}: {typeof value === 'object' && value !== null ? JSON.stringify(value) : String(value)}
                                </span>
                              ))}
                              {Object.keys(step.parameters).length > 2 && (
                                <span className="text-gray-400">+{Object.keys(step.parameters).length - 2} more</span>
                              )}
                            </div>
                          )}
                        </div>
                        <div className="text-sm text-gray-500 w-20 flex-shrink-0">
                          {step.account_ids.length} Account{step.account_ids.length !== 1 ? 's' : ''}
                        </div>
                        <div className="w-24 flex-shrink-0">
                          <span
                            className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-semibold rounded-full ${getStepStatusColor(step.status)}`}
                          >
                            {getStepStatusIcon(step.status)}
                            {step.status.charAt(0).toUpperCase() + step.status.slice(1)}
                          </span>
                        </div>
                        <div className="text-sm text-gray-500 w-28 flex-shrink-0">
                          {step.started_at && step.completed_at ? (
                            (() => {
                              const startTime = new Date(step.started_at).getTime();
                              const endTime = new Date(step.completed_at).getTime();
                              if (isNaN(startTime) || isNaN(endTime)) return 'Invalid';
                              const duration = endTime - startTime;
                              return duration < 0 ? '0.00s' : `${(duration / 1000).toFixed(2)}s`;
                            })()
                          ) : step.started_at ? (
                            'Running...'
                          ) : (
                            '-'
                          )}
                        </div>
                        <div className="w-32 flex-shrink-0">
                          {step.error_message ? (
                            <div className="text-red-600 text-xs truncate" title={step.error_message}>
                              Error: {step.error_message.length > 20 ? `${step.error_message.substring(0, 20)}...` : step.error_message}
                            </div>
                          ) : step.result ? (
                            <div className="text-green-600 text-xs truncate">
                              {typeof step.result === 'object' && step.result !== null ? 
                                (() => {
                                  const keys = Object.keys(step.result);
                                  if (keys.length === 0) return 'No data';
                                  
                                  // Check for message field first
                                  if (step.result.message) {
                                    const message = String(step.result.message);
                                    return message.length > 20 ? 
                                      `${message.substring(0, 20)}...` : 
                                      message;
                                  }
                                  
                                  // Check for data field
                                  if (step.result.data) {
                                    if (typeof step.result.data === 'object') {
                                      const dataKeys = Object.keys(step.result.data);
                                      return dataKeys.length > 0 ? 
                                        `${dataKeys.length} data fields` : 
                                        'Empty data';
                                    }
                                    return 'Data returned';
                                  }
                                  
                                  // Check for success field
                                  if (step.result.success !== undefined) {
                                    return step.result.success ? 'Success' : 'Failed';
                                  }
                                  
                                  return 'Completed';
                                })() : 
                                'Completed'
                              }
                            </div>
                          ) : step.status === 'pending' ? (
                            <span className="text-gray-400 text-xs">Pending</span>
                          ) : step.status === 'running' ? (
                            <span className="text-blue-400 text-xs">Running</span>
                          ) : (
                            <span className="text-gray-500 text-xs">-</span>
                          )}
                        </div>
                      </div>
                      <div className="ml-4 flex-shrink-0">
                        {expandedSteps.has(index) ? (
                          <ChevronDown className="h-4 w-4 text-gray-400" />
                        ) : (
                          <ChevronRight className="h-4 w-4 text-gray-400" />
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Expanded Details */}
                  {expandedSteps.has(index) && (
                    <div className="border-t border-gray-200 p-4 bg-gray-50">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <h5 className="text-sm font-medium text-gray-900 mb-2">Step Details</h5>
                          <div className="space-y-2 text-sm">
                            <div><span className="font-medium">Action:</span> {step.action_type}</div>
                            <div><span className="font-medium">Accounts:</span> {step.account_ids.length} account{step.account_ids.length !== 1 ? 's' : ''}</div>
                            <div><span className="font-medium">Execution:</span> {step.is_async ? 'Asynchronous' : 'Synchronous'}</div>
                            <div><span className="font-medium">Status:</span> {step.status}</div>
                            <div><span className="font-medium">Started:</span> {step.started_at ? formatDate(step.started_at) : 'Not started'}</div>
                            <div><span className="font-medium">Completed:</span> {step.completed_at ? formatDate(step.completed_at) : 'Not completed'}</div>
                            {step.started_at && step.completed_at && (
                              <div><span className="font-medium">Duration:</span> {(() => {
                                const startTime = new Date(step.started_at).getTime();
                                const endTime = new Date(step.completed_at).getTime();
                                if (isNaN(startTime) || isNaN(endTime)) return 'Invalid';
                                const duration = endTime - startTime;
                                return duration < 0 ? '0.00s' : `${(duration / 1000).toFixed(2)}s`;
                              })()}</div>
                            )}
                          </div>
                        </div>
                        <div>
                          <h5 className="text-sm font-medium text-gray-900 mb-2">Parameters</h5>
                          {step.parameters && Object.keys(step.parameters).length > 0 ? (
                            <div className="space-y-1 text-sm">
                              {Object.entries(step.parameters).map(([key, value]) => (
                                <div key={key}>
                                  <span className="font-medium">{key}:</span> {typeof value === 'object' && value !== null ? JSON.stringify(value, null, 2) : String(value)}
                                </div>
                              ))}
                            </div>
                          ) : (
                            <div className="text-sm text-gray-500">No parameters</div>
                          )}
                        </div>
                      </div>
                      
                      {/* Action Summary */}
                      {step.result && step.result.summary && (
                        <div className="mt-4">
                          <h5 className="text-sm font-medium text-gray-900 mb-2">Action Summary</h5>
                          <div className="bg-blue-50 border border-blue-200 rounded p-3">
                            {renderActionSummary(step.result.summary)}
                          </div>
                        </div>
                      )}
                      
                      {/* Result/Error Details */}
                      {(step.result || step.error_message) && (
                        <div className="mt-4">
                          <h5 className="text-sm font-medium text-gray-900 mb-2">Result</h5>
                          {step.error_message ? (
                            <div className="bg-red-50 border border-red-200 rounded p-3">
                              <div className="text-red-700 text-sm font-medium mb-1">Error</div>
                              <div className="text-red-600 text-sm break-words">{step.error_message}</div>
                            </div>
                          ) : step.result ? (
                            <div className="bg-green-50 border border-green-200 rounded p-3">
                              <div className="text-green-700 text-sm font-medium mb-2">Success Response</div>
                              <pre className="text-green-600 text-sm whitespace-pre-wrap break-words max-h-40 overflow-y-auto bg-white border border-green-300 rounded p-2">
                                {JSON.stringify(step.result, null, 2)}
                              </pre>
                            </div>
                          ) : null}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="py-8 text-center text-gray-500">
              No steps found for this job.
            </div>
          )}
        </div>
        )}

        {/* Message when steps are hidden */}
        {!showSteps && job.steps && job.steps.length > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
            <div className="flex items-center">
              <Eye className="h-5 w-5 text-blue-400 mr-2" />
              <div>
                <p className="text-sm text-blue-800">
                  <strong>Job has {job.steps.length} step{job.steps.length !== 1 ? 's' : ''}.</strong> Click "Show Steps" to view detailed step information and execution status.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default JobDetails;
