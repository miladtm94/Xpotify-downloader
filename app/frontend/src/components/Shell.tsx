import type { ReactNode } from "react";

const NAV_ITEMS = [
  { id: "download", label: "Dashboard" },
  { id: "queue", label: "Queue" },
  { id: "library", label: "Library" },
  { id: "about", label: "About" },
] as const;

export type PageId = (typeof NAV_ITEMS)[number]["id"];

type ShellProps = {
  currentPage: PageId;
  onNavigate: (page: PageId) => void;
  children: ReactNode;
};

export function Shell({ currentPage, onNavigate, children }: ShellProps) {
  return (
    <div className="mx-auto flex min-h-screen max-w-7xl flex-col px-4 py-6 sm:px-6 lg:px-8">
      <header className="mb-6 flex flex-col gap-4 rounded-[1.25rem] border border-ink/10 bg-ink px-5 py-5 text-paper shadow-panel md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs uppercase text-brass">LynkOo</p>
          <h1 className="display-font mt-1 text-3xl font-semibold md:text-4xl">
            Local Media Manager
          </h1>
        </div>
        <nav className="flex flex-wrap gap-2">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              className={`rounded-full px-4 py-2 text-sm transition ${
                currentPage === item.id
                  ? "bg-paper text-ink"
                  : "bg-paper/10 text-paper hover:bg-paper/20"
              }`}
              onClick={() => onNavigate(item.id)}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </nav>
      </header>
      <main className="flex-1">{children}</main>
    </div>
  );
}
