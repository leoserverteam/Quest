import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import api, { publicBase } from '../lib/api'

const VISIBILITY_LABELS: Record<string, string> = {
  private: 'Приватный',
  unlisted: 'Доступен по ссылке',
  public: 'Публичный',
}

const VISIBILITY_HINTS: Record<string, string> = {
  private: 'Виден только вам. В библиотеке не отображается.',
  unlisted: 'Не показывается в каталоге, но доступен по специальной ссылке.',
  public: 'Показывается в библиотеке вопросов. Другие пользователи могут добавить пул себе.',
}

const TYPE_LABELS: Record<string, string> = {
  text: 'Короткий текст',
  textarea: 'Развёрнутый текст',
  boolean: 'Да / Нет',
  select: 'Один вариант (Single Choice)',
  multiselect: 'Несколько вариантов (Multiple Choice)',
  number: 'Число',
  date: 'Дата',
  url: 'Ссылка',
}

const CHOICE_TYPES = ['select', 'multiselect']

type Option = { value: string; label: string }

function emptyForm() {
  return {
    title: '',
    description: '',
    type: 'text',
    required: false,
    options: [] as Option[],
  }
}

function validateForm(form: ReturnType<typeof emptyForm>): string {
  if (!form.title.trim()) return 'Укажите текст вопроса'
  if (CHOICE_TYPES.includes(form.type)) {
    if (form.options.length === 0) return 'Добавьте хотя бы один вариант ответа'
    const values = new Set<string>()
    for (const option of form.options) {
      if (!option.value.trim()) return 'Идентификатор варианта не может быть пустым'
      if (!option.label.trim()) return 'Текст варианта не может быть пустым'
      if (values.has(option.value.trim())) return `Вариант с идентификатором «${option.value.trim()}» уже существует`
      values.add(option.value.trim())
    }
  }
  return ''
}

export default function PoolEdit() {
  const { id } = useParams()
  const [pool, setPool] = useState<any>(null)
  const [form, setForm] = useState(emptyForm())
  const [editingId, setEditingId] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const [categories, setCategories] = useState<any[]>([])
  const [pub, setPub] = useState<any>({
    name: '',
    description: '',
    visibility: 'private',
    category: '',
    tags: '',
    cover_url: null,
  })
  const [pubMsg, setPubMsg] = useState('')
  const [pubError, setPubError] = useState('')
  const [pubBusy, setPubBusy] = useState(false)

  const load = () => api.get(`/pools/${id}`).then(r => setPool(r.data)).catch(() => setError('Не удалось загрузить пул'))

  useEffect(() => { load() }, [id])

  useEffect(() => {
    api.get('/library/meta').then(r => setCategories(r.data.categories || [])).catch(() => {})
  }, [])

  useEffect(() => {
    if (!pool) return
    setPub({
      name: pool.name || '',
      description: pool.description || '',
      visibility: pool.visibility || 'private',
      category: pool.category || '',
      tags: (pool.tags || []).join(', '),
      cover_url: pool.cover_url || null,
    })
  }, [pool?.id])

  const isChoice = CHOICE_TYPES.includes(form.type)

  const resetForm = () => {
    setForm(emptyForm())
    setEditingId(null)
    setError('')
  }

  const changeType = (type: string) => {
    setForm(prev => ({
      ...prev,
      type,
      options: CHOICE_TYPES.includes(type) && prev.options.length === 0
        ? [{ value: 'option_1', label: '' }]
        : prev.options,
    }))
  }

  const addOption = () => {
    setForm(prev => ({
      ...prev,
      options: [...prev.options, { value: `option_${prev.options.length + 1}`, label: '' }],
    }))
  }

  const updateOption = (index: number, patch: Partial<Option>) => {
    setForm(prev => ({
      ...prev,
      options: prev.options.map((option, i) => i === index ? { ...option, ...patch } : option),
    }))
  }

  const removeOption = (index: number) => {
    setForm(prev => ({ ...prev, options: prev.options.filter((_, i) => i !== index) }))
  }

  const moveOption = (index: number, direction: -1 | 1) => {
    const target = index + direction
    if (target < 0 || target >= form.options.length) return
    setForm(prev => {
      const options = [...prev.options]
      const [item] = options.splice(index, 1)
      options.splice(target, 0, item)
      return { ...prev, options }
    })
  }

  const startEdit = (item: any) => {
    setEditingId(item.id)
    setForm({
      title: item.title || '',
      description: item.description || '',
      type: item.type || 'text',
      required: !!item.required,
      options: Array.isArray(item.options)
        ? item.options.map((o: any) => ({ value: String(o.value ?? ''), label: String(o.label ?? '') }))
        : [],
    })
    setError('')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const submit = async () => {
    const validationError = validateForm(form)
    if (validationError) {
      setError(validationError)
      return
    }
    setBusy(true)
    setError('')
    try {
      const payload: any = {
        title: form.title.trim(),
        description: form.description.trim() || null,
        type: form.type,
        required: form.required,
        options: isChoice
          ? form.options.map(o => ({ value: o.value.trim(), label: o.label.trim() }))
          : null,
      }
      if (editingId) {
        await api.put(`/pools/${id}/items/${editingId}`, payload)
      } else {
        await api.post(`/pools/${id}/items`, payload)
      }
      resetForm()
      await load()
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Не удалось сохранить вопрос')
    } finally {
      setBusy(false)
    }
  }

  const del = async (item: any) => {
    if (!confirm(`Удалить вопрос «${item.title}»?`)) return
    try {
      await api.delete(`/pools/${id}/items/${item.id}`)
      if (editingId === item.id) resetForm()
      await load()
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Не удалось удалить вопрос')
    }
  }

  const savePublication = async (visibilityOverride?: string) => {
    setPubBusy(true)
    setPubMsg('')
    setPubError('')
    try {
      const payload = {
        visibility: visibilityOverride || pub.visibility,
        name: pub.name,
        description: pub.description || null,
        category: pub.category || null,
        tags: pub.tags.split(',').map((t: string) => t.trim()).filter(Boolean),
      }
      const res = await api.put(`/pools/${id}/publication`, payload)
      setPool({
        ...pool,
        name: pub.name,
        description: pub.description,
        visibility: res.data.visibility,
        share_slug: res.data.share_slug,
        category: res.data.category,
        tags: res.data.tags,
        published_at: res.data.published_at,
      })
      setPub({ ...pub, visibility: res.data.visibility })
      setPubMsg(res.data.visibility === 'private' ? 'Пул снят с публикации' : 'Настройки публикации сохранены')
      setTimeout(() => setPubMsg(''), 2500)
    } catch (e: any) {
      setPubError(e?.response?.data?.detail || 'Не удалось сохранить настройки публикации')
    } finally {
      setPubBusy(false)
    }
  }

  const uploadCover = async (e: any) => {
    const file = e.target.files?.[0]
    if (!file) return
    setPubBusy(true)
    setPubError('')
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await api.post(`/pools/${id}/cover`, fd, { headers: { 'Content-Type': 'multipart/form-data' } })
      setPub({ ...pub, cover_url: res.data.cover_url })
      setPool({ ...pool, cover_url: res.data.cover_url })
    } catch (err: any) {
      setPubError(err?.response?.data?.detail || 'Не удалось загрузить обложку')
    } finally {
      setPubBusy(false)
    }
  }

  const copyShareLink = () => {
    if (!pool?.share_slug) return
    navigator.clipboard.writeText(`${publicBase}/library/${pool.share_slug}`)
    setPubMsg('Ссылка скопирована')
    setTimeout(() => setPubMsg(''), 2000)
  }

  if (!pool) return <div className="p-4">{error || 'Загрузка...'}</div>

  return (
    <div className="min-h-screen">
      <header className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
        <div className="text-xl font-bold">{pool.name}</div>
        <Link to="/pools" className="btn px-3 py-2">К пулам</Link>
      </header>
      <main className="max-w-4xl mx-auto px-4 space-y-4 pb-10">
        {pool.origin && (
          <div className="card p-4 text-sm opacity-80">
            Создано на основе пула пользователя {pool.origin.author_name || 'неизвестного автора'}
            {pool.origin.title ? ` «${pool.origin.title}»` : ''}
            {pool.origin.available && pool.origin.share_slug && (
              <> · <Link to={`/library/${pool.origin.share_slug}`} className="hover:underline">открыть оригинал</Link></>
            )}
          </div>
        )}

        <div className="card p-4 space-y-3">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <div className="font-semibold">Публикация в библиотеке</div>
            <span className="text-xs px-2 py-0.5 rounded border-theme">{VISIBILITY_LABELS[pub.visibility]}</span>
          </div>

          <div className="grid md:grid-cols-2 gap-3">
            <div>
              <label className="block mb-1 text-sm opacity-80">Название</label>
              <input className="input w-full px-3 py-2" value={pub.name} onChange={e => setPub({ ...pub, name: e.target.value })} />
            </div>
            <div>
              <label className="block mb-1 text-sm opacity-80">Категория</label>
              <select className="select w-full px-3 py-2" value={pub.category} onChange={e => setPub({ ...pub, category: e.target.value })}>
                <option value="">Без категории</option>
                {categories.map((category: any) => (
                  <option key={category.id} value={category.id}>{category.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block mb-1 text-sm opacity-80">Описание</label>
            <textarea className="textarea w-full px-3 py-2" value={pub.description} onChange={e => setPub({ ...pub, description: e.target.value })} />
          </div>

          <div>
            <label className="block mb-1 text-sm opacity-80">Теги (через запятую)</label>
            <input className="input w-full px-3 py-2" placeholder="музыка, кино, игры" value={pub.tags} onChange={e => setPub({ ...pub, tags: e.target.value })} />
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            <div>
              <label className="block mb-1 text-sm opacity-80">Обложка</label>
              <input type="file" accept="image/*" onChange={uploadCover} />
            </div>
            {pub.cover_url && <img src={pub.cover_url} className="h-16 w-28 object-cover rounded" alt="" />}
          </div>

          <div className="space-y-2">
            {(['private', 'unlisted', 'public'] as const).map(value => (
              <label key={value} className="flex items-start gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="visibility"
                  className="mt-1"
                  checked={pub.visibility === value}
                  onChange={() => setPub({ ...pub, visibility: value })}
                />
                <span>
                  <span className="font-medium">{VISIBILITY_LABELS[value]}</span>
                  <span className="block text-xs opacity-60">{VISIBILITY_HINTS[value]}</span>
                </span>
              </label>
            ))}
          </div>

          {pubError && <div className="text-danger text-sm">{pubError}</div>}
          {pubMsg && <div className="text-success text-sm">{pubMsg}</div>}

          <div className="flex gap-2 flex-wrap">
            <button onClick={() => savePublication()} disabled={pubBusy} className="btn px-3 py-2">
              {pubBusy ? 'Сохраняем...' : 'Сохранить настройки'}
            </button>
            {pub.visibility !== 'private' && (
              <button onClick={() => savePublication('private')} disabled={pubBusy} className="btn btn-secondary px-3 py-2">
                Снять с публикации
              </button>
            )}
            {pool.share_slug && pool.visibility !== 'private' && (
              <button onClick={copyShareLink} className="btn btn-secondary px-3 py-2">Скопировать ссылку</button>
            )}
          </div>
          {pool.share_slug && pool.visibility !== 'private' && (
            <div className="text-xs break-all opacity-60">{publicBase}/library/{pool.share_slug}</div>
          )}
        </div>

        <div className="card p-4 space-y-3">
          <div className="font-semibold">{editingId ? 'Редактировать вопрос' : 'Добавить вопрос'}</div>

          <div>
            <label className="block mb-1 text-sm opacity-80">Текст вопроса</label>
            <input
              className="input w-full px-3 py-2"
              placeholder="Название вопроса"
              value={form.title}
              onChange={e => setForm({ ...form, title: e.target.value })}
            />
          </div>

          <div>
            <label className="block mb-1 text-sm opacity-80">Описание (необязательно)</label>
            <input
              className="input w-full px-3 py-2"
              placeholder="Подсказка к вопросу"
              value={form.description}
              onChange={e => setForm({ ...form, description: e.target.value })}
            />
          </div>

          <div className="flex flex-wrap gap-4 items-end">
            <div>
              <label className="block mb-1 text-sm opacity-80">Тип вопроса</label>
              <select className="select px-3 py-2" value={form.type} onChange={e => changeType(e.target.value)}>
                {Object.entries(TYPE_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>
            <label className="flex items-center gap-2 pb-2">
              <input
                type="checkbox"
                checked={form.required}
                onChange={e => setForm({ ...form, required: e.target.checked })}
              />
              <span>Обязательный вопрос</span>
            </label>
          </div>

          {isChoice && (
            <div className="space-y-2 rounded border-theme p-3">
              <div className="flex items-center justify-between">
                <div className="font-medium text-sm">Варианты ответа</div>
                <button type="button" className="btn btn-secondary px-3 py-1" onClick={addOption}>Добавить вариант</button>
              </div>
              {form.options.length === 0 && <div className="text-sm opacity-60">Добавьте хотя бы один вариант.</div>}
              {form.options.map((option, index) => (
                <div key={index} className="flex flex-wrap md:flex-nowrap gap-2 items-center">
                  <input
                    className="input px-2 py-1 w-32"
                    placeholder="ID"
                    value={option.value}
                    onChange={e => updateOption(index, { value: e.target.value })}
                  />
                  <input
                    className="input px-2 py-1 flex-1 min-w-[10rem]"
                    placeholder="Текст варианта"
                    value={option.label}
                    onChange={e => updateOption(index, { label: e.target.value })}
                  />
                  <div className="flex gap-1">
                    <button type="button" className="btn btn-secondary px-2 py-1" disabled={index === 0} onClick={() => moveOption(index, -1)}>↑</button>
                    <button type="button" className="btn btn-secondary px-2 py-1" disabled={index === form.options.length - 1} onClick={() => moveOption(index, 1)}>↓</button>
                    <button type="button" className="btn btn-danger px-2 py-1" onClick={() => removeOption(index)}>×</button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {error && <div className="text-danger text-sm">{error}</div>}

          <div className="flex gap-2">
            <button onClick={submit} disabled={busy} className="btn px-3 py-2">
              {busy ? 'Сохраняем...' : editingId ? 'Сохранить изменения' : 'Добавить'}
            </button>
            {editingId && <button onClick={resetForm} className="btn btn-secondary px-3 py-2">Отмена</button>}
          </div>
        </div>

        <div className="space-y-2">
          <div className="font-semibold px-1">Вопросы в пуле ({pool.items?.length || 0})</div>
          {pool.items?.map((it: any) => (
            <div key={it.id} className="card p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="font-medium">
                    {it.title}
                    {it.required && <span className="text-danger"> *</span>}
                  </div>
                  <div className="opacity-70 text-sm">{TYPE_LABELS[it.type] || it.type}</div>
                  {it.description && <div className="opacity-60 text-sm mt-1">{it.description}</div>}
                  {it.options?.length > 0 && (
                    <div className="mt-2 text-sm">
                      {it.options.map((o: any) => (
                        <span key={o.value} className="inline-block mr-2 opacity-80">
                          • {o.label} <span className="opacity-50">({o.value})</span>
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <div className="flex gap-2 shrink-0">
                  <button onClick={() => startEdit(it)} className="btn btn-secondary px-3 py-1">Изменить</button>
                  <button onClick={() => del(it)} className="btn btn-danger px-3 py-1">Удалить</button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  )
}
