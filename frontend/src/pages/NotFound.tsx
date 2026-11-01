import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center">
      <h1 className="text-4xl font-bold mb-4">404</h1>
      <p className="opacity-70 mb-6">Страница не найдена</p>
      <Link to="/" className="btn px-4 py-2">На главную</Link>
    </div>
  )
}
