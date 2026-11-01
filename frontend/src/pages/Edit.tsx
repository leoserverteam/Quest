import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import api from '../lib/api'
import { publicBase } from '../lib/api'

export default function Edit() {
  const { token } = useParams()
  const [data, setData] = useState<any>(null)
  const [answers, setAnswers] = useState<any>({})
  const [design, setDesign] = useState<any>({})
  const [profile, setProfile] = useState<any>({})
  const [tab, setTab] = useState<'info' | 'answers' | 'design' | 'share'>('info')
  const [msg, setMsg] = useState('')

  useEffect(() => {
    api.get('/edit/me', { headers: { 'X-Edit-Token': token } }).then(r => {
      setData(r.data)
      setProfile(r.data.profile)
      setDesign(r.data.design || {})
      const ans: any = {}
      Object.entries(r.data.answers || {}).forEach(([k, v]: any) => { ans[k] = (v as any)?.value })
      setAnswers(ans)
    })
  }, [token])

  const saveProfile = async () => {
    await api.put('/edit/me', profile, { headers: { 'X-Edit-Token': token } })
    setMsg('Сохранено')
    setTimeout(() => setMsg(''), 1500)
  }

  const saveAnswers = async () => {
    const payload = { answers: Object.entries(answers).map(([question_id, value]) => ({ question_id, value })) }
    await api.put('/edit/me/answers', payload, { headers: { 'X-Edit-Token': token } })
    setMsg('Сохранено')
    setTimeout(() => setMsg(''), 1500)
  }

  const saveDesign = async () => {
    await api.put('/edit/me/design', design, { headers: { 'X-Edit-Token': token } })
    setMsg('Сохранено')
    setTimeout(() => setMsg(''), 1500)
    const root = document.documentElement
    Object.entries(design).forEach(([k, v]: any) => {
      if (k === 'preset') return
      if (k.endsWith('_color') && v) root.style.setProperty('--q-' + k.replace('_color', '').replace('_', '-'), v)
      if (k === 'radius' && v) root.style.setProperty('--q-radius', v)
    })
  }

  const uploadAvatar = async (e: any) => {
    const f = e.target.files[0]
    if (!f) return
    const fd = new FormData()
    fd.append('file', f)
    const res = await api.post('/edit/me/avatar', fd, { headers: { 'X-Edit-Token': token, 'Content-Type': 'multipart/form-data' } })
    setProfile({ ...profile, avatar_url: res.data.avatar_url })
  }

  const uploadBg = async (e: any) => {
    const f = e.target.files[0]
    if (!f) return
    const fd = new FormData()
    fd.append('file', f)
    const res = await api.post('/edit/me/bg', fd, { headers: { 'X-Edit-Token': token, 'Content-Type': 'multipart/form-data' } })
    setDesign({ ...design, bg_image_url: res.data.bg_image_url })
  }

  const copyLink = () => {
    navigator.clipboard.writeText(`${publicBase}/u/${profile.slug}`)
    setMsg('Скопировано')
    setTimeout(() => setMsg(''), 1500)
  }

  const del = async () => {
    if (!confirm('Удалить анкету? Это действие нельзя отменить.')) return
    await api.delete('/edit/me', { headers: { 'X-Edit-Token': token } })
    alert('Анкета удалена')
    window.location.href = '/'
  }

  if (!data) return <div className="min-h-screen flex items-center justify-center">Loading...</div>

  const presets: any = {
    Dark: { bg_color: '#0f1026', text_color: '#f4f4f9', heading_color: '#ffffff', accent_color: '#7c3aed', card_color: '#1f2237', radius: '12px' },
    Light: { bg_color: '#f8f9fa', text_color: '#212529', heading_color: '#111111', accent_color: '#6c5ce7', card_color: '#ffffff', radius: '12px' },
    Midnight: { bg_color: '#000814', text_color: '#e0e1dd', heading_color: '#ffffff', accent_color: '#00b4d8', card_color: '#001d3d', radius: '10px' },
    Cyberpunk: { bg_color: '#0a0a0f', text_color: '#00ff9f', heading_color: '#ff00ff', accent_color: '#ff3366', card_color: '#11111b', radius: '0px' },
    Minimal: { bg_color: '#ffffff', text_color: '#1a1a1a', heading_color: '#000000', accent_color: '#333333', card_color: '#f7f7f7', radius: '8px' },
    Pastel: { bg_color: '#fef7ff', text_color: '#4a4a4a', heading_color: '#333333', accent_color: '#a78bfa', card_color: '#ffffff', radius: '16px' },
  }

  const applyPreset = (name: string) => {
    setDesign({ ...design, preset: name, ...presets[name] })
  }

  return (
    <div className="min-h-screen">
      <header className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
        <div className="text-xl font-bold">Редактор анкеты</div>
        <div className="flex gap-2">
          <a className="btn px-3 py-2" href={`/u/${profile.slug}`} target="_blank">Посмотреть публичную</a>
          <button onClick={copyLink} className="btn px-3 py-2">Копировать ссылку</button>
        </div>
      </header>
      <div className="max-w-6xl mx-auto px-4 flex gap-2 mb-4">
        <button className="btn px-3 py-2" onClick={() => setTab('info')}>Инфо</button>
        <button className="btn px-3 py-2" onClick={() => setTab('answers')}>Вопросы</button>
        <button className="btn px-3 py-2" onClick={() => setTab('design')}>Дизайн</button>
        <button className="btn px-3 py-2" onClick={() => setTab('share')}>Поделиться/Удалить</button>
      </div>
      <main className="max-w-6xl mx-auto px-4 pb-10">
        {msg && <div className="mb-3 text-green-400">{msg}</div>}

        {tab === 'info' && (
          <div className="card p-6 space-y-4 max-w-xl">
            <div>
              <label className="block mb-1">Отображаемое имя</label>
              <input className="input w-full px-3 py-2" value={profile.display_name || ''} onChange={e => setProfile({ ...profile, display_name: e.target.value })} />
            </div>
            <div>
              <label className="block mb-1">Краткое описание</label>
              <textarea className="textarea w-full px-3 py-2" value={profile.bio || ''} onChange={e => setProfile({ ...profile, bio: e.target.value })} />
            </div>
            <div>
              <label className="block mb-1">Slug</label>
              <input className="input w-full px-3 py-2" value={profile.slug || ''} onChange={e => setProfile({ ...profile, slug: e.target.value })} />
            </div>
            <div>
              <label className="block mb-1">Аватар</label>
              <input type="file" onChange={uploadAvatar} />
              {profile.avatar_url && <img src={profile.avatar_url} className="w-20 h-20 rounded-full mt-2" />}
            </div>
            <button onClick={saveProfile} className="btn px-4 py-2">Save</button>
          </div>
        )}

        {tab === 'answers' && (
          <div className="space-y-6">
            {data.categories?.map((cat: any) => (
              <section key={cat.id} className="card p-6">
                <h2 className="text-xl font-semibold mb-4">{cat.title}</h2>
                <div className="space-y-4">
                  {cat.questions?.map((q: any) => (
                    <div key={q.id}>
                      <label className="block mb-1">{q.title}{q.required && <span className="text-red-400"> *</span>}</label>
                      {q.description && <div className="text-sm opacity-60 mb-1">{q.description}</div>}
                      {q.type === 'text' && <input className="input w-full px-3 py-2" value={answers[q.id] || ''} onChange={e => setAnswers({ ...answers, [q.id]: e.target.value })} />}
                      {q.type === 'textarea' && <textarea className="textarea w-full px-3 py-2" value={answers[q.id] || ''} onChange={e => setAnswers({ ...answers, [q.id]: e.target.value })} />}
                      {q.type === 'number' && <input type="number" className="input w-full px-3 py-2" value={answers[q.id] || ''} onChange={e => setAnswers({ ...answers, [q.id]: e.target.value })} />}
                      {q.type === 'date' && <input type="date" className="input w-full px-3 py-2" value={answers[q.id] || ''} onChange={e => setAnswers({ ...answers, [q.id]: e.target.value })} />}
                      {q.type === 'url' && <input type="url" className="input w-full px-3 py-2" value={answers[q.id] || ''} onChange={e => setAnswers({ ...answers, [q.id]: e.target.value })} />}
                      {q.type === 'boolean' && (
                        <label className="flex items-center gap-2">
                          <input type="checkbox" checked={!!answers[q.id]} onChange={e => setAnswers({ ...answers, [q.id]: e.target.checked })} />
                          <span>Да/Нет</span>
                        </label>
                      )}
                      {q.type === 'select' && (
                        <select className="select w-full px-3 py-2" value={answers[q.id] || ''} onChange={e => setAnswers({ ...answers, [q.id]: e.target.value })}>
                          <option value="">Не выбрано</option>
                          {q.options?.map((o: any) => <option key={o.value} value={o.value}>{o.label}</option>)}
                        </select>
                      )}
                      {q.type === 'multiselect' && (
                        <div className="flex flex-col gap-2">
                          {q.options?.map((o: any) => (
                            <label key={o.value} className="flex items-center gap-2">
                              <input type="checkbox" checked={(answers[q.id] || []).includes(o.value)} onChange={e => {
                                const arr = answers[q.id] || []
                                if (e.target.checked) setAnswers({ ...answers, [q.id]: [...arr, o.value] })
                                else setAnswers({ ...answers, [q.id]: arr.filter((x: string) => x !== o.value) })
                              }} />
                              <span>{o.label}</span>
                            </label>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            ))}
            <button onClick={saveAnswers} className="btn px-4 py-2">Сохранить ответы</button>
          </div>
        )}

        {tab === 'design' && (
          <div className="card p-6 space-y-4 max-w-xl">
            <div>
              <label className="block mb-1">Пресеты</label>
              <div className="flex flex-wrap gap-2">
                {Object.keys(presets).map(name => (
                  <button key={name} className="btn px-3 py-1" onClick={() => applyPreset(name)}>{name}</button>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block mb-1">Фон</label>
                <input type="color" value={design.bg_color || '#0f1026'} onChange={e => setDesign({ ...design, bg_color: e.target.value })} />
              </div>
              <div>
                <label className="block mb-1">Текст</label>
                <input type="color" value={design.text_color || '#f4f4f9'} onChange={e => setDesign({ ...design, text_color: e.target.value })} />
              </div>
              <div>
                <label className="block mb-1">Заголовки</label>
                <input type="color" value={design.heading_color || '#ffffff'} onChange={e => setDesign({ ...design, heading_color: e.target.value })} />
              </div>
              <div>
                <label className="block mb-1">Акцент</label>
                <input type="color" value={design.accent_color || '#7c3aed'} onChange={e => setDesign({ ...design, accent_color: e.target.value })} />
              </div>
              <div>
                <label className="block mb-1">Карточки</label>
                <input type="color" value={design.card_color || '#1f2237'} onChange={e => setDesign({ ...design, card_color: e.target.value })} />
              </div>
              <div>
                <label className="block mb-1">Скругление</label>
                <input className="input px-2 py-1" value={design.radius || '12px'} onChange={e => setDesign({ ...design, radius: e.target.value })} />
              </div>
            </div>
            <div>
              <label className="block mb-1">Фоновое изображение</label>
              <input type="file" onChange={uploadBg} />
              {design.bg_image_url && <img src={design.bg_image_url} className="mt-2 max-h-40 rounded" />}
            </div>
            <button onClick={saveDesign} className="btn px-4 py-2">Сохранить дизайн</button>
          </div>
        )}

        {tab === 'share' && (
          <div className="card p-6 space-y-4 max-w-xl">
            <div>
              <div className="font-medium mb-1">Публичная ссылка</div>
              <div className="flex gap-2">
                <input className="input flex-1 px-3 py-2" readOnly value={`${publicBase}/u/${profile.slug}`} />
                <button onClick={copyLink} className="btn px-3 py-2">Копировать</button>
              </div>
            </div>
            <div>
              <a className="btn px-3 py-2 inline-block" href={`${api.defaults.baseURL}/profiles/${profile.slug}/json`} target="_blank">Скачать JSON</a>
            </div>
            <div>
              <button onClick={del} className="btn px-3 py-2 bg-red-600">Удалить анкету</button>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
