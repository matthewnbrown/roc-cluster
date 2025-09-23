import React, { useState } from 'react';
import { Account } from '../types/api';
import Button from './ui/Button';
import ArmoryPreferencesComponent from './ArmoryPreferences';
import TrainingPreferencesComponent from './TrainingPreferences';

interface AccountPreferencesProps {
  account: Account;
  onClose: () => void;
}

type PreferenceType = 'armory' | 'training';

const AccountPreferences: React.FC<AccountPreferencesProps> = ({
  account,
  onClose,
}) => {
  const [activePreference, setActivePreference] = useState<PreferenceType | null>(null);

  const handleClose = () => {
    setActivePreference(null);
    onClose();
  };

  const handleOpenArmoryPreferences = () => {
    setActivePreference('armory');
  };

  const handleOpenTrainingPreferences = () => {
    setActivePreference('training');
  };

  const handlePreferenceClose = () => {
    setActivePreference(null);
  };

  if (activePreference === 'armory') {
    return (
      <ArmoryPreferencesComponent
        accountId={account.id}
        accountUsername={account.username}
        onClose={handlePreferenceClose}
      />
    );
  }

  if (activePreference === 'training') {
    return (
      <TrainingPreferencesComponent
        accountId={account.id}
        accountUsername={account.username}
        onClose={handlePreferenceClose}
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-lg font-medium text-gray-900 mb-2">
          Manage Preferences for {account.username}
        </h2>
        <p className="text-gray-600">
          Configure armory and training preferences for this account.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Armory Preferences Card */}
        <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
          <div className="text-center">
            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-md bg-blue-100 mb-4">
              <svg className="h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Armory Preferences</h3>
            <p className="text-gray-600 mb-4">
              Configure weapon purchase preferences based on percentage allocation of available gold.
            </p>
            <Button
              onClick={handleOpenArmoryPreferences}
              variant="primary"
              className="w-full"
            >
              Manage Armory Preferences
            </Button>
          </div>
        </div>

        {/* Training Preferences Card */}
        <div className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
          <div className="text-center">
            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-md bg-green-100 mb-4">
              <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Training Preferences</h3>
            <p className="text-gray-600 mb-4">
              Configure soldier type training preferences based on percentage allocation.
            </p>
            <Button
              onClick={handleOpenTrainingPreferences}
              variant="primary"
              className="w-full"
            >
              Manage Training Preferences
            </Button>
          </div>
        </div>
      </div>

      {/* Information Section */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-blue-800">
              How Preferences Work
            </h3>
            <div className="mt-2 text-sm text-blue-700">
              <ul className="list-disc list-inside space-y-1">
                <li>Percentages determine how much of your available resources (gold/soldiers) to allocate to each item</li>
                <li>Total percentages should not exceed 100%</li>
                <li>At least one item must have a percentage greater than 0%</li>
                <li>Preferences are used by automated purchase systems and job steps</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AccountPreferences;
