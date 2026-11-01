import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import api from '../lib/api'

export default function Public() {
  const { slug } = useParams()
  const [data, setData] = useState<any>(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    api.get(`/profiles/${slug}/public`).then(r => {
      setData(r.data)
      // apply design
      const d = r.data.design
      const root = document.documentElement
      if (d.bg_color) root.style.setProperty('--q-bg', d.bg_color)
      if (d.text_color) root.style.setProperty('--q-text', d.text_color)
      if (d.heading_color) root.style.setProperty('--q-heading', d.heading_color)
      if (d.accent_color) root.style.setProperty('--q-accent', d.accent_color)
      if (d.card_color) root.style.setProperty('--q-card', d.card_color)
      if (d.radius) root.style.setProperty('--q-radius', d.radius)
      if (d.bg_image_url) {
        document.body.style.backgroundImage = `url(${d.bg_image_url})`
        document.body.style.backgroundSize = 'cover'
        document.body.style.backgroundAttachment = 'fixed'
      }
      // OG
      const p = r.data.profile
      const metaTitle = document.createElement('meta')
      metaTitle.setAttribute('property', 'og:title')
      metaTitle.content = p.display_name
      document.head.appendChild(metaTitle)
      const metaDesc = document.createElement('meta')
      metaDesc.setAttribute('property', 'og:description')
      metaDesc.content = p.bio || 'Анкета на Quest'
      document.head.appendChild(metaDesc)
    }).catch(e => setErr(e?.response?.data?.detail || 'Ошибка'))
  }, [slug])

  if (err) return <div className="min-h-screen flex items-center justify-center">{err}</div>
  if (!data) return <div className="min-h-screen flex items-center justify-center">Загрузка...</div>

  const p = data.profile
  const answers = data.answers || {}

  return (
    <div className="min-h-screen">
      <main className="max-w-3xl mx-auto px-4 py-10">
        <div className="card p-6 mb-6 flex items-center gap-4">
          {p.avatar_url ? <img src={p.avatar_url} className="w-20 h-20 rounded-full object-cover" /> : <div className="w-20 h-20 rounded-full bg-white/10" />}
          <div>
            <h1 className="text-2xl font-bold">{p.display_name}</h1>
            {p.bio && <p className="opacity-80">{p.bio}</p>}
          </div>
        </div>

        {data.categories?.map((cat: any) => (
          <section key={cat.id} className="mb-6">
            <h2 className="text-xl font-semibold mb-3">{cat.title}</h2>
            <div className="space-y-3">
              {cat.questions?.map((q: any) => (
                <div key={q.id} className="card p-4">
                  <div className="font-medium mb-1">{q.title}</div>
                  {q.description && <div className="text-sm opacity-60 mb-2">{q.description}</div>}
                  <div className="whitespace-pre-wrap break-words">
                    {Array.isArray(answers[q.id]) ? answers[q.id].join(', ') : String(answers[q.id] ?? '')}
                  </div>
                </div>
              ))}
            </div>
          </section>
        ))}

        <div className="text-center opacity-50 text-sm">Сделано на <a href="/">Quest</a></div>
      </main>
    </div>
  )
}
