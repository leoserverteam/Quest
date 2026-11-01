import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../lib/api'

export default function Create() {
  const nav = useNavigate()
  const [slug, setSlug] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [bio, setBio] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const res = await api.post('/profiles', { slug, display_name: displayName, bio })
      const token = res.data.edit_token
      nav(`/edit/${token}`)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Ошибка создания')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <form onSubmit={submit} className="card p-6 w-full max-w-md space-y-4">
        <h1 className="text-2xl font-bold">Создать анкету</h1>
        <div>
          <label className="block mb-1">Публичный slug</label>
          <input className="input w-full px-3 py-2" value={slug} onChange={e => setSlug(e.target.value)} placeholder="leo" required />
          <p className="text-sm opacity-60 mt-1">Будет в ссылке /u/{slug || '...'}</p>
        </div>
        <div>
          <label className="block mb-1">Отображаемое имя</label>
          <input className="input w-full px-3 py-2" value={displayName} onChange={e => setDisplayName(e.target.value)} required />
        </div>
        <div>
          <label className="block mb-1">Краткое описание</label>
          <textarea className="textarea w-full px-3 py-2" value={bio} onChange={e => setBio(e.target.value)} />
        </div>
        {error && <div className="text-red-400">{error}</div>}
        <button disabled={loading} className="btn px-4 py-2 w-full">{loading ? 'Создаём...' : 'Создать'}</button>
      </form>
    </div>
  )
}
