import React, { useState } from 'react';
import { useClusters, useDeleteCluster } from '../hooks/useClusters';
import { ClusterListResponse } from '../types/api';
import { Table, TableHeader, TableBody, TableRow, TableCell } from './ui/Table';
import Button from './ui/Button';
import Pagination from './ui/Pagination';
import { Plus, Edit, Trash2, Search, Users, Copy, Shield } from 'lucide-react';
import Input from './ui/Input';
import ClusterTag from './ui/ClusterTag';

interface ClusterListProps {
  onViewCluster: (cluster: ClusterListResponse) => void;
  onEditCluster: (cluster: ClusterListResponse) => void;
  onCreateCluster: () => void;
  onCloneCluster: (cluster: ClusterListResponse) => void;
}

const ClusterList: React.FC<ClusterListProps> = ({
  onViewCluster,
  onEditCluster,
  onCreateCluster,
  onCloneCluster,
}) => {
  const [page, setPage] = useState(1);
  const [perPage] = useState(20);
  const [searchTerm, setSearchTerm] = useState('');

  const { data: clustersData, isLoading, error } = useClusters(page, perPage, searchTerm);
  const deleteClusterMutation = useDeleteCluster();

  const handleDeleteCluster = async (cluster: ClusterListResponse) => {
    if (window.confirm(`Are you sure you want to delete cluster "${cluster.name}"?`)) {
      try {
        await deleteClusterMutation.mutateAsync(cluster.id);
      } catch (error) {
        console.error('Failed to delete cluster:', error);
      }
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <div className="text-red-800">
          <p className="font-medium">Error loading clusters</p>
          <p className="text-sm mt-1">
            {error instanceof Error ? error.message : 'An unexpected error occurred'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Clusters</h1>
          <p className="text-gray-600">
            Manage your account clusters ({clustersData?.pagination.total || 0} total)
          </p>
        </div>
        <Button onClick={onCreateCluster} className="flex items-center gap-2">
          <Plus className="h-4 w-4" />
          Create Cluster
        </Button>
      </div>

      {/* Search */}
      <div className="max-w-md relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <Search className="h-5 w-5 text-gray-400" />
        </div>
        <Input
          placeholder="Search clusters..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Table */}
      <div className="bg-white shadow overflow-hidden sm:rounded-md">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableCell header className="w-16">ID</TableCell>
                <TableCell header className="min-w-[150px]">Name</TableCell>
                <TableCell header className="min-w-[200px]">Description</TableCell>
                <TableCell header className="w-24">Members</TableCell>
                <TableCell header className="min-w-[120px]">Created</TableCell>
                <TableCell header className="w-40">Actions</TableCell>
              </TableRow>
            </TableHeader>
            <TableBody>
              {clustersData?.data.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-gray-500">
                    {searchTerm ? 'No clusters found matching your search.' : 'No clusters found.'}
                  </TableCell>
                </TableRow>
              ) : (
                clustersData?.data.map((cluster) => (
                  <TableRow 
                    key={cluster.id}
                    className="cursor-pointer hover:bg-gray-50 transition-colors"
                    onClick={() => onViewCluster(cluster)}
                  >
                    <TableCell className="font-mono text-sm">{cluster.id}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <ClusterTag name={cluster.name} size="sm" />
                        {cluster.name === "all_users" && (
                          <div title="System cluster - cannot be deleted">
                            <Shield className="h-4 w-4 text-blue-500" />
                          </div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="truncate max-w-xs">
                      {cluster.description || <span className="text-gray-400 italic">No description</span>}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Users className="h-4 w-4 text-gray-400" />
                        <span className="text-sm font-medium">{cluster.user_count || 0}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-gray-500 text-sm">
                      {formatDate(cluster.created_at)}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center space-x-2" onClick={(e) => e.stopPropagation()}>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onEditCluster(cluster)}
                          className="p-2 h-10 w-10"
                          title="Edit cluster"
                        >
                          <Edit className="h-5 w-5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onCloneCluster(cluster)}
                          className="p-2 h-10 w-10"
                          title="Clone cluster"
                        >
                          <Copy className="h-5 w-5" />
                        </Button>
                        {cluster.name !== "all_users" && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDeleteCluster(cluster)}
                            className="p-2 h-10 w-10 text-red-600 hover:text-red-700"
                            loading={deleteClusterMutation.isLoading}
                            title="Delete cluster"
                          >
                            <Trash2 className="h-5 w-5" />
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      {/* Pagination */}
      {clustersData && clustersData.pagination.total_pages > 1 && (
        <Pagination
          currentPage={page}
          totalPages={clustersData.pagination.total_pages}
          onPageChange={setPage}
        />
      )}
    </div>
  );
};

export default ClusterList;
