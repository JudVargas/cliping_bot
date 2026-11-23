import * as React from 'react'
import { Outlet, NavLink, useLocation } from 'react-router-dom'

const navItems = [
  { to: '/', label: 'Videos', icon: 'video' },
  { to: '/clips', label: 'Clips', icon: 'scissors' },
  { to: '/ajustes', label: 'Ajustes', icon: 'settings' },
]

function railLinkClassName({ isActive }: { isActive: boolean }): string {
  const base =
    'flex items-center gap-3 w-full px-4 py-3 rounded-panel text-ink-muted transition-colors'
  const active = isActive
    ? 'bg-plasma/10 text-plasma border-r-2 border-plasma'
    : 'hover:bg-panel-2 hover:text-ink'
  return `${base} ${active}`
}

function bottomLinkClassName({ isActive }: { isActive: boolean }): string {
  const base =
    'flex flex-col items-center gap-1 px-3 py-2 rounded-panel text-ink-muted transition-colors'
  const active = isActive
    ? 'bg-plasma/10 text-plasma'
    : 'hover:bg-panel-2 hover:text-ink'
  return `${base} ${active}`
}

export function Shell() {
  const location = useLocation()

  return (
    <div className="min-h-dvh bg-void text-ink relative z-10 lg:grid lg:grid-cols-[72px_1fr]">
      {/* Rail lateral (solo escritorio) */}
      <nav
        className="hidden lg:flex flex-col items-center gap-4 pt-6 pb-6 border-r border-line w-72 surface"
      >
        <div className="flex items-center gap-2 px-4 mb-6">
          <div className="w-6 h-6 rounded-sm bg-plasma flex items-center justify-center">
            <span className="text-[10px] font-bold">CF</span>
          </div>
          <span className="font-sora font-semibold text-lg tracking-tighter">ClipForge</span>
        </div>
        {navItems.map((item) => {
          const isActive =
            item.to === '/'
              ? location.pathname === item.to
              : location.pathname === item.to ||
                location.pathname.startsWith(item.to + '/')
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={railLinkClassName}
              onClick={() => {}}
            >
              {item.icon === 'video' && (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="13 2 3 14 13 22" />
                  <polyline points="22 2 12 14 2 22" />
                </svg>
              )}
              {item.icon === 'scissors' && (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="6" cy="6" r="3" />
                  <circle cx="6" cy="18" r="3" />
                  <line x1="18" y1="6" x2="16.1" y2="7.9" />
                  <line x1="7.9" y1="16.1" x2="6" y2="18" />
                  <line x1="18" y1="18" x2="16.1" y2="16.1" />
                </svg>
              )}
              {item.icon === 'settings' && (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="3" />
                  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82-.33l-.06-.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0 0-1.82l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l.06-.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
                </svg>
              )}
              <span className="font-manrope text-sm">{item.label}</span>
            </NavLink>
          )
        })}
      </nav>

      <main className="flex-1 min-h-0 pb-[calc(4.5rem+env(safe-area-inset-bottom))] lg:pb-0 overflow-y-auto">
        <Outlet />
      </main>

      {/* BottomNav móvil */}
      <nav className="fixed inset-x-0 bottom-0 z-40 surface-glass border-t border-line lg:hidden px-4 py-3">
        <div className="flex justify-around gap-4">
          {navItems.map((item) => {
            const isActive =
              item.to === '/'
                ? location.pathname === item.to
                : location.pathname === item.to ||
                  location.pathname.startsWith(item.to + '/')
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={bottomLinkClassName}
                onClick={() => {}}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  {item.icon === 'video' && (
                    <>
                      <polyline points="13 2 3 14 13 22" />
                      <polyline points="22 2 12 14 2 22" />
                    </>
                  )}
                  {item.icon === 'scissors' && (
                    <>
                      <circle cx="6" cy="6" r="3" />
                      <circle cx="6" cy="18" r="3" />
                      <line x1="18" y1="6" x2="16.1" y2="7.9" />
                      <line x1="7.9" y1="16.1" x2="6" y2="18" />
                      <line x1="18" y1="18" x2="16.1" y2="16.1" />
                    </>
                  )}
                  {item.icon === 'settings' && (
                    <circle cx="12" cy="12" r="3" />
                  )}
                </svg>
                <span className="text-[10px] font-medium">{item.label}</span>
              </NavLink>
            )
          })}
        </div>
      </nav>
    </div>
  )
}
