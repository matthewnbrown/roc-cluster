import React from 'react';
import { ValidationError } from '../types/api';
import { AlertTriangle, X } from 'lucide-react';

interface ValidationErrorDisplayProps {
  errors: ValidationError[];
  onClose?: () => void;
}

const ValidationErrorDisplay: React.FC<ValidationErrorDisplayProps> = ({ errors, onClose }) => {
  if (!errors || errors.length === 0) {
    return null;
  }

  const formatFieldPath = (loc: (string | number)[]): string => {
    // Remove 'body' from the beginning as it's not user-friendly
    const path = loc.filter(part => part !== 'body');
    
    if (path.length === 0) return 'Form';
    
    // Convert array indices to step numbers (1-based)
    const formattedPath = path.map((part, index) => {
      if (typeof part === 'number') {
        // If this is a step index, show it as "Step X"
        if (index === 0 || (index > 0 && typeof path[index - 1] === 'string' && path[index - 1] === 'steps')) {
          return `Step ${part + 1}`;
        }
        return `[${part}]`;
      }
      return part;
    });
    
    return formattedPath.join(' → ');
  };

  const getFieldDisplayName = (loc: (string | number)[]): string => {
    const lastPart = loc[loc.length - 1];
    
    // Map common field names to user-friendly names
    const fieldMap: Record<string, string> = {
      'account_ids': 'Account IDs',
      'cluster_ids': 'Cluster IDs',
      'action_type': 'Action Type',
      'parameters': 'Parameters',
      'max_retries': 'Max Retries',
      'is_async': 'Async Execution',
      'name': 'Job Name',
      'description': 'Description',
      'parallel_execution': 'Parallel Execution',
      'steps': 'Steps'
    };
    
    if (typeof lastPart === 'string' && fieldMap[lastPart]) {
      return fieldMap[lastPart];
    }
    
    return typeof lastPart === 'string' ? lastPart : String(lastPart);
  };

  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <AlertTriangle className="h-5 w-5 text-red-400" />
        </div>
        <div className="ml-3 flex-1">
          <h3 className="text-sm font-medium text-red-800">
            Validation Errors
          </h3>
          <div className="mt-2 text-sm text-red-700">
            <ul className="list-disc list-inside space-y-1">
              {errors.map((error, index) => (
                <li key={index}>
                  <span className="font-medium">
                    {formatFieldPath(error.loc)}:
                  </span>{' '}
                  {error.msg}
                </li>
              ))}
            </ul>
          </div>
        </div>
        {onClose && (
          <div className="ml-auto pl-3">
            <div className="-mx-1.5 -my-1.5">
              <button
                type="button"
                onClick={onClose}
                className="inline-flex bg-red-50 rounded-md p-1.5 text-red-500 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-red-50 focus:ring-red-600"
              >
                <span className="sr-only">Dismiss</span>
                <X className="h-5 w-5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ValidationErrorDisplay;
