"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { getStoredSessionId } from "@/lib/client";
import { useEffect, useState } from "react";

export function Header() {
  const path = usePathname();
  const [sessionId, setSessionId] = useState<string | null>(null);
  useEffect(() => {
    setSessionId(getStoredSessionId());
  }, [path]);

  return (
    <header className="border-b border-line/80">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4">
        <Link href="/" className="flex items-baseline gap-2">
          <span className="display text-xl tracking-tight text-chalk">
            SwingFrames
          </span>
          <span className="hidden text-xs uppercase tracking-[0.18em] text-mute sm:inline">
            review
          </span>
        </Link>
        <nav className="flex items-center gap-5 text-sm text-mute">
          <Link href="/" className={path === "/" ? "text-lime" : "hover:text-chalk"}>
            Upload
          </Link>
          {sessionId && (
            <Link
              href={`/sessions/${sessionId}`}
              className={path.startsWith("/sessions") ? "text-lime" : "hover:text-chalk"}
            >
              Session
            </Link>
          )}
          <Link
            href="/compare"
            className={path.startsWith("/compare") ? "text-lime" : "hover:text-chalk"}
          >
            Compare
          </Link>
        </nav>
      </div>
    </header>
  );
}
