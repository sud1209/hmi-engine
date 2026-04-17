import { ThemeToggle } from '@/components/layout/ThemeToggle'

export default function Page() {
  return (
    <main style={{ padding: '2rem' }}>
      <ThemeToggle />
      <h1 style={{ color: 'var(--text)', marginTop: '1rem' }}>HMI Engine</h1>
    </main>
  )
}
