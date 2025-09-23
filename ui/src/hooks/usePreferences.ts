import { useQuery, useMutation, useQueryClient } from 'react-query';
import { armoryApi } from '../services/api';
import { 
  ArmoryPreferences, 
  ArmoryPreferencesCreate, 
  ArmoryPreferencesUpdate,
  TrainingPreferences,
  TrainingPreferencesCreate,
  TrainingPreferencesUpdate,
  Weapon,
  SoldierType,
  ActionResponse
} from '../types/api';

// Armory Preferences Hooks
export const useArmoryPreferences = (accountId: number) => {
  return useQuery<ArmoryPreferences>(
    ['armory-preferences', accountId],
    () => armoryApi.getArmoryPreferences(accountId),
    {
      enabled: !!accountId,
      retry: 1,
    }
  );
};

export const useCreateArmoryPreferences = () => {
  const queryClient = useQueryClient();
  
  return useMutation<ArmoryPreferences, Error, ArmoryPreferencesCreate>(
    (preferencesData) => armoryApi.createArmoryPreferences(preferencesData),
    {
      onSuccess: (data) => {
        queryClient.invalidateQueries(['armory-preferences', data.account_id]);
      },
    }
  );
};

export const useUpdateArmoryPreferences = () => {
  const queryClient = useQueryClient();
  
  return useMutation<ArmoryPreferences, Error, { accountId: number; data: ArmoryPreferencesUpdate }>(
    ({ accountId, data }) => armoryApi.updateArmoryPreferences(accountId, data),
    {
      onSuccess: (data) => {
        queryClient.invalidateQueries(['armory-preferences', data.account_id]);
      },
    }
  );
};

export const useDeleteArmoryPreferences = () => {
  const queryClient = useQueryClient();
  
  return useMutation<void, Error, number>(
    (accountId) => armoryApi.deleteArmoryPreferences(accountId),
    {
      onSuccess: (_, accountId) => {
        queryClient.invalidateQueries(['armory-preferences', accountId]);
      },
    }
  );
};

// Training Preferences Hooks
export const useTrainingPreferences = (accountId: number) => {
  return useQuery<TrainingPreferences>(
    ['training-preferences', accountId],
    () => armoryApi.getTrainingPreferences(accountId),
    {
      enabled: !!accountId,
      retry: 1,
    }
  );
};

export const useCreateTrainingPreferences = () => {
  const queryClient = useQueryClient();
  
  return useMutation<TrainingPreferences, Error, TrainingPreferencesCreate>(
    (preferencesData) => armoryApi.createTrainingPreferences(preferencesData),
    {
      onSuccess: (data) => {
        queryClient.invalidateQueries(['training-preferences', data.account_id]);
      },
    }
  );
};

export const useUpdateTrainingPreferences = () => {
  const queryClient = useQueryClient();
  
  return useMutation<TrainingPreferences, Error, { accountId: number; data: TrainingPreferencesUpdate }>(
    ({ accountId, data }) => armoryApi.updateTrainingPreferences(accountId, data),
    {
      onSuccess: (data) => {
        queryClient.invalidateQueries(['training-preferences', data.account_id]);
      },
    }
  );
};

export const useDeleteTrainingPreferences = () => {
  const queryClient = useQueryClient();
  
  return useMutation<void, Error, number>(
    (accountId) => armoryApi.deleteTrainingPreferences(accountId),
    {
      onSuccess: (_, accountId) => {
        queryClient.invalidateQueries(['training-preferences', accountId]);
      },
    }
  );
};

// Reference Data Hooks
export const useWeapons = () => {
  return useQuery<Weapon[]>(
    ['weapons'],
    () => armoryApi.getWeapons(),
    {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
    }
  );
};

export const useSoldierTypes = () => {
  return useQuery<SoldierType[]>(
    ['soldier-types'],
    () => armoryApi.getSoldierTypes(),
    {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
    }
  );
};

// Armory Purchase Hook
export const usePurchaseArmoryByPreferences = () => {
  const queryClient = useQueryClient();
  
  return useMutation<ActionResponse, Error, number>(
    (accountId) => armoryApi.purchaseArmoryByPreferences(accountId),
    {
      onSuccess: (_, accountId) => {
        // Invalidate account metadata to refresh gold amounts
        queryClient.invalidateQueries(['account-metadata', accountId]);
      },
    }
  );
};
