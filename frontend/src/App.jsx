import { Routes, Route } from 'react-router-dom'
import NavBar from './components/NavBar'
import DisclaimerModal from './components/DisclaimerModal'
import DisclaimerFooter from './components/DisclaimerFooter'
import Feed from './pages/Feed'
import Entities from './pages/Entities'
import EntityProfile from './pages/EntityProfile'
import FlowMap from './pages/FlowMap'
import Themes from './pages/Themes'
import Search from './pages/Search'
import Login from './pages/Login'

export default function App() {
  return (
    <div className="h-screen flex flex-col bg-white overflow-hidden">
      {/* Legal disclaimer — shown once on first visit */}
      <DisclaimerModal />
      <NavBar />
      {/* Feed uses its own overflow scroll; all other pages scroll naturally */}
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/"               element={<Feed />} />
          <Route path="/entities"       element={<Entities />} />
          <Route path="/entities/:id"   element={<EntityProfile />} />
          <Route path="/flowmap"        element={<FlowMap />} />
          <Route path="/themes"         element={<Themes />} />
          <Route path="/search"         element={<Search />} />
          <Route path="/login"          element={<Login />} />
        </Routes>
      </main>
      {/* Permanent legal footer on every page */}
      <DisclaimerFooter />
    </div>
  )
}
