import React, { useEffect, useState, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiClient } from '../api/client';
import { Case, CaseListResponse, CaseClaimResponse } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { ScanModal } from '../components/ScanModal';
import { NewScanModal } from '../components/NewScanModal';
import {
  FolderKanban,
  CheckCircle2,
  Clock,
  RefreshCw,
  AlertCircle,
  Eye,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Search,
  Filter,
  Camera,
  CheckSquare,
} from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const { user } = useAuth();

  const [cases, setCases] = useState<Case[]>([]);
  const [totalCases, setTotalCases] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Filters & Pagination
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [page, setPage] = useState<number>(0);
  const limit = 10;

  // Selected case for scan trail modal
  const [selectedCase, setSelectedCase] = useState<Case | null>(null);

  // New Scan modal
  const [isNewScanModalOpen, setIsNewScanModalOpen] = useState(false);

  // Claiming state
  const [claimingCaseId, setClaimingCaseId] = useState<number | null>(null);

  const fetchCases = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: any = {
        limit,
        offset: page * limit,
      };
      if (statusFilter) {
        params.status = statusFilter;
      }
      const resp = await apiClient.get<CaseListResponse>('/api/v1/cases', { params });
      setCases(resp.data.items);
      setTotalCases(resp.data.total);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load cases.');
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter]);

  useEffect(() => {
    fetchCases();
  }, [fetchCases]);

  const handleClaim = async (caseId: number) => {
    if (claimingCaseId) return; // prevent duplicate clicks
    setClaimingCaseId(caseId);
    setError(null);
    setSuccessMessage(null);

    try {
      const resp = await apiClient.post<CaseClaimResponse>(`/api/v1/cases/${caseId}/claim`);
      setSuccessMessage(resp.data.message || `Case #${caseId} claimed successfully!`);
      // Refresh cases list
      await fetchCases();
    } catch (err: any) {
      if (err.response?.status === 409) {
        setError(err.response?.data?.detail || 'Conflict: This case has already been claimed by another user.');
      } else {
        setError(err.response?.data?.detail || 'Failed to claim case.');
      }
      // Still refresh to get latest status
      fetchCases();
    } finally {
      setClaimingCaseId(null);
    }
  };

  const handleCloseCase = async (caseId: number) => {
    if (!window.confirm(`Are you sure you want to close Case #${caseId}?`)) return;
    setError(null);
    setSuccessMessage(null);
    try {
      const resp = await apiClient.post<CaseClaimResponse>(`/api/v1/cases/${caseId}/close`);
      setSuccessMessage(resp.data.message || `Case #${caseId} closed successfully.`);
      await fetchCases();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to close case.');
    }
  };

  // Filter cases locally by search query (VIN) if entered
  const filteredCases = cases.filter((c) =>
    c.vin.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const pendingCount = cases.filter((c) => c.status === 'pending_claim').length;
  const activeCount = cases.filter((c) => c.status === 'active' && c.tenant_id === user?.tenant_id).length;

  const totalPages = Math.ceil(totalCases / limit);

  return (
    <div className="dashboard-layout">
      {/* Overview Stats Bar */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon icon-indigo">
            <FolderKanban className="w-5 h-5 text-indigo-400" />
          </div>
          <div className="stat-info">
            <span className="stat-label">Visible Cases</span>
            <span className="stat-value">{totalCases}</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon icon-emerald">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
          </div>
          <div className="stat-info">
            <span className="stat-label">Tenant Active Cases</span>
            <span className="stat-value">{activeCount}</span>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon icon-amber">
            <Clock className="w-5 h-5 text-amber-400" />
          </div>
          <div className="stat-info">
            <span className="stat-label">Claimable Pending</span>
            <span className="stat-value">{pendingCount}</span>
          </div>
        </div>
      </div>

      {/* Alerts */}
      {error && (
        <div className="alert-banner alert-error">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
          <button onClick={() => setError(null)} className="alert-close">×</button>
        </div>
      )}

      {successMessage && (
        <div className="alert-banner alert-success">
          <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
          <span>{successMessage}</span>
          <button onClick={() => setSuccessMessage(null)} className="alert-close">×</button>
        </div>
      )}

      {/* Cases Table Section */}
      <div className="table-card">
        {/* Controls Header */}
        <div className="table-controls">
          <div className="controls-left">
            <div className="search-box">
              <Search className="search-icon w-4 h-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search by VIN..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>

            <div className="filter-dropdown">
              <Filter className="filter-icon w-4 h-4 text-slate-400" />
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPage(0);
                }}
              >
                <option value="">All Visible Cases</option>
                <option value="pending_claim">Pending Claim (Claimable)</option>
                <option value="active">Active (Tenant Cases)</option>
                <option value="closed">Closed Cases</option>
              </select>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsNewScanModalOpen(true)}
              className="btn-primary flex items-center gap-1.5 py-1.5 px-3 text-xs"
              title="Simulate an incoming camera scan webhook"
            >
              <Camera className="w-4 h-4" />
              <span>Simulate Scan</span>
            </button>

            <button
              onClick={() => fetchCases()}
              className="btn-refresh"
              title="Refresh Cases"
              disabled={loading}
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Table Content */}
        {loading && cases.length === 0 ? (
          <div className="table-loading">
            <div className="spinner"></div>
            <p>Loading recovery cases...</p>
          </div>
        ) : filteredCases.length === 0 ? (
          <div className="table-empty">
            <FolderKanban className="w-10 h-10 text-slate-500 mb-2" />
            <p className="empty-title">No cases found</p>
            <p className="empty-subtitle">
              {statusFilter
                ? `No cases with status "${statusFilter}".`
                : 'Scans will appear here as incoming camera sightings create cases.'}
            </p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="cases-table">
              <thead>
                <tr>
                  <th>Case ID</th>
                  <th>VIN</th>
                  <th>Status</th>
                  <th>Tenant Attribution</th>
                  <th>Assigned Agent</th>
                  <th>Created</th>
                  <th className="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredCases.map((c) => {
                  const isClaimable = c.status === 'pending_claim';
                  const isClaiming = claimingCaseId === c.id;
                  const createdDate = new Date(c.created_at).toLocaleString('en-US', {
                    dateStyle: 'short',
                    timeStyle: 'short',
                  });

                  return (
                    <tr
                      key={c.id}
                      className={isClaimable ? 'row-claimable' : ''}
                    >
                      <td className="font-mono text-slate-300">#{c.id}</td>
                      <td>
                        <span className="font-mono font-semibold text-slate-100">
                          {c.vin}
                        </span>
                      </td>
                      <td>
                        <StatusBadge status={c.status} />
                      </td>
                      <td>
                        {c.tenant_name ? (
                          <span className="tenant-badge">{c.tenant_name}</span>
                        ) : (
                          <span className="text-xs text-amber-400 font-medium">Unassigned (Network Pool)</span>
                        )}
                      </td>
                      <td>
                        {c.assigned_agent_username ? (
                          <span className="agent-text">{c.assigned_agent_username}</span>
                        ) : (
                          <span className="text-xs text-slate-500">—</span>
                        )}
                      </td>
                      <td className="text-xs text-slate-400">{createdDate}</td>
                      <td>
                        <div className="table-actions">
                          {/* Claim button if pending */}
                          {isClaimable && (
                            <button
                              onClick={() => handleClaim(c.id)}
                              disabled={isClaiming}
                              className="btn-claim"
                              title="Claim this case for your tenant"
                            >
                              {isClaiming ? (
                                <>
                                  <span className="spinner-sm"></span> Claiming...
                                </>
                              ) : (
                                <>
                                  <Sparkles className="w-3.5 h-3.5" /> Claim Case
                                </>
                              )}
                            </button>
                          )}

                          {/* Close Case button if active and owned by user tenant */}
                          {c.status === 'active' && c.tenant_id === user?.tenant_id && (
                            <button
                              onClick={() => handleCloseCase(c.id)}
                              className="btn-scans text-amber-400 hover:text-amber-300 hover:border-amber-500/50"
                              title="Mark this active case as closed"
                            >
                              <CheckSquare className="w-3.5 h-3.5" />
                              <span>Close</span>
                            </button>
                          )}

                          {/* View Scan History Button */}
                          <button
                            onClick={() => setSelectedCase(c)}
                            className="btn-scans"
                            title="View chronological camera sighting trail"
                          >
                            <Eye className="w-3.5 h-3.5" />
                            <span>Scan Trail</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Footer */}
        {totalPages > 1 && (
          <div className="table-pagination">
            <span className="pagination-info">
              Showing {page * limit + 1}–{Math.min((page + 1) * limit, totalCases)} of {totalCases} cases
            </span>
            <div className="pagination-buttons">
              <button
                onClick={() => setPage((p) => Math.max(p - 1, 0))}
                disabled={page === 0}
                className="btn-page"
              >
                <ChevronLeft className="w-4 h-4" />
                <span>Prev</span>
              </button>
              <span className="page-current">Page {page + 1} of {totalPages}</span>
              <button
                onClick={() => setPage((p) => Math.min(p + 1, totalPages - 1))}
                disabled={page >= totalPages - 1}
                className="btn-page"
              >
                <span>Next</span>
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Sighting History Modal */}
      {selectedCase && (
        <ScanModal
          caseItem={selectedCase}
          onClose={() => setSelectedCase(null)}
        />
      )}

      {/* Simulate New Camera Webhook Modal */}
      <NewScanModal
        isOpen={isNewScanModalOpen}
        onClose={() => setIsNewScanModalOpen(false)}
        onScanCreated={() => fetchCases()}
      />
    </div>
  );
};
