"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "./theme-toggle";
import styles from "./top-bar.module.css";

const TABS = [
  { href: "/map", label: "지도 탐색" },
  { href: "/analysis", label: "AI 분석" },
];

export function TopBar() {
  const pathname = usePathname();

  return (
    <header className={styles.header}>
      {/* BI 로고 = 홈 버튼. 다크 테마에서는 밝은 워드마크 변형을 쓴다. */}
      <Link
        href="/"
        aria-label="홈"
        aria-current={pathname === "/" ? "page" : undefined}
        className={styles.logo}
      >
        <Image src="/brand/logo-light.png" alt="" width={158} height={32} priority unoptimized className="h-7 w-auto md:h-8 [[data-theme=dark]_&]:hidden" />
        <Image src="/brand/logo-dark.png" alt="" width={158} height={32} priority unoptimized className="hidden h-7 w-auto md:h-8 [[data-theme=dark]_&]:block" />
      </Link>
      <nav aria-label="주요 메뉴" className={styles.nav}>
        {TABS.map((tab) => {
          const active = pathname === tab.href;
          return (
            <Link
              key={tab.href}
              href={tab.href}
              aria-current={active ? "page" : undefined}
              className={`${styles.navLink} ${active ? styles.active : ""}`}
            >
              {tab.label}
            </Link>
          );
        })}
      </nav>
      <div className={styles.themeSlot}>
        <ThemeToggle />
      </div>
    </header>
  );
}
