import React from 'react';
import { EyeOff, Users, Search, X } from 'lucide-react';
import Button from './ui/Button';
import Input from './ui/Input';
import AccountAutocomplete from './AccountAutocomplete';
import FriendlyActionParameters from './FriendlyActionParameters';
import { ActionType, ValidationError } from '../types/api';
import { UseFormWatch } from 'react-hook-form';

interface StepEditorProps {
  index: number;
  step: any;
  duplicateStep: (index: number) => void;
  removeStep: (index: number) => void;
  fields: any[];
  watchedSteps: any[];
  getActionTypeInfo: (actionType: string) => ActionType | undefined;
  getSelectedAccounts: (index: number) => any;
  setEditingStepIndex: (index: number | null) => void;
  setValue: any;
  register: any;
  errors: any;
  watch: UseFormWatch<any>;
  clustersData: any;
  actionTypesData: any;
  clusterSearchTerms: { [stepIndex: number]: string };
  setClusterSearchTerms: (terms: { [stepIndex: number]: string }) => void;
  showClusterSuggestions: { [stepIndex: number]: boolean };
  setShowClusterSuggestions: (suggestions: { [stepIndex: number]: boolean }) => void;
  selectedClusterSuggestionIndex: { [stepIndex: number]: number };
  setSelectedClusterSuggestionIndex: (index: { [stepIndex: number]: number }) => void;
  getFilteredClusters: (searchTerm: string, stepIndex: number) => any[];
  addClusterToStep: (stepIndex: number, cluster: any) => void;
  removeClusterFromStep: (stepIndex: number, clusterId: number) => void;
  getClusterById: (clusterId: number) => any;
  handleClusterKeyDown: (stepIndex: number, event: React.KeyboardEvent) => void;
  stepErrors: ValidationError[];
}

const StepEditor: React.FC<StepEditorProps> = ({
  index,
  step,
  duplicateStep,
  removeStep,
  fields,
  watchedSteps,
  getActionTypeInfo,
  getSelectedAccounts,
  setEditingStepIndex,
  setValue,
  register,
  errors,
  watch,
  clustersData,
  actionTypesData,
  clusterSearchTerms,
  setClusterSearchTerms,
  showClusterSuggestions,
  setShowClusterSuggestions,
  selectedClusterSuggestionIndex,
  setSelectedClusterSuggestionIndex,
  getFilteredClusters,
  addClusterToStep,
  removeClusterFromStep,
  getClusterById,
  handleClusterKeyDown,
  stepErrors,
}) => {
  // Use the watched steps array which is already reactive to form changes
  const currentStep = watchedSteps[index];
  const actionType = currentStep?.action_type;
  
  return (
    <div className={`border-l border-r border-b p-4 space-y-4 bg-primary-50 ${
      stepErrors.length > 0 
        ? 'border-red-200' 
        : 'border-primary-200 rounded-b-md'
    }`}>
      <div className="flex items-center justify-between">
        <h4 className="font-medium text-gray-900">Edit Step {index + 1}</h4>
        <div className="flex items-center space-x-2">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setEditingStepIndex(null)}
            className="text-gray-500 hover:text-gray-700"
            title="Close step editor"
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
              // Update the action type and clear parameters when action type changes
              setValue(`steps.${index}.action_type`, e.target.value);
              setValue(`steps.${index}.parameters`, {});
            }}
            className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
          >
            <option value="">Select an action type</option>
            {actionTypesData?.categories && Object.entries(actionTypesData.categories).map(([category, actions]: [string, any]) => (
              <optgroup key={category} label={category.replace('_', ' ').toUpperCase()}>
                {actions.map((action: any) => (
                  <option key={action.action_type} value={action.action_type}>
                    {action.action_type} - {action.description}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
          {errors.steps?.[index]?.action_type && (
            <p className="text-xs text-red-600 mt-1">
              {errors.steps[index].action_type.message}
            </p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Max Retries
          </label>
          <Input
            type="number"
            min="0"
            max="10"
            {...register(`steps.${index}.max_retries`, {
              valueAsNumber: true,
              min: { value: 0, message: 'Must be at least 0' },
              max: { value: 10, message: 'Must be at most 10' },
            })}
            className={errors.steps?.[index]?.max_retries ? 'border-red-300' : ''}
          />
          {errors.steps?.[index]?.max_retries && (
            <p className="text-xs text-red-600 mt-1">
              {errors.steps[index].max_retries.message}
            </p>
          )}
        </div>

        {/* Async Execution */}
        <div className="col-span-1">
          <div className="flex items-center h-full">
            <input
              type="checkbox"
              id={`steps.${index}.is_async`}
              {...register(`steps.${index}.is_async`)}
              defaultChecked={false}
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
            <label htmlFor={`steps.${index}.is_async`} className="ml-2 block text-sm text-gray-900">
              Execute asynchronously
            </label>
          </div>
        </div>
      </div>

      {/* Runners - Hide for delay and collect_async_tasks steps */}
      {actionType !== 'delay' && actionType !== 'collect_async_tasks' && (
        <div className="space-y-4">
          <h5 className="font-medium text-gray-900">Runners</h5>
        
        {/* Individual Accounts */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm text-gray-600">
              <Users className="h-4 w-4 inline mr-1" />
              Individual Accounts
            </label>
          </div>
          
          {/* Account Autocomplete */}
          <AccountAutocomplete
            selectedAccountIds={watchedSteps[index]?.account_ids || watchedSteps[index]?.original_account_ids || []}
            onAccountSelect={(account: any) => {
              const currentAccountIds = watchedSteps[index]?.account_ids || [];
              if (!currentAccountIds.includes(account.id)) {
                setValue(`steps.${index}.account_ids`, [...currentAccountIds, account.id]);
              }
            }}
            onAccountRemove={(accountId: number) => {
              const currentAccountIds = watchedSteps[index]?.account_ids || [];
              const newAccountIds = currentAccountIds.filter((id: number) => id !== accountId);
              setValue(`steps.${index}.account_ids`, newAccountIds);
            }}
            placeholder="Search and select accounts..."
          />
        </div>

        {/* Clusters */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            <Users className="h-4 w-4 inline mr-1" />
            Clusters
          </label>
          
          {/* Selected Clusters */}
          <div className="mb-3">
            {watchedSteps[index]?.cluster_ids?.map((clusterId: number) => {
              const cluster = getClusterById(clusterId);
              if (!cluster) return null;
              
              return (
                <div key={clusterId} className="inline-flex items-center bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-sm mr-2 mb-2">
                  <span>{cluster.name} ({cluster.user_count} members)</span>
                  <button
                    type="button"
                    onClick={() => removeClusterFromStep(index, clusterId)}
                    className="ml-1 text-blue-600 hover:text-blue-800"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              );
            })}
          </div>

          {/* Search Input */}
          <div className="relative">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                value={clusterSearchTerms[index] || ''}
                onChange={(e) => {
                  setClusterSearchTerms({
                    ...clusterSearchTerms,
                    [index]: e.target.value,
                  });
                  setShowClusterSuggestions({
                    ...showClusterSuggestions,
                    [index]: true,
                  });
                }}
                onFocus={() => {
                  setShowClusterSuggestions({
                    ...showClusterSuggestions,
                    [index]: true,
                  });
                }}
                onKeyDown={(e) => handleClusterKeyDown(index, e)}
                placeholder="Search clusters..."
                className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
              />
            </div>

            {/* Suggestions Dropdown */}
            {showClusterSuggestions[index] && clusterSearchTerms[index] && (
              <div className="suggestions-container absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-48 overflow-y-auto">
                {getFilteredClusters(clusterSearchTerms[index], index).map((cluster, suggestionIndex) => (
                  <div
                    key={cluster.id}
                    className={`px-3 py-2 cursor-pointer text-sm ${
                      selectedClusterSuggestionIndex[index] === suggestionIndex
                        ? 'bg-primary-100 text-primary-900'
                        : 'hover:bg-gray-100'
                    }`}
                    onClick={() => {
                      addClusterToStep(index, cluster);
                      setClusterSearchTerms({
                        ...clusterSearchTerms,
                        [index]: '',
                      });
                      setShowClusterSuggestions({
                        ...showClusterSuggestions,
                        [index]: false,
                      });
                    }}
                  >
                    {cluster.name} ({cluster.user_count} members)
                  </div>
                ))}
                {getFilteredClusters(clusterSearchTerms[index], index).length === 0 && (
                  <div className="px-3 py-2 text-sm text-gray-500">No clusters found</div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Targeting Summary */}
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
      )}

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
                  <p className="text-sm text-gray-500">No parameters required for this action type.</p>
                );
              }

              return Object.entries(actionInfo.parameter_details).map(([paramName, paramInfo]: [string, any]) => {
                const isRequired = actionInfo.required_parameters?.includes(paramName) || false;
                
                return (
                  <div key={paramName} className="space-y-1">
                    <label className="block text-sm font-medium text-gray-700">
                      {paramName}
                      {isRequired && <span className="text-red-500 ml-1">*</span>}
                    </label>
                    <p className="text-xs text-gray-500">{paramInfo.description}</p>
                    
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
                          id={`steps.${index}.parameters.${paramName}`}
                          {...register(`steps.${index}.parameters.${paramName}`)}
                          className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                        />
                        <label htmlFor={`steps.${index}.parameters.${paramName}`} className="ml-2 block text-sm text-gray-900">
                          {paramInfo.description || `Enable ${paramName}`}
                        </label>
                      </div>
                    )}
                    
                    {paramInfo.type === 'object' && (
                      <textarea
                        {...register(`steps.${index}.parameters.${paramName}`, {
                          required: isRequired ? `${paramName} is required` : false,
                          validate: (value: any) => {
                            if (!value && !isRequired) return true;
                            try {
                              const parsed = JSON.parse(value);
                              if (typeof parsed !== 'object' || Array.isArray(parsed)) {
                                return 'Must be a valid JSON object';
                              }
                              return true;
                            } catch {
                              return 'Must be valid JSON';
                            }
                          },
                        })}
                        rows={4}
                        className={`block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm ${
                          errors.steps?.[index]?.parameters?.[paramName] 
                            ? 'border-red-300 focus:ring-red-500 focus:border-red-500' 
                            : 'border-gray-300'
                        }`}
                        placeholder={paramInfo.description || `Enter ${paramName} as JSON object`}
                      />
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
  );
};

export default StepEditor;
