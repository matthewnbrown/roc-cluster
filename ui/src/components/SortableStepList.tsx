import React from 'react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import SortableStep from './SortableStep';
import { ActionType } from '../types/api';
import { UseFormWatch } from 'react-hook-form';

interface SortableStepListProps {
  fields: any[];
  watchedSteps: any[];
  editingStepIndex: number | null;
  setEditingStepIndex: (index: number | null) => void;
  duplicateStep: (index: number) => void;
  removeStep: (index: number) => void;
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

const SortableStepList: React.FC<SortableStepListProps> = ({
  fields,
  watchedSteps,
  editingStepIndex,
  setEditingStepIndex,
  duplicateStep,
  removeStep,
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
}) => {
  // Drag and drop sensors
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      const oldIndex = fields.findIndex((field) => field.id === active.id);
      const newIndex = fields.findIndex((field) => field.id === over.id);

      if (oldIndex !== -1 && newIndex !== -1) {
        // Use react-hook-form's setValue to reorder steps
        const newSteps = arrayMove(watchedSteps, oldIndex, newIndex);
        setValue('steps', newSteps);
      }
    }
  };

  return (
    <div className="space-y-4">
      {/* Steps Overview */}
      {fields.length > 0 && (
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-medium text-gray-900">Steps Overview</h4>
            <div className="text-sm text-gray-500">
              Drag to reorder • Click to edit
            </div>
          </div>
          
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <SortableContext
              items={fields.map(field => field.id)}
              strategy={verticalListSortingStrategy}
            >
              <div className="space-y-2">
                {fields.map((field, index) => {
                  const step = watchedSteps[index];
                  const isEditing = editingStepIndex === index;
                  
                  return (
                    <SortableStep
                      key={field.id}
                      id={field.id}
                      index={index}
                      step={step}
                      isEditing={isEditing}
                      editingStepIndex={editingStepIndex}
                      setEditingStepIndex={setEditingStepIndex}
                      duplicateStep={duplicateStep}
                      removeStep={removeStep}
                      fields={fields}
                      watchedSteps={watchedSteps}
                      getActionTypeInfo={getActionTypeInfo}
                      getSelectedAccounts={getSelectedAccounts}
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
                  );
                })}
              </div>
            </SortableContext>
          </DndContext>
        </div>
      )}
    </div>
  );
};

export default SortableStepList;
