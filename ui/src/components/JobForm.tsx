import React, { useState, useEffect } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { useQueryClient, useQuery } from 'react-query';
import { useCreateJob, useValidActionTypes, useJob, useJobs, jobKeys } from '../hooks/useJobs';
import { useClusters } from '../hooks/useClusters';
import { useFavoriteJobs } from '../hooks/useFavoriteJobs';
import { JobCreateRequest, JobStepRequest, ActionType, JobResponse } from '../types/api';
import { jobsApi } from '../services/api';
import Button from './ui/Button';
import Input from './ui/Input';
import Modal from './ui/Modal';
import AccountAutocomplete from './AccountAutocomplete';
import { Plus, Trash2, Users, User, ChevronDown, ChevronRight, EyeOff, Search, X, Star } from 'lucide-react';
import FriendlyActionParameters from './FriendlyActionParameters';

interface JobFormProps {
  isOpen: boolean;
  onClose: () => void;
  jobToClone?: JobResponse | null;
}

interface FormData {
  name: string;
  description: string;
  parallel_execution: boolean;
  steps: Array<{
    action_type: string;
    account_ids: number[];
    cluster_ids: number[];
    original_account_ids?: number[];
    original_cluster_ids?: number[];
    max_retries: number;
    is_async: boolean;
    parameters: Record<string, any>;
  }>;
}

const JobForm: React.FC<JobFormProps> = ({ isOpen, onClose, jobToClone }) => {
  const queryClient = useQueryClient();
  const createJobMutation = useCreateJob();
  const { data: actionTypesData } = useValidActionTypes();
  const { data: clustersData } = useClusters(1, 10000); // Increased limit for autocomplete search
  // Removed large account fetch - now using AccountAutocomplete component
  const { createFavoriteJob } = useFavoriteJobs();
  // Use a separate query for smart numbering that doesn't auto-poll
  const { refetch: refetchJobs } = useQuery(
    jobKeys.list({ page: 1, perPage: 100, status: undefined, includeSteps: true }),
    () => jobsApi.getJobs(1, 100, undefined, true),
    {
      enabled: false, // Only fetch when manually triggered
      staleTime: 5 * 60 * 1000, // Consider data stale after 5 minutes
    }
  );
  const [editingStepIndex, setEditingStepIndex] = useState<number | null>(null);
  // Removed search state - now handled by AccountAutocomplete component
  const [clusterSearchTerms, setClusterSearchTerms] = useState<{ [stepIndex: number]: string }>({});
  const [showClusterSuggestions, setShowClusterSuggestions] = useState<{ [stepIndex: number]: boolean }>({});
  const [selectedClusterSuggestionIndex, setSelectedClusterSuggestionIndex] = useState<{ [stepIndex: number]: number }>({});
  const [showFavoriteModal, setShowFavoriteModal] = useState(false);
  const [favoriteName, setFavoriteName] = useState('');
  const [favoriteDescription, setFavoriteDescription] = useState('');

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
    reset,
    watch,
    setValue,
  } = useForm<FormData>({
    defaultValues: {
      name: '',
      description: '',
      parallel_execution: false,
      steps: [
        {
          action_type: '',
          account_ids: [],
          cluster_ids: [],
          max_retries: 0,
          is_async: true,
          parameters: {},
        },
      ],
    },
  });

  const { fields, append, remove, replace } = useFieldArray({
    control,
    name: 'steps',
  });

  const watchedSteps = watch('steps');

  useEffect(() => {
    if (!isOpen) {
      reset();
    }
  }, [isOpen, reset]);

  // Fetch full job details if needed for cloning
  const shouldFetchJob = !!(isOpen && jobToClone);
  const { data: fullJobData } = useJob(
    shouldFetchJob ? (jobToClone?.id || 0) : 0, 
    true // include steps
  );

  // Function to generate the next available job name with smart numbering
  const generateNextJobName = async (originalName: string): Promise<string> => {
    // Extract the base name (without any existing numbers)
    const baseName = originalName.replace(/\s*\(\d+\)\s*$/, '').trim();
    
    // Try to get fresh data from the query cache first
    const cachedJobsData = queryClient.getQueryData(jobKeys.list({ page: 1, perPage: 100, status: undefined })) as any;
    
    // If no data is available, try to fetch it
    let existingJobNames: string[] = [];
    if (cachedJobsData?.jobs) {
      existingJobNames = cachedJobsData.jobs.map((job: any) => job.name);
    } else {
      // No data available, try to refetch
      try {
        const freshData = await refetchJobs();
        if (freshData.data?.jobs) {
          existingJobNames = freshData.data.jobs.map((job: any) => job.name);
        }
      } catch (error) {
        console.error('Failed to fetch jobs data:', error);
      }
    }
    
    // Find all jobs that start with the base name (including exact matches and numbered variants)
    const escapedBaseName = baseName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const baseNamePattern = new RegExp(`^${escapedBaseName}(?:\\s*\\((\\d+)\\))?\\s*$`);
    
    // Collect all numbers from jobs that match the base name pattern
    const numbers = existingJobNames
      .map((name: string) => {
        const match = name.match(baseNamePattern);
        if (match) {
          // If no number in parentheses, treat as 0 (the base name itself)
          const num = match[1] ? parseInt(match[1], 10) : 0;
          return num;
        }
        return null;
      })
      .filter((num: number | null): num is number => num !== null)
      .sort((a: number, b: number) => a - b);
    
    // Find the next available number starting from 1
    let nextNumber = 1;
    for (const num of numbers) {
      if (num === nextNumber) {
        nextNumber++;
      } else if (num > nextNumber) {
        // Found a gap, use the next number
        break;
      }
    }
    
    return `${baseName} (${nextNumber})`;
  };

  // Prefill form when cloning a job
  useEffect(() => {
    if (isOpen && jobToClone) {
      // Use full job data if available, otherwise use the passed job data
      const jobData = fullJobData || jobToClone;
      
      // Preserve all steps exactly as they were - no consolidation
      const originalSteps = jobData.steps || [];
      const clonedSteps = originalSteps.map((step) => {
        // Convert object parameters to JSON strings for form display
        const formParameters: Record<string, any> = {};
        if (step.parameters) {
          Object.entries(step.parameters).forEach(([key, value]) => {
            // Check if this parameter should be displayed as JSON string
            const actionInfo = getActionTypeInfo(step.action_type);
            const paramInfo = actionInfo?.parameter_details?.[key];
            
            if (paramInfo?.type === 'object' && typeof value === 'object' && value !== null) {
              // Convert object to JSON string for form display
              formParameters[key] = JSON.stringify(value, null, 2);
            } else if (key === 'weapon_percentages' && typeof value === 'object' && value !== null) {
              // Special case for weapon_percentages - always convert to JSON string
              formParameters[key] = JSON.stringify(value, null, 2);
            } else {
              // Keep other parameters as-is
              formParameters[key] = value;
            }
          });
        }
        
        return {
          action_type: step.action_type,
          account_ids: (step as any).original_account_ids || (step as any).account_ids || [],
          cluster_ids: (step as any).original_cluster_ids || (step as any).cluster_ids || [],
          max_retries: step.max_retries || 0,
          is_async: step.is_async !== undefined ? step.is_async : true,
          parameters: formParameters,
          originalParameters: step.parameters || {},
        };
      });

      console.log(`Cloning ${originalSteps.length} steps exactly as they were (no consolidation)`);

      // Generate smart job name with proper numbering
      const generateName = async () => {
        const smartJobName = await generateNextJobName(jobData.name);

        // Reset form with the complete cloned data
        const formData = {
          name: smartJobName,
          description: jobData.description || '',
          parallel_execution: jobData.parallel_execution || false,
          steps: clonedSteps
        };
        
        reset(formData);
      };

      generateName();
    }
  }, [isOpen, jobToClone, fullJobData, reset]);

  // Close suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (!target.closest('.suggestions-container')) {
        setShowClusterSuggestions({});
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const onSubmit = async (data: FormData) => {
    try {
      const jobData: JobCreateRequest = {
        name: data.name,
        description: data.description || undefined,
        parallel_execution: data.parallel_execution,
        steps: data.steps.map((step) => {
          // Filter out empty parameters and parse JSON objects
          let filteredParameters = step.parameters 
            ? Object.fromEntries(
                Object.entries(step.parameters)
                  .filter(([_, value]) => 
                    value !== undefined && value !== null && value !== ''
                  )
                  .map(([key, value]) => {
                    // Special handling for training_orders - parse from JSON string
                    if (key === 'training_orders') {
                      if (typeof value === 'object') {
                        return [key, value];
                      } else if (typeof value === 'string') {
                        try {
                          return [key, JSON.parse(value)];
                        } catch (e) {
                          console.warn('Failed to parse training_orders JSON:', e);
                          return [key, value];
                        }
                      }
                    }
                    
                    // Check if this parameter should be parsed as JSON
                    const actionInfo = getActionTypeInfo(step.action_type);
                    const paramInfo = actionInfo?.parameter_details?.[key];
                    
                    if (paramInfo?.type === 'object' && typeof value === 'string') {
                      try {
                        return [key, JSON.parse(value)];
                      } catch (e) {
                        console.warn(`Failed to parse JSON for parameter ${key}:`, e);
                        return [key, value];
                      }
                    }
                    return [key, value];
                  })
              )
            : {};

          // For purchase_training, only keep training_orders and remove other nested objects
          if (step.action_type === 'purchase_training') {
            const cleanParameters: Record<string, any> = {};
            
            // Keep only training_orders and other non-nested parameters
            Object.entries(filteredParameters).forEach(([key, value]) => {
              // Skip nested objects that are not training_orders
              if (key === 'training_orders') {
                cleanParameters[key] = value;
              } else if (typeof value !== 'object' || value === null) {
                // Keep primitive values
                cleanParameters[key] = value;
              }
              // Skip nested objects like 'buy', 'train', 'untrain'
            });
            
            filteredParameters = cleanParameters;
          }

          return {
            action_type: step.action_type,
            account_ids: (step.original_account_ids && step.original_account_ids.length > 0) || (step.account_ids && step.account_ids.length > 0) 
              ? (step.original_account_ids || step.account_ids) 
              : undefined,
            cluster_ids: (step.original_cluster_ids && step.original_cluster_ids.length > 0) || (step.cluster_ids && step.cluster_ids.length > 0)
              ? (step.original_cluster_ids || step.cluster_ids)
              : undefined,
            max_retries: step.max_retries,
            is_async: step.is_async,
            parameters: Object.keys(filteredParameters).length > 0 ? filteredParameters : undefined,
          };
        }),
      };

      console.log('Submitting job data:', jobData);
      console.log('Raw form data:', data);
      await createJobMutation.mutateAsync(jobData);
      onClose();
    } catch (error) {
      console.error('Failed to create job:', error);
    }
  };

  const addStep = () => {
    append({
      action_type: '',
      account_ids: [],
      cluster_ids: [],
      max_retries: 0,
      is_async: true,
      parameters: {},
    });
  };

  const removeStep = (index: number) => {
    if (fields.length > 1) {
      remove(index);
    }
  };

  const getActionTypeInfo = (actionType: string): ActionType | undefined => {
    return actionTypesData?.action_types.find((at) => at.action_type === actionType);
  };

  const handleSaveAsFavorite = async (data: FormData) => {
    try {
      const jobData: JobCreateRequest = {
        name: data.name,
        description: data.description || undefined,
        parallel_execution: data.parallel_execution,
        steps: data.steps.map((step) => {
          // Filter out empty parameters and parse JSON objects
          let filteredParameters = step.parameters 
            ? Object.fromEntries(
                Object.entries(step.parameters)
                  .filter(([_, value]) => 
                    value !== undefined && value !== null && value !== ''
                  )
                  .map(([key, value]) => {
                    // Special handling for training_orders - parse from JSON string
                    if (key === 'training_orders') {
                      if (typeof value === 'object') {
                        return [key, value];
                      } else if (typeof value === 'string') {
                        try {
                          return [key, JSON.parse(value)];
                        } catch (e) {
                          console.warn('Failed to parse training_orders JSON:', e);
                          return [key, value];
                        }
                      }
                    }
                    
                    // Check if this parameter should be parsed as JSON
                    const actionInfo = getActionTypeInfo(step.action_type);
                    const paramInfo = actionInfo?.parameter_details?.[key];
                    
                    if (paramInfo?.type === 'object' && typeof value === 'string') {
                      try {
                        return [key, JSON.parse(value)];
                      } catch (e) {
                        console.warn(`Failed to parse JSON for parameter ${key}:`, e);
                        return [key, value];
                      }
                    }
                    return [key, value];
                  })
              )
            : {};

          // For purchase_training, only keep training_orders and remove other nested objects
          if (step.action_type === 'purchase_training') {
            const cleanParameters: Record<string, any> = {};
            
            // Keep only training_orders and other non-nested parameters
            Object.entries(filteredParameters).forEach(([key, value]) => {
              // Skip nested objects that are not training_orders
              if (key === 'training_orders') {
                cleanParameters[key] = value;
              } else if (typeof value !== 'object' || value === null) {
                // Keep primitive values
                cleanParameters[key] = value;
              }
              // Skip nested objects like 'buy', 'train', 'untrain'
            });
            
            filteredParameters = cleanParameters;
          }

          return {
            action_type: step.action_type,
            account_ids: step.original_account_ids || step.account_ids || [],
            cluster_ids: step.original_cluster_ids || step.cluster_ids || [],
            parameters: filteredParameters,
            max_retries: step.max_retries,
            is_async: step.is_async,
          };
        }),
      };

      await createFavoriteJob({
        name: favoriteName,
        description: favoriteDescription || undefined,
        job_config: jobData,
      });

      setShowFavoriteModal(false);
      setFavoriteName('');
      setFavoriteDescription('');
    } catch (error) {
      console.error('Error saving as favorite:', error);
    }
  };

  // Account selection helpers - simplified for AccountAutocomplete component

  const addAccountToStep = (stepIndex: number, account: any) => {
    const currentAccountIds = watchedSteps[stepIndex]?.account_ids || [];
    const newAccountIds = [...currentAccountIds, account.id];
    setValue(`steps.${stepIndex}.account_ids`, newAccountIds);
  };

  const removeAccountFromStep = (stepIndex: number, accountId: number) => {
    const currentAccountIds = watchedSteps[stepIndex]?.account_ids || [];
    const newAccountIds = currentAccountIds.filter((id: number) => id !== accountId);
    setValue(`steps.${stepIndex}.account_ids`, newAccountIds);
  };

  const removeAllAccountsFromStep = (stepIndex: number) => {
    setValue(`steps.${stepIndex}.account_ids`, []);
  };

  // Removed getAccountById - account data now comes from AccountAutocomplete component

  // Cluster search and selection helpers
  const getFilteredClusters = (searchTerm: string, stepIndex: number) => {
    if (!searchTerm || !clustersData?.data) return [];
    
    const currentClusterIds = watchedSteps[stepIndex]?.cluster_ids || [];
    
    return clustersData.data.filter((cluster: any) => {
      const isAlreadySelected = currentClusterIds.includes(cluster.id);
      if (isAlreadySelected) return false;
      
      const searchLower = searchTerm.toLowerCase();
      return (
        cluster.name.toLowerCase().includes(searchLower) ||
        cluster.id.toString().includes(searchTerm)
      );
    }).slice(0, 10); // Limit to 10 suggestions
  };

  const addClusterToStep = (stepIndex: number, cluster: any) => {
    const currentClusterIds = watchedSteps[stepIndex]?.cluster_ids || [];
    const newClusterIds = [...currentClusterIds, cluster.id];
    setValue(`steps.${stepIndex}.cluster_ids`, newClusterIds);
    
    // Clear search and hide suggestions
    setClusterSearchTerms(prev => ({ ...prev, [stepIndex]: '' }));
    setShowClusterSuggestions(prev => ({ ...prev, [stepIndex]: false }));
    setSelectedClusterSuggestionIndex(prev => ({ ...prev, [stepIndex]: -1 }));
  };

  const removeClusterFromStep = (stepIndex: number, clusterId: number) => {
    const currentClusterIds = watchedSteps[stepIndex]?.cluster_ids || [];
    const newClusterIds = currentClusterIds.filter((id: number) => id !== clusterId);
    setValue(`steps.${stepIndex}.cluster_ids`, newClusterIds);
  };

  const getClusterById = (clusterId: number) => {
    return clustersData?.data.find((cluster: any) => cluster.id === clusterId);
  };

  // Keyboard navigation removed - now handled by AccountAutocomplete component

  // Keyboard navigation helpers for clusters
  const handleClusterKeyDown = (stepIndex: number, event: React.KeyboardEvent) => {
    const filteredClusters = getFilteredClusters(clusterSearchTerms[stepIndex] || '', stepIndex);
    const currentIndex = selectedClusterSuggestionIndex[stepIndex] ?? -1;

    // Only handle keyboard navigation if suggestions are visible
    if (!showClusterSuggestions[stepIndex] || filteredClusters.length === 0) {
      return;
    }

    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault();
        event.stopPropagation();
        const nextIndex = currentIndex < filteredClusters.length - 1 ? currentIndex + 1 : 0;
        setSelectedClusterSuggestionIndex(prev => ({ ...prev, [stepIndex]: nextIndex }));
        break;
      case 'ArrowUp':
        event.preventDefault();
        event.stopPropagation();
        const prevIndex = currentIndex <= 0 ? filteredClusters.length - 1 : currentIndex - 1;
        setSelectedClusterSuggestionIndex(prev => ({ ...prev, [stepIndex]: prevIndex }));
        break;
      case 'Enter':
        event.preventDefault();
        event.stopPropagation();
        if (currentIndex >= 0 && currentIndex < filteredClusters.length) {
          const cluster = filteredClusters[currentIndex];
          addClusterToStep(stepIndex, cluster);
        }
        break;
      case 'Escape':
        event.preventDefault();
        event.stopPropagation();
        setShowClusterSuggestions(prev => ({ ...prev, [stepIndex]: false }));
        setSelectedClusterSuggestionIndex(prev => ({ ...prev, [stepIndex]: -1 }));
        break;
    }
  };

  const getSelectedAccounts = (stepIndex: number) => {
    const step = watchedSteps[stepIndex];
    if (!step) {
      return {
        individualAccounts: [],
        clusterCount: 0,
        totalIndividual: 0,
        totalClusters: 0
      };
    }
    
    // For now, we can only count individual accounts since cluster users
    // are not available in the cluster list response
    const individualAccounts = step.original_account_ids || step.account_ids || [];
    const clusterCount = step.cluster_ids?.length || 0;
    
    return {
      individualAccounts,
      clusterCount,
      totalIndividual: individualAccounts.length,
      totalClusters: clusterCount
    };
  };

  const isLoading = createJobMutation.isLoading;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Create Job"
      size="lg"
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Basic Job Info */}
        <div className="space-y-4">
          <Input
            label="Job Name"
            {...register('name', {
              required: 'Job name is required',
              minLength: {
                value: 2,
                message: 'Job name must be at least 2 characters',
              },
            })}
            error={errors.name?.message}
            placeholder="Enter job name"
          />

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              {...register('description')}
              className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
              placeholder="Enter job description (optional)"
              rows={3}
            />
          </div>

          <div className="flex items-center">
            <input
              type="checkbox"
              id="parallel_execution"
              {...register('parallel_execution')}
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
            <label htmlFor="parallel_execution" className="ml-2 block text-sm text-gray-900">
              Execute steps in parallel
            </label>
          </div>
        </div>

        {/* Job Steps */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium text-gray-900">Job Steps ({fields.length})</h3>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={addStep}
              className="flex items-center gap-2"
            >
              <Plus className="h-4 w-4" />
              Add Step
            </Button>
          </div>

          {/* Steps Overview */}
          {fields.length > 0 && (
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-medium text-gray-900">Steps Overview</h4>
                <div className="text-sm text-gray-500">
                  Click on any step to edit it
                </div>
              </div>
              <div className="space-y-2">
                {fields.map((field, index) => {
                  const step = watchedSteps[index];
                  const selection = getSelectedAccounts(index);
                  const actionInfo = getActionTypeInfo(step?.action_type || '');
                  const isEditing = editingStepIndex === index;
                  
                  return (
                    <div key={field.id} className="space-y-2">
                      {/* Step Summary - Clickable */}
                      <div 
                        className={`flex items-center justify-between bg-white rounded-md p-3 border cursor-pointer transition-colors ${
                          isEditing ? 'border-primary-500 bg-primary-50' : 'border-gray-200 hover:border-gray-300'
                        }`}
                        onClick={() => setEditingStepIndex(isEditing ? null : index)}
                      >
                        <div className="flex items-center space-x-3">
                          <div className="flex-shrink-0 w-8 h-8 bg-primary-100 text-primary-600 rounded-full flex items-center justify-center text-sm font-medium">
                            {index + 1}
                          </div>
                          <div>
                            <div className="font-medium text-gray-900">
                              {step?.action_type || 'No action selected'}
                            </div>
                            <div className="text-sm text-gray-500">
                              {actionInfo?.description || 'Select an action type'}
                            </div>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-sm text-gray-900">
                            {selection.totalIndividual > 0 && (
                              <span>{selection.totalIndividual} account{selection.totalIndividual !== 1 ? 's' : ''}</span>
                            )}
                            {selection.totalIndividual > 0 && selection.totalClusters > 0 && <span>, </span>}
                            {selection.totalClusters > 0 && (
                              <span>{selection.totalClusters} cluster{selection.totalClusters !== 1 ? 's' : ''}</span>
                            )}
                            {selection.totalIndividual === 0 && selection.totalClusters === 0 && (
                              <span className="text-gray-400">
                                {step?.action_type === 'delay' ? 'No targets needed' : 'No targets selected'}
                              </span>
                            )}
                          </div>
                          <div className="text-xs text-gray-500">
                            Max retries: {step?.max_retries || 0} • {step?.is_async ? 'Async' : 'Sync'}
                          </div>
                        </div>
                      </div>

                      {/* Detailed Step Editor - Only show when editing this step */}
                      {isEditing && (
                        <div className="border border-primary-200 rounded-lg p-4 space-y-4 bg-primary-50">
                          <div className="flex items-center justify-between">
                            <h4 className="font-medium text-gray-900">Edit Step {index + 1}</h4>
                            <div className="flex items-center space-x-2">
                              {fields.length > 1 && (
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => removeStep(index)}
                                  className="text-red-600 hover:text-red-700"
                                >
                                  <Trash2 className="h-4 w-4" />
                                </Button>
                              )}
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                onClick={() => setEditingStepIndex(null)}
                                className="text-gray-500 hover:text-gray-700"
                              >
                                <EyeOff className="h-4 w-4" />
                              </Button>
                            </div>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-1">
                                Action Type
                              </label>
                              <select
                                {...register(`steps.${index}.action_type`, {
                                  required: 'Action type is required',
                                })}
                                onChange={(e) => {
                                  // Clear parameters when action type changes
                                  setValue(`steps.${index}.parameters`, {});
                                  // Trigger the register onChange as well
                                  register(`steps.${index}.action_type`).onChange(e);
                                }}
                                className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                              >
                                <option value="">Select action type</option>
                                {actionTypesData?.categories && Object.entries(actionTypesData.categories).map(([category, actions]) => (
                                  <optgroup key={category} label={category.replace('_', ' ').toUpperCase()}>
                                    {actions.map((action) => (
                                      <option key={action.action_type} value={action.action_type}>
                                        {action.action_type} - {action.description}
                                      </option>
                                    ))}
                                  </optgroup>
                                ))}
                              </select>
                              {errors.steps?.[index]?.action_type && (
                                <p className="mt-1 text-sm text-red-600">
                                  {errors.steps[index]?.action_type?.message}
                                </p>
                              )}
                            </div>

                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-1">
                                Max Retries
                              </label>
                              <input
                                type="number"
                                min="0"
                                max="10"
                                {...register(`steps.${index}.max_retries`, {
                                  valueAsNumber: true,
                                  min: { value: 0, message: 'Must be at least 0' },
                                  max: { value: 10, message: 'Must be at most 10' },
                                })}
                                className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                              />
                              {errors.steps?.[index]?.max_retries && (
                                <p className="mt-1 text-sm text-red-600">
                                  {errors.steps[index]?.max_retries?.message}
                                </p>
                              )}
                            </div>
                          </div>

                          {/* Runners */}
                          <div className="space-y-4">
                            <h5 className="font-medium text-gray-900">Runners</h5>
                            
                            {/* Individual Accounts */}
                            <div>
                              <div className="flex items-center justify-between mb-2">
                                <label className="block text-sm font-medium text-gray-700">
                                  Individual Accounts
                                </label>
                                {watchedSteps[index]?.account_ids?.length > 0 && (
                                  <Button
                                    type="button"
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => removeAllAccountsFromStep(index)}
                                    className="text-red-600 hover:text-red-700 hover:bg-red-50"
                                  >
                                    <Trash2 className="h-4 w-4 mr-1" />
                                    Remove All
                                  </Button>
                                )}
                              </div>
                              
                              {/* Selected Accounts - handled by AccountAutocomplete component */}
                              
                              {/* Account Autocomplete */}
                              <AccountAutocomplete
                                selectedAccountIds={watchedSteps[index]?.account_ids || []}
                                onAccountSelect={(accountId) => addAccountToStep(index, { id: accountId })}
                                onAccountRemove={(accountId) => removeAccountFromStep(index, accountId)}
                                placeholder="Search accounts by username, email, or ID..."
                                maxHeight="200px"
                              />
                            </div>

                            {/* Clusters */}
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-2">
                                Clusters
                              </label>
                              
                              {/* Selected Clusters */}
                              <div className="mb-3">
                                {watchedSteps[index]?.cluster_ids?.map((clusterId: number) => {
                                  const cluster = getClusterById(clusterId);
                                  if (!cluster) return null;
                                  
                                  return (
                                    <span
                                      key={clusterId}
                                      className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 text-green-800 text-sm rounded-md mr-2 mb-2"
                                    >
                                      {cluster.name} ({cluster.user_count} users)
                                      <button
                                        type="button"
                                        onClick={() => removeClusterFromStep(index, clusterId)}
                                        className="text-green-600 hover:text-green-800"
                                      >
                                        <X className="h-3 w-3" />
                                      </button>
                                    </span>
                                  );
                                })}
                              </div>
                              
                              {/* Search Input */}
                              <div className="relative">
                                <div className="relative">
                                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                                  <input
                                    type="text"
                                    placeholder="Search by cluster name or ID..."
                                    value={clusterSearchTerms[index] || ''}
                                    onChange={(e) => {
                                      const value = e.target.value;
                                      setClusterSearchTerms(prev => ({ ...prev, [index]: value }));
                                      setShowClusterSuggestions(prev => ({ ...prev, [index]: value.length > 0 }));
                                      // Reset selection when typing
                                      setSelectedClusterSuggestionIndex(prev => ({ ...prev, [index]: -1 }));
                                    }}
                                    onFocus={() => {
                                      if (clusterSearchTerms[index]) {
                                        setShowClusterSuggestions(prev => ({ ...prev, [index]: true }));
                                      }
                                    }}
                                    onKeyDown={(e) => handleClusterKeyDown(index, e)}
                                    className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
                                  />
                                </div>
                                
                                {/* Suggestions Dropdown */}
                                {showClusterSuggestions[index] && clusterSearchTerms[index] && (
                                  <div className="suggestions-container absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-48 overflow-y-auto">
                                    {getFilteredClusters(clusterSearchTerms[index], index).map((cluster: any, suggestionIndex: number) => {
                                      const isSelected = selectedClusterSuggestionIndex[index] === suggestionIndex;
                                      return (
                                        <button
                                          key={cluster.id}
                                          type="button"
                                          onClick={() => addClusterToStep(index, cluster)}
                                          className={`w-full px-3 py-2 text-left focus:outline-none ${
                                            isSelected 
                                              ? 'bg-primary-100 text-primary-900' 
                                              : 'hover:bg-gray-100 focus:bg-gray-100'
                                          }`}
                                        >
                                          <div className="text-sm text-gray-900">{cluster.name}</div>
                                          <div className="text-xs text-gray-500">{cluster.user_count} users (ID: {cluster.id})</div>
                                        </button>
                                      );
                                    })}
                                    {getFilteredClusters(clusterSearchTerms[index], index).length === 0 && (
                                      <div className="px-3 py-2 text-sm text-gray-500">
                                        No clusters found
                                      </div>
                                    )}
                                  </div>
                                )}
                              </div>
                            </div>
                            
                            {/* Async Execution */}
                            <div className="col-span-1">
                              <div className="flex items-center">
                                <input
                                  type="checkbox"
                                  id={`steps.${index}.is_async`}
                                  {...register(`steps.${index}.is_async`)}
                                  defaultChecked={true}
                                  className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                                />
                                <label htmlFor={`steps.${index}.is_async`} className="ml-2 block text-sm text-gray-900">
                                  Execute asynchronously
                                </label>
                              </div>
                            </div>
                          </div>

              {/* Action Parameters */}
                          {watchedSteps[index]?.action_type && (
                            <div className="space-y-4">
                              <h5 className="font-medium text-gray-900">Action Parameters</h5>
                              <div className="space-y-3">
                                {(() => {
                                  const actionType = watchedSteps[index].action_type;
                                  
                                  // Check if we have friendly parameters for this action
                                  const friendlyActions = ['buy_upgrade', 'sabotage', 'purchase_training', 'purchase_armory', 'set_credit_saving', 'update_armory_preferences'];
                                  if (friendlyActions.includes(actionType)) {
                                    return (
                                      <FriendlyActionParameters 
                                        actionType={actionType} 
                                        stepIndex={index}
                                        register={register}
                                        setValue={setValue}
                                        watch={watch}
                                      />
                                    );
                                  }

                                  // Fall back to generic parameter handling
                                  const actionInfo = getActionTypeInfo(actionType);
                                  if (!actionInfo || !actionInfo.parameter_details) {
                                    return (
                                      <div className="text-sm text-gray-500 italic">
                                        No parameters required for this action type.
                                      </div>
                                    );
                                  }

                                  return Object.entries(actionInfo.parameter_details).map(([paramName, paramInfo]: [string, any]) => {
                                    const isRequired = actionInfo.required_parameters?.includes(paramName) || false;
                                    
                                    return (
                                      <div key={paramName} className="space-y-1">
                                        <label className="block text-sm font-medium text-gray-700">
                                          {paramName}
                                          {isRequired && (
                                            <span className="text-red-500 ml-1">*</span>
                                          )}
                                        </label>
                                        
                                        {paramInfo.type === 'string' && (
                                          <input
                                            type="text"
                                            {...register(`steps.${index}.parameters.${paramName}`, {
                                              required: isRequired ? `${paramName} is required` : false,
                                            })}
                                            className={`block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm ${
                                              errors.steps?.[index]?.parameters?.[paramName] 
                                                ? 'border-red-300 focus:ring-red-500 focus:border-red-500' 
                                                : 'border-gray-300'
                                            }`}
                                            placeholder={paramInfo.description || `Enter ${paramName}`}
                                          />
                                        )}
                                        
                                        {(paramInfo.type === 'number' || paramInfo.type === 'integer' || paramInfo.type === 'float') && (
                                          <input
                                            type="number"
                                            {...register(`steps.${index}.parameters.${paramName}`, {
                                              valueAsNumber: true,
                                              required: isRequired ? `${paramName} is required` : false,
                                            })}
                                            className={`block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm ${
                                              errors.steps?.[index]?.parameters?.[paramName] 
                                                ? 'border-red-300 focus:ring-red-500 focus:border-red-500' 
                                                : 'border-gray-300'
                                            }`}
                                            placeholder={paramInfo.description || `Enter ${paramName}`}
                                          />
                                        )}
                                        
                                        {paramInfo.type === 'boolean' && (
                                          <div className="flex items-center">
                                            <input
                                              type="checkbox"
                                              {...register(`steps.${index}.parameters.${paramName}`)}
                                              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                                            />
                                            <label className="ml-2 block text-sm text-gray-900">
                                              {paramInfo.description || paramName}
                                            </label>
                                          </div>
                                        )}
                                        
                                        {paramInfo.type === 'select' && paramInfo.options && (
                                          <select
                                            {...register(`steps.${index}.parameters.${paramName}`, {
                                              required: isRequired ? `${paramName} is required` : false,
                                            })}
                                            className={`block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm ${
                                              errors.steps?.[index]?.parameters?.[paramName] 
                                                ? 'border-red-300 focus:ring-red-500 focus:border-red-500' 
                                                : 'border-gray-300'
                                            }`}
                                          >
                                            <option value="">Select {paramName}</option>
                                            {paramInfo.options.map((option: any) => (
                                              <option key={option.value || option} value={option.value || option}>
                                                {option.label || option}
                                              </option>
                                            ))}
                                          </select>
                                        )}
                                        
                                        {paramInfo.type === 'object' && (
                                          <div className="space-y-2">
                                            <textarea
                                              {...register(`steps.${index}.parameters.${paramName}`, {
                                                required: isRequired ? `${paramName} is required` : false,
                                                validate: (value) => {
                                                  if (!value) return isRequired ? `${paramName} is required` : true;
                                                  try {
                                                    const parsed = JSON.parse(value);
                                                    if (typeof parsed !== 'object' || Array.isArray(parsed)) {
                                                      return 'Must be a valid JSON object';
                                                    }
                                                    return true;
                                                  } catch {
                                                    return 'Must be valid JSON';
                                                  }
                                                }
                                              })}
                                              className={`block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm font-mono text-sm ${
                                                errors.steps?.[index]?.parameters?.[paramName] 
                                                  ? 'border-red-300 focus:ring-red-500 focus:border-red-500' 
                                                  : 'border-gray-300'
                                              }`}
                                              placeholder={paramInfo.description || `Enter ${paramName} as JSON object`}
                                              rows={4}
                                            />
                                            <div className="text-xs text-gray-500">
                                              <p>Enter as JSON object, e.g.:</p>
                                              <p className="font-mono bg-gray-100 p-1 rounded">
                                                {paramName.includes('weapon') 
                                                  ? '{"dagger": 30, "blade": 25, "shield": 20, "excalibur": 15, "maul": 10}'
                                                  : paramName.includes('soldier')
                                                  ? '{"infantry": 40, "archer": 35, "cavalry": 25}'
                                                  : '{"key1": "value1", "key2": "value2"}'
                                                }
                                              </p>
                                              {paramName.includes('weapon') && (
                                                <p className="mt-1 text-xs text-blue-600">
                                                  Available weapons: dagger, maul, blade, excalibur, sai, shield, mithril, dragonskin, cloak, hook, pickaxe, horn, guard_dog, torch
                                                </p>
                                              )}
                                            </div>
                                          </div>
                                        )}
                                        
                                        {paramInfo.description && (
                                          <p className="text-xs text-gray-500">{paramInfo.description}</p>
                                        )}
                                        
                                        {errors.steps?.[index]?.parameters?.[paramName] && (
                                          <p className="text-xs text-red-600">
                                            {String(errors.steps[index]?.parameters?.[paramName]?.message || 'Invalid value')}
                                          </p>
                                        )}
                                      </div>
                                    );
                                  });
                                })()}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Old Detailed Step Forms - Removed since we now have inline editing */}
          {false && fields.map((field, index) => (
            <div key={field.id} className="border border-gray-200 rounded-lg p-4 space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="font-medium text-gray-900">Step {index + 1}</h4>
                {fields.length > 1 && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => removeStep(index)}
                    className="text-red-600 hover:text-red-700"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Action Type
                  </label>
                  <select
                    {...register(`steps.${index}.action_type`, {
                      required: 'Action type is required',
                    })}
                    onChange={(e) => {
                      // Clear parameters when action type changes
                      setValue(`steps.${index}.parameters`, {});
                      // Trigger the register onChange as well
                      register(`steps.${index}.action_type`).onChange(e);
                    }}
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                  >
                    <option value="">Select action type</option>
                    {actionTypesData?.categories && Object.entries(actionTypesData.categories).map(([category, actions]) => (
                      <optgroup key={category} label={category.replace('_', ' ').toUpperCase()}>
                        {actions.map((action) => (
                          <option key={action.action_type} value={action.action_type}>
                            {action.action_type} - {action.description}
                          </option>
                        ))}
                      </optgroup>
                    ))}
                  </select>
                  {errors.steps?.[index]?.action_type && (
                    <p className="mt-1 text-sm text-red-600">
                      {errors.steps[index]?.action_type?.message}
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Max Retries
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="10"
                    {...register(`steps.${index}.max_retries`, {
                      valueAsNumber: true,
                      min: { value: 0, message: 'Must be 0 or greater' },
                      max: { value: 10, message: 'Must be 10 or less' },
                    })}
                    className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                  />
                  {errors.steps?.[index]?.max_retries && (
                    <p className="mt-1 text-sm text-red-600">
                      {errors.steps[index]?.max_retries?.message}
                    </p>
                  )}
                </div>
              </div>

              {/* Target Selection */}
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Target Accounts
                  </label>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Individual Accounts selection removed - now handled by AccountAutocomplete component */}

                    <div>
                      <label className="block text-sm text-gray-600 mb-1">
                        <Users className="h-4 w-4 inline mr-1" />
                        Clusters
                      </label>
                      <select
                        multiple
                        {...register(`steps.${index}.cluster_ids`)}
                        className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                        size={4}
                      >
                        {clustersData?.data.map((cluster) => (
                          <option key={cluster.id} value={cluster.id}>
                            {cluster.name} ({cluster.user_count} members)
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  
                  {(() => {
                    const selection = getSelectedAccounts(index);
                    const totalSelected = selection.totalIndividual + selection.totalClusters;
                    return totalSelected > 0 && (
                      <div className="mt-2 p-2 bg-blue-50 rounded-md">
                        <p className="text-sm text-blue-800">
                          <strong>Targeting:</strong> {selection.totalIndividual} individual account{selection.totalIndividual !== 1 ? 's' : ''}
                          {selection.totalClusters > 0 && (
                            <span>, {selection.totalClusters} cluster{selection.totalClusters !== 1 ? 's' : ''}</span>
                          )}
                        </p>
                        <p className="text-xs text-blue-600 mt-1">
                          Note: Cluster member counts will be resolved when the job executes
                        </p>
                      </div>
                    );
                  })()}
                </div>
              </div>

              {/* Action Type Info */}
              {watchedSteps[index]?.action_type && (
                <div className="p-3 bg-gray-50 rounded-md">
                  <h5 className="font-medium text-gray-900 mb-1">Action Information</h5>
                  {(() => {
                    const actionInfo = getActionTypeInfo(watchedSteps[index].action_type);
                    return actionInfo ? (
                      <div className="text-sm text-gray-600">
                        <p><strong>Description:</strong> {actionInfo.description}</p>
                        <p><strong>Category:</strong> {actionInfo.category}</p>
                        {actionInfo.required_parameters && actionInfo.required_parameters.length > 0 && (
                          <p><strong>Required Parameters:</strong> {actionInfo.required_parameters.join(', ')}</p>
                        )}
                      </div>
                    ) : null;
                  })()}
                </div>
              )}

              {/* Action Parameters */}
              {watchedSteps[index]?.action_type && (
                <div className="space-y-4">
                  <h5 className="font-medium text-gray-900">Action Parameters</h5>
                  <div className="space-y-3">
                    {(() => {
                      const actionInfo = getActionTypeInfo(watchedSteps[index].action_type);
                      if (!actionInfo || !actionInfo.parameter_details) {
                        return (
                          <div className="text-sm text-gray-500 italic">
                            No parameters required for this action type.
                          </div>
                        );
                      }

                      return Object.entries(actionInfo.parameter_details).map(([paramName, paramInfo]: [string, any]) => {
                        const isRequired = actionInfo.required_parameters?.includes(paramName) || false;
                        
                        return (
                          <div key={paramName} className="space-y-1">
                            <label className="block text-sm font-medium text-gray-700">
                              {paramName}
                              {isRequired && (
                                <span className="text-red-500 ml-1">*</span>
                              )}
                            </label>
                            
                            {paramInfo.type === 'string' && (
                              <input
                                type="text"
                                {...register(`steps.${index}.parameters.${paramName}`, {
                                  required: isRequired ? `${paramName} is required` : false,
                                })}
                                className={`block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm ${
                                  errors.steps?.[index]?.parameters?.[paramName] 
                                    ? 'border-red-300 focus:ring-red-500 focus:border-red-500' 
                                    : 'border-gray-300'
                                }`}
                                placeholder={paramInfo.description || `Enter ${paramName}`}
                              />
                            )}
                            
                            {(paramInfo.type === 'number' || paramInfo.type === 'integer' || paramInfo.type === 'float') && (
                              <input
                                type="number"
                                {...register(`steps.${index}.parameters.${paramName}`, {
                                  valueAsNumber: true,
                                  required: isRequired ? `${paramName} is required` : false,
                                })}
                                className={`block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm ${
                                  errors.steps?.[index]?.parameters?.[paramName] 
                                    ? 'border-red-300 focus:ring-red-500 focus:border-red-500' 
                                    : 'border-gray-300'
                                }`}
                                placeholder={paramInfo.description || `Enter ${paramName}`}
                              />
                            )}
                            
                            {paramInfo.type === 'boolean' && (
                              <div className="flex items-center">
                                <input
                                  type="checkbox"
                                  {...register(`steps.${index}.parameters.${paramName}`)}
                                  className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                                />
                                <label className="ml-2 block text-sm text-gray-900">
                                  {paramInfo.description || paramName}
                                </label>
                              </div>
                            )}
                            
                            {paramInfo.type === 'select' && paramInfo.options && (
                              <select
                                {...register(`steps.${index}.parameters.${paramName}`, {
                                  required: isRequired ? `${paramName} is required` : false,
                                })}
                                className={`block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm ${
                                  errors.steps?.[index]?.parameters?.[paramName] 
                                    ? 'border-red-300 focus:ring-red-500 focus:border-red-500' 
                                    : 'border-gray-300'
                                }`}
                              >
                                <option value="">Select {paramName}</option>
                                {paramInfo.options.map((option: any) => (
                                  <option key={option.value || option} value={option.value || option}>
                                    {option.label || option}
                                  </option>
                                ))}
                              </select>
                            )}
                            
                            {paramInfo.type === 'object' && (
                              <div className="space-y-2">
                                <textarea
                                  {...register(`steps.${index}.parameters.${paramName}`, {
                                    required: isRequired ? `${paramName} is required` : false,
                                    validate: (value) => {
                                      if (!value) return isRequired ? `${paramName} is required` : true;
                                      try {
                                        const parsed = JSON.parse(value);
                                        if (typeof parsed !== 'object' || Array.isArray(parsed)) {
                                          return 'Must be a valid JSON object';
                                        }
                                        return true;
                                      } catch {
                                        return 'Must be valid JSON';
                                      }
                                    }
                                  })}
                                  className={`block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm font-mono text-sm ${
                                    errors.steps?.[index]?.parameters?.[paramName] 
                                      ? 'border-red-300 focus:ring-red-500 focus:border-red-500' 
                                      : 'border-gray-300'
                                  }`}
                                  placeholder={paramInfo.description || `Enter ${paramName} as JSON object`}
                                  rows={4}
                                />
                                <div className="text-xs text-gray-500">
                                  <p>Enter as JSON object, e.g.:</p>
                                  <p className="font-mono bg-gray-100 p-1 rounded">
                                    {paramName.includes('weapon') 
                                      ? '{"dagger": 30, "blade": 25, "shield": 20, "excalibur": 15, "maul": 10}'
                                      : paramName.includes('soldier')
                                      ? '{"infantry": 40, "archer": 35, "cavalry": 25}'
                                      : '{"key1": "value1", "key2": "value2"}'
                                    }
                                  </p>
                                  {paramName.includes('weapon') && (
                                    <p className="mt-1 text-xs text-blue-600">
                                      Available weapons: dagger, maul, blade, excalibur, sai, shield, mithril, dragonskin, cloak, hook, pickaxe, horn, guard_dog, torch
                                    </p>
                                  )}
                                </div>
                              </div>
                            )}
                            
                            {paramInfo.description && (
                              <p className="text-xs text-gray-500">{paramInfo.description}</p>
                            )}
                            
                            {errors.steps?.[index]?.parameters?.[paramName] && (
                              <p className="text-xs text-red-600">
                                {String(errors.steps[index]?.parameters?.[paramName]?.message || 'Invalid value')}
                              </p>
                            )}
                          </div>
                        );
                      });
                    })()}
                  </div>
                </div>
              )}
            </div>
          ))}

        </div>

        {/* Form Actions */}
        <div className="flex justify-between pt-4 border-t">
          <Button
            type="button"
            variant="secondary"
            onClick={() => setShowFavoriteModal(true)}
            disabled={isLoading}
            className="flex items-center gap-2"
          >
            <Star className="h-4 w-4" />
            Save as Favorite
          </Button>
          
          <div className="flex gap-3">
            <Button
              type="button"
              variant="secondary"
              onClick={onClose}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              loading={isLoading}
              disabled={isLoading}
            >
              Create Job
            </Button>
          </div>
        </div>
      </form>

      {/* Favorite Job Modal */}
      <Modal
        isOpen={showFavoriteModal}
        onClose={() => setShowFavoriteModal(false)}
        title="Save as Favorite Job"
      >
        <form onSubmit={handleSubmit(handleSaveAsFavorite)} className="space-y-4">
          <div>
            <label htmlFor="favoriteName" className="block text-sm font-medium text-gray-700 mb-1">
              Favorite Name *
            </label>
            <Input
              id="favoriteName"
              type="text"
              value={favoriteName}
              onChange={(e) => setFavoriteName(e.target.value)}
              placeholder="Enter a name for this favorite job"
              required
            />
          </div>

          <div>
            <label htmlFor="favoriteDescription" className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              id="favoriteDescription"
              value={favoriteDescription}
              onChange={(e) => setFavoriteDescription(e.target.value)}
              placeholder="Enter a description (optional)"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              rows={3}
            />
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setShowFavoriteModal(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={!favoriteName.trim()}
            >
              Save Favorite
            </Button>
          </div>
        </form>
      </Modal>
    </Modal>
  );
};

export default JobForm;
