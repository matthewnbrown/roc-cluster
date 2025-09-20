import React from 'react';
import { useForm } from 'react-hook-form';
import { ClusterListResponse, ClusterResponse } from '../types/api';
import { useCreateCluster, useUpdateCluster } from '../hooks/useClusters';
import Button from './ui/Button';
import Input from './ui/Input';
import Modal from './ui/Modal';

interface ClusterFormProps {
  isOpen: boolean;
  onClose: () => void;
  cluster?: ClusterListResponse | ClusterResponse; // If provided, we're editing; if not, we're creating
}

interface FormData {
  name: string;
  description: string;
}

const ClusterForm: React.FC<ClusterFormProps> = ({ isOpen, onClose, cluster }) => {
  const isEditing = !!cluster;
  const createClusterMutation = useCreateCluster();
  const updateClusterMutation = useUpdateCluster();

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<FormData>({
    defaultValues: {
      name: cluster?.name || '',
      description: cluster?.description || '',
    },
  });

  React.useEffect(() => {
    if (cluster) {
      reset({
        name: cluster.name,
        description: cluster.description || '',
      });
    } else {
      reset({
        name: '',
        description: '',
      });
    }
  }, [cluster, reset]);

  const onSubmit = async (data: FormData) => {
    try {
      if (isEditing && cluster) {
        await updateClusterMutation.mutateAsync({
          id: cluster.id,
          data: {
            name: data.name,
            description: data.description || undefined,
          },
        });
      } else {
        await createClusterMutation.mutateAsync({
          name: data.name,
          description: data.description || undefined,
        });
      }
      
      onClose();
    } catch (error) {
      console.error('Failed to save cluster:', error);
    }
  };

  const isLoading = createClusterMutation.isLoading || updateClusterMutation.isLoading;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEditing ? 'Edit Cluster' : 'Create New Cluster'}
      size="md"
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Input
          label="Cluster Name"
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
          placeholder="Enter cluster name"
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
            {isEditing ? 'Update Cluster' : 'Create Cluster'}
          </Button>
        </div>
      </form>
    </Modal>
  );
};

export default ClusterForm;
