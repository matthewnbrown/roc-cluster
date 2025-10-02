import React, { useState } from 'react';
import { ClusterResponse, ClusterUser } from '../types/api';
import { useCluster, useAddUsersToCluster, useRemoveUserFromCluster } from '../hooks/useClusters';
import { useAccounts } from '../hooks/useAccounts';
import Button from './ui/Button';
import Modal from './ui/Modal';
import AccountAutocomplete from './AccountAutocomplete';
import { Table, TableHeader, TableBody, TableRow, TableCell } from './ui/Table';
import Pagination from './ui/Pagination';
import { ArrowLeft, Edit, Trash2, User, Mail, Calendar, Users, Plus, X, Copy, Shield } from 'lucide-react';
import Input from './ui/Input';

interface ClusterDetailsProps {
  clusterId: number;
  onBack: () => void;
  onEditCluster: (cluster: ClusterResponse) => void;
  onCloneCluster: (cluster: ClusterResponse) => void;
}

const ClusterDetails: React.FC<ClusterDetailsProps> = ({
  clusterId,
  onBack,
  onEditCluster,
  onCloneCluster,
}) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'users'>('overview');
  const [usersPage, setUsersPage] = useState(1);
  const [addUsersModalOpen, setAddUsersModalOpen] = useState(false);
  const [selectedAccountIds, setSelectedAccountIds] = useState<number[]>([]);

  const { data: cluster, isLoading: clusterLoading, error: clusterError } = useCluster(clusterId);
  // Removed large account fetch - now using AccountAutocomplete component
  const addUsersToClusterMutation = useAddUsersToCluster();
  const removeUserFromClusterMutation = useRemoveUserFromCluster();

  const handleAddUsers = async () => {
    if (!clusterId || selectedAccountIds.length === 0) return;
    
    try {
      await addUsersToClusterMutation.mutateAsync({
        clusterId,
        accountIds: selectedAccountIds,
      });
      setAddUsersModalOpen(false);
      setSelectedAccountIds([]);
    } catch (error) {
      console.error('Failed to add users to cluster:', error);
    }
  };

  const handleRemoveUser = async (accountId: number) => {
    if (!clusterId || !window.confirm('Are you sure you want to remove this user from the cluster?')) return;
    
    try {
      await removeUserFromClusterMutation.mutateAsync({
        clusterId,
        accountId,
      });
    } catch (error) {
      console.error('Failed to remove user from cluster:', error);
    }
  };

  // Removed handleAccountSelect - now handled by AccountAutocomplete component

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (clusterLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (clusterError || !cluster) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <div className="text-red-800">
          <p className="font-medium">Error loading cluster</p>
          <p className="text-sm mt-1">
            {clusterError instanceof Error ? clusterError.message : 'Cluster not found'}
          </p>
        </div>
        <Button onClick={onBack} className="mt-4">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Clusters
        </Button>
      </div>
    );
  }

  const tabs = [
    { id: 'overview', label: 'Overview', icon: Users },
    { id: 'users', label: 'Users', icon: User },
  ];

  // Removed availableAccounts filtering - now handled by AccountAutocomplete component

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button variant="ghost" onClick={onBack} className="p-2">
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-gray-900">{cluster.name}</h1>
              {cluster.name === "all_users" && (
                <div title="System cluster - cannot be deleted">
                  <Shield className="h-5 w-5 text-blue-500" />
                </div>
              )}
            </div>
            <p className="text-gray-600">Cluster Details</p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <Button onClick={() => onEditCluster(cluster)} className="flex items-center gap-2">
            <Edit className="h-4 w-4" />
            Edit Cluster
          </Button>
          <Button 
            onClick={() => onCloneCluster(cluster)} 
            variant="secondary" 
            className="flex items-center gap-2"
          >
            <Copy className="h-4 w-4" />
            Clone Cluster
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center space-x-2 py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === tab.id
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Icon className="h-4 w-4" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="bg-white shadow rounded-lg">
        {activeTab === 'overview' && (
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div className="flex items-center space-x-3">
                  <Users className="h-5 w-5 text-gray-400" />
                  <div>
                    <p className="text-sm font-medium text-gray-500">Cluster Name</p>
                    <p className="text-lg text-gray-900">{cluster.name}</p>
                  </div>
                </div>
                
                <div className="flex items-center space-x-3">
                  <User className="h-5 w-5 text-gray-400" />
                  <div>
                    <p className="text-sm font-medium text-gray-500">Member Count</p>
                    <p className="text-lg text-gray-900">{cluster.user_count}</p>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-center space-x-3">
                  <Calendar className="h-5 w-5 text-gray-400" />
                  <div>
                    <p className="text-sm font-medium text-gray-500">Created</p>
                    <p className="text-lg text-gray-900">{formatDate(cluster.created_at)}</p>
                  </div>
                </div>

                {cluster.updated_at && (
                  <div className="flex items-center space-x-3">
                    <Calendar className="h-5 w-5 text-gray-400" />
                    <div>
                      <p className="text-sm font-medium text-gray-500">Last Updated</p>
                      <p className="text-lg text-gray-900">{formatDate(cluster.updated_at)}</p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {cluster.description && (
              <div className="mt-6">
                <h3 className="text-sm font-medium text-gray-500 mb-2">Description</h3>
                <p className="text-gray-900 bg-gray-50 rounded-md p-4">{cluster.description}</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'users' && (
          <div className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900">Cluster Members</h3>
              {cluster.name !== "all_users" && (
                <Button
                  onClick={() => setAddUsersModalOpen(true)}
                  size="sm"
                  className="flex items-center gap-2"
                >
                  <Plus className="h-4 w-4" />
                  Add Users
                </Button>
              )}
              {cluster.name === "all_users" && (
                <div className="text-sm text-gray-500 italic">
                  System cluster - automatically contains all users
                </div>
              )}
            </div>
            
            {cluster.users.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableCell header>ID</TableCell>
                    <TableCell header>Username</TableCell>
                    <TableCell header>Email</TableCell>
                    <TableCell header>Added</TableCell>
                    <TableCell header>Actions</TableCell>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {cluster.users.map((user) => (
                    <TableRow key={user.id}>
                      <TableCell className="font-mono text-sm">{user.account_id}</TableCell>
                      <TableCell className="font-medium">{user.username}</TableCell>
                      <TableCell>{user.email}</TableCell>
                      <TableCell className="text-gray-500 text-sm">
                        {formatDate(user.added_at)}
                      </TableCell>
                      <TableCell>
                        {cluster.name !== "all_users" && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleRemoveUser(user.account_id)}
                            className="p-2 h-8 w-8 text-red-600 hover:text-red-700"
                            loading={removeUserFromClusterMutation.isLoading}
                            title="Remove from cluster"
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        )}
                        {cluster.name === "all_users" && (
                          <div title="Cannot remove users from system cluster" className="p-2 h-8 w-8 flex items-center justify-center">
                            <X className="h-4 w-4 text-gray-300" />
                          </div>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="bg-gray-50 rounded-md p-8 text-center">
                <User className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                {cluster.name === "all_users" ? (
                  <p className="text-gray-500 mb-4">System cluster - will automatically contain all users.</p>
                ) : (
                  <>
                    <p className="text-gray-500 mb-4">No users in this cluster.</p>
                    <Button
                      onClick={() => setAddUsersModalOpen(true)}
                      variant="secondary"
                      className="flex items-center gap-2"
                    >
                      <Plus className="h-4 w-4" />
                      Add Users
                    </Button>
                  </>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Add Users Modal */}
      <Modal
        isOpen={addUsersModalOpen}
        onClose={() => {
          setAddUsersModalOpen(false);
          setSelectedAccountIds([]);
        }}
        title="Add Users to Cluster"
        size="lg"
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Select accounts to add to this cluster:
          </p>
          
          <AccountAutocomplete
            selectedAccountIds={selectedAccountIds}
            onAccountSelect={(accountId) => {
              if (!selectedAccountIds.includes(accountId)) {
                setSelectedAccountIds(prev => [...prev, accountId]);
              }
            }}
            onAccountRemove={(accountId) => {
              setSelectedAccountIds(prev => prev.filter(id => id !== accountId));
            }}
            placeholder="Search accounts to add to cluster..."
            maxHeight="300px"
          />
          
          <div className="flex items-center justify-between pt-4">
            <p className="text-sm text-gray-600">
              {selectedAccountIds.length} user{selectedAccountIds.length !== 1 ? 's' : ''} selected
            </p>
            <div className="flex space-x-3">
              <Button
                variant="secondary"
                onClick={() => {
                  setAddUsersModalOpen(false);
                  setSelectedAccountIds([]);
                }}
              >
                Cancel
              </Button>
              <Button
                onClick={handleAddUsers}
                loading={addUsersToClusterMutation.isLoading}
                disabled={selectedAccountIds.length === 0}
              >
                Add {selectedAccountIds.length} User{selectedAccountIds.length !== 1 ? 's' : ''}
              </Button>
            </div>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default ClusterDetails;
