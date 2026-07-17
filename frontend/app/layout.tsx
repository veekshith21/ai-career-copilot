import type { Metadata } from 'next'
import './globals.css'
import { Providers } from './providers'
import { Toaster } from 'sonner'

export const metadata: Metadata = {
  title: 'AI Career Copilot',
  description: 'Multi-agent AI platform for job search, ATS optimization, and interview prep',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#0f0f13] text-[#f0f0f8] min-h-screen">
        <Providers>
          {children}
          <Toaster
            theme="dark"
            position="top-right"
            toastOptions={{
              style: {
                background: '#1e1e28',
                border: '1px solid #2a2a38',
                color: '#f0f0f8',
              },
            }}
          />
        </Providers>
      </body>
    </html>
  )
}
