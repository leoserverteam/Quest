import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import api from '../lib/api'

type LibraryItem = {
  id: string
  share_slug: string
  name: string
  description?: string | null
  category?: string | null
  category_label?: string | null
  tags: string[]
  cover_url?: string | null
  count: number
  author?: { display_name: string; avatar_url?: string | null; profile_slug?: string | null } | null
  views_count: number
  adds_count: number
  published_at?: string | null
  is_owner: boolean
  is_added: boolean
  origin?: { title?: string | null; author_name?: string | null } | null
  preview: { title: string; type: string; required: boolean }[]
}

const TYPE_LABELS: Record<string, string> = {
  text: 'Короткий текст',
  textarea: 'Развёрнутый текст',
  boolean: 'Да / Нет',
  select: 'Один вариант',
  multiselect: 'Несколько вариантов',
  number: 'Число',
  date: 'Дата',
  url: 'Ссылка',
}

function formatDate(value?: string | null) {
  if (!value) return ''
  try {
    return new Date(value).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', year: 'numeric' })
  } catch {
    return ''
  }
}

export default function Library() {
  const nav = useNavigate()
  const [searchParams] = useSearchParams()
  const [items, setItems] = useState<LibraryItem[]>([])
  const [meta, setMeta] = useState<any>(null)
  const [q, setQ] = useState('')
  const [category, setCategory] = useState(searchParams.get('category') || '')
  const [tag, setTag] = useState(searchParams.get('tag') || '')
  const [sort, setSort] = useState('popular')
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(0)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [preview, setPreview] = useState<any>(null)
  const [previewLoading, setPreviewLoading] = useState(false)

  useEffect(() => {
    api.get('/library/meta').then(r => setMeta(r.data)).catch(() => {})
  }, [])

  useEffect(() => {
    setTag(searchParams.get('tag') || '')
    setCategory(searchParams.get('category') || '')
  }, [searchParams])

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await api.get('/library/pools', {
        params: { q: q || undefined, category: category || undefined, tag: tag || undefined, sort, page, limit: 12 },
      })
      setItems(res.data.items || [])
      setPages(res.data.pages || 0)
      setTotal(res.data.total || 0)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Не удалось загрузить библиотеку')
    } finally {
      setLoading(false)
    }
  }, [q, category, tag, sort, page])

  useEffect(() => {
    const timer = setTimeout(load, q ? 300 : 0)
    return () => clearTimeout(timer)
  }, [load, q])

  useEffect(() => {
    setPage(1)
  }, [q, category, tag, sort])

  const tags = useMemo(() => meta?.tags || [], [meta])

  const openPreview = async (item: LibraryItem) => {
    setPreviewLoading(true)
    setPreview({ ...item, items: null })
    try {
      const res = await api.get(`/library/pools/${item.share_slug}`, { params: { preview: 1 } })
      setPreview(res.data)
    } catch {
      // keep the short preview from the list response
    } finally {
      setPreviewLoading(false)
    }
  }

  return (
    <div className="min-h-screen">
      <header className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between gap-3 flex-wrap">
        <div>
          <div className="text-xl font-bold">Библиотека вопросов</div>
          <div className="text-sm opacity-60">Публичные пулы, которыми поделились пользователи Quest</div>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Link to="/pools" className="btn btn-secondary px-3 py-2">Мои пулы</Link>
          <Link to="/cabinet" className="btn px-3 py-2">В кабинет</Link>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 pb-12 space-y-5">
        <section className="card p-4 space-y-3">
          <div className="flex flex-col md:flex-row gap-2">
            <input
              className="input flex-1 px-3 py-2"
              placeholder="Поиск по названию и описанию"
              value={q}
              onChange={e => setQ(e.target.value)}
            />
            <select className="select px-3 py-2" value={category} onChange={e => setCategory(e.target.value)}>
              <option value="">Все категории</option>
              {(meta?.categories_with_counts?.length ? meta.categories_with_counts : meta?.categories || []).map((c: any) => (
                <option key={c.id} value={c.id}>
                  {c.label}{typeof c.count === 'number' ? ` (${c.count})` : ''}
                </option>
              ))}
            </select>
            <select className="select px-3 py-2" value={sort} onChange={e => setSort(e.target.value)}>
              <option value="popular">По популярности</option>
              <option value="recent">По дате публикации</option>
            </select>
          </div>

          {tags.length > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm opacity-60">Теги:</span>
              <button
                className={`btn px-2 py-1 text-sm ${tag ? 'btn-secondary' : ''}`}
                onClick={() => setTag('')}
              >
                все
              </button>
              {tags.slice(0, 16).map((t: any) => (
                <button
                  key={t.tag}
                  className={`btn px-2 py-1 text-sm ${tag === t.tag ? '' : 'btn-secondary'}`}
                  onClick={() => setTag(tag === t.tag ? '' : t.tag)}
                >
                  #{t.tag} <span className="opacity-60">{t.count}</span>
                </button>
              ))}
            </div>
          )}
        </section>

        {error && <div className="text-danger">{error}</div>}
        {loading && <div className="opacity-70">Загрузка...</div>}
        {!loading && !error && items.length === 0 && (
          <div className="card p-8 text-center space-y-2">
            <div className="text-lg font-semibold">Пока ничего не найдено</div>
            <div className="opacity-70 text-sm">
              {q || category || tag ? 'Попробуйте изменить фильтры.' : 'Опубликуйте свой пул — он появится здесь.'}
            </div>
            <Link to="/pools" className="btn px-4 py-2 inline-block">Перейти к моим пулам</Link>
          </div>
        )}

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map(item => (
            <article key={item.id} className="card overflow-hidden flex flex-col">
              <button className="block text-left" onClick={() => nav(`/library/${item.share_slug}`)}>
                <div className="h-28 w-full bg-black/20 relative">
                  {item.cover_url ? (
                    <img src={item.cover_url} alt="" className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-3xl font-bold opacity-40">
                      {item.name.slice(0, 2).toUpperCase()}
                    </div>
                  )}
                  {item.category_label && (
                    <span className="absolute top-2 left-2 text-xs px-2 py-1 rounded bg-black/50">
                      {item.category_label}
                    </span>
                  )}
                </div>
              </button>
              <div className="p-4 flex-1 flex flex-col gap-2">
                <div className="flex items-start justify-between gap-2">
                  <button className="text-left font-semibold hover:underline" onClick={() => nav(`/library/${item.share_slug}`)}>
                    {item.name}
                  </button>
                  {item.is_added && <span className="text-xs text-success shrink-0">добавлен</span>}
                </div>
                {item.description && <p className="text-sm opacity-70 line-clamp-3">{item.description}</p>}
                <div className="text-sm opacity-70">
                  {item.author?.display_name ? (
                    item.author.profile_slug ? (
                      <Link to={`/u/${item.author.profile_slug}`} className="hover:underline">{item.author.display_name}</Link>
                    ) : (
                      item.author.display_name
                    )
                  ) : (
                    'Неизвестный автор'
                  )}
                </div>
                {item.tags?.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {item.tags.slice(0, 4).map(t => (
                      <button key={t} className="text-xs opacity-70 hover:opacity-100" onClick={() => setTag(t)}>#{t}</button>
                    ))}
                  </div>
                )}
                <div className="mt-auto flex items-center justify-between text-xs opacity-70 pt-2">
                  <span>{item.count} вопросов</span>
                  <span>+{item.adds_count} · {item.views_count} просм.</span>
                </div>
                {item.published_at && <div className="text-xs opacity-50">{formatDate(item.published_at)}</div>}
                <div className="flex gap-2 pt-1">
                  <button className="btn btn-secondary px-3 py-1 text-sm flex-1" onClick={() => openPreview(item)}>
                    Предпросмотр
                  </button>
                  <button className="btn px-3 py-1 text-sm flex-1" onClick={() => nav(`/library/${item.share_slug}`)}>
                    Открыть
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>

        {pages > 1 && (
          <div className="flex items-center justify-center gap-3">
            <button className="btn btn-secondary px-3 py-1" disabled={page <= 1} onClick={() => setPage(p => Math.max(1, p - 1))}>
              Назад
            </button>
            <span className="text-sm opacity-70">Страница {page} из {pages} · всего {total}</span>
            <button className="btn btn-secondary px-3 py-1" disabled={page >= pages} onClick={() => setPage(p => p + 1)}>
              Вперёд
            </button>
          </div>
        )}
      </main>

      {preview && (
        <div className="modal-backdrop fixed inset-0 z-50 flex items-center justify-center p-4" onClick={() => setPreview(null)}>
          <div className="modal modal-content card max-w-2xl w-full max-h-[85vh] overflow-y-auto p-6" onClick={e => e.stopPropagation()}>
            <div className="flex items-start justify-between gap-3 mb-3">
              <div>
                <h2 className="text-xl font-bold">{preview.name}</h2>
                <div className="text-sm opacity-70">
                  {preview.author?.display_name || 'Неизвестный автор'} · {preview.count} вопросов
                </div>
              </div>
              <button className="btn btn-secondary px-3 py-1" onClick={() => setPreview(null)}>Закрыть</button>
            </div>
            {preview.description && <p className="opacity-80 mb-4">{preview.description}</p>}
            {preview.tags?.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-4">
                {preview.tags.map((t: string) => <span key={t} className="text-xs opacity-70">#{t}</span>)}
              </div>
            )}
            {previewLoading && <div className="opacity-70 text-sm">Загрузка вопросов...</div>}
            <div className="space-y-2">
              {(preview.items || preview.preview || []).map((question: any, index: number) => (
                <div key={question.id || index} className="rounded border-theme p-3">
                  <div className="font-medium">{index + 1}. {question.title}{question.required && <span className="text-danger"> *</span>}</div>
                  <div className="text-xs opacity-60">{TYPE_LABELS[question.type] || question.type}</div>
                  {question.options?.length > 0 && (
                    <div className="text-sm opacity-80 mt-1">{question.options.map((o: any) => o.label).join(' · ')}</div>
                  )}
                </div>
              ))}
            </div>
            <div className="flex gap-2 mt-4">
              <button className="btn px-4 py-2" onClick={() => nav(`/library/${preview.share_slug}`)}>Открыть пул</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
