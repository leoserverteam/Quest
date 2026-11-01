import { Link } from 'react-router-dom'

export default function Home() {
  return (
    <div className="min-h-screen">
      <header className="max-w-5xl mx-auto px-4 py-8 flex items-center justify-between">
        <div className="text-xl font-bold">Quest</div>
        <Link to="/create" className="btn px-4 py-2">Создать анкету</Link>
      </header>
      <main className="max-w-5xl mx-auto px-4">
        <section className="text-center py-16">
          <h1 className="text-4xl md:text-6xl font-bold mb-4">Социальная анкета для тебя</h1>
          <p className="text-lg opacity-80 mb-8">Создай персональную интерактивную анкету без регистрации. Настрой дизайн, ответь на вопросы, поделись ссылкой.</p>
          <Link to="/create" className="btn px-6 py-3 text-lg">Создать анкету</Link>
        </section>
        <section className="grid md:grid-cols-3 gap-6 py-10">
          <div className="card p-6">
            <h3 className="text-xl font-semibold mb-2">Просто</h3>
            <p className="opacity-80">Зашёл → Создал → Ответил → Поделился</p>
          </div>
          <div className="card p-6">
            <h3 className="text-xl font-semibold mb-2">Гибко</h3>
            <p className="opacity-80">Внешние вопросы и кастомный дизайн</p>
          </div>
          <div className="card p-6">
            <h3 className="text-xl font-semibold mb-2">Круто в превью</h3>
            <p className="opacity-80">Open Graph для красивого шаринга</p>
          </div>
        </section>
        <section className="py-10 text-center">
          <p className="opacity-70">Пример: <a href="/u/leo">/u/leo</a></p>
        </section>
      </main>
      <footer className="max-w-5xl mx-auto px-4 py-10 text-center opacity-60">
        Quest • Создай свою анкету
      </footer>
    </div>
  )
}
