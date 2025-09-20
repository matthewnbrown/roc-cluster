import React from 'react';
import { useForm } from 'react-hook-form';
import { ClusterListResponse, ClusterResponse } from '../types/api';
import { useCloneCluster } from '../hooks/useClusters';
import Button from './ui/Button';
import Input from './ui/Input';
import Modal from './ui/Modal';

interface ClusterCloneFormProps {
  isOpen: boolean;
  onClose: () => void;
  sourceCluster: ClusterListResponse | ClusterResponse;
}

interface FormData {
  name: string;
  description: string;
  includeUsers: boolean;
}

const ClusterCloneForm: React.FC<ClusterCloneFormProps> = ({ 
  isOpen, 
  onClose, 
  sourceCluster 
}) => {
  const cloneClusterMutation = useCloneCluster();

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    watch,
    setValue,
  } = useForm<FormData>({
    defaultValues: {
      name: '',
      description: '',
      includeUsers: true,
    },
    mode: 'onChange', // Validate on change instead of on submit
  });

  const includeUsers = watch('includeUsers');

  React.useEffect(() => {
    if (sourceCluster) {
      // Only set the name if it's empty (first time opening)
      setValue('description', sourceCluster.description || '');
      setValue('includeUsers', true);
    }
  }, [sourceCluster, setValue]);

  const onSubmit = async (data: FormData) => {
    console.log('Form data:', data);
    console.log('Form errors:', errors);
    
    // Check if there are any validation errors
    if (Object.keys(errors).length > 0) {
      console.log('Form has validation errors, not submitting');
      return;
    }
    
    if (!data.name || !data.name.trim()) {
      console.log('Name is empty, not submitting');
      return; // Don't submit if name is empty
    }

    const cloneData = {
      name: data.name.trim(),
      description: data.description?.trim() || undefined,
      include_users: data.includeUsers,
    };

    console.log('Sending clone data:', cloneData);
    console.log('Source cluster ID:', sourceCluster.id);

    try {
      // Use the clone endpoint which handles everything in one call
      const result = await cloneClusterMutation.mutateAsync({
        clusterId: sourceCluster.id,
        cloneData,
      });
      
      console.log('Clone successful:', result);
      onClose();
    } catch (error: any) {
      console.error('Failed to clone cluster:', error);
      console.error('Error details:', error.response?.data);
      console.error('Error status:', error.response?.status);
    }
  };

  const isLoading = cloneClusterMutation.isLoading;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Clone Cluster"
      size="md"
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
          <p className="text-sm text-blue-800">
            <strong>Cloning from:</strong> {sourceCluster.name}
          </p>
          {sourceCluster.user_count > 0 && (
            <p className="text-sm text-blue-700 mt-1">
              This cluster has {sourceCluster.user_count} member{sourceCluster.user_count !== 1 ? 's' : ''}.
            </p>
          )}
        </div>

        <Input
          label="New Cluster Name"
          {...register('name', {
            required: 'Cluster name is required',
            minLength: {
              value: 2,
              message: 'Cluster name must be at least 2 characters',
            },
            maxLength: {
              value: 100,
              message: 'Cluster name must be less than 100 characters',
            },
          })}
          error={errors.name?.message}
          placeholder={`e.g., ${sourceCluster.name} (Copy)`}
        />

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Description
          </label>
          <textarea
            {...register('description', {
              maxLength: {
                value: 500,
                message: 'Description must be less than 500 characters',
              },
            })}
            className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
            placeholder="Enter cluster description (optional)"
            rows={3}
          />
          {errors.description && (
            <p className="mt-1 text-sm text-red-600">{errors.description.message}</p>
          )}
        </div>

        <div className="flex items-center">
          <input
            type="checkbox"
            id="includeUsers"
            {...register('includeUsers')}
            className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
          />
          <label htmlFor="includeUsers" className="ml-2 block text-sm text-gray-900">
            Include users from original cluster
          </label>
        </div>

        {includeUsers && sourceCluster.user_count > 0 && (
          <div className="bg-green-50 border border-green-200 rounded-md p-3">
            <p className="text-sm text-green-800">
              <strong>Great!</strong> All {sourceCluster.user_count} member{sourceCluster.user_count !== 1 ? 's' : ''} 
              from the original cluster will be automatically added to the new cluster.
            </p>
          </div>
        )}

        <div className="flex justify-end space-x-3 pt-4">
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
            Clone Cluster
          </Button>
        </div>
      </form>
    </Modal>
  );
};

export default ClusterCloneForm;
