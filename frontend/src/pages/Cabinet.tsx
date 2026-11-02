import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../lib/api'

export default function Cabinet() {
  const [user, setUser] = useState<any>(null)
  const [data, setData] = useState<any>(null)
  const [token, setToken] = useState('')

  useEffect(() => {
    api.get('/auth/me').then(r => setUser(r.data.user))
    api.get('/cabinet').then(r => setData(r.data)).catch(() => {})
  }, [])

  const loginVk = async () => {
    const res = await api.get('/auth/vk/login')
    if (res.data.url) window.location.href = res.data.url
  }

  const logout = async () => {
    await api.post('/auth/logout')
    window.location.reload()
  }

  const attach = async () => {
    if (!token) return
    await api.post('/cabinet/attach', null, { params: { edit_token: token } })
    window.location.reload()
  }

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="card p-6 space-y-4 max-w-md w-full text-center">
          <h1 className="text-2xl font-bold">Личный кабинет</h1>
          <p className="opacity-80">Войдите через VK ID, чтобы управлять анкетами и пулами вопросов</p>
          <button onClick={loginVk} className="btn px-4 py-2 w-full">Войти через VK</button>
          <Link to="/" className="block opacity-70">На главную</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen">
      <header className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
        <div className="text-xl font-bold">Кабинет</div>
        <div className="flex gap-2 items-center">
          <span className="opacity-80">{user.display_name}</span>
          <button onClick={logout} className="btn px-3 py-2">Выйти</button>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-4 space-y-6">
        <section className="card p-6">
          <h2 className="text-xl font-semibold mb-3">Мои анкеты</h2>
          <div className="flex flex-wrap gap-2 mb-4">
            {data?.profiles?.map((p: any) => (
              <a key={p.id} className="btn px-3 py-2" href={`/u/${p.slug}`} target="_blank">{p.display_name} (/u/{p.slug})</a>
            ))}
          </div>
          <div className="flex gap-2">
            <input className="input px-3 py-2" placeholder="Секретный edit-токен для привязки" value={token} onChange={e => setToken(e.target.value)} />
            <button onClick={attach} className="btn px-3 py-2">Привязать старую анкету</button>
          </div>
        </section>
        <section className="grid md:grid-cols-3 gap-4">
          <Link to="/pools" className="card p-6 hover:opacity-90">Мои пулы вопросов ({data?.pools_count || 0})</Link>
          <Link to="/themes" className="card p-6 hover:opacity-90">Мои оформления ({data?.themes_count || 0})</Link>
          <Link to="/create" className="card p-6 hover:opacity-90">Создать новую анкету</Link>
        </section>
      </main>
    </div>
  )
}
