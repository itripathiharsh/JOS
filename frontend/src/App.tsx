import React, { useState, useEffect } from 'react';
import { Navigation } from './components/Navigation';
import type { PageId } from './components/Navigation';
import { DashboardPage } from './pages/DashboardPage';
import { JobsPage } from './pages/JobsPage';
import { ApplicationsPage } from './pages/ApplicationsPage';
import { ProfilePage } from './pages/ProfilePage';
import { SettingsPage } from './pages/SettingsPage';
import { api } from './api/client';
import type { HealthResponse } from './api/client';

export const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState<PageId>('dashboard');
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loadingHealth, setLoadingHealth] = useState<boolean>(true);

  const fetchGlobalData = async () => {
    setLoadingHealth(true);
    try {
      const h = await api.getHealth();
      setHealth(h);
    } catch (e) {
      setHealth({
        status: 'error',
        database: 'disconnected',
        environment: 'unknown',
        version: '0.1.0',
      });
    } finally {
      setLoadingHealth(false);
    }
  };

  useEffect(() => {
    fetchGlobalData();
  }, []);

  return (
    <div className="flex min-h-screen bg-[#0b0f17] text-slate-100">
      {/* Sidebar Navigation */}
      <Navigation
        currentPage={currentPage}
        onSelectPage={setCurrentPage}
        health={health}
        loadingHealth={loadingHealth}
      />

      {/* Main Content Viewport */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-6xl mx-auto p-6 md:p-8">
          {currentPage === 'dashboard' && (
            <DashboardPage
              onNavigate={(page) => setCurrentPage(page)}
            />
          )}

          {currentPage === 'jobs' && <JobsPage />}

          {currentPage === 'applications' && <ApplicationsPage />}

          {currentPage === 'profile' && <ProfilePage />}

          {currentPage === 'settings' && <SettingsPage />}
        </div>
      </main>
    </div>
  );
};

export default App;
