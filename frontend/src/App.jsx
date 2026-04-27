import { Routes, Route, useLocation } from 'react-router-dom'
import NavBar from './components/NavBar'
import DisclaimerModal from './components/DisclaimerModal'
import DisclaimerFooter from './components/DisclaimerFooter'
import ProtectedRoute from './components/ProtectedRoute'
import Feed from './pages/Feed'
import Entities from './pages/Entities'
import EntityProfile from './pages/EntityProfile'
import FlowMap from './pages/FlowMap'
import GeoMap from './pages/GeoMap'
import Themes from './pages/Themes'
import Search from './pages/Search'
import Login from './pages/Login'
import Watchlist from './pages/Watchlist'
import CashFlow from './pages/CashFlow'
import Settings from './pages/Settings'
import Disclaimer from './pages/Disclaimer'
import TermsOfService from './pages/TermsOfService'
import PrivacyPolicy from './pages/PrivacyPolicy'
import RiskWarning from './pages/RiskWarning'
import AdminDashboard from './pages/AdminDashboard'
import AdminAnalytics from './pages/AdminAnalytics'

function P({ children }) {
  return <ProtectedRoute>{children}</ProtectedRoute>
}

export default function App() {
  const { pathname } = useLocation()
  const isAuthPage  = pathname === '/login'
  const isLegalPage = pathname.startsWith('/legal')

  return (
    <div className="h-screen flex flex-col bg-white overflow-hidden">
      {/* Disclaimer shown on first visit regardless of page */}
      <DisclaimerModal />
      {!isAuthPage && <NavBar />}
      <main className="flex-1 overflow-auto">
        <Routes>
          {/* Auth */}
          <Route path="/login"               element={<Login />} />

          {/* Legal (publicly accessible, no auth required) */}
          <Route path="/legal/disclaimer"    element={<Disclaimer />} />
          <Route path="/legal/terms"         element={<TermsOfService />} />
          <Route path="/legal/privacy"       element={<PrivacyPolicy />} />
          <Route path="/legal/risk"          element={<RiskWarning />} />

          {/* Protected app routes */}
          <Route path="/"                    element={<P><Feed /></P>} />
          <Route path="/entities"            element={<P><Entities /></P>} />
          <Route path="/entities/:id"        element={<P><EntityProfile /></P>} />
          <Route path="/flowmap"             element={<P><FlowMap /></P>} />
          <Route path="/world"               element={<P><GeoMap /></P>} />
          <Route path="/themes"              element={<P><Themes /></P>} />
          <Route path="/search"              element={<P><Search /></P>} />
          <Route path="/watchlist"           element={<P><Watchlist /></P>} />
          <Route path="/cashflow"            element={<P><CashFlow /></P>} />
          <Route path="/settings"            element={<P><Settings /></P>} />
          <Route path="/admin/health"        element={<AdminDashboard />} />
          <Route path="/admin/analytics"     element={<AdminAnalytics />} />
        </Routes>
      </main>
      {!isAuthPage && !isLegalPage && <DisclaimerFooter />}
    </div>
  )
}
