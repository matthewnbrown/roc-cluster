import React, { useState, useEffect } from 'react';
import { systemApi } from '../services/api';
import { PruningStats } from '../types/api';
import { formatDateTime } from '../utils/dateUtils';

interface SystemStatusProps {
  show: boolean;
  onClose: () => void;
  onShowNotifications?: () => void;
}

const SystemStatus: React.FC<SystemStatusProps> = ({ show, onClose, onShowNotifications }) => {
  const [stats, setStats] = useState<PruningStats | null>(null);
  const [dbStats, setDbStats] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [triggeringPruning, setTriggeringPruning] = useState(false);
  const [triggeringVacuum, setTriggeringVacuum] = useState(false);
  const [triggeringFullVacuum, setTriggeringFullVacuum] = useState(false);

  useEffect(() => {
    if (show) {
      fetchStats();
    }
  }, [show]);

  const fetchStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const [pruningResponse, dbResponse] = await Promise.all([
        systemApi.getPruningStats(),
        systemApi.getDatabaseStats()
      ]);
      setStats(pruningResponse.data);
      setDbStats(dbResponse.data);
    } catch (err) {
      setError('Failed to fetch system status');
      console.error('Error fetching system status:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleTriggerPruning = async () => {
    if (!window.confirm('Are you sure you want to manually trigger job pruning? This will remove steps from old jobs (keeping latest 10 jobs).')) {
      return;
    }

    setTriggeringPruning(true);
    try {
      await systemApi.triggerManualPruning();
      // Refresh stats after pruning
      await fetchStats();
      alert('Job pruning completed successfully!');
    } catch (err) {
      console.error('Error triggering pruning:', err);
      alert('Failed to trigger job pruning');
    } finally {
      setTriggeringPruning(false);
    }
  };

  const handleTriggerVacuum = async () => {
    if (!window.confirm('Are you sure you want to manually trigger database vacuum? This will reclaim unused space but may take a moment.')) {
      return;
    }

    setTriggeringVacuum(true);
    try {
      const result = await systemApi.triggerVacuum();
      // Refresh stats after vacuum
      await fetchStats();
      if (result.details) {
        const pagesFreed = result.details.pages_freed || 0;
        const freelistFreed = result.details.freelist_freed || 0;
        alert(`Database vacuum completed! Freed ${pagesFreed} pages, ${freelistFreed} freelist pages (${(pagesFreed * 4096 / 1024 / 1024).toFixed(2)} MB)`);
      } else {
        alert('Database vacuum completed successfully!');
      }
    } catch (err) {
      console.error('Error triggering vacuum:', err);
      alert('Failed to trigger database vacuum');
    } finally {
      setTriggeringVacuum(false);
    }
  };

  const handleTriggerFullVacuum = async () => {
    if (!window.confirm('Are you sure you want to trigger FULL database vacuum? This will reclaim ALL unused space but may take longer and requires exclusive access to the database.')) {
      return;
    }

    setTriggeringFullVacuum(true);
    try {
      const result = await systemApi.triggerFullVacuum();
      // Refresh stats after vacuum
      await fetchStats();
      if (result.details) {
        const pagesFreed = result.details.pages_freed || 0;
        const freelistFreed = result.details.freelist_freed || 0;
        alert(`Full database vacuum completed! Freed ${pagesFreed} pages, ${freelistFreed} freelist pages (${(pagesFreed * 4096 / 1024 / 1024).toFixed(2)} MB)`);
      } else {
        alert('Full database vacuum completed successfully!');
      }
    } catch (err) {
      console.error('Error triggering full vacuum:', err);
      alert('Failed to trigger full database vacuum');
    } finally {
      setTriggeringFullVacuum(false);
    }
  };

  if (!show) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">System Status</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-6">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <span className="ml-2 text-gray-600">Loading system status...</span>
            </div>
          ) : error ? (
            <div className="text-center py-8">
              <div className="text-red-600 mb-2">{error}</div>
              <button
                onClick={fetchStats}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
              >
                Retry
              </button>
            </div>
          ) : stats ? (
            <div className="space-y-6">
              {/* Service Status */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-3">Job Pruning Service</h3>
                <div className="flex items-center space-x-2">
                  <div className={`w-3 h-3 rounded-full ${stats.service_running ? 'bg-green-500' : 'bg-red-500'}`}></div>
                  <span className="text-sm text-gray-700">
                    {stats.service_running ? 'Running' : 'Stopped'}
                  </span>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Automatically prunes job steps every 8 hours
                </p>
              </div>

              {/* Job Statistics */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-3">Job Statistics</h3>
                <div className="grid grid-cols-1 gap-3">
                  <div className="flex justify-between items-center py-2 border-b border-gray-100">
                    <span className="text-sm text-gray-600">Total Jobs</span>
                    <span className="text-sm font-medium text-gray-900">{stats.total_jobs}</span>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b border-gray-100">
                    <span className="text-sm text-gray-600">Old Jobs to Prune</span>
                    <span className="text-sm font-medium text-gray-900">{stats.jobs_beyond_10th}</span>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b border-gray-100">
                    <span className="text-sm text-gray-600">Steps to Prune</span>
                    <span className="text-sm font-medium text-gray-900">{stats.total_steps_to_prune}</span>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b border-gray-100">
                    <span className="text-sm text-gray-600">Already Pruned</span>
                    <span className="text-sm font-medium text-gray-900">{stats.pruned_jobs_count}</span>
                  </div>
                </div>
              </div>

              {/* Database Statistics */}
              {dbStats && (
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-3">Database Statistics</h3>
                  <div className="grid grid-cols-1 gap-3">
                    <div className="flex justify-between items-center py-2 border-b border-gray-100">
                      <span className="text-sm text-gray-600">Database Size</span>
                      <span className="text-sm font-medium text-gray-900">{dbStats.database_size_mb} MB</span>
                    </div>
                    <div className="flex justify-between items-center py-2 border-b border-gray-100">
                      <span className="text-sm text-gray-600">Auto Vacuum</span>
                      <span className="text-sm font-medium text-gray-900">
                        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs ${
                          dbStats.auto_vacuum_enabled ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                        }`}>
                          {dbStats.auto_vacuum_mode}
                        </span>
                      </span>
                    </div>
                    <div className="flex justify-between items-center py-2 border-b border-gray-100">
                      <span className="text-sm text-gray-600">Wasted Space</span>
                      <span className="text-sm font-medium text-gray-900">{dbStats.wasted_space_mb} MB</span>
                    </div>
                    <div className="flex justify-between items-center py-2 border-b border-gray-100">
                      <span className="text-sm text-gray-600">Free Pages</span>
                      <span className="text-sm font-medium text-gray-900">{dbStats.freelist_count}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Manual Actions */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-3">Manual Actions</h3>
                <div className="space-y-3">
                  <button
                    onClick={handleTriggerPruning}
                    disabled={triggeringPruning || !stats.service_running}
                    className="w-full px-4 py-2 text-sm font-medium text-white bg-orange-600 border border-transparent rounded-md hover:bg-orange-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-orange-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {triggeringPruning ? 'Pruning...' : 'Trigger Manual Pruning'}
                  </button>
                  <p className="text-xs text-gray-500">
                    This will remove all steps from old jobs (keeping latest 10 jobs)
                  </p>
                  
                  <div className="space-y-2">
                    <button
                      onClick={handleTriggerVacuum}
                      disabled={triggeringVacuum || triggeringFullVacuum}
                      className="w-full px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {triggeringVacuum ? 'Vacuuming...' : 'Smart Vacuum'}
                    </button>
                    <p className="text-xs text-gray-500">
                      Reclaims space based on auto vacuum settings
                    </p>
                    
                    <button
                      onClick={handleTriggerFullVacuum}
                      disabled={triggeringVacuum || triggeringFullVacuum}
                      className="w-full px-4 py-2 text-sm font-medium text-white bg-purple-600 border border-transparent rounded-md hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {triggeringFullVacuum ? 'Full Vacuuming...' : 'Full Vacuum'}
                    </button>
                    <p className="text-xs text-gray-500">
                      Aggressively reclaims ALL unused space (takes longer)
                    </p>
                  </div>
                </div>
              </div>

              {/* Last Check */}
              <div className="text-xs text-gray-500 text-center">
                Last checked: {formatDateTime(stats.last_checked)}
              </div>
            </div>
          ) : null}
        </div>

        <div className="flex items-center justify-between p-6 border-t border-gray-200 bg-gray-50">
          <div className="flex space-x-3">
            <button
              onClick={fetchStats}
              disabled={loading}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Refresh
            </button>
            {onShowNotifications && (
              <button
                onClick={onShowNotifications}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                View Notifications
              </button>
            )}
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default SystemStatus;
