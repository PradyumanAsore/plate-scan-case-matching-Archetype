import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../api/client';
import { AuthResponse } from '../types';
import { Shield, Lock, User, AlertCircle, ArrowRight } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const [username, setUsername] = useState('alice');
  const [password, setPassword] = useState('alice123');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError('Please enter both username and password.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const resp = await apiClient.post<AuthResponse>('/api/v1/auth/login', {
        username,
        password,
      });
      login(resp.data);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Authentication failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const setDemoUser = (user: string, pass: string) => {
    setUsername(user);
    setPassword(pass);
    setError(null);
  };

  return (
    <div className="login-page">
      <div className="login-card">
        {/* Header */}
        <div className="login-header">
          <div className="login-icon-wrapper">
            <Shield className="w-8 h-8 text-indigo-400" />
          </div>
          <h2>PlateScan Recovery Portal</h2>
          <p className="login-subtitle">Cross-Tenant Vehicle Tracking & Case Assignment</p>
        </div>

        {/* Error message */}
        {error && (
          <div className="login-error-banner">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <div className="input-wrapper">
              <User className="input-icon" />
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter username"
                required
                autoComplete="username"
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <div className="input-wrapper">
              <Lock className="input-icon" />
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                required
                autoComplete="current-password"
              />
            </div>
          </div>

          <button type="submit" className="btn-primary w-full" disabled={loading}>
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="spinner-sm"></span> Signing in...
              </span>
            ) : (
              <span className="flex items-center justify-center gap-2">
                Sign In <ArrowRight className="w-4 h-4" />
              </span>
            )}
          </button>
        </form>

        {/* Quick Demo Credentials */}
        <div className="demo-credentials-box">
          <p className="demo-title">Quick Demo Login (Seed Accounts):</p>
          <div className="demo-buttons">
            <button
              type="button"
              className={`demo-btn ${username === 'alice' ? 'demo-btn-active' : ''}`}
              onClick={() => setDemoUser('alice', 'alice123')}
            >
              <strong>Alice</strong> (Tenant A: Acme)
            </button>
            <button
              type="button"
              className={`demo-btn ${username === 'bob' ? 'demo-btn-active' : ''}`}
              onClick={() => setDemoUser('bob', 'bob123')}
            >
              <strong>Bob</strong> (Tenant B: Beta)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
