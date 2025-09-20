import React from 'react';
import { useForm } from 'react-hook-form';
import { Account, AccountCreate, AccountUpdate } from '../types/api';
import { useCreateAccount, useUpdateAccount } from '../hooks/useAccounts';
import Button from './ui/Button';
import Input from './ui/Input';
import Modal from './ui/Modal';

interface AccountFormProps {
  isOpen: boolean;
  onClose: () => void;
  account?: Account; // If provided, we're editing; if not, we're creating
}

interface FormData {
  username: string;
  email: string;
  password: string;
  is_active: boolean;
}

const AccountForm: React.FC<AccountFormProps> = ({ isOpen, onClose, account }) => {
  const isEditing = !!account;
  const createAccountMutation = useCreateAccount();
  const updateAccountMutation = useUpdateAccount();

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    watch,
  } = useForm<FormData>({
    defaultValues: {
      username: account?.username || '',
      email: account?.email || '',
      password: '',
      is_active: account?.is_active ?? true,
    },
  });

  const isActive = watch('is_active');

  React.useEffect(() => {
    if (account) {
      reset({
        username: account.username,
        email: account.email,
        password: '',
        is_active: account.is_active,
      });
    } else {
      reset({
        username: '',
        email: '',
        password: '',
        is_active: true,
      });
    }
  }, [account, reset]);

  const onSubmit = async (data: FormData) => {
    try {
      if (isEditing && account) {
        const updateData: AccountUpdate = {
          username: data.username,
          email: data.email,
          is_active: data.is_active,
        };
        
        // Only include password if it's provided
        if (data.password.trim()) {
          updateData.password = data.password;
        }

        await updateAccountMutation.mutateAsync({
          id: account.id,
          data: updateData,
        });
      } else {
        const createData: AccountCreate = {
          username: data.username,
          email: data.email,
          password: data.password,
        };

        await createAccountMutation.mutateAsync(createData);
      }
      
      onClose();
    } catch (error) {
      console.error('Failed to save account:', error);
    }
  };

  const isLoading = createAccountMutation.isLoading || updateAccountMutation.isLoading;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEditing ? 'Edit Account' : 'Create New Account'}
      size="md"
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Input
          label="Username"
          {...register('username', {
            required: 'Username is required',
            minLength: {
              value: 3,
              message: 'Username must be at least 3 characters',
            },
          })}
          error={errors.username?.message}
          placeholder="Enter username"
        />

        <Input
          label="Email"
          type="email"
          {...register('email', {
            required: 'Email is required',
            pattern: {
              value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
              message: 'Invalid email address',
            },
          })}
          error={errors.email?.message}
          placeholder="Enter email address"
        />

        <Input
          label={isEditing ? 'New Password (leave blank to keep current)' : 'Password'}
          type="password"
          {...register('password', {
            required: !isEditing ? 'Password is required' : false,
            minLength: {
              value: 6,
              message: 'Password must be at least 6 characters',
            },
          })}
          error={errors.password?.message}
          placeholder={isEditing ? 'Enter new password' : 'Enter password'}
        />

        <div className="flex items-center">
          <input
            type="checkbox"
            id="is_active"
            {...register('is_active')}
            className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
          />
          <label htmlFor="is_active" className="ml-2 block text-sm text-gray-900">
            Account is active
          </label>
        </div>

        {isEditing && (
          <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
            <p className="text-sm text-blue-800">
              <strong>Note:</strong> Leave the password field blank to keep the current password unchanged.
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
            {isEditing ? 'Update Account' : 'Create Account'}
          </Button>
        </div>
      </form>
    </Modal>
  );
};

export default AccountForm;
