import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import api from '../lib/api'

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

  const load = () => api.get(`/pools/${id}`).then(r => setPool(r.data)).catch(() => setError('Не удалось загрузить пул'))

  useEffect(() => { load() }, [id])

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

  if (!pool) return <div className="p-4">{error || 'Загрузка...'}</div>

  return (
    <div className="min-h-screen">
      <header className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
        <div className="text-xl font-bold">{pool.name}</div>
        <Link to="/pools" className="btn px-3 py-2">К пулам</Link>
      </header>
      <main className="max-w-4xl mx-auto px-4 space-y-4 pb-10">
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
