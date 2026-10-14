import React from 'react';
import { useAuth } from '../context/AuthContext';
import { Shield, User, LogOut, Building2 } from 'lucide-react';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <header className="navbar">
      <div className="navbar-container">
        <div className="navbar-brand">
          <div className="brand-icon">
            <Shield className="w-5 h-5 text-indigo-400" />
          </div>
          <div className="brand-text">
            <span className="brand-title">PlateScan Portal</span>
            <span className="brand-subtitle">Cross-Tenant Recovery Service</span>
          </div>
        </div>

        {user && (
          <div className="navbar-user-section">
            <div className="user-tenant-pill">
              <Building2 className="w-4 h-4 text-emerald-400" />
              <span className="tenant-name">{user.tenant_name}</span>
            </div>

            <div className="user-profile">
              <div className="user-avatar">
                <User className="w-4 h-4 text-slate-300" />
              </div>
              <div className="user-info">
                <span className="user-name">{user.username}</span>
                <span className="user-role">{user.role}</span>
              </div>
            </div>

            <button onClick={logout} className="btn-logout" title="Sign out">
              <LogOut className="w-4 h-4" />
              <span>Logout</span>
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
