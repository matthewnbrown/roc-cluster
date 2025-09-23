import React, { useState, useEffect } from 'react';
import { 
  useTrainingPreferences, 
  useCreateTrainingPreferences, 
  useUpdateTrainingPreferences,
  useDeleteTrainingPreferences,
  useSoldierTypes
} from '../hooks/usePreferences';
// Types are used in the component logic
import Button from './ui/Button';
import Input from './ui/Input';
import Modal from './ui/Modal';

interface TrainingPreferencesProps {
  accountId: number;
  accountUsername: string;
  onClose: () => void;
}

const TrainingPreferencesComponent: React.FC<TrainingPreferencesProps> = ({
  accountId,
  accountUsername,
  onClose,
}) => {
  const [soldierTypePercentages, setSoldierTypePercentages] = useState<Record<string, number>>({});
  // Removed isEditing state - always editable now

  const { data: preferences, isLoading: preferencesLoading, error: preferencesError } = useTrainingPreferences(accountId);
  const { data: soldierTypes, isLoading: soldierTypesLoading } = useSoldierTypes();
  const createPreferences = useCreateTrainingPreferences();
  const updatePreferences = useUpdateTrainingPreferences();
  const deletePreferences = useDeleteTrainingPreferences();

  // Initialize soldier type percentages when preferences or soldier types load
  useEffect(() => {
    if (soldierTypes) {
      const percentages: Record<string, number> = {};
      
      // Initialize with existing preferences if they exist
      if (preferences) {
        preferences.soldier_type_preferences.forEach(pref => {
          percentages[pref.soldier_type_name] = pref.percentage;
        });
      }
      
      // Initialize all soldier types with 0 if not already set (excluding untrained mercs)
      soldierTypes.filter(soldierType => soldierType.name !== 'untrained_mercs').forEach(soldierType => {
        if (!(soldierType.name in percentages)) {
          percentages[soldierType.name] = 0;
        }
      });
      
      setSoldierTypePercentages(percentages);
    }
  }, [preferences, soldierTypes]);

  const handlePercentageChange = (soldierTypeName: string, value: string) => {
    const numValue = parseFloat(value) || 0;
    setSoldierTypePercentages(prev => ({
      ...prev,
      [soldierTypeName]: numValue
    }));
  };

  const getTotalPercentage = () => {
    return Object.values(soldierTypePercentages).reduce((sum, percentage) => sum + percentage, 0);
  };

  const handleSave = async () => {
    try {
      if (preferences) {
        // Update existing preferences
        await updatePreferences.mutateAsync({
          accountId,
          data: { soldier_type_percentages: soldierTypePercentages }
        });
      } else {
        // Create new preferences
        await createPreferences.mutateAsync({
          account_id: accountId,
          soldier_type_percentages: soldierTypePercentages
        });
      }
    } catch (error) {
      console.error('Failed to save preferences:', error);
    }
  };

  const handleDelete = async () => {
    if (preferences && window.confirm('Are you sure you want to delete these preferences?')) {
      try {
        await deletePreferences.mutateAsync(accountId);
        setSoldierTypePercentages({});
      } catch (error) {
        console.error('Failed to delete preferences:', error);
      }
    }
  };

  const totalPercentage = getTotalPercentage();
  const isValid = totalPercentage <= 100 && totalPercentage > 0;

  if (preferencesLoading || soldierTypesLoading) {
    return (
      <Modal isOpen={true} onClose={onClose} title="Training Preferences" size="xl">
        <div className="flex justify-center items-center py-8">
          <div className="text-gray-500">Loading...</div>
        </div>
      </Modal>
    );
  }

  if (preferencesError) {
    return (
      <Modal isOpen={true} onClose={onClose} title="Training Preferences" size="xl">
        <div className="text-center py-8">
          <div className="text-red-500 mb-4">Error loading preferences</div>
          <Button onClick={onClose}>Close</Button>
        </div>
      </Modal>
    );
  }

  return (
    <Modal isOpen={true} onClose={onClose} title={`Training Preferences - ${accountUsername}`} size="xl">
      <div className="space-y-6">
        {/* Total Percentage Display */}
        <div className="bg-gray-50 p-4 rounded-lg">
          <div className="flex justify-between items-center">
            <span className="font-medium">Total Percentage:</span>
            <span className={`font-bold ${totalPercentage > 100 ? 'text-red-500' : totalPercentage === 0 ? 'text-gray-500' : 'text-green-600'}`}>
              {totalPercentage.toFixed(1)}%
            </span>
          </div>
          {totalPercentage > 100 && (
            <div className="text-red-500 text-sm mt-1">
              Total cannot exceed 100%
            </div>
          )}
          {totalPercentage === 0 && (
            <div className="text-gray-500 text-sm mt-1">
              At least one soldier type must have a percentage greater than 0
            </div>
          )}
        </div>

        {/* Soldier Type Preferences */}
        <div className="space-y-4">
          <h3 className="font-medium text-gray-900">Soldier Type Preferences</h3>
          
          {/* Responsive grid layout */}
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-3">
            {soldierTypes?.filter(soldierType => soldierType.name !== 'untrained_mercs').map((soldierType) => (
              <div key={soldierType.id} className="flex items-center justify-between p-3 border rounded-lg bg-white hover:bg-gray-50 transition-colors">
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm truncate">{soldierType.display_name}</div>
                  <div className="text-xs text-gray-500 truncate">{soldierType.name}</div>
                  {soldierType.costs_soldiers && (
                    <div className="text-xs text-blue-600">Costs soldiers</div>
                  )}
                </div>
                <div className="flex items-center space-x-2 ml-3">
                  <Input
                    type="number"
                    min="0"
                    max="100"
                    step="0.1"
                    value={soldierTypePercentages[soldierType.name] ?? 0}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => handlePercentageChange(soldierType.name, e.target.value)}
                    className="w-16 text-right text-sm"
                    placeholder="0"
                  />
                  <span className="text-xs text-gray-500">%</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row justify-between gap-4 pt-4 border-t">
          <div className="flex flex-wrap gap-2">
            <Button
              onClick={handleSave}
              disabled={!isValid || updatePreferences.isLoading || createPreferences.isLoading}
              variant="primary"
              size="sm"
            >
              {updatePreferences.isLoading || createPreferences.isLoading ? 'Saving...' : 'Save Preferences'}
            </Button>
            {preferences && (
              <Button
                onClick={handleDelete}
                disabled={deletePreferences.isLoading}
                variant="danger"
                size="sm"
              >
                {deletePreferences.isLoading ? 'Deleting...' : 'Delete'}
              </Button>
            )}
          </div>
          <Button onClick={onClose} variant="secondary" size="sm">
            Close
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export default TrainingPreferencesComponent;
