import React, { useState, useEffect } from 'react';
import { 
  useArmoryPreferences, 
  useCreateArmoryPreferences, 
  useUpdateArmoryPreferences,
  useDeleteArmoryPreferences,
  useWeapons,
  usePurchaseArmoryByPreferences
} from '../hooks/usePreferences';
import { ActionResponse } from '../types/api';
import { getCurrentTimestamp } from '../utils/dateUtils';
// Types are used in the component logic
import Button from './ui/Button';
import Input from './ui/Input';
import Modal from './ui/Modal';

interface ArmoryPreferencesProps {
  accountId: number;
  accountUsername: string;
  onClose: () => void;
}

const ArmoryPreferencesComponent: React.FC<ArmoryPreferencesProps> = ({
  accountId,
  accountUsername,
  onClose,
}) => {
  const [weaponPercentages, setWeaponPercentages] = useState<Record<string, number>>({});
  // Removed isEditing state - always editable now
  const [showPurchaseConfirm, setShowPurchaseConfirm] = useState(false);
  const [purchaseResult, setPurchaseResult] = useState<ActionResponse | null>(null);
  const [showPurchaseResult, setShowPurchaseResult] = useState(false);

  const { data: preferences, isLoading: preferencesLoading, error: preferencesError } = useArmoryPreferences(accountId);
  const { data: weapons, isLoading: weaponsLoading } = useWeapons();
  const createPreferences = useCreateArmoryPreferences();
  const updatePreferences = useUpdateArmoryPreferences();
  const deletePreferences = useDeleteArmoryPreferences();
  const purchaseArmory = usePurchaseArmoryByPreferences();

  // Initialize weapon percentages when preferences or weapons load
  useEffect(() => {
    if (weapons) {
      const percentages: Record<string, number> = {};
      
      // Initialize with existing preferences if they exist
      if (preferences) {
        preferences.weapon_preferences.forEach(pref => {
          percentages[pref.weapon_name] = pref.percentage;
        });
      }
      
      // Initialize all weapons with 0 if not already set
      weapons.forEach(weapon => {
        if (!(weapon.name in percentages)) {
          percentages[weapon.name] = 0;
        }
      });
      
      setWeaponPercentages(percentages);
    }
  }, [preferences, weapons]);

  const handlePercentageChange = (weaponName: string, value: string) => {
    const numValue = parseFloat(value) || 0;
    setWeaponPercentages(prev => ({
      ...prev,
      [weaponName]: numValue
    }));
  };

  const getTotalPercentage = () => {
    return Object.values(weaponPercentages).reduce((sum, percentage) => sum + percentage, 0);
  };

  const handleSave = async () => {
    try {
      if (preferences) {
        // Update existing preferences
        await updatePreferences.mutateAsync({
          accountId,
          data: { weapon_percentages: weaponPercentages }
        });
      } else {
        // Create new preferences
        await createPreferences.mutateAsync({
          account_id: accountId,
          weapon_percentages: weaponPercentages
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
        setWeaponPercentages({});
      } catch (error) {
        console.error('Failed to delete preferences:', error);
      }
    }
  };

  const handlePurchase = async () => {
    try {
      const result = await purchaseArmory.mutateAsync(accountId);
      setPurchaseResult(result);
      setShowPurchaseConfirm(false);
      setShowPurchaseResult(true);
    } catch (error) {
      console.error('Failed to purchase armory:', error);
      // Create error result for display
      const errorResult: ActionResponse = {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred',
        timestamp: getCurrentTimestamp()
      };
      setPurchaseResult(errorResult);
      setShowPurchaseConfirm(false);
      setShowPurchaseResult(true);
    }
  };

  const totalPercentage = getTotalPercentage();
  const isValid = totalPercentage <= 100 && totalPercentage > 0;


  if (preferencesLoading || weaponsLoading) {
    return (
      <Modal isOpen={true} onClose={onClose} title="Armory Preferences" size="xl">
        <div className="flex justify-center items-center py-8">
          <div className="text-gray-500">Loading...</div>
        </div>
      </Modal>
    );
  }

  if (preferencesError) {
    return (
      <Modal isOpen={true} onClose={onClose} title="Armory Preferences" size="xl">
        <div className="text-center py-8">
          <div className="text-red-500 mb-4">Error loading preferences</div>
          <Button onClick={onClose}>Close</Button>
        </div>
      </Modal>
    );
  }

  return (
    <>
      <Modal isOpen={true} onClose={onClose} title={`Armory Preferences - ${accountUsername}`} size="xl">
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
                At least one weapon must have a percentage greater than 0
              </div>
            )}
          </div>

          {/* Weapon Preferences */}
          <div className="space-y-4">
            <h3 className="font-medium text-gray-900">Weapon Preferences</h3>
            
            {/* Responsive grid layout */}
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-3">
              {weapons?.map((weapon) => (
                <div key={weapon.id} className="flex items-center justify-between p-3 border rounded-lg bg-white hover:bg-gray-50 transition-colors">
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-sm truncate">{weapon.display_name}</div>
                    <div className="text-xs text-gray-500 truncate">{weapon.name}</div>
                  </div>
                  <div className="flex items-center space-x-2 ml-3">
                    <Input
                      type="number"
                      min="0"
                      max="100"
                      step="0.1"
                      value={weaponPercentages[weapon.name] ?? 0}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => handlePercentageChange(weapon.name, e.target.value)}
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
            <div className="flex flex-wrap gap-2">
              {preferences && isValid && (
                <Button
                  onClick={() => setShowPurchaseConfirm(true)}
                  disabled={purchaseArmory.isLoading}
                  variant="primary"
                  size="sm"
                >
                  {purchaseArmory.isLoading ? 'Purchasing...' : 'Purchase Armory'}
                </Button>
              )}
              <Button onClick={onClose} variant="secondary" size="sm">
                Close
              </Button>
            </div>
          </div>
        </div>
      </Modal>

      {/* Purchase Confirmation Modal */}
      <Modal 
        isOpen={showPurchaseConfirm} 
        onClose={() => setShowPurchaseConfirm(false)} 
        title="Confirm Armory Purchase"
      >
        <div className="space-y-4">
          <p>
            Are you sure you want to purchase armory items for <strong>{accountUsername}</strong> based on their preferences?
          </p>
          <div className="bg-yellow-50 p-3 rounded-lg">
            <p className="text-sm text-yellow-800">
              This will use the account's current gold to purchase weapons according to the configured percentages.
            </p>
          </div>
          <div className="flex justify-end space-x-2">
            <Button
              onClick={() => setShowPurchaseConfirm(false)}
              variant="secondary"
            >
              Cancel
            </Button>
            <Button
              onClick={handlePurchase}
              disabled={purchaseArmory.isLoading}
              variant="primary"
            >
              {purchaseArmory.isLoading ? 'Purchasing...' : 'Confirm Purchase'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Purchase Result Modal */}
      <Modal 
        isOpen={showPurchaseResult} 
        onClose={() => setShowPurchaseResult(false)} 
        title={purchaseResult?.success ? "Purchase Successful" : "Purchase Failed"}
      >
        <div className="space-y-4">
          {purchaseResult?.success ? (
            <div>
              <div className="bg-green-50 p-4 rounded-lg mb-4">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-green-800">
                      Armory purchase completed successfully!
                    </h3>
                  </div>
                </div>
              </div>
              
              {purchaseResult.data && Object.keys(purchaseResult.data).length > 0 ? (
                <div className="space-y-2">
                  <h4 className="font-medium text-gray-900">Purchase Details:</h4>
                  <div className="bg-gray-50 p-3 rounded-lg">
                    <div className="space-y-1">
                      {Object.entries(purchaseResult.data).map(([weaponId, amount]) => {
                        const weapon = weapons?.find(w => w.id.toString() === weaponId);
                        return (
                          <div key={weaponId} className="flex justify-between text-sm">
                            <span className="text-gray-700">
                              {weapon ? weapon.display_name : `Weapon ID: ${weaponId}`}
                            </span>
                            <span className="font-medium text-gray-900">
                              {amount} purchased
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-sm text-gray-600">
                  No weapons were purchased (possibly due to insufficient gold or other constraints).
                </div>
              )}
            </div>
          ) : (
            <div>
              <div className="bg-red-50 p-4 rounded-lg mb-4">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-red-800">
                      Armory purchase failed
                    </h3>
                    <div className="mt-2 text-sm text-red-700">
                      <p>{purchaseResult?.error || 'An unknown error occurred'}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          <div className="flex justify-end">
            <Button
              onClick={() => setShowPurchaseResult(false)}
              variant="primary"
            >
              Close
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
};

export default ArmoryPreferencesComponent;
