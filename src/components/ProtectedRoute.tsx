import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './AuthProvider';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireAdmin?: boolean;
}

export function ProtectedRoute({ children, requireAdmin = false }: ProtectedRouteProps) {
  const { user, profile, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center" style={{ background: '#eaebf6' }}>
        <div className="w-12 h-12 border-4 rounded-full animate-spin" style={{ borderColor: '#c7d2fe', borderTopColor: '#3d5af1' }} />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/?auth=1" state={{ from: location }} replace />;
  }

  if (requireAdmin) {
    const isAdmin = profile?.role === 'admin' || profile?.role === 'super_admin';
    if (!isAdmin) {
      return <Navigate to="/app/dashboard" replace />;
    }
  }

  return <>{children}</>;
}
