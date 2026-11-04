import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import api from '../lib/api'

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
    return new Date(value).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })
  } catch {
    return ''
  }
}

export default function LibraryPool() {
  const { slug } = useParams()
  const [data, setData] = useState<any>(null)
  const [user, setUser] = useState<any>(null)
  const [error, setError] = useState('')
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.get('/auth/me').then(r => setUser(r.data.user)).catch(() => setUser(null))
  }, [])

  useEffect(() => {
    api.get(`/library/pools/${slug}`)
      .then(r => setData(r.data))
      .catch(e => setError(e?.response?.status === 404
        ? 'Пул не найден, снят с публикации или ссылка недействительна'
        : e?.response?.data?.detail || 'Не удалось загрузить пул'))
  }, [slug])

  const loginVk = async () => {
    const res = await api.get('/auth/vk/login')
    if (res.data.url) window.location.href = res.data.url
  }

  const add = async () => {
    setBusy(true)
    setError('')
    setMsg('')
    try {
      const res = await api.post(`/library/pools/${slug}/copy`)
      setMsg(res.data.message)
      setData({
        ...data,
        is_added: true,
        adds_count: (data.adds_count || 0) + (res.data.created ? 1 : 0),
        users_count: (data.users_count || data.adds_count || 0) + (res.data.created ? 1 : 0),
      })
    } catch (e: any) {
      if (e?.response?.status === 401) {
        setUser(null)
      } else {
        setError(e?.response?.data?.detail || 'Не удалось добавить пул')
      }
    } finally {
      setBusy(false)
    }
  }

  const copyLink = () => {
    navigator.clipboard.writeText(window.location.href)
    setMsg('Ссылка скопирована')
    setTimeout(() => setMsg(''), 2000)
  }

  if (error && !data) return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="card p-6 text-center space-y-3 max-w-md">
        <div className="text-lg font-semibold">{error}</div>
        <Link to="/library" className="btn px-4 py-2 inline-block">В библиотеку</Link>
      </div>
    </div>
  )
  if (!data) return <div className="min-h-screen flex items-center justify-center">Загрузка...</div>

  return (
    <div className="min-h-screen">
      <header className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between gap-3 flex-wrap">
        <Link to="/library" className="btn btn-secondary px-3 py-2">← Библиотека</Link>
        <button onClick={copyLink} className="btn btn-secondary px-3 py-2">Скопировать ссылку</button>
      </header>

      <main className="max-w-4xl mx-auto px-4 pb-12 space-y-5">
        {msg && <div className="text-success">{msg}</div>}
        {error && <div className="text-danger">{error}</div>}

        <section className="card overflow-hidden">
          {data.cover_url && <img src={data.cover_url} alt="" className="w-full max-h-64 object-cover" />}
          <div className="p-6 space-y-4">
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div>
                <h1 className="text-2xl md:text-3xl font-bold">{data.name}</h1>
                <div className="opacity-70 mt-1">
                  {data.author?.display_name ? (
                    data.author.profile_slug ? (
                      <Link to={`/u/${data.author.profile_slug}`} className="hover:underline">{data.author.display_name}</Link>
                    ) : data.author.display_name
                  ) : 'Неизвестный автор'}
                  {data.published_at && <> · опубликован {formatDate(data.published_at)}</>}
                </div>
              </div>
              <div className="flex gap-2 flex-wrap">
                {data.is_owner ? (
                  <Link to={`/pools/${data.id}`} className="btn px-4 py-2">Редактировать пул</Link>
                ) : data.is_added ? (
                  <Link to="/pools" className="btn btn-secondary px-4 py-2">Уже в моих пулах</Link>
                ) : user ? (
                  <button className="btn px-4 py-2" disabled={busy} onClick={add}>
                    {busy ? 'Добавляем...' : 'Добавить в мои пулы'}
                  </button>
                ) : (
                  <button className="btn px-4 py-2" onClick={loginVk}>Войти через VK ID</button>
                )}
              </div>
            </div>

            {!user && !data.is_owner && (
              <div className="text-sm opacity-70">
                Чтобы добавить пул в свои коллекции, войдите через VK ID. Пулы можно смотреть без авторизации.
              </div>
            )}

            {data.description && <p className="whitespace-pre-wrap opacity-90">{data.description}</p>}

            <div className="flex flex-wrap items-center gap-2 text-sm">
              {data.category_label && <span className="px-2 py-1 rounded border-theme">{data.category_label}</span>}
              {data.tags?.map((tag: string) => (
                <Link key={tag} to={`/library?tag=${encodeURIComponent(tag)}`} className="px-2 py-1 rounded border-theme opacity-80 hover:opacity-100">
                  #{tag}
                </Link>
              ))}
            </div>

            <div className="flex flex-wrap gap-4 text-sm opacity-80 pt-2 border-t-theme">
              <span>{data.count} вопросов</span>
              <span>{data.adds_count} добавлений</span>
              <span>{data.users_count ?? data.adds_count} пользователей</span>
              <span>{data.views_count} просмотров</span>
            </div>

            {data.origin && (
              <div className="text-sm opacity-80 rounded border-theme p-3">
                Создано на основе пула пользователя{' '}
                {data.origin.author_name ? (
                  data.origin.author_profile_slug ? (
                    <Link to={`/u/${data.origin.author_profile_slug}`} className="hover:underline">{data.origin.author_name}</Link>
                  ) : (
                    <span>{data.origin.author_name}</span>
                  )
                ) : (
                  'неизвестного автора'
                )}
                {data.origin.title ? <> «{data.origin.title}»</> : null}.
                {data.origin.available && data.origin.share_slug && (
                  <> <Link to={`/library/${data.origin.share_slug}`} className="hover:underline">Открыть оригинал</Link>.</>
                )}
              </div>
            )}
          </div>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold px-1">Вопросы пула</h2>
          {data.items?.length === 0 && <div className="card p-4 opacity-70">В пуле пока нет вопросов.</div>}
          {data.items?.map((question: any, index: number) => (
            <div key={question.id} className="card p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="font-medium">
                  {index + 1}. {question.title}
                  {question.required && <span className="text-danger"> *</span>}
                </div>
                <span className="text-xs opacity-60 shrink-0">{TYPE_LABELS[question.type] || question.type}</span>
              </div>
              {question.description && <div className="text-sm opacity-60 mt-1">{question.description}</div>}
              {question.options?.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {question.options.map((option: any) => (
                    <span key={option.value} className="text-sm px-2 py-1 rounded border-theme opacity-80">
                      {option.label}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </section>
      </main>
    </div>
  )
}
