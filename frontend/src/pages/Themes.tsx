import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../lib/api'

export default function Themes() {
  const [presets, setPresets] = useState<any>({})
  const [themes, setThemes] = useState<any[]>([])

  useEffect(() => {
    api.get('/themes/presets').then(r => setPresets(r.data))
    api.get('/themes').then(r => setThemes(r.data))
  }, [])

  return (
    <div className="min-h-screen">
      <header className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
        <div className="text-xl font-bold">Оформления</div>
        <Link to="/cabinet" className="btn px-3 py-2">В кабинет</Link>
      </header>
      <main className="max-w-6xl mx-auto px-4 space-y-6">
        <section>
          <h2 className="text-xl font-semibold mb-3">Готовые темы</h2>
          <div className="grid md:grid-cols-3 gap-3">
            {Object.entries(presets).map(([name, cfg]: any) => (
              <div key={name} className="card p-4">
                <div className="font-semibold mb-1">{name}</div>
                <div className="text-sm opacity-70 mb-2">{cfg.preset}</div>
              </div>
            ))}
          </div>
        </section>
        <section>
          <h2 className="text-xl font-semibold mb-3">Мои сохранённые темы</h2>
          <div className="grid md:grid-cols-3 gap-3">
            {themes.map(t => (
              <div key={t.id} className="card p-4">
                <div className="font-semibold">{t.name}</div>
              </div>
            ))}
            {themes.length === 0 && <div className="opacity-70">Пока нет сохранённых тем</div>}
          </div>
        </section>
      </main>
    </div>
  )
}
