import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../lib/api'

export default function Pools() {
  const [pools, setPools] = useState<any[]>([])
  const [name, setName] = useState('')

  const load = () => api.get('/pools').then(r => setPools(r.data))
  useEffect(() => { load() }, [])

  const create = async () => {
    if (!name) return
    await api.post('/pools', { name })
    setName('')
    load()
  }

  return (
    <div className="min-h-screen">
      <header className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
        <div className="text-xl font-bold">Мои пулы вопросов</div>
        <Link to="/cabinet" className="btn px-3 py-2">В кабинет</Link>
      </header>
      <main className="max-w-5xl mx-auto px-4 space-y-4">
        <div className="card p-4 flex gap-2">
          <input className="input flex-1 px-3 py-2" placeholder="Название пула" value={name} onChange={e => setName(e.target.value)} />
          <button onClick={create} className="btn px-3 py-2">Создать</button>
        </div>
        {pools.map(p => (
          <div key={p.id} className="card p-4 flex items-center justify-between">
            <div>
              <div className="font-semibold">{p.name}</div>
              <div className="opacity-70 text-sm">{p.count} вопросов</div>
            </div>
            <a className="btn px-3 py-2" href={`/pools/${p.id}`}>Редактировать</a>
          </div>
        ))}
      </main>
    </div>
  )
}
