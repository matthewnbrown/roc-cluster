import React, { useEffect, useState, useRef } from 'react';
import { UseFormRegister, UseFormSetValue, UseFormWatch } from 'react-hook-form';
import { armoryApi } from '../services/api';
import { SoldierType, Weapon } from '../types/api';
import Input from './ui/Input';
import Select from './ui/Select';

// Separate component for sabotage to handle number conversion properly
const SabotageForm: React.FC<{
  stepIndex: number;
  weapons: Weapon[];
  currentParams: any;
  register: UseFormRegister<any>;
  setValue: UseFormSetValue<any>;
}> = ({ stepIndex, weapons, currentParams, register, setValue }) => {
  const [enemyWeaponValue, setEnemyWeaponValue] = useState<string>(String(currentParams.enemy_weapon || ''));

  const handleEnemyWeaponChange = (value: string) => {
    setEnemyWeaponValue(value);
    // Convert to number and set in form
    const numValue = parseInt(value);
    if (!isNaN(numValue)) {
      setValue(`steps.${stepIndex}.parameters.enemy_weapon`, numValue);
    }
  };

  return (
    <div className="space-y-3">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Target User ID <span className="text-red-500">*</span>
        </label>
        <Input
          {...register(`steps.${stepIndex}.parameters.target_id`, {
            required: 'Target user ID is required',
          })}
          placeholder="Enter target user ID"
          defaultValue={currentParams.target_id || ''}
        />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Spy Count
          </label>
          <Input
            type="number"
            min={1}
            {...register(`steps.${stepIndex}.parameters.spy_count`, {
              valueAsNumber: true,
              min: { value: 1, message: 'Spy count must be at least 1' },
            })}
            defaultValue={currentParams.spy_count || 1}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Enemy Weapon <span className="text-red-500">*</span>
          </label>
          <Select
            value={enemyWeaponValue}
            onChange={(e) => handleEnemyWeaponChange(e.target.value)}
          >
            <option value="">Select weapon</option>
            {weapons.map(weapon => (
              <option key={weapon.id} value={weapon.id}>
                {weapon.display_name}
              </option>
            ))}
          </Select>
        </div>
      </div>
    </div>
  );
};

// Separate component for training to handle proper form structure
const TrainingForm: React.FC<{
  stepIndex: number;
  register: UseFormRegister<any>;
  setValue: UseFormSetValue<any>;
  watch: UseFormWatch<any>;
}> = ({ stepIndex, register, setValue, watch }) => {
  const [showUntrained, setShowUntrained] = useState(false);
  const [trainingOrders, setTrainingOrders] = useState<Record<string, string>>({});
  const initializedRef = useRef(false);
  
  // Get current parameters from the form
  const currentParams = watch(`steps.${stepIndex}.parameters`) || {};
  console.log(`TrainingForm - watch result for step ${stepIndex}:`, currentParams);
  
  // All training fields in the exact order from backend
  const allFields = [
    { key: 'train[attack_soldiers]', label: 'Train Attack Soldiers', description: 'Train soldiers for attack' },
    { key: 'train[defense_soldiers]', label: 'Train Defense Soldiers', description: 'Train soldiers for defense' },
    { key: 'train[spies]', label: 'Train Spies', description: 'Train spies' },
    { key: 'train[sentries]', label: 'Train Sentries', description: 'Train sentries' },
    { key: 'buy[attack_mercs]', label: 'Buy Attack Mercs', description: 'Buy mercenaries for attack' },
    { key: 'buy[defense_mercs]', label: 'Buy Defense Mercs', description: 'Buy mercenaries for defense' },
    { key: 'buy[untrained_mercs]', label: 'Buy Untrained Mercs', description: 'Buy untrained mercenaries' },
    { key: 'untrain[attack_soldiers]', label: 'Untrain Attack Soldiers', description: 'Untrain attack soldiers' },
    { key: 'untrain[defense_soldiers]', label: 'Untrain Defense Soldiers', description: 'Untrain defense soldiers' },
    { key: 'untrain[attack_mercs]', label: 'Untrain Attack Mercs', description: 'Untrain attack mercenaries' },
    { key: 'untrain[defense_mercs]', label: 'Untrain Defense Mercs', description: 'Untrain defense mercenaries' },
    { key: 'untrain[untrained_mercs]', label: 'Untrain Untrained Mercs', description: 'Untrain untrained mercenaries' },
  ];

  // Initialize training orders from current params (only once)
  useEffect(() => {
    if (initializedRef.current) return;
    
    console.log('TrainingForm - currentParams:', currentParams);
    console.log('TrainingForm - currentParams.training_orders:', currentParams.training_orders);
    console.log('TrainingForm - typeof currentParams.training_orders:', typeof currentParams.training_orders);
    
    let currentOrders = {};
    if (currentParams.training_orders) {
      if (typeof currentParams.training_orders === 'string') {
        try {
          currentOrders = JSON.parse(currentParams.training_orders);
        } catch (e) {
          console.warn('Failed to parse training_orders string:', e);
          currentOrders = {};
        }
      } else if (typeof currentParams.training_orders === 'object') {
        currentOrders = currentParams.training_orders;
      }
    }
    
    if (Object.keys(currentOrders).length > 0) {
      console.log('Initializing training orders from params:', currentOrders);
      setTrainingOrders(currentOrders);
      initializedRef.current = true;
    }
  }, [currentParams]);

  const handleFieldChange = (fieldKey: string, value: string) => {
    const newOrders = { ...trainingOrders };
    
    // If value is empty, remove the field from the object
    if (value === '' || value === '0') {
      delete newOrders[fieldKey];
    } else {
      newOrders[fieldKey] = value;
    }
    
    setTrainingOrders(newOrders);
    console.log('Setting training_orders:', newOrders);
  };

  // Split fields into visible and collapsible sections
  const visibleFields = allFields.slice(0, 7); // First 7 fields (train + buy)
  const untrainFields = allFields.slice(7); // Last 5 fields (untrain)

  // Update the form whenever trainingOrders changes (but only if it has values)
  useEffect(() => {
    if (Object.keys(trainingOrders).length > 0) {
      console.log('Setting training_orders in form:', trainingOrders);
      setValue(`steps.${stepIndex}.parameters.training_orders`, trainingOrders);
    }
  }, [trainingOrders, setValue, stepIndex]);

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-3">
          Training Orders
        </label>
        <div className="text-sm text-gray-600 mb-4">
          Enter quantities for each training action (leave 0 to skip):
        </div>
        
        {/* Visible fields */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {visibleFields.map(field => (
            <div key={field.key} className="bg-gray-50 p-3 rounded border">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium text-gray-900">
                    {field.label}
                  </div>
                  <div className="text-xs text-gray-500">
                    {field.description}
                  </div>
                </div>
                <Input
                  type="number"
                  min={0}
                  value={trainingOrders[field.key] || ''}
                  onChange={(e) => handleFieldChange(field.key, e.target.value)}
                  className="w-24"
                />
              </div>
            </div>
          ))}
        </div>
        
        {/* Collapsible Untrained Section */}
        <div className="border-t pt-4">
          <button
            type="button"
            onClick={() => setShowUntrained(!showUntrained)}
            className="flex items-center justify-between w-full text-left"
          >
            <h4 className="text-sm font-medium text-gray-900">Untrain Units</h4>
            <span className="text-sm text-gray-500">
              {showUntrained ? '▼' : '▶'}
            </span>
          </button>
          {showUntrained && (
            <div className="mt-3">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {untrainFields.map(field => (
                  <div key={field.key} className="bg-gray-50 p-3 rounded border">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          {field.label}
                        </div>
                        <div className="text-xs text-gray-500">
                          {field.description}
                        </div>
                      </div>
                      <Input
                        type="number"
                        min={0}
                        value={trainingOrders[field.key] || ''}
                        onChange={(e) => handleFieldChange(field.key, e.target.value)}
                        className="w-24"
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Separate component for credit saving to handle form properly
const CreditSavingForm: React.FC<{
  stepIndex: number;
  currentParams: any;
  register: UseFormRegister<any>;
  setValue: UseFormSetValue<any>;
}> = ({ stepIndex, currentParams, register, setValue }) => {
  const [creditSavingValue, setCreditSavingValue] = useState<string>(currentParams.value || 'on');

  const handleCreditSavingChange = (value: string) => {
    setCreditSavingValue(value);
    // Set the value in the form
    setValue(`steps.${stepIndex}.parameters.value`, value);
  };

  return (
    <div className="space-y-3">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Credit Saving <span className="text-red-500">*</span>
        </label>
        <Select
          {...register(`steps.${stepIndex}.parameters.value`, {
            required: 'Credit saving value is required',
          })}
          value={creditSavingValue}
          onChange={(e) => handleCreditSavingChange(e.target.value)}
        >
          <option value="">Select credit saving setting</option>
          <option value="on">Enable Credit Saving</option>
          <option value="off">Disable Credit Saving</option>
        </Select>
      </div>
    </div>
  );
};

// Separate component for armory preferences to avoid hooks rules violation
const ArmoryPreferencesForm: React.FC<{
  stepIndex: number;
  weapons: Weapon[];
  currentParams: any;
  setValue: UseFormSetValue<any>;
}> = ({ stepIndex, weapons, currentParams, setValue }) => {
  const [weaponPercentages, setWeaponPercentages] = useState<Record<string, number>>({});
  const [totalPercentage, setTotalPercentage] = useState(0);

  // Initialize weapon percentages from current params or default to 0
  useEffect(() => {
    const currentWeaponPercentages = currentParams.weapon_percentages || {};
    const newPercentages: Record<string, number> = {};
    
    weapons.forEach(weapon => {
      newPercentages[weapon.name] = currentWeaponPercentages[weapon.name] || 0;
    });
    
    setWeaponPercentages(newPercentages);
    
    // Calculate total percentage
    const total = Object.values(newPercentages).reduce((sum, percentage) => sum + percentage, 0);
    setTotalPercentage(total);
  }, [weapons, currentParams.weapon_percentages]);

  const handlePercentageChange = (weaponName: string, value: string) => {
    const numValue = Math.max(0, Math.min(100, parseFloat(value) || 0));
    const newPercentages = { ...weaponPercentages, [weaponName]: numValue };
    setWeaponPercentages(newPercentages);
    
    // Calculate new total
    const total = Object.values(newPercentages).reduce((sum, percentage) => sum + percentage, 0);
    setTotalPercentage(total);
    
    // Update form value
    setValue(`steps.${stepIndex}.parameters.weapon_percentages`, newPercentages);
  };

  return (
    <div className="space-y-3">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Weapon Percentages
        </label>
        <div className="text-sm text-gray-600 mb-3">
          Set percentage allocation for each weapon (total: {totalPercentage}%)
          {totalPercentage > 100 && (
            <span className="text-red-600 ml-2">⚠️ Total cannot exceed 100%</span>
          )}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {weapons.map(weapon => (
            <div key={weapon.id} className="bg-gray-50 p-3 rounded border">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium text-gray-900">
                    {weapon.display_name}
                  </div>
                  <div className="text-xs text-gray-500">
                    {weapon.name}
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Input
                    type="number"
                    min={0}
                    max={100}
                    step={0.1}
                    value={weaponPercentages[weapon.name] || 0}
                    onChange={(e) => handlePercentageChange(weapon.name, e.target.value)}
                    className="w-20"
                  />
                  <span className="text-sm text-gray-500">%</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

interface FriendlyActionParametersProps {
  actionType: string;
  stepIndex: number;
  register: UseFormRegister<any>;
  setValue: UseFormSetValue<any>;
  watch: UseFormWatch<any>;
}

type UpgradeOption = 'siege' | 'fortification' | 'covert' | 'recruiter';

const FriendlyActionParameters: React.FC<FriendlyActionParametersProps> = ({ actionType, stepIndex, register, setValue, watch }) => {
  const [weapons, setWeapons] = useState<Weapon[]>([]);
  const [soldierTypes, setSoldierTypes] = useState<SoldierType[]>([]);

  // Watch current parameter values
  const currentParams = watch(`steps.${stepIndex}.parameters`) || {};

  useEffect(() => {
    // Load weapons and soldier types in background
    armoryApi.getWeapons().then(setWeapons).catch(() => {});
    armoryApi.getSoldierTypes().then(setSoldierTypes).catch(() => {});
  }, []);

  // Buy Upgrade Parameters
  if (actionType === 'buy_upgrade') {
    return (
      <div className="space-y-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Upgrade Type <span className="text-red-500">*</span>
          </label>
          <Select
            {...register(`steps.${stepIndex}.parameters.upgrade_option`, {
              required: 'Upgrade option is required',
            })}
            defaultValue={currentParams.upgrade_option || 'siege'}
          >
            <option value="siege">Siege</option>
            <option value="fortification">Fortification</option>
            <option value="covert">Covert</option>
            <option value="recruiter">Recruiter</option>
          </Select>
        </div>
      </div>
    );
  }

  // Sabotage Parameters
  if (actionType === 'sabotage') {
    return <SabotageForm stepIndex={stepIndex} weapons={weapons} currentParams={currentParams} register={register} setValue={setValue} />;
  }

  // Purchase Training Parameters
  if (actionType === 'purchase_training') {
    return <TrainingForm stepIndex={stepIndex} register={register} setValue={setValue} watch={watch} />;
  }

  // Purchase Armory Parameters
  if (actionType === 'purchase_armory') {
    return (
      <div className="space-y-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Armory Items
          </label>
          <div className="text-sm text-gray-600 mb-3">
            Enter quantities for each weapon (leave 0 to skip):
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {weapons.map(weapon => (
              <div key={weapon.id} className="bg-gray-50 p-3 rounded border">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium text-gray-900">
                      {weapon.display_name}
                    </div>
                    <div className="text-xs text-gray-500">
                      {weapon.name}
                    </div>
                  </div>
                  <Input
                    type="number"
                    min={0}
                    {...register(`steps.${stepIndex}.parameters.items.${weapon.name}`, {
                      valueAsNumber: true,
                      min: { value: 0, message: 'Quantity must be 0 or greater' },
                    })}
                    defaultValue={currentParams.items?.[weapon.name] || 0}
                    className="w-24"
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Set Credit Saving Parameters
  if (actionType === 'set_credit_saving') {
    return <CreditSavingForm stepIndex={stepIndex} currentParams={currentParams} register={register} setValue={setValue} />;
  }

  // Update Armory Preferences Parameters
  if (actionType === 'update_armory_preferences') {
    return <ArmoryPreferencesForm stepIndex={stepIndex} weapons={weapons} currentParams={currentParams} setValue={setValue} />;
  }

  // Default: return null to fall back to generic parameter handling
  return null;
};

export default FriendlyActionParameters;
