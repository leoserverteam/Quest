import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api, { publicBase } from '../lib/api'

const VISIBILITY_LABELS: Record<string, string> = {
  private: 'Приватный',
  unlisted: 'По ссылке',
  public: 'Публичный',
}

function shareUrl(pool: any) {
  return pool.share_slug ? `${publicBase}/library/${pool.share_slug}` : ''
}

export default function Pools() {
  const [pools, setPools] = useState<any[]>([])
  const [name, setName] = useState('')
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')

  const load = () => api.get('/pools').then(r => setPools(r.data)).catch(() => setError('Не удалось загрузить пулы'))
  useEffect(() => { load() }, [])

  const create = async () => {
    if (!name.trim()) return
    setError('')
    try {
      await api.post('/pools', { name })
      setName('')
      load()
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Не удалось создать пул')
    }
  }

  const copyShareLink = (pool: any) => {
    const url = shareUrl(pool)
    if (!url) return
    navigator.clipboard.writeText(url)
    setMsg('Ссылка скопирована')
    setTimeout(() => setMsg(''), 2000)
  }

  return (
    <div className="min-h-screen">
      <header className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between gap-3 flex-wrap">
        <div>
          <div className="text-xl font-bold">Мои пулы вопросов</div>
          <div className="text-sm opacity-60">Собственные коллекции и пулы, добавленные из библиотеки</div>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Link to="/library" className="btn px-3 py-2">Библиотека вопросов</Link>
          <Link to="/cabinet" className="btn btn-secondary px-3 py-2">В кабинет</Link>
        </div>
      </header>
      <main className="max-w-5xl mx-auto px-4 space-y-4 pb-12">
        {msg && <div className="text-success">{msg}</div>}
        {error && <div className="text-danger">{error}</div>}

        <div className="card p-4 flex flex-col sm:flex-row gap-2">
          <input
            className="input flex-1 px-3 py-2"
            placeholder="Название пула"
            value={name}
            onChange={e => setName(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') create() }}
          />
          <button onClick={create} className="btn px-3 py-2">Создать</button>
        </div>

        {pools.length === 0 && (
          <div className="card p-8 text-center space-y-3">
            <div className="text-lg font-semibold">У вас пока нет пулов</div>
            <div className="opacity-70 text-sm">Создайте свой пул или добавьте готовый из библиотеки.</div>
            <Link to="/library" className="btn px-4 py-2 inline-block">Открыть библиотеку</Link>
          </div>
        )}

        {pools.map(pool => (
          <div key={pool.id} className="card p-4 space-y-3">
            <div className="flex items-start justify-between gap-3 flex-wrap">
              <div>
                <div className="font-semibold flex items-center gap-2 flex-wrap">
                  {pool.name}
                  <span className={`text-xs px-2 py-0.5 rounded border-theme ${pool.visibility === 'public' ? 'text-success' : ''}`}>
                    {VISIBILITY_LABELS[pool.visibility] || pool.visibility}
                  </span>
                  {pool.origin && <span className="text-xs opacity-60">из библиотеки</span>}
                </div>
                <div className="opacity-70 text-sm">
                  {pool.count} вопросов
                  {pool.category && <> · {pool.category}</>}
                  {pool.adds_count > 0 && <> · {pool.adds_count} добавлений</>}
                  {pool.views_count > 0 && <> · {pool.views_count} просмотров</>}
                </div>
                {pool.description && <div className="text-sm opacity-60 mt-1 line-clamp-2">{pool.description}</div>}
                {pool.tags?.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-1 text-xs opacity-60">
                    {pool.tags.map((tag: string) => <span key={tag}>#{tag}</span>)}
                  </div>
                )}
              </div>
              <div className="flex gap-2 flex-wrap">
                {pool.visibility !== 'private' && pool.share_slug && (
                  <Link to={`/library/${pool.share_slug}`} className="btn btn-secondary px-3 py-1 text-sm">Открыть</Link>
                )}
                {pool.share_slug && pool.visibility !== 'private' && (
                  <button onClick={() => copyShareLink(pool)} className="btn btn-secondary px-3 py-1 text-sm">Ссылка</button>
                )}
                <Link to={`/pools/${pool.id}`} className="btn px-3 py-1 text-sm">Редактировать</Link>
              </div>
            </div>
            {pool.origin && (
              <div className="text-xs opacity-60">
                Создано на основе пула пользователя {pool.origin.author_name || 'неизвестного автора'}
                {pool.origin.title ? ` «${pool.origin.title}»` : ''}
                {pool.origin.available && pool.origin.share_slug && (
                  <> · <Link to={`/library/${pool.origin.share_slug}`} className="hover:underline">оригинал</Link></>
                )}
              </div>
            )}
          </div>
        ))}
      </main>
    </div>
  )
}
