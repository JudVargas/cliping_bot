import React from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { router } from './app/router'
import { Providers } from './app/providers'
import { Toaster } from 'sonner'
import './styles/tokens.css'
import './styles/base.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <Providers>
        <RouterProvider router={router} />
      </Providers>
      <Toaster
        position="top-right"
        richColors
        closeButton
        duration={4000}
        className="max-w-[400px]"
      />
    </QueryClientProvider>
  </React.StrictMode>,
)
