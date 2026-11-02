import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import api from '../lib/api'

export default function PoolEdit() {
  const { id } = useParams()
  const [pool, setPool] = useState<any>(null)
  const [form, setForm] = useState<any>({ title: '', type: 'text' })

  const load = () => api.get(`/pools/${id}`).then(r => setPool(r.data))
  useEffect(() => { load() }, [id])

  const add = async () => {
    await api.post(`/pools/${id}/items`, form)
    setForm({ title: '', type: 'text' })
    load()
  }

  const del = async (itemId: string) => {
    await api.delete(`/pools/${id}/items/${itemId}`)
    load()
  }

  if (!pool) return <div className="p-4">Загрузка...</div>

  return (
    <div className="min-h-screen">
      <header className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
        <div className="text-xl font-bold">{pool.name}</div>
        <Link to="/pools" className="btn px-3 py-2">К пулам</Link>
      </header>
      <main className="max-w-4xl mx-auto px-4 space-y-4">
        <div className="card p-4 space-y-2">
          <div className="font-semibold">Добавить вопрос</div>
          <input className="input w-full px-3 py-2" placeholder="Название вопроса" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} />
          <select className="select px-3 py-2" value={form.type} onChange={e => setForm({ ...form, type: e.target.value })}>
            <option value="text">Короткий текст</option>
            <option value="textarea">Развёрнутый текст</option>
            <option value="boolean">Да/Нет</option>
            <option value="select">Один вариант</option>
            <option value="multiselect">Несколько вариантов</option>
            <option value="number">Число</option>
            <option value="date">Дата</option>
            <option value="url">Ссылка</option>
          </select>
          <button onClick={add} className="btn px-3 py-2">Добавить</button>
        </div>
        {pool.items?.map((it: any) => (
          <div key={it.id} className="card p-4 flex items-center justify-between">
            <div>
              <div className="font-medium">{it.title}</div>
              <div className="opacity-70 text-sm">{it.type}</div>
            </div>
            <button onClick={() => del(it.id)} className="btn px-3 py-2">Удалить</button>
          </div>
        ))}
      </main>
    </div>
  )
}
