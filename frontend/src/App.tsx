import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from '@/components/AppShell'
import { AdminRoute, BusinessRoute, ProtectedRoute } from '@/components/RouteGuards'
import { Placeholder } from '@/components/Placeholder'
import { HomePage } from '@/features/HomePage'
import { LoginPage } from '@/features/auth/LoginPage'
import { SignupPage } from '@/features/auth/SignupPage'
import { BusinessSignupPage } from '@/features/auth/BusinessSignupPage'
import { BusinessDashboardPage } from '@/features/business/BusinessDashboardPage'
import { BusinessPublicPage } from '@/features/business/BusinessPublicPage'
import { ForgotPasswordPage } from '@/features/auth/ForgotPasswordPage'
import { ResetPasswordPage } from '@/features/auth/ResetPasswordPage'
import { VerifyEmailPage } from '@/features/auth/VerifyEmailPage'
import { AdminLoginPage } from '@/features/auth/AdminLoginPage'
import { InsightsPage } from '@/features/insights/InsightsPage'
import { PackagesPage as TravellerPackagesPage } from '@/features/packages/PackagesPage'
import { PackageDetailPage } from '@/features/packages/PackageDetailPage'
import { DashboardPage } from '@/features/trips/DashboardPage'
import { NewTripPage } from '@/features/trips/NewTripPage'
import { PlanEditorPage } from '@/features/trips/PlanEditorPage'
import { TripDetailPage } from '@/features/trips/TripDetailPage'
import { TripRoomPage } from '@/features/trips/TripRoomPage'
import { JoinPage } from '@/features/trips/JoinPage'
import { TrainsPage } from '@/features/bookings/TrainsPage'
import { FlightsPage } from '@/features/bookings/FlightsPage'
import { HotelsPage } from '@/features/bookings/HotelsPage'
import { BusesPage } from '@/features/bookings/BusesPage'
import { PackingPage } from '@/features/packing/PackingPage'
import { AssistantPage } from '@/features/assistant/AssistantPage'
import { PackingDefaultsPage } from '@/features/admin/PackingDefaultsPage'
import { RecommendPage } from '@/features/recommend/RecommendPage'
import { ProfilePage } from '@/features/profile/ProfilePage'
import { AdminLayout } from '@/features/admin/AdminLayout'
import { OverviewPage } from '@/features/admin/OverviewPage'
import { UsersPage } from '@/features/admin/UsersPage'
import { TripsPage } from '@/features/admin/TripsPage'
import { PackagesPage } from '@/features/admin/PackagesPage'
import { BookingsPage } from '@/features/admin/BookingsPage'
import { BusinessesPage } from '@/features/admin/BusinessesPage'
import { FraudPage } from '@/features/admin/FraudPage'
import { EscalationsPage } from '@/features/admin/EscalationsPage'
import { FeedbackPage } from '@/features/admin/FeedbackPage'
import { ChatLogsPage } from '@/features/admin/ChatLogsPage'
import { AuditPage } from '@/features/admin/AuditPage'

/**
 * Every route in the build checklist has a line here from day one, so adding a
 * feature means replacing one placeholder -- never rewiring navigation.
 */
export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<HomePage />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="signup" element={<SignupPage />} />
        <Route path="signup/business" element={<BusinessSignupPage />} />
        <Route path="b/:slug" element={<BusinessPublicPage />} />

        <Route element={<BusinessRoute />}>
          <Route path="business" element={<BusinessDashboardPage />} />
        </Route>
        <Route path="forgot-password" element={<ForgotPasswordPage />} />
        <Route path="reset-password" element={<ResetPasswordPage />} />
        <Route path="verify" element={<VerifyEmailPage />} />
        <Route path="insights" element={<InsightsPage />} />
        <Route path="packages" element={<TravellerPackagesPage />} />
        <Route path="packages/:id" element={<PackageDetailPage />} />
        <Route path="admin/login" element={<AdminLoginPage />} />

        <Route element={<ProtectedRoute />}>
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="trips/new" element={<NewTripPage />} />
          <Route path="trips/new/own" element={<PlanEditorPage />} />
          <Route path="trips/:id/edit" element={<PlanEditorPage />} />
          <Route path="trips/:id" element={<TripDetailPage />} />
          <Route path="trips/:id/room" element={<TripRoomPage />} />
          <Route path="trips/:id/packing" element={<PackingPage />} />
          <Route path="join" element={<JoinPage />} />
          <Route path="profile" element={<ProfilePage />} />
          <Route path="recommend" element={<RecommendPage />} />
          <Route path="assistant" element={<AssistantPage />} />
          <Route path="book" element={<Navigate to="/book/flights" replace />} />
          <Route path="book/flights" element={<FlightsPage />} />
          <Route path="book/hotels" element={<HotelsPage />} />
          <Route path="book/trains" element={<TrainsPage />} />
          <Route path="book/buses" element={<BusesPage />} />
        </Route>

        <Route element={<AdminRoute />}>
          <Route path="admin" element={<AdminLayout />}>
            <Route index element={<OverviewPage />} />
            <Route path="users" element={<UsersPage />} />
            <Route path="trips" element={<TripsPage />} />
            <Route path="packages" element={<PackagesPage />} />
            <Route path="businesses" element={<BusinessesPage />} />
            <Route path="bookings" element={<BookingsPage />} />
            <Route path="packing" element={<PackingDefaultsPage />} />
            <Route path="fraud" element={<FraudPage />} />
            <Route path="escalations" element={<EscalationsPage />} />
            <Route path="feedback" element={<FeedbackPage />} />
            <Route path="chat-logs" element={<ChatLogsPage />} />
            <Route path="audit" element={<AuditPage />} />
          </Route>
        </Route>

        <Route path="*" element={<Placeholder title="Page not found" phase="—" />} />
      </Route>
    </Routes>
  )
}
