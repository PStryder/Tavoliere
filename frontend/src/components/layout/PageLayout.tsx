import type { ReactNode } from "react";
import { Header } from "./Header";

export function PageLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col bg-gray-900">
      <Header />
      <main className="flex-1">{children}</main>
    </div>
  );
}
