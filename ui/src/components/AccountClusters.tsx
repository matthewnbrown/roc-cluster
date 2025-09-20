import React from 'react';
import { useAccountClusters } from '../hooks/useClusters';
import ClusterTag from './ui/ClusterTag';

interface AccountClustersProps {
  accountId: number;
  maxVisible?: number;
  className?: string;
}

const AccountClusters: React.FC<AccountClustersProps> = ({
  accountId,
  maxVisible = 3,
  className,
}) => {
  const { data: clusters, isLoading, error } = useAccountClusters(accountId);

  if (isLoading) {
    return (
      <div className={`flex items-center gap-1 ${className}`}>
        <div className="animate-pulse bg-gray-200 rounded-full h-5 w-16"></div>
      </div>
    );
  }

  if (error || !clusters || clusters.length === 0) {
    return null;
  }

  const visibleClusters = clusters.slice(0, maxVisible);
  const remainingCount = clusters.length - maxVisible;

  return (
    <div className={`flex items-center gap-1 flex-wrap ${className}`}>
      {visibleClusters.map((cluster) => (
        <ClusterTag
          key={cluster.id}
          name={cluster.name}
          description={cluster.description}
          size="sm"
        />
      ))}
      {remainingCount > 0 && (
        <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
          +{remainingCount} more
        </span>
      )}
    </div>
  );
};

export default AccountClusters;
