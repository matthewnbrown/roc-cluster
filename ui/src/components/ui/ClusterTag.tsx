import React from 'react';
import { clsx } from 'clsx';
import { Users } from 'lucide-react';

interface ClusterTagProps {
  name: string;
  description?: string;
  className?: string;
  size?: 'sm' | 'md';
}

const ClusterTag: React.FC<ClusterTagProps> = ({
  name,
  description,
  className,
  size = 'sm',
}) => {
  const sizeClasses = {
    sm: 'px-2 py-1 text-xs',
    md: 'px-3 py-1.5 text-sm',
  };

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 rounded-full font-medium text-gray-700 bg-blue-100 hover:bg-blue-200 transition-colors',
        sizeClasses[size],
        className
      )}
      title={description || name}
    >
      <Users className="h-3 w-3" />
      {name}
    </span>
  );
};

export default ClusterTag;
