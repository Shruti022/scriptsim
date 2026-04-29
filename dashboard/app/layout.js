import './globals.css'

export const metadata = {
  title: 'ScriptSim Dashboard',
  description: 'AI QA Testing Results',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
