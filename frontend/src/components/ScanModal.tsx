import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import { Scan, Case } from '../types';
import { X, MapPin, Camera as CameraIcon, Clock, AlertCircle, ExternalLink, Car } from 'lucide-react';
import { StatusBadge } from './StatusBadge';

interface Props {
  caseItem: Case | null;
  onClose: () => void;
}

export const ScanModal: React.FC<Props> = ({ caseItem, onClose }) => {
  const [scans, setScans] = useState<Scan[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!caseItem) return;

    const fetchScans = async () => {
      setLoading(true);
      setError(null);
      try {
        const resp = await apiClient.get<Scan[]>(`/api/v1/cases/${caseItem.id}/scans`);
        setScans(resp.data);
      } catch (err: any) {
        if (err.response?.status === 404) {
          setError('Access denied: You do not have permission to view scans for this case.');
        } else {
          setError(err.response?.data?.detail || 'Failed to load scan trail.');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchScans();
  }, [caseItem]);

  if (!caseItem) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-container" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div className="modal-header-info">
            <div className="modal-title-row">
              <Car className="w-5 h-5 text-indigo-400" />
              <h3>Vehicle Sighting History</h3>
              <StatusBadge status={caseItem.status} />
            </div>
            <p className="modal-subtitle">
              VIN: <span className="font-mono">{caseItem.vin}</span> • Case #{caseItem.id}
            </p>
          </div>
          <button onClick={onClose} className="modal-close-btn" aria-label="Close">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="modal-body">
          {loading && (
            <div className="modal-loading">
              <div className="spinner"></div>
              <p>Fetching multi-tenant sighting trail...</p>
            </div>
          )}

          {error && (
            <div className="modal-error">
              <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0" />
              <p>{error}</p>
            </div>
          )}

          {!loading && !error && scans.length === 0 && (
            <div className="modal-empty">
              <MapPin className="w-8 h-8 text-slate-500 mb-2" />
              <p>No historical camera sightings found for this VIN.</p>
            </div>
          )}

          {!loading && !error && scans.length > 0 && (
            <div className="scan-timeline">
              <div className="timeline-header-info">
                <span>Total Sightings: <strong>{scans.length}</strong></span>
                <span className="text-xs text-slate-400">Chronological trail across all network cameras</span>
              </div>
              <div className="timeline-items">
                {scans.map((scan, idx) => {
                  const scanDate = new Date(scan.scanned_at).toLocaleString('en-US', {
                    dateStyle: 'medium',
                    timeStyle: 'medium',
                  });

                  return (
                    <div key={scan.id} className="timeline-item">
                      <div className="timeline-marker">
                        <div className="marker-dot"></div>
                        {idx !== scans.length - 1 && <div className="marker-line"></div>}
                      </div>

                      <div className="timeline-card">
                        <div className="timeline-card-header">
                          <div className="flex items-center gap-2">
                            <span className="license-plate font-mono">{scan.plate}</span>
                            <span className="scan-id-tag">Scan #{scan.id}</span>
                          </div>
                          <div className="scan-time flex items-center gap-1 text-xs text-slate-400">
                            <Clock className="w-3.5 h-3.5" />
                            <span>{scanDate}</span>
                          </div>
                        </div>

                        <div className="timeline-card-body">
                          <div className="card-detail-item">
                            <CameraIcon className="w-4 h-4 text-slate-400" />
                            <span>Camera: <strong className="font-mono text-slate-200">{scan.camera_id}</strong></span>
                            {scan.camera_description && (
                              <span className="text-xs text-slate-400">({scan.camera_description})</span>
                            )}
                          </div>

                          <div className="card-detail-item">
                            <MapPin className="w-4 h-4 text-emerald-400" />
                            <span>Coordinates: </span>
                            <span className="font-mono text-xs text-slate-300">
                              {scan.latitude.toFixed(4)}, {scan.longitude.toFixed(4)}
                            </span>
                          </div>

                          {scan.image_url && (
                            <div className="card-detail-item">
                              <ExternalLink className="w-4 h-4 text-indigo-400" />
                              <a
                                href={scan.image_url}
                                target="_blank"
                                rel="noreferrer"
                                className="scan-image-link"
                              >
                                View Capture Image
                              </a>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="modal-footer">
          <button onClick={onClose} className="btn-secondary">
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
