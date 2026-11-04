import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './styles/index.css'
import Home from './pages/Home'
import Create from './pages/Create'
import Edit from './pages/Edit'
import Public from './pages/Public'
import NotFound from './pages/NotFound'
import Cabinet from './pages/Cabinet'
import Pools from './pages/Pools'
import PoolEdit from './pages/PoolEdit'
import Themes from './pages/Themes'
import Library from './pages/Library'
import LibraryPool from './pages/LibraryPool'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/create" element={<Create />} />
        <Route path="/edit/:token" element={<Edit />} />
        <Route path="/u/:slug" element={<Public />} />
        <Route path="/cabinet" element={<Cabinet />} />
        <Route path="/pools" element={<Pools />} />
        <Route path="/pools/:id" element={<PoolEdit />} />
        <Route path="/themes" element={<Themes />} />
        <Route path="/library" element={<Library />} />
        <Route path="/library/:slug" element={<LibraryPool />} />
        <Route path="/pool/:slug" element={<LibraryPool />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
)
