import React, { useState, useEffect } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { useQueryClient, useQuery } from 'react-query';
import { useCreateJob, useValidActionTypes, useJob, useJobs, jobKeys } from '../hooks/useJobs';
import { useClusters } from '../hooks/useClusters';
import { useFavoriteJobs } from '../hooks/useFavoriteJobs';
import { JobCreateRequest, JobStepRequest, ActionType, JobResponse, ValidationError } from '../types/api';
import { jobsApi, getValidationErrors, getValidationErrorsByStep } from '../services/api';
import Button from './ui/Button';
import Input from './ui/Input';
import Modal from './ui/Modal';
import AccountAutocomplete from './AccountAutocomplete';
import SortableStepList from './SortableStepList';
import { Plus, Trash2, Users, User, ChevronDown, ChevronRight, EyeOff, Search, X, Star, Copy } from 'lucide-react';
import FriendlyActionParameters from './FriendlyActionParameters';
import ValidationErrorDisplay from './ValidationErrorDisplay';

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
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([]);
  const [errorsByStep, setErrorsByStep] = useState<{ [stepIndex: number]: ValidationError[] }>({});

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
    reset,
    watch,
    setValue,
    getValues,
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
          is_async: false,
          parameters: {},
        },
      ],
    },
  });

  const { fields, append, remove, replace, insert } = useFieldArray({
    control,
    name: 'steps',
  });

  const watchedSteps = watch('steps');

  // Note: Removed automatic reset on modal close to preserve user's work
  // Form will only reset when explicitly creating a job or canceling

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
          original_account_ids: (step as any).original_account_ids || (step as any).account_ids || [],
          original_cluster_ids: (step as any).original_cluster_ids || (step as any).cluster_ids || [],
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

  // Clear validation errors when modal is closed
  useEffect(() => {
    if (!isOpen) {
      setValidationErrors([]);
      setErrorsByStep({});
    }
  }, [isOpen]);

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
    // Clear any previous validation errors
    setValidationErrors([]);
    setErrorsByStep({});
    
    try {
      // Generate job name and description if not provided
      let jobName = data.name;
      let jobDescription = data.description;
      
      if (!jobName || jobName.trim() === '') {
        // Generate a random GUID for the job name
        jobName = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
          const r = Math.random() * 16 | 0;
          const v = c === 'x' ? r : (r & 0x3 | 0x8);
          return v.toString(16);
        });
        
        // Create CSV description from step action types
        const stepNames = data.steps
          .map(step => step.action_type)
          .filter(actionType => actionType && actionType.trim() !== '')
          .join(', ');
        
        jobDescription = stepNames || 'No steps defined';
      }
      
      const jobData: JobCreateRequest = {
        name: jobName,
        description: jobDescription || undefined,
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
      // Reset the form to clear all fields with explicit default values
      reset({
        name: '',
        description: '',
        parallel_execution: false,
        steps: [
          {
            action_type: '',
            account_ids: [],
            cluster_ids: [],
            max_retries: 0,
            is_async: false,
            parameters: {},
          },
        ],
      });
      setValidationErrors([]);
      onClose();
    } catch (error) {
      console.error('Failed to create job:', error);
      
      // Check if this is a validation error
      const validationErrors = getValidationErrors(error);
      if (validationErrors.length > 0) {
        setValidationErrors(validationErrors);
        setErrorsByStep(getValidationErrorsByStep(validationErrors));
        
        // Scroll to the first step with an error
        const errorsByStep = getValidationErrorsByStep(validationErrors);
        const firstErrorStepIndex = Math.min(...Object.keys(errorsByStep).map(Number));
        const stepElement = document.getElementById(`step-${firstErrorStepIndex}`);
        if (stepElement) {
          stepElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }
    }
  };

  const addStep = () => {
    append({
      action_type: '',
      account_ids: [],
      cluster_ids: [],
      max_retries: 0,
      is_async: false,
      parameters: {},
    });
  };

  const removeStep = (index: number) => {
    if (fields.length > 1) {
      remove(index);
    }
  };

  const duplicateStep = (index: number) => {
    const stepToDuplicate = fields[index];
    if (stepToDuplicate) {
      // Insert the duplicated step right after the current step
      insert(index + 1, {
        action_type: stepToDuplicate.action_type,
        account_ids: [...(stepToDuplicate.account_ids || [])],
        cluster_ids: [...(stepToDuplicate.cluster_ids || [])],
        original_account_ids: stepToDuplicate.original_account_ids ? [...stepToDuplicate.original_account_ids] : undefined,
        original_cluster_ids: stepToDuplicate.original_cluster_ids ? [...stepToDuplicate.original_cluster_ids] : undefined,
        parameters: stepToDuplicate.parameters ? { ...stepToDuplicate.parameters } : {},
        max_retries: stepToDuplicate.max_retries,
        is_async: stepToDuplicate.is_async,
      });
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

  const handleFavoriteFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!favoriteName.trim()) {
      return;
    }

    try {
      // Get the current form data
      const currentFormData = getValues();
      
      // Create the job data from current form
      const jobData: JobCreateRequest = {
        name: currentFormData.name,
        description: currentFormData.description || undefined,
        parallel_execution: currentFormData.parallel_execution,
        steps: currentFormData.steps.map((step) => {
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
    // Check account_ids first (current form state), then fall back to original_account_ids (cloned data)
    const individualAccounts = step.account_ids || step.original_account_ids || [];
    const clusterCount = step.cluster_ids?.length || 0;
    
    return {
      individualAccounts,
      clusterCount,
      totalIndividual: individualAccounts.length,
      totalClusters: clusterCount
    };
  };

  const isLoading = createJobMutation.isLoading;

  const handleCancel = () => {
    // Reset the form to clear all fields with explicit default values
    reset({
      name: '',
      description: '',
      parallel_execution: false,
      steps: [
        {
          action_type: '',
          account_ids: [],
          cluster_ids: [],
          max_retries: 0,
          is_async: false,
          parameters: {},
        },
      ],
    });
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Create Job"
      size="2xl"
    >
      <div className="flex flex-col min-h-0">
        {/* Fixed Header - Job Info */}
        <div className="flex-shrink-0 space-y-4 pb-4 border-b border-gray-200">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div>
              <Input
                label="Job Name"
                {...register('name', {
                  minLength: {
                    value: 2,
                    message: 'Job name must be at least 2 characters',
                  },
                })}
                error={errors.name?.message}
                placeholder="Enter job name (optional - will auto-generate if empty)"
              />
            </div>
            
            <div className="flex items-start pt-6">
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
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              {...register('description')}
              className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
              placeholder="Enter job description (optional)"
              rows={2}
            />
          </div>
        </div>

        {/* Job Steps Header */}
        <div className="flex-shrink-0 flex items-center justify-between py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">
            Job Steps ({fields.length})
            {Object.keys(errorsByStep).length > 0 && (
              <span className="ml-2 inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                {Object.keys(errorsByStep).length} error{Object.keys(errorsByStep).length !== 1 ? 's' : ''}
              </span>
            )}
          </h3>
          <Button
            type="button"
            variant="secondary"
            onClick={addStep}
            className="flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            Add Step
          </Button>
        </div>

        {/* Scrollable Content - Job Steps */}
        <div className="flex-1 overflow-y-auto py-4 min-h-0 max-h-[calc(90vh-150px)]">
          <form onSubmit={handleSubmit(onSubmit)}>
            <ValidationErrorDisplay 
              errors={validationErrors} 
              onClose={() => setValidationErrors([])} 
            />
            <SortableStepList
              fields={fields}
              watchedSteps={watchedSteps}
              editingStepIndex={editingStepIndex}
              setEditingStepIndex={setEditingStepIndex}
              duplicateStep={duplicateStep}
              removeStep={removeStep}
              getActionTypeInfo={getActionTypeInfo}
              getSelectedAccounts={getSelectedAccounts}
              setValue={setValue}
              register={register}
              errors={errors}
              watch={watch}
              clustersData={clustersData}
              actionTypesData={actionTypesData}
              clusterSearchTerms={clusterSearchTerms}
              setClusterSearchTerms={setClusterSearchTerms}
              showClusterSuggestions={showClusterSuggestions}
              setShowClusterSuggestions={setShowClusterSuggestions}
              selectedClusterSuggestionIndex={selectedClusterSuggestionIndex}
              setSelectedClusterSuggestionIndex={setSelectedClusterSuggestionIndex}
              getFilteredClusters={getFilteredClusters}
              addClusterToStep={addClusterToStep}
              removeClusterFromStep={removeClusterFromStep}
              getClusterById={getClusterById}
              handleClusterKeyDown={handleClusterKeyDown}
              errorsByStep={errorsByStep}
            />
          </form>
        </div>

        {/* Fixed Footer - Form Actions */}
        <div className="flex-shrink-0 flex justify-between pt-4 border-t border-gray-200">
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
              onClick={handleCancel}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button
              type="button"
              onClick={handleSubmit(onSubmit)}
              loading={isLoading}
              disabled={isLoading}
            >
              Create Job
            </Button>
          </div>
        </div>
      </div>

      {/* Favorite Job Modal */}
      <Modal
        isOpen={showFavoriteModal}
        onClose={() => setShowFavoriteModal(false)}
        title="Save as Favorite Job"
      >
        <form onSubmit={handleFavoriteFormSubmit} className="space-y-4">
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
