import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { AppLayout } from './components/layout/AppLayout'
import { LogoMark } from './components/brand/Logo'

const LoginPage = lazy(() => import('./pages/auth/LoginPage'))
const SignupPage = lazy(() => import('./pages/auth/SignupPage'))
const AccessDeniedPage = lazy(() => import('./pages/auth/AccessDeniedPage'))
const NotFoundPage = lazy(() => import('./pages/auth/NotFoundPage'))
const HelpPage = lazy(() => import('./pages/help/HelpPage'))
const DashboardPage = lazy(() => import('./pages/dashboard/DashboardPage'))
const OverlapRadarPage = lazy(() => import('./pages/intelligence/OverlapRadarPage'))
const RiskRadarPage = lazy(() => import('./pages/intelligence/RiskRadarPage'))
const IdentityLabPage = lazy(() => import('./pages/intelligence/IdentityLabPage'))
const InstitutionListPage = lazy(() => import('./pages/institutions/InstitutionListPage'))
const InstitutionDetailPage = lazy(() => import('./pages/institutions/InstitutionDetailPage'))
const CaseListPage = lazy(() => import('./pages/cases/CaseListPage'))
const CreateCasePage = lazy(() => import('./pages/cases/CreateCasePage'))
const CaseDetailPage = lazy(() => import('./pages/cases/CaseDetailPage'))
const TransfersPage = lazy(() => import('./pages/cases/TransfersPage'))
const RelationshipInboxPage = lazy(() => import('./pages/cases/RelationshipInboxPage'))
const CoordinationListPage = lazy(() => import('./pages/coordination/CoordinationListPage'))
const CreateCoordinationPage = lazy(() => import('./pages/coordination/CreateCoordinationPage'))
const CoordinationDetailPage = lazy(() => import('./pages/coordination/CoordinationDetailPage'))
const NotificationsPage = lazy(() => import('./pages/notifications/NotificationsPage'))
const ReportsPage = lazy(() => import('./pages/reports/ReportsPage'))
const ImportsPage = lazy(() => import('./pages/imports/ImportsPage'))
const UserManagementPage = lazy(() => import('./pages/admin/UserManagementPage'))
const AuditLogPage = lazy(() => import('./pages/admin/AuditLogPage'))
const ProfilePage = lazy(() => import('./pages/profile/ProfilePage'))

function FullScreenLoader() {
  return (
    <div className="flex h-screen items-center justify-center bg-canvas">
      <div className="flex flex-col items-center gap-4">
        <div className="relative">
          <span className="absolute inset-0 animate-pulse-ring rounded-2xl bg-royal-300/50" />
          <LogoMark size={52} className="relative" />
        </div>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Loading</p>
      </div>
    </div>
  )
}

function InlineLoader() {
  return (
    <div className="flex min-h-[50vh] items-center justify-center">
      <span className="h-8 w-8 animate-spin rounded-full border-[3px] border-royal-100 border-t-royal-500" />
    </div>
  )
}

function ProtectedRoute({ roles }: { roles?: string[] }) {
  const { isAuthenticated, isLoading, user } = useAuth()
  if (isLoading) return <FullScreenLoader />
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (roles && user && !roles.includes(user.role as string)) return <Navigate to="/403" replace />
  return <Outlet />
}

function Section() {
  return (
    <Suspense fallback={<InlineLoader />}>
      <Outlet />
    </Suspense>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Suspense fallback={<FullScreenLoader />}>
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route path="/403" element={<AccessDeniedPage />} />
            <Route path="/404" element={<NotFoundPage />} />
            <Route element={<ProtectedRoute />}>
              <Route element={<AppLayout />}>
                <Route element={<Section />}>
                  <Route path="/dashboard" element={<DashboardPage />} />
                  <Route path="/overlaps" element={<OverlapRadarPage />} />
                  <Route path="/risk" element={<RiskRadarPage />} />
                  <Route path="/identity-lab" element={<IdentityLabPage />} />
                  <Route path="/institutions" element={<InstitutionListPage />} />
                  <Route path="/institutions/:id" element={<InstitutionDetailPage />} />
                  <Route path="/cases" element={<CaseListPage />} />
                  <Route path="/cases/new" element={<CreateCasePage />} />
                  <Route path="/cases/:id" element={<CaseDetailPage />} />
                  <Route path="/transfers" element={<TransfersPage />} />
                  <Route path="/relationships" element={<RelationshipInboxPage />} />
                  <Route path="/coordination" element={<CoordinationListPage />} />
                  <Route path="/coordination/new" element={<CreateCoordinationPage />} />
                  <Route path="/coordination/:id" element={<CoordinationDetailPage />} />
                  <Route path="/notifications" element={<NotificationsPage />} />
                  <Route path="/reports" element={<ReportsPage />} />
                  <Route path="/profile" element={<ProfilePage />} />
                  <Route path="/help" element={<HelpPage />} />
                  <Route element={<ProtectedRoute roles={['data_admin', 'system_admin']} />}>
                    <Route path="/imports" element={<ImportsPage />} />
                  </Route>
                  <Route element={<ProtectedRoute roles={['system_admin']} />}>
                    <Route path="/admin/users" element={<UserManagementPage />} />
                  </Route>
                  <Route element={<ProtectedRoute roles={['system_admin', 'senior_management']} />}>
                    <Route path="/admin/audit" element={<AuditLogPage />} />
                  </Route>
                </Route>
              </Route>
            </Route>
            <Route path="*" element={<Navigate to="/404" replace />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </AuthProvider>
  )
}
