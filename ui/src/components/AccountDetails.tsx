import React, { useState } from 'react';
import { Account, SetCreditSavingRequest } from '../types/api';
import { useAccount } from '../hooks/useAccounts';
import { useCookies as useCookiesHook, useUpsertCookies, useDeleteCookies } from '../hooks/useCookies';
import { useAccountCreditLogs as useCreditLogsHook } from '../hooks/useCreditLogs';
import { useAccountClusters, useClusters, useAddUsersToCluster, useRemoveUserFromCluster } from '../hooks/useClusters';
import { useAccountMetadata } from '../hooks/useMetadata';
import { useArmoryPreferences, usePurchaseArmoryByPreferences } from '../hooks/usePreferences';
import { actionsApi } from '../services/api';
import Button from './ui/Button';
import Modal from './ui/Modal';
import { Table, TableHeader, TableBody, TableRow, TableCell } from './ui/Table';
import Pagination from './ui/Pagination';
import { ArrowLeft, Edit, Trash2, Cookie, CreditCard, User, Mail, Calendar, Shield, Users, Plus, X, Settings, Info } from 'lucide-react';
import ClusterTag from './ui/ClusterTag';
// Input import removed as it's not used in this component
import AccountPreferences from './AccountPreferences';

interface AccountDetailsProps {
  accountId: number;
  onBack: () => void;
  onEditAccount: (account: Account) => void;
}

const AccountDetails: React.FC<AccountDetailsProps> = ({
  accountId,
  onBack,
  onEditAccount,
}) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'cookies' | 'credit-logs' | 'clusters' | 'preferences'>('overview');
  const [creditLogsPage, setCreditLogsPage] = useState(1);
  const [cookiesModalOpen, setCookiesModalOpen] = useState(false);
  const [cookiesText, setCookiesText] = useState('');
  const [addToClusterModalOpen, setAddToClusterModalOpen] = useState(false);
  const [creditSavingLoading, setCreditSavingLoading] = useState(false);

  const { data: account, isLoading: accountLoading, error: accountError } = useAccount(accountId);
  const { data: cookies, isLoading: cookiesLoading, error: cookiesError } = useCookiesHook(accountId);
  const { data: creditLogsData, isLoading: creditLogsLoading } = useCreditLogsHook(accountId, creditLogsPage, 10);
  const { data: clusters, isLoading: clustersLoading, error: clustersError } = useAccountClusters(accountId);
  const { data: allClustersData } = useClusters(1, 100); // Get all clusters for the add modal
  const { data: metadata, isLoading: metadataLoading, error: metadataError, refetch: refetchMetadata } = useAccountMetadata(accountId, 0, true);
  const { data: armoryPreferences } = useArmoryPreferences(accountId);
  const addUsersToClusterMutation = useAddUsersToCluster();
  const removeUserFromClusterMutation = useRemoveUserFromCluster();
  const purchaseArmoryByPreferencesMutation = usePurchaseArmoryByPreferences();

  const upsertCookiesMutation = useUpsertCookies();
  const deleteCookiesMutation = useDeleteCookies();

  const handleSaveCookies = async () => {
    if (!accountId) return;
    
    try {
      await upsertCookiesMutation.mutateAsync({
        accountId,
        data: {
          account_id: accountId,
          cookies: cookiesText,
        },
      });
      setCookiesModalOpen(false);
      setCookiesText('');
    } catch (error) {
      console.error('Failed to save cookies:', error);
    }
  };

  const handleSetCreditSaving = async (value: 'on' | 'off') => {
    if (!accountId) return;
    
    setCreditSavingLoading(true);
    try {
      const request: SetCreditSavingRequest = {
        acting_user: {
          id_type: 'id',
          id: accountId.toString(),
        },
        max_retries: 0,
        value,
      };
      
      const response = await actionsApi.setCreditSaving(request);
      if (response.success) {
        alert(`Credit saving ${value === 'on' ? 'enabled' : 'disabled'} successfully!`);
        // Refresh metadata to show updated credit saving status
        refetchMetadata();
      } else {
        alert(`Failed to set credit saving: ${response.error}`);
      }
    } catch (error) {
      console.error('Failed to set credit saving:', error);
      alert('Failed to set credit saving. Please try again.');
    } finally {
      setCreditSavingLoading(false);
    }
  };

  const handleBuyWithPreferences = async () => {
    if (!accountId) return;
    
    try {
      const response = await purchaseArmoryByPreferencesMutation.mutateAsync(accountId);
      if (response.success) {
        alert('Armory purchase completed successfully!');
        // Refresh metadata to show updated gold amounts
        refetchMetadata();
      } else {
        alert(`Failed to purchase armory: ${response.error}`);
      }
    } catch (error) {
      console.error('Failed to purchase armory:', error);
      alert('Failed to purchase armory. Please try again.');
    }
  };

  const handleDeleteCookies = async () => {
    if (!accountId || !window.confirm('Are you sure you want to delete the cookies for this account?')) return;
    
    try {
      await deleteCookiesMutation.mutateAsync(accountId);
    } catch (error) {
      console.error('Failed to delete cookies:', error);
    }
  };

  const handleAddToCluster = async (clusterId: number) => {
    if (!accountId) return;
    
    try {
      await addUsersToClusterMutation.mutateAsync({
        clusterId,
        accountIds: [accountId],
      });
      setAddToClusterModalOpen(false);
    } catch (error) {
      console.error('Failed to add user to cluster:', error);
    }
  };

  const handleRemoveFromCluster = async (clusterId: number) => {
    if (!accountId || !window.confirm('Are you sure you want to remove this account from the cluster?')) return;
    
    try {
      await removeUserFromClusterMutation.mutateAsync({
        clusterId,
        accountId,
      });
    } catch (error) {
      console.error('Failed to remove user from cluster:', error);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    // Check if it's the Unix epoch (1970-01-01T00:00:00+00:00 or similar)
    if (date.getTime() === 0 || date.getFullYear() === 1970) {
      return 'Never';
    }
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const LoadingPlaceholder = ({ width = 'w-20', height = 'h-4' }: { width?: string; height?: string }) => (
    <div className={`animate-pulse bg-gray-300 rounded ${width} ${height}`}></div>
  );

  if (accountLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (accountError || !account) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <div className="text-red-800">
          <p className="font-medium">Error loading account</p>
          <p className="text-sm mt-1">
            {accountError instanceof Error ? accountError.message : 'Account not found'}
          </p>
        </div>
        <Button onClick={onBack} className="mt-4">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Accounts
        </Button>
      </div>
    );
  }

  const tabs = [
    { id: 'overview', label: 'Overview', icon: User },
    { id: 'cookies', label: 'Cookies', icon: Cookie },
    { id: 'credit-logs', label: 'Credit Logs', icon: CreditCard },
    { id: 'clusters', label: 'Clusters', icon: Users },
    { id: 'preferences', label: 'Preferences', icon: Settings },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button variant="ghost" onClick={onBack} className="p-2">
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{account.username}</h1>
            <p className="text-gray-600">Account Details</p>
          </div>
        </div>
        <Button onClick={() => onEditAccount(account)} className="flex items-center gap-2">
          <Edit className="h-4 w-4" />
          Edit Account
        </Button>
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
            {/* Account Basic Info */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
              <div className="space-y-4">
                <div className="flex items-center space-x-3">
                  <User className="h-5 w-5 text-gray-400" />
                  <div>
                    <p className="text-sm font-medium text-gray-500">Username</p>
                    <p className="text-lg text-gray-900">{account.username}</p>
                  </div>
                </div>
                
                <div className="flex items-center space-x-3">
                  <Mail className="h-5 w-5 text-gray-400" />
                  <div>
                    <p className="text-sm font-medium text-gray-500">Email</p>
                    <p className="text-lg text-gray-900">{account.email}</p>
                  </div>
                </div>

                <div className="flex items-center space-x-3">
                  <Shield className="h-5 w-5 text-gray-400" />
                  <div>
                    <p className="text-sm font-medium text-gray-500">Status</p>
                    <span
                      className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        account.is_active
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-100 text-red-800'
                      }`}
                    >
                      {account.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-center space-x-3">
                  <Calendar className="h-5 w-5 text-gray-400" />
                  <div>
                    <p className="text-sm font-medium text-gray-500">Created</p>
                    <p className="text-lg text-gray-900">{formatDate(account.created_at)}</p>
                  </div>
                </div>

                {account.updated_at && (
                  <div className="flex items-center space-x-3">
                    <Calendar className="h-5 w-5 text-gray-400" />
                    <div>
                      <p className="text-sm font-medium text-gray-500">Last Updated</p>
                      <p className="text-lg text-gray-900">{formatDate(account.updated_at)}</p>
                    </div>
                  </div>
                )}

                {account.last_login && (
                  <div className="flex items-center space-x-3">
                    <Calendar className="h-5 w-5 text-gray-400" />
                    <div>
                      <p className="text-sm font-medium text-gray-500">Last Login</p>
                      <p className="text-lg text-gray-900">{formatDate(account.last_login)}</p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Game Metadata */}
            <div className="border-t pt-6 mb-8">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center space-x-3">
                  <Info className="h-5 w-5 text-gray-400" />
                  <h3 className="text-lg font-medium text-gray-900">Game Status</h3>
                </div>
                <Button
                  onClick={() => refetchMetadata()}
                  size="sm"
                  disabled={metadataLoading}
                  className="flex items-center gap-2"
                >
                  <Info className="h-4 w-4" />
                  {metadataLoading ? 'Refreshing...' : 'Refresh'}
                </Button>
              </div>

              {metadataError ? (
                <div className="bg-red-50 border border-red-200 rounded-md p-4">
                  <p className="text-red-800">
                    Error loading game metadata: {metadataError instanceof Error ? metadataError.message : 'Unknown error'}
                  </p>
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Game Stats */}
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    <div className="bg-gray-50 rounded-lg p-4">
                      <div className="flex items-center space-x-2 mb-2">
                        <Shield className="h-5 w-5 text-gray-400" />
                        <h4 className="text-sm font-medium text-gray-900">Rank</h4>
                      </div>
                      {metadataLoading ? (
                        <LoadingPlaceholder width="w-16" height="h-6" />
                      ) : metadata ? (
                        <p className="text-lg text-gray-700">#{metadata.rank.toLocaleString()}</p>
                      ) : (
                        <p className="text-sm text-gray-500">No data</p>
                      )}
                    </div>

                    <div className="bg-gray-50 rounded-lg p-4">
                      <div className="flex items-center space-x-2 mb-2">
                        <CreditCard className="h-5 w-5 text-gray-400" />
                        <h4 className="text-sm font-medium text-gray-900">Credits</h4>
                      </div>
                      {metadataLoading ? (
                        <LoadingPlaceholder width="w-20" height="h-6" />
                      ) : metadata ? (
                        <p className="text-lg text-gray-700">{metadata.credits.toLocaleString()}</p>
                      ) : (
                        <p className="text-sm text-gray-500">No data</p>
                      )}
                    </div>

                    <div className="bg-gray-50 rounded-lg p-4">
                      <div className="flex items-center space-x-2 mb-2">
                        <div className="h-5 w-5 text-gray-400">💰</div>
                        <h4 className="text-sm font-medium text-gray-900">Gold</h4>
                      </div>
                      {metadataLoading ? (
                        <LoadingPlaceholder width="w-20" height="h-6" />
                      ) : metadata ? (
                        <p className="text-lg text-gray-700">{metadata.gold.toLocaleString()}</p>
                      ) : (
                        <p className="text-sm text-gray-500">No data</p>
                      )}
                    </div>

                    <div className="bg-gray-50 rounded-lg p-4">
                      <div className="flex items-center space-x-2 mb-2">
                        <div className="h-5 w-5 text-gray-400">⚡</div>
                        <h4 className="text-sm font-medium text-gray-900">Turns</h4>
                      </div>
                      {metadataLoading ? (
                        <LoadingPlaceholder width="w-12" height="h-6" />
                      ) : metadata ? (
                        <p className="text-lg text-gray-700">{metadata.turns}</p>
                      ) : (
                        <p className="text-sm text-gray-500">No data</p>
                      )}
                    </div>
                  </div>

                  {/* Activity & Settings */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-gray-50 rounded-lg p-4">
                      <h4 className="text-sm font-medium text-gray-900 mb-3">Recent Activity</h4>
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">Next Turn:</span>
                          {metadataLoading ? (
                            <LoadingPlaceholder width="w-24" height="h-4" />
                          ) : metadata ? (
                            <span className="text-sm text-gray-900">{formatDate(metadata.next_turn)}</span>
                          ) : (
                            <span className="text-sm text-gray-500">No data</span>
                          )}
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">Last Hit:</span>
                          {metadataLoading ? (
                            <LoadingPlaceholder width="w-24" height="h-4" />
                          ) : metadata ? (
                            <span className="text-sm text-gray-900">{formatDate(metadata.last_hit)}</span>
                          ) : (
                            <span className="text-sm text-gray-500">No data</span>
                          )}
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">Last Sabotaged:</span>
                          {metadataLoading ? (
                            <LoadingPlaceholder width="w-24" height="h-4" />
                          ) : metadata ? (
                            <span className="text-sm text-gray-900">{formatDate(metadata.last_sabbed)}</span>
                          ) : (
                            <span className="text-sm text-gray-500">No data</span>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="bg-gray-50 rounded-lg p-4">
                      <h4 className="text-sm font-medium text-gray-900 mb-3">Credit Statistics</h4>
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">Credits Given:</span>
                          {metadataLoading ? (
                            <LoadingPlaceholder width="w-16" height="h-4" />
                          ) : metadata ? (
                            <span className="text-sm text-gray-900">{metadata.credits_given.toLocaleString()}</span>
                          ) : (
                            <span className="text-sm text-gray-500">No data</span>
                          )}
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">Credits Received:</span>
                          {metadataLoading ? (
                            <LoadingPlaceholder width="w-16" height="h-4" />
                          ) : metadata ? (
                            <span className="text-sm text-gray-900">{metadata.credits_received.toLocaleString()}</span>
                          ) : (
                            <span className="text-sm text-gray-500">No data</span>
                          )}
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">Credit Saving:</span>
                          {metadataLoading ? (
                            <LoadingPlaceholder width="w-16" height="h-4" />
                          ) : metadata ? (
                            <span className={`text-sm font-semibold ${metadata.saving === 'enabled' ? 'text-green-600' : 'text-red-600'}`}>
                              {metadata.saving === 'enabled' ? 'Enabled' : 'Disabled'}
                            </span>
                          ) : (
                            <span className="text-sm text-gray-500">No data</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Additional Info */}
                  {metadata && (
                    <div className="bg-gray-50 rounded-lg p-4">
                      <h4 className="text-sm font-medium text-gray-900 mb-3">Additional Information</h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">User ID:</span>
                          <span className="text-sm text-gray-900 font-mono">{metadata.userid}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">Alliance ID:</span>
                          <span className="text-sm text-gray-900 font-mono">{metadata.allianceid}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">Gets:</span>
                          <span className="text-sm text-gray-900">{metadata.gets}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">Last Clicked:</span>
                          <span className="text-sm text-gray-900">{formatDate(metadata.lastclicked)}</span>
                        </div>
                      </div>
                      {metadata.mail && (
                        <div className="mt-3 pt-3 border-t border-gray-200">
                          <div className="flex items-center space-x-2">
                            <Mail className="h-4 w-4 text-gray-400" />
                            <span className="text-sm text-gray-600">Mail:</span>
                            <span className="text-sm text-gray-900">{metadata.mail}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
            
            {/* Credit Saving Actions */}
            <div className="border-t pt-6">
              <div className="flex items-center space-x-3 mb-4">
                <Settings className="h-5 w-5 text-gray-400" />
                <h3 className="text-lg font-medium text-gray-900">Account Actions</h3>
              </div>
              
              <div className="space-y-4">
                {/* Credit Saving */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-sm font-medium text-gray-900">Credit Saving</h4>
                      <p className="text-sm text-gray-500">Enable or disable automatic credit saving for this account</p>
                    </div>
                    <div className="flex space-x-2">
                      <Button
                        onClick={() => handleSetCreditSaving('on')}
                        disabled={creditSavingLoading}
                        className="bg-green-600 hover:bg-green-700 text-white"
                      >
                        {creditSavingLoading ? 'Loading...' : 'Enable'}
                      </Button>
                      <Button
                        onClick={() => handleSetCreditSaving('off')}
                        disabled={creditSavingLoading}
                        className="bg-red-600 hover:bg-red-700 text-white"
                      >
                        {creditSavingLoading ? 'Loading...' : 'Disable'}
                      </Button>
                    </div>
                  </div>
                </div>

                {/* Buy With Preferences - Only show if user has preferences */}
                {armoryPreferences && (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="text-sm font-medium text-gray-900">Armory Purchase</h4>
                        <p className="text-sm text-gray-500">Purchase armory items based on saved preferences</p>
                      </div>
                      <Button
                        onClick={handleBuyWithPreferences}
                        disabled={purchaseArmoryByPreferencesMutation.isLoading}
                        className="bg-blue-600 hover:bg-blue-700 text-white"
                      >
                        {purchaseArmoryByPreferencesMutation.isLoading ? 'Purchasing...' : 'Buy With Preferences'}
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'cookies' && (
          <div className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900">Account Cookies</h3>
              <div className="flex space-x-2">
                <Button
                  onClick={() => {
                    setCookiesText(cookies?.cookies || '');
                    setCookiesModalOpen(true);
                  }}
                  size="sm"
                >
                  {cookies ? 'Update Cookies' : 'Add Cookies'}
                </Button>
                {cookies && (
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={handleDeleteCookies}
                    loading={deleteCookiesMutation.isLoading}
                  >
                    <Trash2 className="h-4 w-4 mr-1" />
                    Delete
                  </Button>
                )}
              </div>
            </div>

            {cookiesLoading ? (
              <div className="flex items-center justify-center h-32">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
              </div>
            ) : cookiesError ? (
              <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
                <p className="text-yellow-800">No cookies found for this account.</p>
              </div>
            ) : cookies ? (
              <div className="bg-gray-50 rounded-md p-4">
                <pre className="text-sm text-gray-700 whitespace-pre-wrap break-all">
                  {cookies.cookies}
                </pre>
                <p className="text-xs text-gray-500 mt-2">
                  Last updated: {formatDate(cookies.updated_at || cookies.created_at)}
                </p>
              </div>
            ) : (
              <div className="bg-gray-50 rounded-md p-8 text-center">
                <Cookie className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500">No cookies configured for this account.</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'credit-logs' && (
          <div className="p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Credit Logs</h3>
            
            {creditLogsLoading ? (
              <div className="flex items-center justify-center h-32">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
              </div>
            ) : creditLogsData && creditLogsData.data.length > 0 ? (
              <>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableCell header>Target User</TableCell>
                      <TableCell header>Amount</TableCell>
                      <TableCell header>Status</TableCell>
                      <TableCell header>Date</TableCell>
                      <TableCell header>Error</TableCell>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {creditLogsData.data.map((log) => (
                      <TableRow key={log.id}>
                        <TableCell className="font-mono text-sm">{log.target_user_id}</TableCell>
                        <TableCell>{log.amount.toLocaleString()}</TableCell>
                        <TableCell>
                          <span
                            className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                              log.success
                                ? 'bg-green-100 text-green-800'
                                : 'bg-red-100 text-red-800'
                            }`}
                          >
                            {log.success ? 'Success' : 'Failed'}
                          </span>
                        </TableCell>
                        <TableCell className="text-gray-500">
                          {formatDate(log.timestamp)}
                        </TableCell>
                        <TableCell className="text-red-600 text-sm">
                          {log.error_message || '-'}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>

                {creditLogsData.pagination.total_pages > 1 && (
                  <div className="mt-4">
                    <Pagination
                      currentPage={creditLogsPage}
                      totalPages={creditLogsData.pagination.total_pages}
                      onPageChange={setCreditLogsPage}
                    />
                  </div>
                )}
              </>
            ) : (
              <div className="bg-gray-50 rounded-md p-8 text-center">
                <CreditCard className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500">No credit logs found for this account.</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'clusters' && (
          <div className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900">Cluster Membership</h3>
              <Button
                onClick={() => setAddToClusterModalOpen(true)}
                size="sm"
                className="flex items-center gap-2"
              >
                <Plus className="h-4 w-4" />
                Add to Cluster
              </Button>
            </div>
            
            {clustersLoading ? (
              <div className="flex items-center justify-center h-32">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
              </div>
            ) : clustersError ? (
              <div className="bg-red-50 border border-red-200 rounded-md p-4">
                <p className="text-red-800">Error loading cluster information.</p>
              </div>
            ) : clusters && clusters.length > 0 ? (
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {clusters.map((cluster) => (
                    <div key={cluster.id} className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                      <div className="flex items-center justify-between mb-2">
                        <ClusterTag name={cluster.name} description={cluster.description} size="md" />
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRemoveFromCluster(cluster.id)}
                          className="p-1 h-8 w-8 text-red-600 hover:text-red-700"
                          loading={removeUserFromClusterMutation.isLoading}
                          title="Remove from cluster"
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                      {cluster.description && (
                        <p className="text-sm text-gray-600 mb-2">{cluster.description}</p>
                      )}
                      {cluster.added_at && (
                        <p className="text-xs text-gray-500">
                          Added: {formatDate(cluster.added_at)}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="bg-gray-50 rounded-md p-8 text-center">
                <Users className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500 mb-4">This account is not a member of any clusters.</p>
                <Button
                  onClick={() => setAddToClusterModalOpen(true)}
                  variant="secondary"
                  className="flex items-center gap-2"
                >
                  <Plus className="h-4 w-4" />
                  Add to Cluster
                </Button>
              </div>
            )}
          </div>
        )}

        {activeTab === 'preferences' && account && (
          <div className="p-6">
            <AccountPreferences
              account={account}
              onClose={() => {}} // No-op since we're not using a modal
            />
          </div>
        )}

      </div>

      {/* Cookies Modal */}
      <Modal
        isOpen={cookiesModalOpen}
        onClose={() => setCookiesModalOpen(false)}
        title="Edit Cookies"
        size="lg"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Cookies (JSON format)
            </label>
            <textarea
              value={cookiesText}
              onChange={(e) => setCookiesText(e.target.value)}
              className="w-full h-64 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 font-mono text-sm"
              placeholder="Paste your cookies here..."
            />
          </div>
          <div className="flex justify-end space-x-3">
            <Button
              variant="secondary"
              onClick={() => setCookiesModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={handleSaveCookies}
              loading={upsertCookiesMutation.isLoading}
            >
              Save Cookies
            </Button>
          </div>
        </div>
      </Modal>

      {/* Add to Cluster Modal */}
      <Modal
        isOpen={addToClusterModalOpen}
        onClose={() => setAddToClusterModalOpen(false)}
        title="Add to Cluster"
        size="md"
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Select a cluster to add this account to:
          </p>
          
          {allClustersData && allClustersData.data.length > 0 ? (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {allClustersData.data
                .filter(cluster => !clusters?.some(accountCluster => accountCluster.id === cluster.id))
                .map((cluster) => (
                  <div
                    key={cluster.id}
                    className="flex items-center justify-between p-3 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer"
                    onClick={() => handleAddToCluster(cluster.id)}
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <ClusterTag name={cluster.name} size="sm" />
                        <span className="text-sm text-gray-500">
                          ({cluster.user_count || 0} members)
                        </span>
                      </div>
                      {cluster.description && (
                        <p className="text-sm text-gray-600 mt-1">{cluster.description}</p>
                      )}
                    </div>
                    <Button
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleAddToCluster(cluster.id);
                      }}
                      loading={addUsersToClusterMutation.isLoading}
                    >
                      Add
                    </Button>
                  </div>
                ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Users className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500">No clusters available to add this account to.</p>
            </div>
          )}
          
          <div className="flex justify-end pt-4">
            <Button
              variant="secondary"
              onClick={() => setAddToClusterModalOpen(false)}
            >
              Cancel
            </Button>
          </div>
        </div>
      </Modal>

    </div>
  );
};

export default AccountDetails;
