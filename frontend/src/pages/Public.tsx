import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import api from '../lib/api'
import { applyTheme } from '../lib/theme'

function optionLabel(question: any, value: any): string {
  const options: any[] = question.options || []
  const found = options.find(o => String(o.value) === String(value))
  return found ? (found.label ?? String(found.value)) : String(value ?? '')
}

function formatAnswer(question: any, value: any): string {
  if (value === null || value === undefined || value === '') return ''
  if (typeof value === 'boolean') return value ? 'Да' : 'Нет'
  if (question.type === 'boolean') return value ? 'Да' : 'Нет'
  if (question.type === 'select') return optionLabel(question, value)
  if (question.type === 'multiselect') {
    const values = Array.isArray(value) ? value : [value]
    return values.map(v => optionLabel(question, v)).join(', ')
  }
  if (Array.isArray(value)) return value.join(', ')
  return String(value)
}

export default function Public() {
  const { slug } = useParams()
  const [data, setData] = useState<any>(null)
  const [err, setErr] = useState('')

  useEffect(() => {
    api.get(`/profiles/${slug}/public`).then(r => {
      setData(r.data)
      // Apply the full theme (dark, light, gradient, translucent, custom).
      applyTheme(r.data.design || {})

      // OG meta tags
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
          {p.avatar_url ? <img src={p.avatar_url} className="w-20 h-20 rounded-full object-cover" /> : <div className="w-20 h-20 rounded-full avatar-placeholder" />}
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
                    {formatAnswer(q, answers[q.id])}
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
