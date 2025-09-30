import React, { useState } from 'react';
import { useJobs, useCancelJob, useJobProgress } from '../hooks/useJobs';
import { JobResponse, JobStatus } from '../types/api';
import { Table, TableHeader, TableBody, TableRow, TableCell } from './ui/Table';
import Button from './ui/Button';
import Pagination from './ui/Pagination';
import { Plus, Eye, X, Search, Clock, CheckCircle, XCircle, AlertCircle, Pause, Copy } from 'lucide-react';
import Input from './ui/Input';

interface JobListProps {
  onViewJob: (job: JobResponse) => void;
  onCreateJob: () => void;
  onCloneJob: (job: JobResponse) => void;
}

const JobList: React.FC<JobListProps> = ({ onViewJob, onCreateJob, onCloneJob }) => {
  const [page, setPage] = useState(1);
  const [perPage] = useState(20);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedJobId, setExpandedJobId] = useState<number | null>(null);
  const [actionResultsSearch, setActionResultsSearch] = useState<{[jobId: number]: string}>({});

  const { data: jobsData, isLoading, error } = useJobs(page, perPage, statusFilter || undefined);
  const cancelJobMutation = useCancelJob();

  // Get progress data for all running/pending jobs
  const runningJobs = jobsData?.jobs.filter(job => job.status === 'running' || job.status === 'pending') || [];
  
  // Create a map of job progress data
  const jobProgressData: Record<number, any> = {};
  
  // Always call hooks in the same order - use enabled flag to control when they run
  const progressQuery1 = useJobProgress(runningJobs[0]?.id || 0);
  const progressQuery2 = useJobProgress(runningJobs[1]?.id || 0);
  const progressQuery3 = useJobProgress(runningJobs[2]?.id || 0);
  const progressQuery4 = useJobProgress(runningJobs[3]?.id || 0);
  const progressQuery5 = useJobProgress(runningJobs[4]?.id || 0);
  
  // Populate the progress data map
  if (progressQuery1.data && runningJobs[0]) jobProgressData[runningJobs[0].id] = progressQuery1.data;
  if (progressQuery2.data && runningJobs[1]) jobProgressData[runningJobs[1].id] = progressQuery2.data;
  if (progressQuery3.data && runningJobs[2]) jobProgressData[runningJobs[2].id] = progressQuery3.data;
  if (progressQuery4.data && runningJobs[3]) jobProgressData[runningJobs[3].id] = progressQuery4.data;
  if (progressQuery5.data && runningJobs[4]) jobProgressData[runningJobs[4].id] = progressQuery5.data;

  const handleCancelJob = async (job: JobResponse) => {
    if (window.confirm(`Are you sure you want to cancel job "${job.name}"?`)) {
      try {
        await cancelJobMutation.mutateAsync({ id: job.id });
      } catch (error) {
        console.error('Failed to cancel job:', error);
      }
    }
  };

  const handleRowClick = (job: JobResponse) => {
    setExpandedJobId(expandedJobId === job.id ? null : job.id);
  };

  const getStatusIcon = (status: JobStatus) => {
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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getProgressPercentage = (job: JobResponse) => {
    if (job.total_steps === 0) return 0;
    // Include both completed and failed steps as "finished" steps
    const finishedSteps = job.completed_steps + job.failed_steps;
    return Math.round((finishedSteps / job.total_steps) * 100);
  };

  const getAdvancedProgressPercentage = (job: JobResponse, progressData?: any) => {
    if (job.total_steps === 0) return 0;
    
    // If we have progress data, calculate partial step progress
    if (progressData?.steps && progressData.steps.length > 0) {
      let totalProgress = 0;
      
      for (const step of progressData.steps) {
        if (step.status === 'completed' || step.status === 'failed') {
          // Completed/failed steps count as 100%
          totalProgress += 100;
        } else if (step.status === 'running' && step.total_accounts > 0) {
          // Running steps count as partial progress
          const stepProgress = (step.processed_accounts / step.total_accounts) * 100;
          totalProgress += stepProgress;
        }
        // Pending steps count as 0%
      }
      
      return Math.round(totalProgress / job.total_steps);
    }
    
    // Fallback to simple step counting
    const finishedSteps = job.completed_steps + job.failed_steps;
    return Math.round((finishedSteps / job.total_steps) * 100);
  };

  // Filter jobs by search term
  const filteredJobs = jobsData?.jobs.filter(job =>
    job.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (job.description && job.description.toLowerCase().includes(searchTerm.toLowerCase()))
  ) || [];

  const renderActionSummary = (summary: any, searchTerm: string = '') => {
    const actionType = summary.action_type || 'unknown';
    
    // Common summary items
    const commonItems = [
      { key: 'successes', label: 'Completed', value: summary.successes, color: 'text-green-600' },
      { key: 'failed', label: 'Failed', value: summary.failed, color: 'text-red-600' },
      { key: 'total_retries', label: 'Retries', value: summary.total_retries, color: 'text-orange-600' }
    ];

    // Action-specific summary items
    const actionSpecificItems = [];
    
    switch (actionType) {
      case 'attack':
        actionSpecificItems.push(
          { key: 'battle_wins', label: 'Wins', value: summary.battle_wins, color: 'text-green-600' },
          { key: 'battle_losses', label: 'Losses', value: summary.battle_losses, color: 'text-red-600' },
          { key: 'protection_buffs', label: 'Protection Buffs', value: summary.protection_buffs, color: 'text-blue-600' },
          { key: 'maxed_hits', label: 'Maxed Hits', value: summary.maxed_hits, color: 'text-purple-600' },
          { key: 'runs_away', label: 'Runs Away', value: summary.runs_away, color: 'text-orange-600' },
          { key: 'gold_won', label: 'Gold Won', value: summary.gold_won?.toLocaleString(), color: 'text-yellow-600' },
          { key: 'troops_killed', label: 'Troops Killed', value: summary.troops_killed, color: 'text-red-600' },
          { key: 'troops_lost', label: 'Troops Lost', value: summary.troops_lost, color: 'text-red-600' }
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
          { key: 'spies_successful', label: 'Successful', value: summary.spies_successful, color: 'text-green-600' },
          { key: 'spies_successful_data', label: 'Data Collected', value: summary.spies_successful_data, color: 'text-blue-600' },
          { key: 'spies_caught', label: 'Caught', value: summary.spies_caught, color: 'text-red-600' },
          { key: 'spies_failed', label: 'Failed', value: summary.spies_failed, color: 'text-red-600' },
          { key: 'maxed_spy_attempts', label: 'Max Attempts', value: summary.maxed_spy_attempts, color: 'text-purple-600' }
        );
        break;
        
      case 'send_credits':
        actionSpecificItems.push(
          { key: 'credits_sent', label: 'Credits Sent', value: summary.credits_sent?.toLocaleString(), color: 'text-green-600' },
          { key: 'jackpot_credits', label: 'Jackpot', value: summary.jackpot_credits?.toLocaleString(), color: 'text-yellow-600' },
          { key: 'transfers_successful', label: 'Successful', value: summary.transfers_successful, color: 'text-green-600' }
        );
        break;
        
      case 'recruit':
        actionSpecificItems.push(
          { key: 'recruitments_successful', label: 'Successful', value: summary.recruitments_successful, color: 'text-green-600' },
          { key: 'total_cost', label: 'Cost', value: summary.total_cost?.toLocaleString(), color: 'text-yellow-600' }
        );
        break;
        
      case 'purchase_armory':
        actionSpecificItems.push(
          { key: 'weapons_purchased', label: 'Purchased', value: summary.weapons_purchased, color: 'text-green-600' },
          { key: 'total_cost', label: 'Cost', value: summary.total_cost?.toLocaleString(), color: 'text-yellow-600' },
          { key: 'total_revenue', label: 'Revenue', value: summary.total_revenue?.toLocaleString(), color: 'text-green-600' }
        );
        break;
        
      case 'purchase_training':
        actionSpecificItems.push(
          { key: 'soldiers_trained', label: 'Soldiers', value: summary.soldiers_trained, color: 'text-blue-600' },
          { key: 'mercs_trained', label: 'Mercs', value: summary.mercs_trained, color: 'text-purple-600' },
          { key: 'total_cost', label: 'Cost', value: summary.total_cost?.toLocaleString(), color: 'text-yellow-600' }
        );
        break;
        
      case 'become_officer':
        actionSpecificItems.push(
          { key: 'applications_successful', label: 'Successful', value: summary.applications_successful, color: 'text-green-600' },
          { key: 'applications_failed', label: 'Failed', value: summary.applications_failed, color: 'text-red-600' }
        );
        break;
        
      case 'get_metadata':
        actionSpecificItems.push(
          { key: 'retrievals_successful', label: 'Successful', value: summary.retrievals_successful, color: 'text-green-600' },
          { key: 'accounts_updated', label: 'Updated', value: summary.accounts_updated, color: 'text-blue-600' }
        );
        break;
        
      default:
        actionSpecificItems.push(
          { key: 'operations_completed', label: 'Operations', value: summary.operations_completed, color: 'text-green-600' }
        );
    }

    // Combine all items
    const allItems = [...commonItems, ...actionSpecificItems];
    
    // Filter out items with zero or undefined values for cleaner display
    const displayItems = allItems.filter(item => item.value !== undefined && item.value !== null && item.value !== 0);

    // Show errors if any
    const errorItems = summary.error_list && summary.error_list.length > 0 ? summary.error_list : [];

    return (
      <div className="grid grid-cols-3 gap-4 w-full">
        {/* Action Results Column */}
        <div className="space-y-2">
          <div className="text-sm font-medium text-gray-600 mb-3">Action Results</div>
          <div className="space-y-2">
            {displayItems.map((item) => (
              <div key={item.key} className="flex items-center justify-between">
                <span className="text-sm text-gray-600">{item.label}:</span>
                <span className={`text-sm font-semibold ${item.color}`}>
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
            <div className="max-h-48 overflow-y-auto space-y-2">
              {Object.entries(summary.messages)
                .filter(([username, messages]: [string, any]) => {
                  if (!searchTerm) return true;
                  const searchLower = searchTerm.toLowerCase();
                  return username.toLowerCase().includes(searchLower) ||
                    (Array.isArray(messages) ? messages : [messages]).some((msg: string) => 
                      String(msg).toLowerCase().includes(searchLower)
                    );
                })
                .map(([username, messages]: [string, any]) => (
                  <div key={username} className="bg-blue-100 rounded p-1">
                    <div className="text-xs font-medium text-blue-800 mb-1">{username}</div>
                    <div className="space-y-1">
                      {Array.isArray(messages) ? messages.map((message: string, index: number) => (
                        <div key={index} className="text-xs text-blue-700 break-words">
                          {String(message)}
                        </div>
                      )) : (
                        <div className="text-xs text-blue-700 break-words">
                          {String(messages)}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
            </div>
          ) : (
            <div className="text-xs text-gray-500 italic">No messages</div>
          )}
        </div>

        {/* Errors Column */}
        <div>
          <div className="text-sm font-medium text-red-600 mb-3">Errors</div>
          {errorItems && errorItems.length > 0 ? (
            <div className="max-h-48 overflow-y-auto space-y-2">
              {errorItems
                .filter((errorItem: any) => {
                  if (!searchTerm) return true;
                  const searchLower = searchTerm.toLowerCase();
                  const username = errorItem.username || (errorItem.account_id ? `Account ${errorItem.account_id}` : 'Unknown Account');
                  return username.toLowerCase().includes(searchLower) ||
                    (errorItem.errors || [errorItem.error]).some((error: string) => 
                      String(error).toLowerCase().includes(searchLower)
                    );
                })
                .map((errorItem: any, index: number) => (
                  <div key={index} className="bg-red-100 rounded p-1">
                    <div className="text-xs font-medium text-red-800">
                      {errorItem.username || (errorItem.account_id ? `Account ${errorItem.account_id}` : 'Unknown Account')}
                    </div>
                    <div className="space-y-1">
                      {(errorItem.errors || [errorItem.error]).map((error: string, errorIndex: number) => (
                        <div key={errorIndex} className="text-xs text-red-700 break-words">
                          {error}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
            </div>
          ) : (
            <div className="text-xs text-gray-500 italic">No errors</div>
          )}
        </div>
      </div>
    );
  };

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <p className="text-red-800">Error loading jobs: {error.message}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Jobs</h1>
          <p className="text-gray-600">Manage and monitor bulk operations</p>
        </div>
        <Button onClick={onCreateJob} className="flex items-center gap-2">
          <Plus className="h-4 w-4" />
          Create Job
        </Button>
      </div>

      {/* Filters */}
      <div className="flex items-center space-x-4">
        <div className="flex-1 max-w-md">
          <Input
            placeholder="Search jobs..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
        >
          <option value="">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="running">Running</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      {/* Jobs Table */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableCell header className="w-16">ID</TableCell>
                <TableCell header className="min-w-[200px]">Name</TableCell>
                <TableCell header className="min-w-[120px]">Status</TableCell>
                <TableCell header className="min-w-[120px]">Progress</TableCell>
                <TableCell header className="min-w-[120px]">Steps</TableCell>
                <TableCell header className="min-w-[150px]">Created</TableCell>
                <TableCell header className="min-w-[120px]">Duration</TableCell>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredJobs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-gray-500">
                    {searchTerm ? 'No jobs found matching your search.' : 'No jobs found.'}
                  </TableCell>
                </TableRow>
              ) : (
                filteredJobs.map((job) => (
                  <React.Fragment key={job.id}>
                    <TableRow 
                      className="cursor-pointer hover:bg-gray-50 transition-colors"
                      onClick={() => handleRowClick(job)}
                    >
                      <TableCell className="font-mono text-sm">{job.id}</TableCell>
                      <TableCell>
                        <div>
                          <div className="font-medium text-gray-900">{job.name}</div>
                          {job.description && (
                            <div className="text-sm text-gray-500 truncate max-w-xs">
                              {job.description}
                            </div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(job.status)}`}
                        >
                          {getStatusIcon(job.status)}
                          {job.status.charAt(0).toUpperCase() + job.status.slice(1)}
                        </span>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center space-x-2">
                          <div className="flex-1 bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-primary-600 h-2 rounded-full transition-all duration-300"
                              style={{ width: `${getAdvancedProgressPercentage(job, jobProgressData[job.id])}%` }}
                            ></div>
                          </div>
                          <span className="text-xs text-gray-500 w-8">
                            {getAdvancedProgressPercentage(job, jobProgressData[job.id])}%
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="text-sm text-gray-900">
                        {job.completed_steps}/{job.total_steps}
                        {job.failed_steps > 0 && (
                          <span className="text-red-600 ml-1">
                            ({job.failed_steps} failed)
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="text-gray-500 text-sm">
                        {formatDate(job.created_at)}
                      </TableCell>
                      <TableCell className="text-gray-500 text-sm">
                        {job.started_at && job.completed_at ? (
                          <>
                            {Math.round(
                              (new Date(job.completed_at).getTime() - new Date(job.started_at).getTime()) / 1000
                            )}s
                          </>
                        ) : job.started_at ? (
                          'Running...'
                        ) : (
                          '-'
                        )}
                      </TableCell>
                    </TableRow>
                    
                    {/* Expanded Job Details */}
                    {expandedJobId === job.id && (
                      <TableRow>
                        <TableCell colSpan={7} className="p-0">
                          <div className="bg-gray-50 border-t border-gray-200 p-6">
                            <JobExpandedDetails 
                              job={job} 
                              onViewJob={onViewJob}
                              onCloneJob={onCloneJob}
                              handleCancelJob={handleCancelJob}
                              cancelJobMutation={cancelJobMutation}
                              actionResultsSearch={actionResultsSearch}
                              setActionResultsSearch={setActionResultsSearch}
                              renderActionSummary={renderActionSummary}
                            />
                          </div>
                        </TableCell>
                      </TableRow>
                    )}
                  </React.Fragment>
                ))
              )}
            </TableBody>
          </Table>
        )}
      </div>

      {/* Pagination */}
      {jobsData && jobsData.total > perPage && (
        <Pagination
          currentPage={page}
          totalPages={Math.ceil(jobsData.total / perPage)}
          onPageChange={setPage}
        />
      )}
    </div>
  );
};

// Separate component for expanded job details with progress tracking
const JobExpandedDetails: React.FC<{ 
  job: JobResponse; 
  onViewJob: (job: JobResponse) => void;
  onCloneJob: (job: JobResponse) => void;
  handleCancelJob: (job: JobResponse) => void;
  cancelJobMutation: any;
  actionResultsSearch: {[jobId: number]: string};
  setActionResultsSearch: React.Dispatch<React.SetStateAction<{[jobId: number]: string}>>;
  renderActionSummary: (summary: any, searchTerm: string) => React.ReactNode;
}> = ({ 
  job, 
  onViewJob, 
  onCloneJob, 
  handleCancelJob, 
  cancelJobMutation, 
  actionResultsSearch, 
  setActionResultsSearch, 
  renderActionSummary 
}) => {
  const { data: progressData, isLoading: progressLoading, error: progressError } = useJobProgress(job.id);
  
  // Debug logging
  console.log(`Job ${job.id} progress:`, {
    progressData,
    progressLoading,
    progressError,
    jobStatus: job.status
  });
  
  // Helper functions
  const getStatusIcon = (status: JobStatus) => {
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
        return <AlertCircle className="h-4 w-4 text-gray-500" />;
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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getProgressPercentage = (job: JobResponse) => {
    if (job.total_steps === 0) return 0;
    // Include both completed and failed steps as "finished" steps
    const finishedSteps = job.completed_steps + job.failed_steps;
    return Math.round((finishedSteps / job.total_steps) * 100);
  };

  const getAdvancedProgressPercentage = (job: JobResponse, progressData?: any) => {
    if (job.total_steps === 0) return 0;
    
    // If we have progress data, calculate partial step progress
    if (progressData?.steps && progressData.steps.length > 0) {
      let totalProgress = 0;
      
      for (const step of progressData.steps) {
        if (step.status === 'completed' || step.status === 'failed') {
          // Completed/failed steps count as 100%
          totalProgress += 100;
        } else if (step.status === 'running' && step.total_accounts > 0) {
          // Running steps count as partial progress
          const stepProgress = (step.processed_accounts / step.total_accounts) * 100;
          totalProgress += stepProgress;
        }
        // Pending steps count as 0%
      }
      
      return Math.round(totalProgress / job.total_steps);
    }
    
    // Fallback to simple step counting
    const finishedSteps = job.completed_steps + job.failed_steps;
    return Math.round((finishedSteps / job.total_steps) * 100);
  };
  
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Job Overview */}
        <div className="space-y-4">
          <h4 className="font-medium text-gray-900">Job Overview</h4>
          <div className="space-y-2 text-sm">
            <div>
              <span className="font-medium text-gray-700">ID:</span>
              <span className="ml-2 font-mono">{job.id}</span>
            </div>
            <div>
              <span className="font-medium text-gray-700">Name:</span>
              <span className="ml-2">{job.name}</span>
            </div>
            {job.description && (
              <div>
                <span className="font-medium text-gray-700">Description:</span>
                <span className="ml-2">{job.description}</span>
              </div>
            )}
            <div>
              <span className="font-medium text-gray-700">Status:</span>
              <span className={`ml-2 inline-flex items-center gap-1 px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(job.status)}`}>
                {getStatusIcon(job.status)}
                {job.status.charAt(0).toUpperCase() + job.status.slice(1)}
              </span>
            </div>
            <div>
              <span className="font-medium text-gray-700">Parallel Execution:</span>
              <span className="ml-2">{job.parallel_execution ? 'Yes' : 'No'}</span>
            </div>
          </div>
        </div>

        {/* Progress & Timing */}
        <div className="space-y-4">
          <h4 className="font-medium text-gray-900">Progress & Timing</h4>
          <div className="space-y-2 text-sm">
            <div>
              <span className="font-medium text-gray-700">Progress:</span>
              <div className="mt-1 flex items-center space-x-2">
                <div className="flex-1 bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-primary-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${getAdvancedProgressPercentage(job, progressData)}%` }}
                  ></div>
                </div>
                <span className="text-xs text-gray-500 w-8">
                  {getAdvancedProgressPercentage(job, progressData)}%
                </span>
              </div>
            </div>
            <div>
              <span className="font-medium text-gray-700">Steps:</span>
              <span className="ml-2">{job.completed_steps + job.failed_steps}/{job.total_steps}</span>
              {job.failed_steps > 0 && (
                <span className="text-red-600 ml-1">({job.failed_steps} failed)</span>
              )}
            </div>
            <div>
              <span className="font-medium text-gray-700">Created:</span>
              <span className="ml-2">{formatDate(job.created_at)}</span>
            </div>
            {job.started_at && (
              <div>
                <span className="font-medium text-gray-700">Started:</span>
                <span className="ml-2">{formatDate(job.started_at)}</span>
              </div>
            )}
            {job.completed_at && (
              <div>
                <span className="font-medium text-gray-700">Completed:</span>
                <span className="ml-2">{formatDate(job.completed_at)}</span>
              </div>
            )}
            {job.started_at && job.completed_at && (
              <div>
                <span className="font-medium text-gray-700">Duration:</span>
                <span className="ml-2">
                  {Math.round(
                    (new Date(job.completed_at).getTime() - new Date(job.started_at).getTime()) / 1000
                  )}s
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Actions & Status */}
        <div className="space-y-4">
          <h4 className="font-medium text-gray-900">Actions & Status</h4>
          <div className="space-y-2 text-sm">
            <div className="flex items-center space-x-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => onViewJob(job)}
                className="flex items-center gap-2"
              >
                <Eye className="h-4 w-4" />
                View Full Details
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => onCloneJob(job)}
                className="flex items-center gap-2"
              >
                <Copy className="h-4 w-4" />
                Clone Job
              </Button>
            </div>
            {(job.status === 'pending' || job.status === 'running') && (
              <div className="flex items-center space-x-2">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => handleCancelJob(job)}
                  className="text-red-600 hover:text-red-700"
                  loading={cancelJobMutation.isLoading}
                >
                  <X className="h-4 w-4 mr-1" />
                  Cancel Job
                </Button>
              </div>
            )}
            {job.error_message && (
              <div>
                <span className="font-medium text-gray-700">Error:</span>
                <div className="mt-1 p-2 bg-red-50 border border-red-200 rounded text-red-700 text-xs">
                  {job.error_message}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
      
      {/* Action Results - Full Width Section */}
      {job.steps && job.steps.length > 0 && (
        <div className="mt-6 space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="font-medium text-gray-900">Action Results</h4>
            <div className="flex items-center space-x-2">
              <Search className="h-4 w-4 text-gray-400" />
              <Input
                type="text"
                placeholder="Search messages & errors..."
                value={actionResultsSearch[job.id] || ''}
                onChange={(e) => setActionResultsSearch(prev => ({
                  ...prev,
                  [job.id]: e.target.value
                }))}
                className="w-64 text-sm"
              />
            </div>
          </div>
          <div className="space-y-4">
            {job.steps.map((step, stepIndex) => {
              // Get real-time progress data for this step by matching step ID
              const progressStep = progressData?.steps?.find(ps => ps.id === step.id);
              const stepData = progressStep || step;
              
              // Debug logging
              console.log(`Step ${stepIndex} (ID: ${step.id}):`, {
                stepId: step.id,
                stepData,
                progressStep,
                progressDataSteps: progressData?.steps,
                progressDataStepsLength: progressData?.steps?.length,
                progressDataStepAtIndex: progressData?.steps?.[stepIndex],
                total_accounts: stepData.total_accounts,
                processed_accounts: stepData.processed_accounts,
                status: stepData.status,
                isUsingProgressData: !!progressStep
              });
              
              return (
              <div key={step.id} className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                <div className="mb-3">
                  <div className="flex items-center space-x-2 mb-1">
                    <span className="font-mono text-sm text-gray-500">#{step.step_order}</span>
                    <span className="font-medium text-base text-gray-900 truncate flex-1" title={step.action_type}>
                      {step.action_type}
                    </span>
                    <span
                      className={`inline-flex items-center gap-1 px-3 py-1 text-sm font-semibold rounded-full flex-shrink-0 ${
                        stepData.status === 'completed' ? 'bg-green-100 text-green-800' :
                        stepData.status === 'failed' ? 'bg-red-100 text-red-800' :
                        stepData.status === 'running' ? 'bg-blue-100 text-blue-800' :
                        'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {stepData.status.charAt(0).toUpperCase() + stepData.status.slice(1)}
                    </span>
                  </div>
                  <div className="text-sm text-gray-500">
                    {stepData.total_accounts > 0 ? (
                      <div className="space-y-1">
                        <div>
                          {stepData.processed_accounts}/{stepData.total_accounts} accounts processed • {step.is_async ? 'Async' : 'Sync'}
                        </div>
                        {/* Always show progress bar for debugging */}
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div 
                            className="bg-blue-600 h-2 rounded-full transition-all duration-300" 
                            style={{ width: `${stepData.total_accounts > 0 ? (stepData.processed_accounts / stepData.total_accounts) * 100 : 0}%` }}
                          ></div>
                        </div>
                        <div className="text-xs text-gray-500">
                          Progress: {stepData.processed_accounts || 0}/{stepData.total_accounts || 0} ({stepData.total_accounts > 0 ? Math.round((stepData.processed_accounts / stepData.total_accounts) * 100) : 0}%)
                        </div>
                        {stepData.successful_accounts > 0 || stepData.failed_accounts > 0 ? (
                          <div className="text-xs text-gray-400">
                            ✓ {stepData.successful_accounts} successful • ✗ {stepData.failed_accounts} failed
                          </div>
                        ) : null}
                      </div>
                    ) : (
                      <div>
                        {step.account_ids.length} account{step.account_ids.length !== 1 ? 's' : ''} • {step.is_async ? 'Async' : 'Sync'}
                      </div>
                    )}
                  </div>
                </div>
                
                {/* Action Summary */}
                {step.result && step.result.summary && (
                  <div className="bg-blue-50 border border-blue-200 rounded p-4">
                    {renderActionSummary(step.result.summary, actionResultsSearch[job.id] || '')}
                  </div>
                )}
                
                {/* Error Display */}
                {step.error_message && (
                  <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
                    {step.error_message}
                  </div>
                )}
              </div>
            );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default JobList;
