/**
 * Date and time utility functions for consistent local time formatting
 * 
 * The backend stores all timestamps in UTC and sends them with 'Z' suffix.
 * These functions automatically convert UTC timestamps to the user's local timezone
 * for display while preserving the original UTC data.
 */

/**
 * Formats a date string to a localized date string
 * @param dateString - ISO date string (UTC with 'Z' suffix from backend)
 * @param options - Intl.DateTimeFormatOptions for customization
 * @returns Formatted date string in user's local timezone
 */
export const formatDate = (
  dateString: string, 
  options: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }
): string => {
  if (!dateString) return 'Never';
  
  // Parse the UTC timestamp - JavaScript automatically handles timezone conversion
  const date = new Date(dateString);
  
  // Check if it's a valid date and not the Unix epoch
  if (isNaN(date.getTime()) || date.getTime() === 0 || date.getFullYear() === 1970) {
    return 'Never';
  }
  
  // Convert to user's local timezone for display
  return date.toLocaleDateString(undefined, options);
};

/**
 * Formats a date string to a localized date and time string
 * @param dateString - ISO date string (UTC with 'Z' suffix from backend)
 * @param options - Intl.DateTimeFormatOptions for customization
 * @returns Formatted date and time string in user's local timezone
 */
export const formatDateTime = (
  dateString: string,
  options: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }
): string => {
  if (!dateString) return 'Never';
  
  // Parse the UTC timestamp - JavaScript automatically handles timezone conversion
  const date = new Date(dateString);
  
  if (isNaN(date.getTime()) || date.getTime() === 0 || date.getFullYear() === 1970) {
    return 'Never';
  }
  
  // Convert to user's local timezone for display
  return date.toLocaleString(undefined, options);
};

/**
 * Formats a date string to show only the time in local timezone
 * @param dateString - ISO date string (UTC with 'Z' suffix from backend)
 * @returns Formatted time string in user's local timezone
 */
export const formatTime = (dateString: string): string => {
  if (!dateString) return 'Never';
  
  // Parse the UTC timestamp - JavaScript automatically handles timezone conversion
  const date = new Date(dateString);
  
  if (isNaN(date.getTime()) || date.getTime() === 0 || date.getFullYear() === 1970) {
    return 'Never';
  }
  
  // Convert to user's local timezone for display
  return date.toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};

/**
 * Formats a date string to show relative time (e.g., "2 hours ago", "3 days ago")
 * @param dateString - ISO date string or any valid date string
 * @returns Relative time string
 */
export const formatRelativeTime = (dateString: string): string => {
  if (!dateString) return 'Never';
  
  const date = new Date(dateString);
  const now = new Date();
  
  if (isNaN(date.getTime()) || date.getTime() === 0 || date.getFullYear() === 1970) {
    return 'Never';
  }
  
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);
  
  if (diffInSeconds < 60) {
    return `${diffInSeconds} second${diffInSeconds !== 1 ? 's' : ''} ago`;
  } else if (diffInSeconds < 3600) {
    const minutes = Math.floor(diffInSeconds / 60);
    return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`;
  } else if (diffInSeconds < 86400) {
    const hours = Math.floor(diffInSeconds / 3600);
    return `${hours} hour${hours !== 1 ? 's' : ''} ago`;
  } else if (diffInSeconds < 2592000) {
    const days = Math.floor(diffInSeconds / 86400);
    return `${days} day${days !== 1 ? 's' : ''} ago`;
  } else {
    return formatDate(dateString, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  }
};

/**
 * Calculates duration between two dates in a human-readable format
 * @param startDate - Start date string
 * @param endDate - End date string (optional, defaults to now)
 * @returns Duration string (e.g., "2h 30m", "45s")
 */
export const calculateDuration = (startDate: string, endDate?: string): string => {
  if (!startDate) return 'Unknown';
  
  const start = new Date(startDate);
  const end = endDate ? new Date(endDate) : new Date();
  
  if (isNaN(start.getTime()) || isNaN(end.getTime())) {
    return 'Invalid';
  }
  
  const diffInSeconds = Math.floor((end.getTime() - start.getTime()) / 1000);
  
  if (diffInSeconds < 0) {
    return '0s';
  }
  
  if (diffInSeconds < 60) {
    return `${diffInSeconds}s`;
  } else if (diffInSeconds < 3600) {
    const minutes = Math.floor(diffInSeconds / 60);
    const seconds = diffInSeconds % 60;
    return seconds > 0 ? `${minutes}m ${seconds}s` : `${minutes}m`;
  } else {
    const hours = Math.floor(diffInSeconds / 3600);
    const minutes = Math.floor((diffInSeconds % 3600) / 60);
    return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`;
  }
};

/**
 * Gets the current timestamp in ISO format (UTC)
 * @returns Current timestamp in UTC ISO format with 'Z' suffix
 */
export const getCurrentTimestamp = (): string => {
  return new Date().toISOString();
};

/**
 * Ensures a date string is in proper UTC format for backend
 * @param dateString - Date string to normalize
 * @returns UTC ISO string with 'Z' suffix
 */
export const ensureUTCTimestamp = (dateString: string): string => {
  if (!dateString) return getCurrentTimestamp();
  
  const date = new Date(dateString);
  if (isNaN(date.getTime())) {
    return getCurrentTimestamp();
  }
  
  // Return in UTC ISO format with 'Z' suffix
  return date.toISOString();
};

/**
 * Formats a number with locale-specific number formatting
 * @param value - Number to format
 * @returns Formatted number string
 */
export const formatNumber = (value: number | string): string => {
  if (value === null || value === undefined) return '0';
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return '0';
  return num.toLocaleString();
};
