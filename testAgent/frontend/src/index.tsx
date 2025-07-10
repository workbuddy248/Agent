import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import E2ETestingAgent from './App';

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <E2ETestingAgent />
  </React.StrictMode>
);