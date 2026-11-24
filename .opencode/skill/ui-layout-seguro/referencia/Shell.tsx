import { NavLink, Outlet } from 'react-router-dom'
import { Film, Scissors, Settings } from 'lucide-react'
import './shell.css'

const NAV = [
  { to: '/', label: 'Videos', icon: Film, end: true },
  { to: '/clips', label: 'Clips', icon: Scissors, end: false },
  { to: '/ajustes', label: 'Ajustes', icon: Settings, end: false },
]

export function Shell() {
  return (
    <div className="shell">
      <aside className="shell__side">
        <div className="brand"><span className="brand__logo">CF</span><span className="brand__name">ClipForge</span></div>
        <nav aria-label="Principal">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} className="navlink">
              <Icon size={18} strokeWidth={1.75} aria-hidden="true" />{label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <main className="shell__main">
        <div className="shell__content"><Outlet /></div>
      </main>

      <nav className="shell__tabs" aria-label="Principal (móvil)">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} className="tab">
            <Icon size={20} strokeWidth={1.75} aria-hidden="true" />{label}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
