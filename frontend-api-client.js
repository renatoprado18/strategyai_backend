/**
 * Strategy AI - Frontend API Client
 *
 * Drop-in API client for your frontend application.
 * Handles authentication, token management, and all API calls.
 *
 * Usage:
 *   import { strategyAPI } from './frontend-api-client.js';
 *
 *   // Public submission
 *   await strategyAPI.submitLead({ name, email, company, ... });
 *
 *   // Admin login
 *   await strategyAPI.admin.login(email, password);
 *
 *   // Admin operations
 *   await strategyAPI.admin.getSubmissions();
 */

// ============================================
// Configuration
// ============================================

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ||
                     process.env.VITE_API_URL ||
                     process.env.REACT_APP_API_URL ||
                     'http://localhost:8000'; // Fallback for development

const TOKEN_KEY = 'strategy_admin_token';
const USER_KEY = 'strategy_admin_user';

// ============================================
// Token Management
// ============================================

const TokenManager = {
  save: (token, user) => {
    if (typeof window === 'undefined') return;
    localStorage.setItem(TOKEN_KEY, token);
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
  },

  get: () => {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem(TOKEN_KEY);
  },

  getUser: () => {
    if (typeof window === 'undefined') return null;
    const user = localStorage.getItem(USER_KEY);
    return user ? JSON.parse(user) : null;
  },

  clear: () => {
    if (typeof window === 'undefined') return;
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },

  isAuthenticated: () => {
    return !!TokenManager.get();
  }
};

// ============================================
// API Client
// ============================================

class StrategyAPIClient {
  constructor(baseURL) {
    this.baseURL = baseURL;
  }

  // Generic fetch wrapper
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;

    const config = {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    };

    try {
      const response = await fetch(url, config);
      const data = await response.json();

      // Handle 401 Unauthorized (token expired)
      if (response.status === 401) {
        TokenManager.clear();
        if (typeof window !== 'undefined') {
          window.location.href = '/admin/login';
        }
        throw new Error('Session expired. Please login again.');
      }

      // Handle other errors
      if (!response.ok) {
        throw new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
      }

      return data;
    } catch (error) {
      console.error(`API Error [${endpoint}]:`, error);
      throw error;
    }
  }

  // Authenticated request wrapper
  async authenticatedRequest(endpoint, options = {}) {
    const token = TokenManager.get();

    if (!token) {
      throw new Error('No authentication token. Please login first.');
    }

    return this.request(endpoint, {
      ...options,
      headers: {
        ...options.headers,
        'Authorization': `Bearer ${token}`,
      },
    });
  }

  // ============================================
  // Public Endpoints (No auth required)
  // ============================================

  /**
   * Submit a lead form (public endpoint)
   * @param {Object} leadData - Lead submission data
   * @returns {Promise<{success: boolean, submission_id?: number, error?: string}>}
   */
  async submitLead(leadData) {
    const { name, email, company, website, industry, challenge } = leadData;

    // Validate required fields
    if (!name || !email || !company || !industry) {
      throw new Error('Missing required fields: name, email, company, industry');
    }

    return this.request('/api/submit', {
      method: 'POST',
      body: JSON.stringify({
        name,
        email,
        company,
        website: website || null,
        industry,
        challenge: challenge || null,
      }),
    });
  }

  /**
   * Health check
   * @returns {Promise<Object>}
   */
  async healthCheck() {
    return this.request('/');
  }

  // ============================================
  // Admin Endpoints (Auth required)
  // ============================================

  admin = {
    /**
     * Admin login
     * @param {string} email - Admin email
     * @param {string} password - Admin password
     * @returns {Promise<{success: boolean, data?: Object, error?: string}>}
     */
    login: async (email, password) => {
      const response = await this.request('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });

      // Save token on successful login
      if (response.success && response.data) {
        TokenManager.save(response.data.access_token, response.data.user);
      }

      return response;
    },

    /**
     * Logout (clears token)
     */
    logout: () => {
      TokenManager.clear();
      if (typeof window !== 'undefined') {
        window.location.href = '/admin/login';
      }
    },

    /**
     * Check if user is authenticated
     * @returns {boolean}
     */
    isAuthenticated: () => {
      return TokenManager.isAuthenticated();
    },

    /**
     * Get current user
     * @returns {Object|null}
     */
    getCurrentUser: () => {
      return TokenManager.getUser();
    },

    /**
     * Get all submissions (admin only)
     * @returns {Promise<{success: boolean, data?: Array, error?: string}>}
     */
    getSubmissions: async () => {
      return this.authenticatedRequest('/api/admin/submissions');
    },

    /**
     * Reprocess a failed submission (admin only)
     * @param {number} submissionId - Submission ID
     * @returns {Promise<{success: boolean, error?: string}>}
     */
    reprocessSubmission: async (submissionId) => {
      return this.authenticatedRequest(`/api/admin/reprocess/${submissionId}`, {
        method: 'POST',
      });
    },
  };
}

// ============================================
// Export singleton instance
// ============================================

export const strategyAPI = new StrategyAPIClient(API_BASE_URL);

// Also export TokenManager for direct access if needed
export { TokenManager };

// ============================================
// Usage Examples
// ============================================

/**
 * EXAMPLE 1: Public Lead Submission
 *
 * import { strategyAPI } from './frontend-api-client.js';
 *
 * const handleSubmit = async (formData) => {
 *   try {
 *     const result = await strategyAPI.submitLead({
 *       name: formData.name,
 *       email: formData.email,
 *       company: formData.company,
 *       website: formData.website,
 *       industry: formData.industry,
 *       challenge: formData.challenge,
 *     });
 *
 *     if (result.success) {
 *       console.log('Submission ID:', result.submission_id);
 *       alert('Thank you! Your analysis is being generated.');
 *     }
 *   } catch (error) {
 *     console.error('Submission error:', error);
 *     alert('Error: ' + error.message);
 *   }
 * };
 */

/**
 * EXAMPLE 2: Admin Login
 *
 * import { strategyAPI } from './frontend-api-client.js';
 *
 * const handleLogin = async (email, password) => {
 *   try {
 *     const result = await strategyAPI.admin.login(email, password);
 *
 *     if (result.success) {
 *       console.log('Logged in as:', result.data.user.email);
 *       window.location.href = '/admin/dashboard';
 *     } else {
 *       alert('Login failed: ' + result.error);
 *     }
 *   } catch (error) {
 *     console.error('Login error:', error);
 *     alert('Error: ' + error.message);
 *   }
 * };
 */

/**
 * EXAMPLE 3: Admin Dashboard - Get Submissions
 *
 * import { strategyAPI } from './frontend-api-client.js';
 * import { useEffect, useState } from 'react';
 *
 * function AdminDashboard() {
 *   const [submissions, setSubmissions] = useState([]);
 *   const [loading, setLoading] = useState(true);
 *
 *   useEffect(() => {
 *     loadSubmissions();
 *   }, []);
 *
 *   const loadSubmissions = async () => {
 *     try {
 *       const result = await strategyAPI.admin.getSubmissions();
 *       if (result.success) {
 *         setSubmissions(result.data);
 *       }
 *     } catch (error) {
 *       console.error('Error loading submissions:', error);
 *     } finally {
 *       setLoading(false);
 *     }
 *   };
 *
 *   const handleReprocess = async (id) => {
 *     try {
 *       const result = await strategyAPI.admin.reprocessSubmission(id);
 *       if (result.success) {
 *         alert('Reprocessing started!');
 *         loadSubmissions(); // Reload
 *       }
 *     } catch (error) {
 *       alert('Error: ' + error.message);
 *     }
 *   };
 *
 *   return (
 *     <div>
 *       <button onClick={strategyAPI.admin.logout}>Logout</button>
 *       {submissions.map(sub => (
 *         <div key={sub.id}>
 *           <h3>{sub.company}</h3>
 *           <p>Status: {sub.status}</p>
 *           {sub.status === 'failed' && (
 *             <button onClick={() => handleReprocess(sub.id)}>
 *               Reprocess
 *             </button>
 *           )}
 *         </div>
 *       ))}
 *     </div>
 *   );
 * }
 */

/**
 * EXAMPLE 4: Protected Route (React Router)
 *
 * import { Navigate } from 'react-router-dom';
 * import { strategyAPI } from './frontend-api-client.js';
 *
 * function ProtectedRoute({ children }) {
 *   if (!strategyAPI.admin.isAuthenticated()) {
 *     return <Navigate to="/admin/login" replace />;
 *   }
 *   return children;
 * }
 *
 * // In your routes:
 * <Route
 *   path="/admin/dashboard"
 *   element={
 *     <ProtectedRoute>
 *       <AdminDashboard />
 *     </ProtectedRoute>
 *   }
 * />
 */
