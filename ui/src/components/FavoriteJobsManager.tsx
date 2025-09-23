import React, { useState } from 'react';
import { Star, Trash2, Edit, Play, Plus } from 'lucide-react';
import { useFavoriteJobs } from '../hooks/useFavoriteJobs';
import { FavoriteJobResponse, FavoriteJobCreateRequest } from '../types/api';
import Button from './ui/Button';
import Modal from './ui/Modal';
import Input from './ui/Input';

interface FavoriteJobsManagerProps {
  onUseFavorite: (favorite: FavoriteJobResponse) => void;
  onCreateFromFavorite?: (favorite: FavoriteJobResponse) => void;
}

interface FavoriteJobFormData {
  name: string;
  description: string;
}

const FavoriteJobsManager: React.FC<FavoriteJobsManagerProps> = ({
  onUseFavorite,
  onCreateFromFavorite,
}) => {
  const {
    favoriteJobs,
    loading,
    error,
    createFavoriteJob,
    updateFavoriteJob,
    deleteFavoriteJob,
    markFavoriteJobAsUsed,
  } = useFavoriteJobs();

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingFavorite, setEditingFavorite] = useState<FavoriteJobResponse | null>(null);
  const [formData, setFormData] = useState<FavoriteJobFormData>({ name: '', description: '' });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleOpenModal = (favorite?: FavoriteJobResponse) => {
    if (favorite) {
      setEditingFavorite(favorite);
      setFormData({
        name: favorite.name,
        description: favorite.description || '',
      });
    } else {
      setEditingFavorite(null);
      setFormData({ name: '', description: '' });
    }
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingFavorite(null);
    setFormData({ name: '', description: '' });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) return;

    setIsSubmitting(true);
    try {
      const favoriteData: FavoriteJobCreateRequest = {
        name: formData.name.trim(),
        description: formData.description.trim() || undefined,
        job_config: editingFavorite?.job_config || {}, // This would need to be passed from parent
      };

      if (editingFavorite) {
        await updateFavoriteJob(editingFavorite.id, favoriteData);
      } else {
        await createFavoriteJob(favoriteData);
      }

      handleCloseModal();
    } catch (err) {
      console.error('Error saving favorite job:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (favorite: FavoriteJobResponse) => {
    if (window.confirm(`Are you sure you want to delete "${favorite.name}"?`)) {
      await deleteFavoriteJob(favorite.id);
    }
  };

  const handleUse = async (favorite: FavoriteJobResponse) => {
    await markFavoriteJobAsUsed(favorite.id);
    onUseFavorite(favorite);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-gray-500">Loading favorite jobs...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="text-red-800">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">Favorite Jobs</h3>
        <Button
          onClick={() => handleOpenModal()}
          className="flex items-center gap-2"
          size="sm"
        >
          <Plus className="h-4 w-4" />
          Add Favorite
        </Button>
      </div>

      {favoriteJobs.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <Star className="h-12 w-12 mx-auto mb-4 text-gray-300" />
          <p>No favorite jobs yet</p>
          <p className="text-sm">Create your first favorite job configuration</p>
        </div>
      ) : (
        <div className="grid gap-3">
          {favoriteJobs.map((favorite) => (
            <div
              key={favorite.id}
              className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-sm transition-shadow"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Star className="h-4 w-4 text-yellow-500 fill-current" />
                    <h4 className="font-medium text-gray-900 truncate">
                      {favorite.name}
                    </h4>
                  </div>
                  
                  {favorite.description && (
                    <p className="text-sm text-gray-600 mb-2 line-clamp-2">
                      {favorite.description}
                    </p>
                  )}
                  
                  <div className="flex items-center gap-4 text-xs text-gray-500">
                    <span>Used {favorite.usage_count} times</span>
                    {favorite.last_used_at && (
                      <span>Last used: {formatDate(favorite.last_used_at)}</span>
                    )}
                    <span>Created: {formatDate(favorite.created_at)}</span>
                  </div>
                </div>

                <div className="flex items-center gap-1 ml-4">
                  <Button
                    onClick={() => handleUse(favorite)}
                    variant="secondary"
                    size="sm"
                    className="flex items-center gap-1"
                    title="Use this favorite"
                  >
                    <Play className="h-3 w-3" />
                  </Button>
                  
                  {onCreateFromFavorite && (
                    <Button
                      onClick={() => onCreateFromFavorite(favorite)}
                      variant="secondary"
                      size="sm"
                      className="flex items-center gap-1"
                      title="Create job from this favorite"
                    >
                      <Plus className="h-3 w-3" />
                    </Button>
                  )}
                  
                  <Button
                    onClick={() => handleOpenModal(favorite)}
                    variant="secondary"
                    size="sm"
                    className="flex items-center gap-1"
                    title="Edit favorite"
                  >
                    <Edit className="h-3 w-3" />
                  </Button>
                  
                  <Button
                    onClick={() => handleDelete(favorite)}
                    variant="secondary"
                    size="sm"
                    className="flex items-center gap-1 text-red-600 hover:text-red-700"
                    title="Delete favorite"
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal for creating/editing favorites */}
      <Modal
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        title={editingFavorite ? 'Edit Favorite Job' : 'Create Favorite Job'}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
              Name *
            </label>
            <Input
              id="name"
              type="text"
              value={formData.name}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setFormData(prev => ({ ...prev, name: e.target.value }))}
              placeholder="Enter favorite job name"
              required
            />
          </div>

          <div>
            <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              id="description"
              value={formData.description}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              placeholder="Enter description (optional)"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              rows={3}
            />
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <Button
              type="button"
              variant="secondary"
              onClick={handleCloseModal}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting || !formData.name.trim()}
            >
              {isSubmitting ? 'Saving...' : editingFavorite ? 'Update' : 'Create'}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default FavoriteJobsManager;
