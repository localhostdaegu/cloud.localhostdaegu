"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "./theme-toggle";

const TABS = [
  { href: "/map", label: "지도 탐색" },
  { href: "/analysis", label: "AI 분석" },
];

export function TopBar() {
  const pathname = usePathname();

  return (
    <header className="flex shrink-0 items-center justify-between border-b border-[var(--border)] bg-[var(--bg-surface)] px-5">
      <div className="flex items-center gap-7">
        {/* BI 로고 = 홈 버튼. 원본 가로형(약 5:1)을 상단 바(≈48px)에 맞춰 높이 32px, 3배 해상도 PNG.
            다크 테마는 진청록 워드마크가 배경에 묻혀 밝게 바꾼 변형을 쓴다 */}
        <Link
          href="/"
          aria-label="홈"
          aria-current={pathname === "/" ? "page" : undefined}
          className="flex shrink-0 items-center rounded-sm focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[var(--accent)]"
        >
          <Image src="/brand/logo-light.png" alt="" width={158} height={32} priority unoptimized className="h-8 w-auto [[data-theme=dark]_&]:hidden" />
          <Image src="/brand/logo-dark.png" alt="" width={158} height={32} priority unoptimized className="hidden h-8 w-auto [[data-theme=dark]_&]:block" />
        </Link>
        <nav className="flex items-center gap-1">
          {TABS.map((tab) => {
            const active = pathname === tab.href;
            return (
              <Link
                key={tab.href}
                href={tab.href}
                aria-current={active ? "page" : undefined}
                className={`border-b-2 px-2 py-3.5 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[var(--accent)] ${
                  active
                    ? "border-[var(--accent)] text-[var(--accent)]"
                    : "border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
                }`}
              >
                {tab.label}
              </Link>
            );
          })}
        </nav>
      </div>
      <ThemeToggle />
    </header>
  );
}
