import React from 'react';
import {
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { GripVertical, Copy, Trash2 } from 'lucide-react';
import { ActionType } from '../types/api';
import { UseFormWatch } from 'react-hook-form';
import Button from './ui/Button';
import StepEditor from './StepEditor';

interface SortableStepProps {
  id: string;
  index: number;
  step: any;
  isEditing: boolean;
  editingStepIndex: number | null;
  setEditingStepIndex: (index: number | null) => void;
  duplicateStep: (index: number) => void;
  removeStep: (index: number) => void;
  fields: any[];
  watchedSteps: any[];
  getActionTypeInfo: (actionType: string) => ActionType | undefined;
  getSelectedAccounts: (index: number) => any;
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
}

function SortableStep({
  id,
  index,
  step,
  isEditing,
  editingStepIndex,
  setEditingStepIndex,
  duplicateStep,
  removeStep,
  fields,
  watchedSteps,
  getActionTypeInfo,
  getSelectedAccounts,
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
}: SortableStepProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} className="space-y-2">
      {/* Step Summary - Clickable */}
      <div 
        className={`flex items-center justify-between bg-white rounded-md p-3 border transition-colors ${
          isEditing ? 'border-primary-500 bg-primary-50' : 'border-gray-200 hover:border-gray-300'
        } ${isDragging ? 'shadow-lg' : ''}`}
      >
        <div 
          className="flex items-center space-x-3 flex-1 cursor-pointer"
          onClick={() => setEditingStepIndex(isEditing ? null : index)}
        >
          {/* Drag Handle */}
          <div
            {...attributes}
            {...listeners}
            className="cursor-grab hover:cursor-grabbing p-1 text-gray-400 hover:text-gray-600"
            title="Drag to reorder"
          >
            <GripVertical className="h-4 w-4" />
          </div>
          
          <div className="flex-shrink-0 w-8 h-8 bg-primary-100 text-primary-600 rounded-full flex items-center justify-center text-sm font-medium">
            {index + 1}
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-medium text-gray-900">
                {step?.action_type || 'Select Action'}
              </span>
              {step?.is_async && (
                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  Async
                </span>
              )}
            </div>
            <div className="text-sm text-gray-500">
              {(() => {
                const actionInfo = getActionTypeInfo(step?.action_type || '');
                return actionInfo?.description || 'Select an action type';
              })()}
            </div>
            <div className="text-sm text-gray-600">
              {(() => {
                const selection = getSelectedAccounts(index);
                if (selection.totalIndividual > 0 && selection.totalClusters > 0) {
                  return (
                    <span>
                      {selection.totalIndividual} individual, {selection.totalClusters} cluster{selection.totalClusters !== 1 ? 's' : ''}
                    </span>
                  );
                } else if (selection.totalIndividual > 0) {
                  return <span>{selection.totalIndividual} individual account{selection.totalIndividual !== 1 ? 's' : ''}</span>;
                } else if (selection.totalClusters > 0) {
                  return <span>{selection.totalClusters} cluster{selection.totalClusters !== 1 ? 's' : ''}</span>;
                } else {
                  return (
                    <span className="text-gray-400">
                      {step?.action_type === 'delay' ? 'No targets needed' : 'No targets selected'}
                    </span>
                  );
                }
              })()}
            </div>
            <div className="text-xs text-gray-500">
              Max retries: {step?.max_retries || 0} • {step?.is_async ? 'Async' : 'Sync'}
            </div>
          </div>
        </div>
        
        {/* Action Buttons */}
        <div className="flex items-center space-x-1 ml-4">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              duplicateStep(index);
            }}
            className="text-blue-600 hover:text-blue-700"
            title="Duplicate this step"
          >
            <Copy className="h-4 w-4" />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              if (fields.length > 1) {
                removeStep(index);
              }
            }}
            disabled={fields.length <= 1}
            className={fields.length > 1 ? "text-red-600 hover:text-red-700" : "text-gray-400 cursor-not-allowed"}
            title={fields.length > 1 ? "Delete this step" : "Cannot delete the last step"}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Step Editor */}
      {isEditing && (
        <StepEditor
          index={index}
          step={step}
          duplicateStep={duplicateStep}
          removeStep={removeStep}
          fields={fields}
          watchedSteps={watchedSteps}
          getActionTypeInfo={getActionTypeInfo}
          getSelectedAccounts={getSelectedAccounts}
          setEditingStepIndex={setEditingStepIndex}
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
        />
      )}
    </div>
  );
}

export default SortableStep;
