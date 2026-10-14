import React, { useState } from 'react';
import { apiClient } from '../api/client';
import { X, Camera, Send, CheckCircle2, AlertCircle } from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onScanCreated: () => void;
}

export const NewScanModal: React.FC<Props> = ({ isOpen, onClose, onScanCreated }) => {
  const [cameraId, setCameraId] = useState('cam_1001');
  const [plate, setPlate] = useState('7XYZ123');
  const [vin, setVin] = useState('1FTFW1E51NFA12345');
  const [latitude, setLatitude] = useState('33.7490');
  const [longitude, setLongitude] = useState('-84.3880');
  const [imageUrl, setImageUrl] = useState('https://images.unsplash.com/photo-1549399542-7e3f8b79c341');

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  if (!isOpen) return null;

  const handlePreset = (presetPlate: string, presetVin: string, cam: string) => {
    setPlate(presetPlate);
    setVin(presetVin);
    setCameraId(cam);
    setResult(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setResult(null);

    try {
      const resp = await apiClient.post('/api/v1/scans', {
        camera_id: cameraId,
        plate: plate.trim().toUpperCase(),
        vin: vin.trim().toUpperCase(),
        latitude: parseFloat(latitude),
        longitude: parseFloat(longitude),
        scanned_at: new Date().toISOString(),
        image_url: imageUrl.trim() || null,
      });

      setResult({
        type: 'success',
        message: resp.data.message || 'Scan successfully ingested!',
      });
      onScanCreated();
    } catch (err: any) {
      setResult({
        type: 'error',
        message: err.response?.data?.detail || 'Failed to ingest camera scan.',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-container" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div className="modal-header-info">
            <div className="modal-title-row">
              <Camera className="w-5 h-5 text-indigo-400" />
              <h3>Simulate Camera Webhook</h3>
            </div>
            <p className="modal-subtitle">Ingest a live license plate & VIN sighting into the service</p>
          </div>
          <button onClick={onClose} className="modal-close-btn" aria-label="Close">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="modal-body">
          {/* Presets */}
          <div className="mb-4">
            <p className="text-xs font-semibold uppercase text-slate-400 mb-2">Quick Presets:</p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <button
                type="button"
                className="preset-btn"
                onClick={() => handlePreset('7XYZ123', '1FTFW1E51NFA12345', 'cam_1001')}
              >
                <strong>Match Active Case</strong>
                <span className="text-xs text-slate-400">VIN: 1FTFW1E5...</span>
              </button>
              <button
                type="button"
                className="preset-btn"
                onClick={() => handlePreset('NEW_CLAIM', `VIN_${Math.floor(100000 + Math.random() * 900000)}`, 'cam_2050')}
              >
                <strong>Create Claimable Case</strong>
                <span className="text-xs text-slate-400">Eligible random VIN</span>
              </button>
              <button
                type="button"
                className="preset-btn"
                onClick={() => handlePreset('INELIG1', 'INELIGIBLE_VIN_999', 'cam_1001')}
              >
                <strong>Ineligible Vehicle</strong>
                <span className="text-xs text-slate-400">Scan only (no case)</span>
              </button>
            </div>
          </div>

          {result && (
            <div
              className={`p-3 rounded-lg mb-4 flex items-center gap-2 text-sm ${
                result.type === 'success'
                  ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-300'
                  : 'bg-rose-500/10 border border-rose-500/30 text-rose-300'
              }`}
            >
              {result.type === 'success' ? (
                <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
              ) : (
                <AlertCircle className="w-5 h-5 flex-shrink-0" />
              )}
              <span>{result.message}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            <div className="form-group">
              <label>Originating Camera</label>
              <select
                value={cameraId}
                onChange={(e) => setCameraId(e.target.value)}
                className="input-select"
              >
                <option value="cam_1001">cam_1001 (Tenant A: Acme truck #12)</option>
                <option value="cam_2050">cam_2050 (Tenant B: Beta mobile unit #3)</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="form-group">
                <label>Plate Number</label>
                <input
                  type="text"
                  value={plate}
                  onChange={(e) => setPlate(e.target.value)}
                  placeholder="e.g. 7XYZ123"
                  required
                  className="input-text font-mono"
                />
              </div>
              <div className="form-group">
                <label>VIN</label>
                <input
                  type="text"
                  value={vin}
                  onChange={(e) => setVin(e.target.value)}
                  placeholder="17-character VIN"
                  required
                  className="input-text font-mono"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="form-group">
                <label>Latitude</label>
                <input
                  type="number"
                  step="any"
                  value={latitude}
                  onChange={(e) => setLatitude(e.target.value)}
                  required
                  className="input-text font-mono"
                />
              </div>
              <div className="form-group">
                <label>Longitude</label>
                <input
                  type="number"
                  step="any"
                  value={longitude}
                  onChange={(e) => setLongitude(e.target.value)}
                  required
                  className="input-text font-mono"
                />
              </div>
            </div>

            <div className="form-group">
              <label>Photo URL (Optional)</label>
              <input
                type="url"
                value={imageUrl}
                onChange={(e) => setImageUrl(e.target.value)}
                placeholder="https://..."
                className="input-text"
              />
            </div>

            <div className="modal-footer px-0 pb-0 pt-3">
              <button type="button" onClick={onClose} className="btn-secondary">
                Cancel
              </button>
              <button type="submit" disabled={loading} className="btn-primary">
                {loading ? 'Ingesting...' : (
                  <span className="flex items-center gap-1">
                    <Send className="w-4 h-4" /> Send Camera Webhook
                  </span>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
