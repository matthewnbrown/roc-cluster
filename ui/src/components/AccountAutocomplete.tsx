import React, { useState, useRef, useEffect } from 'react';
import { Search, X, Check, ChevronDown } from 'lucide-react';
import { useAccountSearch, useAccountsByIds } from '../hooks/useAccounts';
import { Account } from '../types/api';

interface AccountAutocompleteProps {
  selectedAccountIds: number[];
  onAccountSelect: (account: Account) => void;
  onAccountRemove: (accountId: number) => void;
  placeholder?: string;
  maxHeight?: string;
  disabled?: boolean;
}

const AccountAutocomplete: React.FC<AccountAutocompleteProps> = ({
  selectedAccountIds,
  onAccountSelect,
  onAccountRemove,
  placeholder = "Search accounts...",
  maxHeight = "200px",
  disabled = false,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const { data: searchResults, isLoading } = useAccountSearch(searchTerm);
  const { data: accountsByIds, isLoading: isLoadingByIds } = useAccountsByIds(selectedAccountIds);
  
  const availableAccounts = searchResults?.data || [];
  
  // Use accounts fetched by IDs as the selected accounts
  const selectedAccounts = accountsByIds || [];

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setFocusedIndex(prev => 
            prev < availableAccounts.length - 1 ? prev + 1 : prev
          );
          break;
        case 'ArrowUp':
          e.preventDefault();
          setFocusedIndex(prev => prev > 0 ? prev - 1 : prev);
          break;
        case 'Enter':
          e.preventDefault();
          if (focusedIndex >= 0 && focusedIndex < availableAccounts.length) {
            const account = availableAccounts[focusedIndex];
            if (!selectedAccountIds.includes(account.id)) {
              onAccountSelect(account);
            }
            setSearchTerm('');
            setIsOpen(false);
            setFocusedIndex(-1);
          }
          break;
        case 'Escape':
          setIsOpen(false);
          setFocusedIndex(-1);
          inputRef.current?.blur();
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, focusedIndex, availableAccounts, selectedAccountIds, onAccountSelect]);

  // Handle click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
        setFocusedIndex(-1);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchTerm(value);
    setIsOpen(value.length >= 2);
    setFocusedIndex(-1);
  };

  const handleAccountSelect = (account: Account) => {
    if (!selectedAccountIds.includes(account.id)) {
      onAccountSelect(account);
    }
    setSearchTerm('');
    setIsOpen(false);
    setFocusedIndex(-1);
  };

  const handleInputFocus = () => {
    if (searchTerm.length >= 2) {
      setIsOpen(true);
    }
  };

  const clearSearch = () => {
    setSearchTerm('');
    setIsOpen(false);
    setFocusedIndex(-1);
    inputRef.current?.focus();
  };

  return (
    <div className="space-y-3">
      {/* Search Input */}
      <div className="relative">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            ref={inputRef}
            type="text"
            value={searchTerm}
            onChange={handleInputChange}
            onFocus={handleInputFocus}
            placeholder={placeholder}
            disabled={disabled}
            className="w-full pl-10 pr-10 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
          />
          {searchTerm && (
            <button
              onClick={clearSearch}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <X className="h-4 w-4" />
            </button>
          )}
          <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
        </div>

        {/* Dropdown */}
        {isOpen && (
          <div
            ref={dropdownRef}
            className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-y-auto"
            style={{ maxHeight }}
          >
            {isLoading ? (
              <div className="p-3 text-center text-gray-500">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600 mx-auto"></div>
                <p className="text-sm mt-1">Searching...</p>
              </div>
            ) : availableAccounts.length === 0 ? (
              <div className="p-3 text-center text-gray-500">
                <p className="text-sm">No accounts found</p>
              </div>
            ) : (
              availableAccounts.map((account, index) => {
                const isSelected = selectedAccountIds.includes(account.id);
                const isFocused = index === focusedIndex;
                
                return (
                  <div
                    key={account.id}
                    onClick={() => handleAccountSelect(account)}
                    className={`p-3 cursor-pointer border-b border-gray-100 last:border-b-0 ${
                      isFocused ? 'bg-blue-50' : 'hover:bg-gray-50'
                    } ${isSelected ? 'bg-green-50' : ''}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <p className={`font-medium ${isSelected ? 'text-green-800' : 'text-gray-900'}`}>
                          {account.username}
                        </p>
                        <p className={`text-sm ${isSelected ? 'text-green-600' : 'text-gray-500'}`}>
                          {account.email}
                        </p>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className="text-xs text-gray-400 font-mono">
                          #{account.id}
                        </span>
                        {isSelected && (
                          <Check className="h-4 w-4 text-green-600" />
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>

      {/* Selected Accounts */}
      {selectedAccountIds.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium text-gray-700">
            Selected Accounts ({selectedAccountIds.length})
          </p>
          {isLoadingByIds ? (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-primary-600"></div>
              Loading account details...
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              {selectedAccounts.map((account) => (
                <span
                  key={account.id}
                  className="inline-flex items-center gap-1 px-3 py-1 bg-blue-100 text-blue-800 text-sm rounded-full"
                >
                  <span>{account.username}</span>
                  <button
                    onClick={() => onAccountRemove(account.id)}
                    className="text-blue-600 hover:text-blue-800 focus:outline-none"
                    disabled={disabled}
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AccountAutocomplete;
