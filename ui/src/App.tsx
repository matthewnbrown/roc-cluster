import React, { useState } from 'react';
import { QueryClient, QueryClientProvider } from 'react-query';
import { Account, ClusterListResponse, ClusterResponse, JobResponse } from './types/api';
import AccountList from './components/AccountList';
import AccountForm from './components/AccountForm';
import AccountDetails from './components/AccountDetails';
import ClusterList from './components/ClusterList';
import ClusterForm from './components/ClusterForm';
import ClusterDetails from './components/ClusterDetails';
import ClusterCloneForm from './components/ClusterCloneForm';
import JobList from './components/JobList';
import JobForm from './components/JobForm';
import JobDetails from './components/JobDetails';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

type ViewState = 'accounts' | 'account-details' | 'account-create' | 'account-edit' | 'clusters' | 'cluster-details' | 'cluster-create' | 'cluster-edit' | 'cluster-clone' | 'jobs' | 'job-details' | 'job-create';

interface AppState {
  view: ViewState;
  selectedAccount?: Account;
  selectedCluster?: ClusterListResponse | ClusterResponse;
  selectedJob?: JobResponse;
}

const App: React.FC = () => {
  const [appState, setAppState] = useState<AppState>({ view: 'accounts' });
  const [accountFormModalOpen, setAccountFormModalOpen] = useState(false);
  const [clusterFormModalOpen, setClusterFormModalOpen] = useState(false);
  const [clusterCloneModalOpen, setClusterCloneModalOpen] = useState(false);
  const [jobFormModalOpen, setJobFormModalOpen] = useState(false);
  const [jobToClone, setJobToClone] = useState<JobResponse | null>(null);

  // Account handlers
  const handleViewAccount = (account: Account) => {
    setAppState({ view: 'account-details', selectedAccount: account });
  };

  const handleEditAccount = (account: Account) => {
    setAppState({ view: 'account-edit', selectedAccount: account });
    setAccountFormModalOpen(true);
  };

  const handleCreateAccount = () => {
    setAppState({ view: 'account-create' });
    setAccountFormModalOpen(true);
  };

  // Cluster handlers
  const handleViewCluster = (cluster: ClusterListResponse) => {
    setAppState({ view: 'cluster-details', selectedCluster: cluster });
  };

  const handleEditCluster = (cluster: ClusterListResponse | ClusterResponse) => {
    setAppState({ view: 'cluster-edit', selectedCluster: cluster });
    setClusterFormModalOpen(true);
  };

  const handleCreateCluster = () => {
    setAppState({ view: 'cluster-create' });
    setClusterFormModalOpen(true);
  };

  const handleCloneCluster = (cluster: ClusterListResponse | ClusterResponse) => {
    setAppState({ view: 'cluster-clone', selectedCluster: cluster });
    setClusterCloneModalOpen(true);
  };

  // Job handlers
  const handleViewJob = (job: JobResponse) => {
    setAppState({ view: 'job-details', selectedJob: job });
  };

  const handleCreateJob = () => {
    setAppState({ view: 'job-create' });
    setJobFormModalOpen(true);
    setJobToClone(null);
  };

  const handleCloneJob = (job: JobResponse) => {
    setAppState({ view: 'job-create' });
    setJobFormModalOpen(true);
    setJobToClone(job);
  };

  // Navigation handlers
  const handleBackToAccounts = () => {
    setAppState({ view: 'accounts' });
  };

  const handleBackToClusters = () => {
    setAppState({ view: 'clusters' });
  };

  const handleBackToJobs = () => {
    setAppState({ view: 'jobs' });
  };

  const handleShowClusters = () => {
    setAppState({ view: 'clusters' });
  };

  const handleShowAccounts = () => {
    setAppState({ view: 'accounts' });
  };

  const handleShowJobs = () => {
    setAppState({ view: 'jobs' });
  };

  // Form close handlers
  const handleAccountFormClose = () => {
    setAccountFormModalOpen(false);
    setAppState({ view: 'accounts' });
  };

  const handleClusterFormClose = () => {
    setClusterFormModalOpen(false);
    setAppState({ view: 'clusters' });
  };

  const handleClusterCloneClose = () => {
    setClusterCloneModalOpen(false);
    setAppState({ view: 'clusters' });
  };

  const handleJobFormClose = () => {
    setJobFormModalOpen(false);
    setJobToClone(null);
    setAppState({ view: 'jobs' });
  };

  const renderContent = () => {
    switch (appState.view) {
      case 'accounts':
        return (
          <AccountList
            onViewAccount={handleViewAccount}
            onEditAccount={handleEditAccount}
            onCreateAccount={handleCreateAccount}
          />
        );
      case 'account-details':
        return appState.selectedAccount ? (
          <AccountDetails
            accountId={appState.selectedAccount.id}
            onBack={handleBackToAccounts}
            onEditAccount={handleEditAccount}
          />
        ) : null;
      case 'clusters':
        return (
          <ClusterList
            onViewCluster={handleViewCluster}
            onEditCluster={handleEditCluster}
            onCreateCluster={handleCreateCluster}
            onCloneCluster={handleCloneCluster}
          />
        );
      case 'cluster-details':
        return appState.selectedCluster ? (
          <ClusterDetails
            clusterId={appState.selectedCluster.id}
            onBack={handleBackToClusters}
            onEditCluster={handleEditCluster}
            onCloneCluster={handleCloneCluster}
          />
        ) : null;
      case 'jobs':
        return (
          <JobList
            onViewJob={handleViewJob}
            onCreateJob={handleCreateJob}
            onCloneJob={handleCloneJob}
          />
        );
      case 'job-details':
        return appState.selectedJob ? (
          <JobDetails
            jobId={appState.selectedJob.id}
            onBack={handleBackToJobs}
          />
        ) : null;
      default:
        return null;
    }
  };

  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <header className="bg-white shadow">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center py-6">
              <div className="flex items-center">
                <h1 className="text-3xl font-bold text-gray-900">ROC Cluster Management</h1>
              </div>
                  <div className="flex items-center space-x-4">
                    <nav className="flex space-x-4">
                      <button
                        onClick={handleShowAccounts}
                        className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                          appState.view.startsWith('account')
                            ? 'bg-primary-100 text-primary-700'
                            : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                        }`}
                      >
                        Accounts
                      </button>
                      <button
                        onClick={handleShowClusters}
                        className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                          appState.view.startsWith('cluster')
                            ? 'bg-primary-100 text-primary-700'
                            : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                        }`}
                      >
                        Clusters
                      </button>
                      <button
                        onClick={handleShowJobs}
                        className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                          appState.view.startsWith('job')
                            ? 'bg-primary-100 text-primary-700'
                            : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                        }`}
                      >
                        Jobs
                      </button>
                    </nav>
                  </div>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
          <div className="px-4 py-6 sm:px-0">
            {renderContent()}
          </div>
        </main>

        {/* Account Form Modal */}
        <AccountForm
          isOpen={accountFormModalOpen}
          onClose={handleAccountFormClose}
          account={appState.selectedAccount}
        />

        {/* Cluster Form Modal */}
        <ClusterForm
          isOpen={clusterFormModalOpen}
          onClose={handleClusterFormClose}
          cluster={appState.selectedCluster}
        />

        {/* Cluster Clone Modal */}
        {appState.selectedCluster && (
          <ClusterCloneForm
            isOpen={clusterCloneModalOpen}
            onClose={handleClusterCloneClose}
            sourceCluster={appState.selectedCluster}
          />
        )}

        {/* Job Form Modal */}
        <JobForm
          isOpen={jobFormModalOpen}
          onClose={handleJobFormClose}
          jobToClone={jobToClone}
        />
      </div>
    </QueryClientProvider>
  );
};

export default App;
