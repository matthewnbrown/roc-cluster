import React, { useState } from 'react';
import { useAccounts, useDeleteAccount } from '../hooks/useAccounts';
import { Account } from '../types/api';
import { Table, TableHeader, TableBody, TableRow, TableCell } from './ui/Table';
import Button from './ui/Button';
import Pagination from './ui/Pagination';
import { Plus, Edit, Trash2, Search } from 'lucide-react';
import Input from './ui/Input';
import AccountClusters from './AccountClusters';

interface AccountListProps {
  onViewAccount: (account: Account) => void;
  onEditAccount: (account: Account) => void;
  onCreateAccount: () => void;
}

const AccountList: React.FC<AccountListProps> = ({
  onViewAccount,
  onEditAccount,
  onCreateAccount,
}) => {
  const [page, setPage] = useState(1);
  const [perPage] = useState(20);
  const [searchTerm, setSearchTerm] = useState('');

  const { data: accountsData, isLoading, error } = useAccounts(page, perPage, searchTerm);
  const deleteAccountMutation = useDeleteAccount();

  const handleDeleteAccount = async (account: Account) => {
    if (window.confirm(`Are you sure you want to delete account "${account.username}"?`)) {
      try {
        await deleteAccountMutation.mutateAsync(account.id);
      } catch (error) {
        console.error('Failed to delete account:', error);
      }
    }
  };

  // Reset to page 1 when search term changes
  React.useEffect(() => {
    setPage(1);
  }, [searchTerm]);

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
          <p className="font-medium">Error loading accounts</p>
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
          <h1 className="text-2xl font-bold text-gray-900">Accounts</h1>
          <p className="text-gray-600">
            Manage your ROC accounts ({accountsData?.pagination.total || 0} total)
          </p>
        </div>
        <Button onClick={onCreateAccount} className="flex items-center gap-2">
          <Plus className="h-4 w-4" />
          Add Account
        </Button>
      </div>

      {/* Search */}
      <div className="max-w-md relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <Search className="h-5 w-5 text-gray-400" />
        </div>
        <Input
          placeholder="Search accounts..."
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
                <TableCell header className="min-w-[120px]">Username</TableCell>
                <TableCell header className="min-w-[180px]">Email</TableCell>
                <TableCell header className="min-w-[150px]">Clusters</TableCell>
                <TableCell header className="w-20">Status</TableCell>
                <TableCell header className="w-40">Actions</TableCell>
              </TableRow>
            </TableHeader>
            <TableBody>
            {!accountsData?.data || accountsData.data.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8 text-gray-500">
                  {searchTerm ? 'No accounts found matching your search.' : 'No accounts found.'}
                </TableCell>
              </TableRow>
            ) : (
              accountsData?.data.map((account) => (
                <TableRow 
                  key={account.id} 
                  className="cursor-pointer hover:bg-gray-50 transition-colors"
                  onClick={() => onViewAccount(account)}
                >
                  <TableCell className="font-mono text-sm">{account.id}</TableCell>
                  <TableCell className="font-medium">{account.username}</TableCell>
                  <TableCell className="truncate">{account.email}</TableCell>
                  <TableCell>
                    <AccountClusters accountId={account.id} maxVisible={2} />
                  </TableCell>
                  <TableCell>
                    <span
                      className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        account.is_active
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-100 text-red-800'
                      }`}
                    >
                      {account.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center space-x-3" onClick={(e) => e.stopPropagation()}>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onEditAccount(account)}
                        className="p-2 h-10 w-10"
                        title="Edit account"
                      >
                        <Edit className="h-5 w-5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteAccount(account)}
                        className="p-2 h-10 w-10 text-red-600 hover:text-red-700"
                        loading={deleteAccountMutation.isLoading}
                        title="Delete account"
                      >
                        <Trash2 className="h-5 w-5" />
                      </Button>
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
      {accountsData && accountsData.pagination.total_pages > 1 && (
        <Pagination
          currentPage={page}
          totalPages={accountsData.pagination.total_pages}
          onPageChange={setPage}
        />
      )}
    </div>
  );
};

export default AccountList;
