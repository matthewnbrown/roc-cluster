import React, { useState } from 'react';
import { QueryClient, QueryClientProvider } from 'react-query';
import { BrowserRouter as Router, Routes, Route, useNavigate, useParams, useLocation } from 'react-router-dom';
import { Account, ClusterListResponse, ClusterResponse, JobResponse } from './types/api';
import { getCurrentTimestamp } from './utils/dateUtils';
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
import FavoriteJobsManager from './components/FavoriteJobsManager';
import SystemNotifications from './components/SystemNotifications';
import SystemStatus from './components/SystemStatus';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// Main App component with routing
const AppContent: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [accountFormModalOpen, setAccountFormModalOpen] = useState(false);
  const [clusterFormModalOpen, setClusterFormModalOpen] = useState(false);
  const [clusterCloneModalOpen, setClusterCloneModalOpen] = useState(false);
  const [jobFormModalOpen, setJobFormModalOpen] = useState(false);
  const [jobToClone, setJobToClone] = useState<JobResponse | null>(null);
  const [showFavoriteJobs, setShowFavoriteJobs] = useState(false);
  const [selectedAccount, setSelectedAccount] = useState<Account | undefined>(undefined);
  const [selectedCluster, setSelectedCluster] = useState<ClusterListResponse | ClusterResponse | undefined>(undefined);
  const [showSystemNotifications, setShowSystemNotifications] = useState(false);
  const [showSystemStatus, setShowSystemStatus] = useState(false);

  // Account handlers
  const handleViewAccount = (account: Account) => {
    navigate(`/accounts/${account.id}`);
  };

  const handleEditAccount = (account: Account) => {
    setSelectedAccount(account);
    setAccountFormModalOpen(true);
  };

  const handleCreateAccount = () => {
    setSelectedAccount(undefined);
    setAccountFormModalOpen(true);
  };

  // Cluster handlers
  const handleViewCluster = (cluster: ClusterListResponse) => {
    navigate(`/clusters/${cluster.id}`);
  };

  const handleEditCluster = (cluster: ClusterListResponse | ClusterResponse) => {
    setSelectedCluster(cluster);
    setClusterFormModalOpen(true);
  };

  const handleCreateCluster = () => {
    setSelectedCluster(undefined);
    setClusterFormModalOpen(true);
  };

  const handleCloneCluster = (cluster: ClusterListResponse | ClusterResponse) => {
    setSelectedCluster(cluster);
    setClusterCloneModalOpen(true);
  };

  // Job handlers
  const handleViewJob = (job: JobResponse) => {
    navigate(`/jobs/${job.id}`);
  };

  const handleCreateJob = () => {
    setJobFormModalOpen(true);
    setJobToClone(null);
  };

  const handleCloneJob = (job: JobResponse) => {
    setJobFormModalOpen(true);
    setJobToClone(job);
  };

  // Favorite job handlers
  const handleUseFavorite = (favorite: any) => {
    // Convert favorite job config to JobResponse format and clone it
    const jobToClone: JobResponse = {
      id: 0, // Temporary ID for cloning
      name: favorite.name,
      description: favorite.description,
      status: 'pending' as any,
      parallel_execution: favorite.job_config.parallel_execution,
      created_at: getCurrentTimestamp(),
      started_at: undefined,
      completed_at: undefined,
      total_steps: favorite.job_config.steps?.length || 0,
      completed_steps: 0,
      failed_steps: 0,
      error_message: undefined,
      steps: favorite.job_config.steps?.map((step: any, index: number) => ({
        id: index,
        step_order: index + 1,
        action_type: step.action_type,
        account_ids: step.account_ids || [],
        target_id: step.parameters?.target_id,
        parameters: step.parameters,
        max_retries: step.max_retries,
        is_async: false,
        status: 'pending' as any,
        result: undefined,
        error_message: undefined,
        started_at: undefined,
        completed_at: undefined,
        // Preserve cluster_ids from the saved configuration
        cluster_ids: step.cluster_ids || [],
      })) || [],
    };
    
    setJobToClone(jobToClone);
    setJobFormModalOpen(true);
    setShowFavoriteJobs(false);
  };

  const handleCreateFromFavorite = (favorite: any) => {
    handleUseFavorite(favorite);
  };

  // Navigation handlers
  const handleBackToAccounts = () => {
    navigate('/accounts');
  };

  const handleBackToClusters = () => {
    navigate('/clusters');
  };

  const handleBackToJobs = () => {
    navigate('/jobs');
  };

  const handleShowClusters = () => {
    navigate('/clusters');
  };

  const handleShowAccounts = () => {
    navigate('/accounts');
  };

  const handleShowJobs = () => {
    navigate('/jobs');
  };

  // Form close handlers
  const handleAccountFormClose = () => {
    setAccountFormModalOpen(false);
    setSelectedAccount(undefined);
  };

  const handleClusterFormClose = () => {
    setClusterFormModalOpen(false);
    setSelectedCluster(undefined);
  };

  const handleClusterCloneClose = () => {
    setClusterCloneModalOpen(false);
    setSelectedCluster(undefined);
  };

  const handleJobFormClose = () => {
    setJobFormModalOpen(false);
    setJobToClone(null);
  };

  return (
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
                    location.pathname.startsWith('/accounts')
                      ? 'bg-primary-100 text-primary-700'
                      : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  Accounts
                </button>
                <button
                  onClick={handleShowClusters}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    location.pathname.startsWith('/clusters')
                      ? 'bg-primary-100 text-primary-700'
                      : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  Clusters
                </button>
                <button
                  onClick={handleShowJobs}
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    location.pathname.startsWith('/jobs')
                      ? 'bg-primary-100 text-primary-700'
                      : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  Jobs
                </button>
                <div className="relative">
                  <button
                    onClick={() => setShowSystemStatus(true)}
                    className="px-3 py-2 rounded-md text-sm font-medium transition-colors text-gray-500 hover:text-gray-700 hover:bg-gray-100"
                  >
                    System
                  </button>
                </div>
              </nav>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <Routes>
            <Route path="/" element={<AccountList onViewAccount={handleViewAccount} onEditAccount={handleEditAccount} onCreateAccount={handleCreateAccount} />} />
            <Route path="/accounts" element={<AccountList onViewAccount={handleViewAccount} onEditAccount={handleEditAccount} onCreateAccount={handleCreateAccount} />} />
            <Route path="/accounts/:id" element={<AccountDetailsWrapper onBack={handleBackToAccounts} onEditAccount={handleEditAccount} />} />
            <Route path="/clusters" element={<ClusterList onViewCluster={handleViewCluster} onEditCluster={handleEditCluster} onCreateCluster={handleCreateCluster} onCloneCluster={handleCloneCluster} />} />
            <Route path="/clusters/:id" element={<ClusterDetailsWrapper onBack={handleBackToClusters} onEditCluster={handleEditCluster} onCloneCluster={handleCloneCluster} />} />
            <Route path="/jobs" element={
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <h1 className="text-2xl font-bold text-gray-900">Jobs</h1>
                  <div className="flex gap-3">
                    <button
                      onClick={() => setShowFavoriteJobs(!showFavoriteJobs)}
                      className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      {showFavoriteJobs ? 'Hide' : 'Show'} Favorites
                    </button>
                  </div>
                </div>
                
                {showFavoriteJobs && (
                  <div className="bg-gray-50 rounded-lg p-6">
                    <FavoriteJobsManager
                      onUseFavorite={handleUseFavorite}
                      onCreateFromFavorite={handleCreateFromFavorite}
                    />
                  </div>
                )}
                
                <JobList 
                  onViewJob={handleViewJob} 
                  onCreateJob={handleCreateJob} 
                  onCloneJob={handleCloneJob} 
                />
              </div>
            } />
            <Route path="/jobs/:id" element={<JobDetailsWrapper onBack={handleBackToJobs} />} />
          </Routes>
        </div>
      </main>

      {/* Account Form Modal */}
      <AccountForm
        isOpen={accountFormModalOpen}
        onClose={handleAccountFormClose}
        account={selectedAccount}
      />

      {/* Cluster Form Modal */}
      <ClusterForm
        isOpen={clusterFormModalOpen}
        onClose={handleClusterFormClose}
        cluster={selectedCluster}
      />

      {/* Cluster Clone Modal */}
      {selectedCluster && (
        <ClusterCloneForm
          isOpen={clusterCloneModalOpen}
          onClose={handleClusterCloneClose}
          sourceCluster={selectedCluster}
        />
      )}

      {/* Job Form Modal */}
      <JobForm
        isOpen={jobFormModalOpen}
        onClose={handleJobFormClose}
        jobToClone={jobToClone}
      />

      {/* System Status Modal */}
      <SystemStatus
        show={showSystemStatus}
        onClose={() => setShowSystemStatus(false)}
        onShowNotifications={() => {
          setShowSystemStatus(false);
          setShowSystemNotifications(true);
        }}
      />

      {/* System Notifications Modal */}
      <SystemNotifications
        show={showSystemNotifications}
        onClose={() => setShowSystemNotifications(false)}
      />
    </div>
  );
};

// Wrapper components to extract URL parameters
const AccountDetailsWrapper: React.FC<{ onBack: () => void; onEditAccount: (account: Account) => void }> = ({ onBack, onEditAccount }) => {
  const { id } = useParams<{ id: string }>();
  return id ? <AccountDetails accountId={parseInt(id)} onBack={onBack} onEditAccount={onEditAccount} /> : null;
};

const ClusterDetailsWrapper: React.FC<{ onBack: () => void; onEditCluster: (cluster: ClusterListResponse | ClusterResponse) => void; onCloneCluster: (cluster: ClusterListResponse | ClusterResponse) => void }> = ({ onBack, onEditCluster, onCloneCluster }) => {
  const { id } = useParams<{ id: string }>();
  return id ? <ClusterDetails clusterId={parseInt(id)} onBack={onBack} onEditCluster={onEditCluster} onCloneCluster={onCloneCluster} /> : null;
};

const JobDetailsWrapper: React.FC<{ onBack: () => void }> = ({ onBack }) => {
  const { id } = useParams<{ id: string }>();
  return id ? <JobDetails jobId={parseInt(id)} onBack={onBack} /> : null;
};

// Main App component with Router
const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <AppContent />
      </Router>
    </QueryClientProvider>
  );
};

export default App;
