"use client";

import { ChevronDown, LogOut, Settings } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { usePathname } from "next/navigation";

import { useAuthContext } from "@/app/providers";
import { AUTH_ENABLED } from "@/lib/auth";
import { cn, getInitials } from "@/lib/utils";

const SHOW_TRACES = process.env.NEXT_PUBLIC_SHOW_TRACES === "true";

const NAV = [
  { href: "/", label: "Asystent" },
  { href: "/documents", label: "Dokumenty" },
  { href: "/historia", label: "Historia" },
  ...(SHOW_TRACES ? [{ href: "/slady", label: "Ślady" }] : []),
];

type User = { name: string; email: string; picture: string };

function UserDropdown({ user, logout }: { user: User; logout: () => void }) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: PointerEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  const initials = getInitials(user.name);

  return (
    <div ref={containerRef} className="relative flex justify-end">
      {/* Trigger */}
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Menu użytkownika: ${user.name}`}
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm transition-colors duration-150 hover:bg-white/8"
      >
        {/* Avatar */}
        <span
          aria-hidden="true"
          className="flex size-8 shrink-0 items-center justify-center rounded-full bg-sky-500/20 text-xs font-bold text-sky-400 ring-1 ring-sky-500/30"
        >
          {initials}
        </span>

        {/* Name */}
        <span className="max-w-[120px] truncate font-medium text-gray-200">
          {user.name}
        </span>

        {/* Chevron */}
        <ChevronDown
          className={cn(
            "size-3.5 shrink-0 text-gray-400 transition-transform duration-200",
            open && "rotate-180",
          )}
        />
      </button>

      {/* Dropdown panel */}
      {open && (
        <div
          role="menu"
          aria-label="Menu użytkownika"
          className="absolute right-0 top-[calc(100%+6px)] z-50 w-52 overflow-hidden rounded-xl border border-white/10 bg-[#161b27] shadow-2xl"
        >
          {/* User info header */}
          <div className="border-b border-white/8 px-3.5 py-3">
            <p className="truncate text-sm font-semibold text-gray-100">{user.name}</p>
            <p className="mt-0.5 truncate text-xs text-gray-500">{user.email}</p>
          </div>

          {/* Menu items */}
          <div className="py-1">
            <button
              role="menuitem"
              type="button"
              onClick={() => { setOpen(false); router.push("/settings"); }}
              className="flex w-full items-center gap-3 px-3.5 py-2.5 text-sm text-gray-300 transition-colors duration-100 hover:bg-white/6 hover:text-gray-100"
            >
              <Settings className="size-4 shrink-0 text-gray-400" />
              Ustawienia
            </button>

            <div className="mx-3 my-1 border-t border-white/8" />

            <button
              role="menuitem"
              type="button"
              onClick={() => { setOpen(false); logout(); }}
              className="flex w-full items-center gap-3 px-3.5 py-2.5 text-sm text-gray-300 transition-colors duration-100 hover:bg-red-500/10 hover:text-red-400"
            >
              <LogOut className="size-4 shrink-0" />
              Wyloguj
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export function Header() {
  const pathname = usePathname();
  const { user, logout } = useAuthContext();

  return (
    <header className="border-b border-border/60 bg-card/80 backdrop-blur-sm">
      {/* 3-col grid: logo | nav (centered) | user menu */}
      <div className="mx-auto grid w-full max-w-5xl grid-cols-[1fr_auto_1fr] items-center px-4 py-3">

        {/* Col 1 — Logo */}
        <Link
          href="/"
          className="justify-self-start transition-opacity hover:opacity-80"
        >
          <Image
            src="/logo_azure.png"
            alt="Azure RAG Assistant"
            width={320}
            height={218}
            className="h-20 w-auto object-contain"
            priority
          />
        </Link>

        {/* Col 2 — Nav (auto-width, naturally centered by grid) */}
        <nav aria-label="Główna nawigacja" className="flex items-center gap-1 text-sm">
          {NAV.map(({ href, label }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "rounded-full px-4 py-2 transition-colors duration-200",
                  active
                    ? "bg-white/10 font-semibold text-sky-400"
                    : "font-medium text-gray-400 hover:text-gray-200",
                )}
              >
                {label}
              </Link>
            );
          })}
        </nav>

        {/* Col 3 — User dropdown (right-aligned) */}
        {AUTH_ENABLED && user ? (
          <UserDropdown user={user} logout={logout} />
        ) : (
          <div aria-hidden="true" />
        )}
      </div>
    </header>
  );
}
