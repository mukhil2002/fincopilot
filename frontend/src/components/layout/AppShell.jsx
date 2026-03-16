// AppShell.jsx
// The permanent outer frame of the entire application.
// Sidebar is always visible. Main content scrolls independently.
// Every page after login renders inside this shell.

export default function AppShell({ children }) {
    return (
      // Full screen height. Flex row = sidebar beside main content.
      // overflow-hidden on the outer div stops double scrollbars.
      <div
        className="flex h-screen overflow-hidden"
        style={{ background: '#f4f6fb' }}
      >
        {/* 
          children gets split into two slots by convention:
          We pass Sidebar and main content separately from Dashboard.jsx.
          AppShell itself is dumb — it just provides the layout frame.
          It doesn't know what Sidebar contains or what pages render.
        */}
        {children}
      </div>
    )
  }