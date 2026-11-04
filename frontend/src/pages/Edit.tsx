import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import api, { publicBase } from '../lib/api'
import { applyTheme } from '../lib/theme'


function optionLabel(question: any, value: any): string {
  const options: any[] = question.options || []
  const found = options.find(o => String(o.value) === String(value))
  return found ? (found.label ?? String(found.value)) : String(value ?? '')
}

export default function Edit() {
  const { token } = useParams()
  const [data, setData] = useState<any>(null)
  const [poolData, setPoolData] = useState<any>(null)
  const [answers, setAnswers] = useState<any>({})
  const [design, setDesign] = useState<any>({})
  const [profile, setProfile] = useState<any>({})
  const [tab, setTab] = useState<'info' | 'answers' | 'pools' | 'design' | 'share'>('info')
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')
  const [savingPools, setSavingPools] = useState(false)

  const headers = { 'X-Edit-Token': token }

  const load = useCallback(async () => {
    try {
      const [profileRes, poolsRes] = await Promise.all([
        api.get('/edit/me', { headers }),
        api.get('/edit/me/pools', { headers }).catch(() => ({ data: null })),
      ])
      setData(profileRes.data)
      setProfile(profileRes.data.profile)
      setDesign(profileRes.data.design || {})
      const ans: any = {}
      Object.entries(profileRes.data.answers || {}).forEach(([k, v]: any) => {
        ans[k] = v?.value ?? ''
      })
      setAnswers(ans)
      setPoolData(poolsRes.data)
      setError('')
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Не удалось загрузить анкету')
    }
  }, [token])

  useEffect(() => { load() }, [load])

  const flash = (text: string) => {
    setMsg(text)
    setTimeout(() => setMsg(''), 1500)
  }

  const saveProfile = async () => {
    await api.put('/edit/me', profile, { headers })
    flash('Сохранено')
  }

  const saveAnswers = async () => {
    const payload = {
      answers: Object.entries(answers).map(([question_id, value]) => ({ question_id, value })),
    }
    await api.put('/edit/me/answers', payload, { headers })
    flash('Сохранено')
  }

  const saveDesign = async () => {
    await api.put('/edit/me/design', design, { headers })
    applyTheme(design)
    flash('Сохранено')
  }

  const uploadAvatar = async (e: any) => {
    const f = e.target.files[0]
    if (!f) return
    const fd = new FormData()
    fd.append('file', f)
    const res = await api.post('/edit/me/avatar', fd, { headers: { ...headers, 'Content-Type': 'multipart/form-data' } })
    setProfile({ ...profile, avatar_url: res.data.avatar_url })
  }

  const uploadBg = async (e: any) => {
    const f = e.target.files[0]
    if (!f) return
    const fd = new FormData()
    fd.append('file', f)
    const res = await api.post('/edit/me/bg', fd, { headers: { ...headers, 'Content-Type': 'multipart/form-data' } })
    setDesign({ ...design, bg_image_url: res.data.bg_image_url })
  }

  const copyLink = () => {
    navigator.clipboard.writeText(`${publicBase}/u/${profile.slug}`)
    flash('Скопировано')
  }

  const del = async () => {
    if (!confirm('Удалить анкету? Это действие нельзя отменить.')) return
    await api.delete('/edit/me', { headers })
    alert('Анкета удалена')
    window.location.href = '/'
  }

  const togglePool = async (poolId: string, checked: boolean) => {
    if (!poolData?.can_manage) return
    const selected: string[] = (poolData.pools || [])
      .filter((p: any) => (p.id === poolId ? checked : p.attached))
      .map((p: any) => p.id)
    setSavingPools(true)
    try {
      await api.put('/edit/me/pools', { pool_ids: selected }, { headers })
      await load()
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Не удалось обновить пулы')
    } finally {
      setSavingPools(false)
    }
  }

  const removePool = async (linkId: string) => {
    setSavingPools(true)
    try {
      await api.delete(`/edit/me/pools/${linkId}`, { headers })
      await load()
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Не удалось отключить пул')
    } finally {
      setSavingPools(false)
    }
  }

  if (error && !data) return <div className="min-h-screen flex items-center justify-center px-4">{error}</div>
  if (!data) return <div className="min-h-screen flex items-center justify-center">Loading...</div>

  const presets: any = {
    Dark: { bg_color: '#0f1026', text_color: '#f4f4f9', heading_color: '#ffffff', accent_color: '#7c3aed', card_color: '#1f2237', radius: '12px', bg_type: 'color' },
    Light: { bg_color: '#f8f9fa', text_color: '#212529', heading_color: '#111111', accent_color: '#6c5ce7', card_color: '#ffffff', radius: '12px', bg_type: 'color' },
    Midnight: { bg_color: '#000814', text_color: '#e0e1dd', heading_color: '#ffffff', accent_color: '#00b4d8', card_color: '#001d3d', radius: '10px', bg_type: 'color' },
    Cyberpunk: { bg_color: '#0a0a0f', text_color: '#00ff9f', heading_color: '#ff00ff', accent_color: '#ff3366', card_color: '#11111b', radius: '0px', bg_type: 'color' },
    Minimal: { bg_color: '#ffffff', text_color: '#1a1a1a', heading_color: '#000000', accent_color: '#333333', card_color: '#f7f7f7', radius: '8px', bg_type: 'color' },
    Pastel: { bg_color: '#fef7ff', text_color: '#4a4a4a', heading_color: '#333333', accent_color: '#a78bfa', card_color: '#ffffff', radius: '16px', bg_type: 'color' },
  }

  const applyPreset = (name: string) => {
    setDesign({ ...design, preset: name, ...presets[name] })
  }

  return (
    <div className="min-h-screen">
      <header className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
        <div className="text-xl font-bold">Редактор анкеты</div>
        <div className="flex gap-2">
          <a className="btn px-3 py-2" href={`/u/${profile.slug}`} target="_blank" rel="noreferrer">Посмотреть публичную</a>
          <button onClick={copyLink} className="btn px-3 py-2">Копировать ссылку</button>
        </div>
      </header>
      <div className="max-w-6xl mx-auto px-4 flex gap-2 mb-4 flex-wrap">
        <button className="btn px-3 py-2" onClick={() => setTab('info')}>Инфо</button>
        <button className="btn px-3 py-2" onClick={() => setTab('answers')}>Вопросы</button>
        <button className="btn px-3 py-2" onClick={() => setTab('pools')}>Мои пулы</button>
        <button className="btn px-3 py-2" onClick={() => setTab('design')}>Дизайн</button>
        <button className="btn px-3 py-2" onClick={() => setTab('share')}>Поделиться/Удалить</button>
      </div>
      <main className="max-w-6xl mx-auto px-4 pb-10">
        {msg && <div className="mb-3 text-success">{msg}</div>}
        {error && <div className="mb-3 text-danger">{error}</div>}

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
              <input type="file" accept="image/*" onChange={uploadAvatar} />
              {profile.avatar_url && <img src={profile.avatar_url} className="w-20 h-20 rounded-full mt-2 object-cover" />}
            </div>
            <button onClick={saveProfile} className="btn px-4 py-2">Save</button>
          </div>
        )}

        {tab === 'answers' && (
          <div className="space-y-6">
            {data.categories?.map((cat: any) => (
              <section key={cat.id} className="card p-6">
                <h2 className="text-xl font-semibold mb-1">{cat.title}</h2>
                {cat.source === 'pool' && <div className="text-sm opacity-60 mb-4">Пользовательский пул</div>}
                <div className="space-y-4">
                  {cat.questions?.map((q: any) => (
                    <div key={q.id}>
                      <label className="block mb-1">{q.title}{q.required && <span className="text-danger"> *</span>}</label>
                      {q.description && <div className="text-sm opacity-60 mb-1">{q.description}</div>}
                      {q.type === 'text' && <input className="input w-full px-3 py-2" value={answers[q.id] || ''} onChange={e => setAnswers({ ...answers, [q.id]: e.target.value })} />}
                      {q.type === 'textarea' && <textarea className="textarea w-full px-3 py-2" value={answers[q.id] || ''} onChange={e => setAnswers({ ...answers, [q.id]: e.target.value })} />}
                      {q.type === 'number' && <input type="number" className="input w-full px-3 py-2" value={answers[q.id] ?? ''} onChange={e => setAnswers({ ...answers, [q.id]: e.target.value })} />}
                      {q.type === 'date' && <input type="date" className="input w-full px-3 py-2" value={answers[q.id] || ''} onChange={e => setAnswers({ ...answers, [q.id]: e.target.value })} />}
                      {q.type === 'url' && <input type="url" className="input w-full px-3 py-2" value={answers[q.id] || ''} onChange={e => setAnswers({ ...answers, [q.id]: e.target.value })} />}
                      {q.type === 'boolean' && (
                        <label className="flex items-center gap-2">
                          <input type="checkbox" checked={!!answers[q.id]} onChange={e => setAnswers({ ...answers, [q.id]: e.target.checked })} />
                          <span>{answers[q.id] ? 'Да' : 'Нет'}</span>
                        </label>
                      )}
                      {q.type === 'select' && (
                        <select className="select w-full px-3 py-2" value={typeof answers[q.id] === 'string' ? answers[q.id] : ''} onChange={e => setAnswers({ ...answers, [q.id]: e.target.value })}>
                          <option value="">Не выбрано</option>
                          {q.options?.map((o: any) => <option key={o.value} value={o.value}>{o.label ?? o.value}</option>)}
                        </select>
                      )}
                      {q.type === 'multiselect' && (
                        <div className="flex flex-col gap-2">
                          {q.options?.map((o: any) => {
                            const current: string[] = Array.isArray(answers[q.id]) ? answers[q.id] : []
                            return (
                              <label key={o.value} className="flex items-center gap-2">
                                <input type="checkbox" checked={current.includes(o.value)} onChange={e => {
                                  const next = e.target.checked
                                    ? [...current, o.value]
                                    : current.filter((x: string) => x !== o.value)
                                  setAnswers({ ...answers, [q.id]: next })
                                }} />
                                <span>{o.label ?? o.value}</span>
                              </label>
                            )
                          })}
                        </div>
                      )}
                      {q.type === 'select' && answers[q.id] && (
                        <div className="text-xs opacity-60 mt-1">Выбрано: {optionLabel(q, answers[q.id])}</div>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            ))}
            <button onClick={saveAnswers} className="btn px-4 py-2">Сохранить ответы</button>
          </div>
        )}

        {tab === 'pools' && (
          <div className="space-y-4 max-w-3xl">
            <div className="card p-6">
              <h2 className="text-xl font-semibold mb-2">Стандартные вопросы</h2>
              <p className="opacity-70">Включены по умолчанию. Их можно отредактировать в разделе «Вопросы».</p>
            </div>

            <div className="card p-6 space-y-4">
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <h2 className="text-xl font-semibold">Мои пулы вопросов</h2>
                <div className="flex gap-2">
                  <Link to="/library" className="btn btn-secondary px-3 py-2" target="_blank">Библиотека</Link>
                  <Link to="/pools" className="btn px-3 py-2" target="_blank">Управлять пулами</Link>
                </div>
              </div>

              {!poolData?.authenticated && (
                <div className="text-sm opacity-80">
                  Войдите через VK ID в <Link to="/cabinet">личном кабинете</Link>, чтобы подключать свои пулы к этой анкете.
                </div>
              )}

              {poolData?.authenticated && !poolData?.can_manage && (
                <div className="text-sm text-danger">
                  Эта анкета привязана к другому аккаунту, поэтому подключать пулы нельзя.
                </div>
              )}

              {poolData?.authenticated && (poolData?.pools || []).length === 0 && (
                <div className="text-sm opacity-70">
                  У вас пока нет пулов. <Link to="/pools">Создайте первый пул</Link>.
                </div>
              )}

              <div className="space-y-2">
                {(poolData?.pools || []).map((pool: any) => (
                  <label key={pool.id} className="flex items-center justify-between gap-3 rounded border-theme px-3 py-2 cursor-pointer">
                    <span className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        checked={!!pool.attached}
                        disabled={!poolData?.can_manage || savingPools}
                        onChange={e => togglePool(pool.id, e.target.checked)}
                      />
                      <span>
                        <span className="font-medium">{pool.name}</span>
                        <span className="opacity-60 text-sm"> ({pool.count} вопросов)</span>
                        {pool.origin && <span className="text-xs opacity-60"> · из библиотеки</span>}
                      </span>
                    </span>
                    {pool.attached && <span className="text-xs opacity-70">подключён</span>}
                  </label>
                ))}
              </div>

              {(poolData?.attached || []).length > 0 && (
                <div className="pt-3 border-t-theme">
                  <div className="font-medium mb-2">Подключённые пулы</div>
                  <div className="space-y-2">
                    {poolData.attached.map((link: any) => (
                      <div key={link.id} className="flex items-center justify-between gap-3 text-sm">
                        <span>{link.name} ({link.count} вопросов)</span>
                        <button
                          className="btn btn-secondary px-3 py-1"
                          disabled={savingPools || !poolData?.can_manage}
                          onClick={() => removePool(link.id)}
                        >
                          Отключить
                        </button>
                      </div>
                    ))}
                  </div>
                  <p className="text-xs opacity-60 mt-2">
                    При отключении пула уже сохранённые ответы остаются в базе.
                  </p>
                </div>
              )}
            </div>

            <div className="card p-6">
              <h2 className="text-xl font-semibold mb-3">Вопросы в анкете</h2>
              <div className="space-y-2 text-sm">
                {(data.categories || []).map((cat: any) => (
                  <div key={cat.id} className="flex items-center justify-between gap-3">
                    <span>{cat.title} <span className="opacity-60">({cat.questions?.length || 0})</span></span>
                    <span className="opacity-60">{cat.source === 'pool' ? 'пул' : 'стандартные'}</span>
                  </div>
                ))}
              </div>
            </div>
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
              <input type="file" accept="image/*" onChange={uploadBg} />
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
              <a className="btn px-3 py-2 inline-block" href={`${api.defaults.baseURL}/profiles/${profile.slug}/json`} target="_blank" rel="noreferrer">Скачать JSON</a>
            </div>
            <div>
              <button onClick={del} className="btn btn-danger px-3 py-2">Удалить анкету</button>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
