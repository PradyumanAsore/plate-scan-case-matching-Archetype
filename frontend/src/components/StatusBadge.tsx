import React from 'react';

interface Props {
  status: 'pending_claim' | 'active' | 'closed' | string;
}

export const StatusBadge: React.FC<Props> = ({ status }) => {
  switch (status) {
    case 'pending_claim':
      return (
        <span className="badge badge-pending">
          <span className="badge-dot dot-amber"></span>
          Pending Claim
        </span>
      );
    case 'active':
      return (
        <span className="badge badge-active">
          <span className="badge-dot dot-emerald"></span>
          Active
        </span>
      );
    case 'closed':
      return (
        <span className="badge badge-closed">
          <span className="badge-dot dot-slate"></span>
          Closed
        </span>
      );
    default:
      return <span className="badge badge-slate">{status}</span>;
  }
};
