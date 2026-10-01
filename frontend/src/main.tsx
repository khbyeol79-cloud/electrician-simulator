import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { AccountGate } from './components/AccountGate'
import { ErrorBoundary } from './components/ErrorBoundary'
import './styles/global.css'
import './styles/responsive.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <AccountGate>{(account, onAccountOpen) => <App key={account?.userId ?? 'local'} account={account} onAccountOpen={onAccountOpen} />}</AccountGate>
      </BrowserRouter>
    </ErrorBoundary>
  </React.StrictMode>,
)

