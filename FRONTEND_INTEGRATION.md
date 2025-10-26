# Frontend Integration Guide - Strategy AI v2.0

This guide explains what changes are needed in your frontend to support the new authentication system.

## 🎯 Quick Summary

### What Changed:
- **Public Submission Form**: ✅ **NO CHANGES** - works exactly the same
- **Admin Dashboard**: ⚠️ **REQUIRES AUTH** - needs login flow and JWT token management

---

## 🔓 Public Submission Form (No Changes)

Your existing submission form continues to work **exactly the same**:

```javascript
// This still works without any changes
const response = await fetch('https://your-backend.railway.app/api/submit', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    name: 'João Silva',
    email: 'joao@empresa.com.br',
    company: 'Tech Startup',
    website: 'https://example.com',
    industry: 'Tecnologia',
    challenge: 'Need to scale sales'
  })
});

const data = await response.json();
// { success: true, submission_id: 123 }
```

**✅ No frontend changes needed for the public form!**

---

## 🔐 Admin Dashboard Changes (Authentication Required)

### 1. Add Login Page/Component

You need to create a login page for admin users.

**Example: `AdminLogin.jsx` (React)**

```jsx
import { useState } from 'react';

export default function AdminLogin({ onLoginSuccess }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await fetch('https://your-backend.railway.app/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password })
      });

      const data = await response.json();

      if (data.success) {
        // Save token to localStorage
        localStorage.setItem('admin_token', data.data.access_token);
        localStorage.setItem('admin_user', JSON.stringify(data.data.user));

        // Redirect to admin dashboard
        onLoginSuccess();
      } else {
        setError(data.error || 'Login failed');
      }
    } catch (err) {
      setError('Connection error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <h2>Admin Login</h2>
      <form onSubmit={handleLogin}>
        <div>
          <label>Email:</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            placeholder="admin@company.com"
          />
        </div>
        <div>
          <label>Password:</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        {error && <div className="error">{error}</div>}
        <button type="submit" disabled={loading}>
          {loading ? 'Logging in...' : 'Login'}
        </button>
      </form>
    </div>
  );
}
```

---

### 2. Create API Helper Functions

Create a utility file to handle authenticated requests.

**Example: `api/admin.js`**

```javascript
const API_BASE_URL = 'https://your-backend.railway.app';

// Get stored token
const getToken = () => {
  return localStorage.getItem('admin_token');
};

// Check if user is authenticated
export const isAuthenticated = () => {
  return !!getToken();
};

// Logout
export const logout = () => {
  localStorage.removeItem('admin_token');
  localStorage.removeItem('admin_user');
  window.location.href = '/admin/login';
};

// Generic authenticated fetch
const authenticatedFetch = async (endpoint, options = {}) => {
  const token = getToken();

  if (!token) {
    throw new Error('No authentication token found');
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...options.headers,
    },
  });

  // Handle 401 Unauthorized (token expired or invalid)
  if (response.status === 401) {
    logout();
    throw new Error('Session expired. Please login again.');
  }

  return response;
};

// Get all submissions (admin only)
export const getSubmissions = async () => {
  const response = await authenticatedFetch('/api/admin/submissions');
  return response.json();
};

// Reprocess a submission (admin only)
export const reprocessSubmission = async (submissionId) => {
  const response = await authenticatedFetch(`/api/admin/reprocess/${submissionId}`, {
    method: 'POST',
  });
  return response.json();
};
```

---

### 3. Update Admin Dashboard Component

**Example: `AdminDashboard.jsx`**

```jsx
import { useState, useEffect } from 'react';
import { getSubmissions, reprocessSubmission, logout } from './api/admin';

export default function AdminDashboard() {
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadSubmissions();
  }, []);

  const loadSubmissions = async () => {
    try {
      setLoading(true);
      const data = await getSubmissions();

      if (data.success) {
        setSubmissions(data.data);
      } else {
        setError(data.error);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleReprocess = async (id) => {
    if (!confirm('Reprocess this submission?')) return;

    try {
      const result = await reprocessSubmission(id);
      if (result.success) {
        alert('Submission queued for reprocessing!');
        loadSubmissions(); // Reload list
      }
    } catch (err) {
      alert('Error: ' + err.message);
    }
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div className="admin-dashboard">
      <div className="header">
        <h2>Admin Dashboard</h2>
        <button onClick={logout}>Logout</button>
      </div>

      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Company</th>
            <th>Email</th>
            <th>Industry</th>
            <th>Status</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {submissions.map((sub) => (
            <tr key={sub.id}>
              <td>{sub.id}</td>
              <td>{sub.company}</td>
              <td>{sub.email}</td>
              <td>{sub.industry}</td>
              <td>
                <span className={`status-${sub.status}`}>
                  {sub.status}
                </span>
              </td>
              <td>{new Date(sub.created_at).toLocaleString()}</td>
              <td>
                {sub.status === 'failed' && (
                  <button onClick={() => handleReprocess(sub.id)}>
                    Reprocess
                  </button>
                )}
                {sub.status === 'completed' && (
                  <button onClick={() => viewReport(sub.id)}>
                    View Report
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

---

### 4. Add Protected Route Logic

**Example: React Router Protected Route**

```jsx
import { Navigate } from 'react-router-dom';
import { isAuthenticated } from './api/admin';

function ProtectedRoute({ children }) {
  if (!isAuthenticated()) {
    return <Navigate to="/admin/login" replace />;
  }

  return children;
}

// In your router:
<Routes>
  <Route path="/admin/login" element={<AdminLogin />} />
  <Route
    path="/admin/dashboard"
    element={
      <ProtectedRoute>
        <AdminDashboard />
      </ProtectedRoute>
    }
  />
</Routes>
```

---

### 5. Next.js Example (if using Next.js)

**`pages/admin/login.js`**

```jsx
import { useState } from 'react';
import { useRouter } from 'next/router';

export default function AdminLogin() {
  const router = useRouter();
  const [credentials, setCredentials] = useState({ email: '', password: '' });
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();

    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials)
    });

    const data = await res.json();

    if (data.success) {
      localStorage.setItem('admin_token', data.data.access_token);
      router.push('/admin/dashboard');
    } else {
      setError(data.error);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* form fields */}
    </form>
  );
}
```

**`pages/admin/dashboard.js`**

```jsx
import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';

export default function AdminDashboard() {
  const router = useRouter();
  const [submissions, setSubmissions] = useState([]);

  useEffect(() => {
    const token = localStorage.getItem('admin_token');
    if (!token) {
      router.push('/admin/login');
      return;
    }

    fetchSubmissions(token);
  }, []);

  const fetchSubmissions = async (token) => {
    const res = await fetch('https://your-backend.railway.app/api/admin/submissions', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (res.status === 401) {
      localStorage.removeItem('admin_token');
      router.push('/admin/login');
      return;
    }

    const data = await res.json();
    setSubmissions(data.data);
  };

  return (
    <div>
      {/* Dashboard UI */}
    </div>
  );
}
```

---

## 📋 Frontend Checklist

### For Public Form (No Changes):
- [ ] ✅ Submission form already works - no changes needed

### For Admin Dashboard (New):
- [ ] Create admin login page/component
- [ ] Add token storage (localStorage)
- [ ] Create authenticated API helper functions
- [ ] Update admin dashboard to use authenticated requests
- [ ] Add protected route logic (redirect to login if not authenticated)
- [ ] Add logout functionality
- [ ] Handle 401 errors (token expiration)
- [ ] Add "Bearer {token}" to Authorization header for admin endpoints

---

## 🔑 Token Management Best Practices

### Store Token:
```javascript
// After successful login
localStorage.setItem('admin_token', token);
```

### Include in Requests:
```javascript
headers: {
  'Authorization': `Bearer ${token}`
}
```

### Handle Expiration:
```javascript
// Token expires after 24 hours
// On 401 response, redirect to login
if (response.status === 401) {
  localStorage.removeItem('admin_token');
  window.location.href = '/admin/login';
}
```

---

## 🚀 Testing Your Integration

### Test Login:
1. Go to your admin login page
2. Enter credentials (created in Supabase Auth)
3. Check browser console for token in localStorage
4. Should redirect to dashboard

### Test Protected Endpoints:
1. Open browser dev tools → Application → Local Storage
2. Verify `admin_token` is stored
3. Open Network tab
4. Navigate to admin dashboard
5. Check requests include `Authorization: Bearer ...` header

### Test Logout:
1. Click logout button
2. Verify token is removed from localStorage
3. Redirected to login page
4. Cannot access admin pages without token

---

## 🐛 Common Issues

### Issue: "401 Unauthorized" on admin requests
**Solution**: Check that token is included in Authorization header as `Bearer {token}`

### Issue: Login returns error
**Solution**: Verify admin user exists in Supabase Auth panel

### Issue: CORS errors
**Solution**: Add your frontend URL to `ALLOWED_ORIGINS` in Railway env vars

### Issue: Token expired
**Solution**: Implement token refresh or re-login flow (tokens last 24h)

---

## 📝 Environment Variables (Frontend)

If you want to centralize API URL:

```env
# .env.local (Next.js)
NEXT_PUBLIC_API_URL=https://your-backend.railway.app

# .env (React/Vite)
VITE_API_URL=https://your-backend.railway.app
```

Then use:
```javascript
const API_URL = process.env.NEXT_PUBLIC_API_URL || process.env.VITE_API_URL;
```

---

## ✅ Summary

### Public Form:
- **No changes needed** - continues to work as-is

### Admin Dashboard:
- Add login page
- Store JWT token in localStorage
- Include `Authorization: Bearer {token}` in admin API calls
- Handle token expiration (401 errors)
- Add logout functionality

**That's it!** Your frontend integration is complete. 🎉
