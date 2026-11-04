import { Link } from 'react-router-dom'

export default function Home() {
  return (
    <div className="min-h-screen">
      <header className="max-w-6xl mx-auto px-4 py-8 flex items-center justify-between">
        <div className="text-xl font-bold">Quest</div>
        <div className="flex gap-2">
          <Link to="/library" className="btn btn-secondary px-4 py-2">Библиотека</Link>
          <Link to="/cabinet" className="btn px-4 py-2">Личный кабинет</Link>
          <Link to="/create" className="btn px-4 py-2">Создать анкету</Link>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-4">
        <section className="text-center py-16">
          <h1 className="text-4xl md:text-6xl font-bold mb-4 animate-fade-in-up">Персональная платформа анкет</h1>
          <p className="text-lg opacity-80 mb-8 animate-fade-in-up">Создай уникальную страницу о себе с кастомным дизайном, своими вопросами и пулами. Войди через VK чтобы управлять всеми анкетами в одном месте.</p>
          <div className="flex gap-3 justify-center flex-wrap">
            <Link to="/create" className="btn px-6 py-3 text-lg">Создать анкету</Link>
            <Link to="/cabinet" className="btn px-6 py-3 text-lg">Личный кабинет</Link>
          </div>
        </section>
        <section className="grid md:grid-cols-4 gap-4 py-10">
          <div className="card p-6 animate-fade-in-up">
            <h3 className="text-xl font-semibold mb-2">VK ID</h3>
            <p className="opacity-80">Быстрый вход и привязка старых анкет</p>
          </div>
          <div className="card p-6 animate-fade-in-up">
            <h3 className="text-xl font-semibold mb-2">Пулы вопросов</h3>
            <p className="opacity-80">Создай свои коллекции и используй в нескольких анкетах</p>
          </div>
          <div className="card p-6 animate-fade-in-up">
            <h3 className="text-xl font-semibold mb-2">Расширенный дизайн</h3>
            <p className="opacity-80">Градиенты, шрифты, эффекты, сохранение тем</p>
          </div>
          <div className="card p-6 animate-fade-in-up">
            <h3 className="text-xl font-semibold mb-2">Анимации</h3>
            <p className="opacity-80">Живой интерфейс с поддержкой prefers-reduced-motion</p>
          </div>
        </section>
        <section className="py-10 text-center">
          <p className="opacity-70">Пример: <a href="/u/leo">/u/leo</a></p>
        </section>
      </main>
      <footer className="max-w-6xl mx-auto px-4 py-10 text-center opacity-60">
        Quest • Персональные страницы с индивидуальностью
      </footer>
    </div>
  )
}
