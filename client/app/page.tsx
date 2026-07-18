"use client";

import React, { useState, useEffect, useRef, useMemo } from "react";
import Link from "next/link";
import { AgentProvider } from "../components/agent/AgentProvider";
import AgentButton from "../components/agent/AgentButton";
import AgentWidget from "../components/agent/AgentWidget";
import { useAgent } from "../hooks/useAgent";
import { useProducts } from "../hooks/useProducts";
import { useCart } from "../hooks/useCart";
import { formatPrice } from "../lib/api";

const CITY_TABS = ["All Items", "Karachi Picks", "Lahore Specials", "Islamabad Favorites"];

// ─── Inner Content (needs useAgent) ──────────────────────────────────────────
function HomeContent() {
  const { toggleWidget } = useAgent();
  const { addItem } = useCart();
  const { products, categories, loading } = useProducts();
  const [activeCity, setActiveCity] = useState(0);
  const [scrolled, setScrolled] = useState(false);
  const heroImgRef = useRef<HTMLImageElement>(null);

  const trending = useMemo(() => {
    const featured = products.filter((p) => p.isFeatured);
    const list = featured.length ? featured : products;
    return list.slice(0, 4);
  }, [products]);

  const categoryTiles = useMemo(() => {
    const bySlug = (slug: string) => categories.find((c) => c.slug === slug);
    return [
      bySlug("electronics") || categories[0],
      bySlug("fashion") || categories[1],
      bySlug("home-living") || categories[2],
      bySlug("shoes") || categories[3],
    ].filter(Boolean);
  }, [categories]);

  // Parallax + header glass on scroll
  useEffect(() => {
    const onScroll = () => {
      const y = window.scrollY;
      setScrolled(y > 50);
      if (heroImgRef.current) {
        heroImgRef.current.style.transform = `translateY(${y * 0.15}px)`;
      }
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div
      className="min-h-screen flex flex-col"
      style={{ background: "var(--color-background)", color: "var(--color-on-surface)" }}
    >
      {/* ── TopNavBar ──────────────────────────────────────────────────── */}
      <header
        className={`sticky top-0 z-50 border-b transition-all duration-300 ${
          scrolled ? "shadow-md py-0" : "shadow-sm py-0"
        }`}
        style={{
          background: scrolled
            ? "rgba(248,249,250,0.85)"
            : "var(--color-surface)",
          backdropFilter: scrolled ? "blur(8px)" : "none",
          borderColor: "var(--color-surface-variant)",
        }}
      >
        <div className="flex justify-between items-center h-20 px-4 md:px-10 max-w-[1280px] mx-auto">
          {/* Brand + Nav */}
          <div className="flex items-center gap-6 md:gap-10">
            <span
              className="text-2xl font-bold"
              style={{ color: "var(--color-primary)", fontFamily: "var(--font-headline-md)" }}
            >
              ShopEase
            </span>
            <nav className="hidden md:flex gap-6 items-center">
              {["Categories", "New Arrivals", "Deals"].map((l, i) => (
                <a
                  key={l}
                  href="#"
                  className={`text-base transition-colors duration-200 hover:text-[var(--color-secondary)] ${
                    i === 1 ? "font-bold border-b-2 pb-0.5" : ""
                  }`}
                  style={{
                    color: i === 1 ? "var(--color-secondary)" : "var(--color-on-surface-variant)",
                    borderColor: i === 1 ? "var(--color-secondary)" : "transparent",
                    fontFamily: "var(--font-body-md)",
                  }}
                >
                  {l}
                </a>
              ))}
            </nav>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-4 md:gap-6">
            {/* Desktop search */}
            <div
              className="hidden lg:flex items-center px-4 py-2 rounded-full border gap-2"
              style={{ background: "var(--color-surface-container)", borderColor: "var(--color-outline-variant)" }}
            >
              <span className="material-symbols-outlined" style={{ color: "var(--color-outline)", fontSize: 20 }}>
                search
              </span>
              <input
                className="bg-transparent border-none outline-none text-sm w-56"
                style={{ fontFamily: "var(--font-body-sm)" }}
                placeholder="Search products..."
                type="text"
              />
            </div>
            <div className="flex items-center gap-2">
              {["shopping_cart", "account_circle"].map((icon) => (
                <button
                  key={icon}
                  className="p-2 transition-all active:scale-95 hover:text-[var(--color-secondary)] cursor-pointer"
                  style={{ color: "var(--color-on-surface-variant)" }}
                >
                  <span className="material-symbols-outlined" style={{ fontSize: 24 }}>{icon}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </header>

      {/* ── Hero Section ───────────────────────────────────────────────── */}
      <section className="relative h-[600px] md:h-[800px] overflow-hidden flex items-center">
        {/* Background image with parallax */}
        <div className="absolute inset-0 z-0">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            ref={heroImgRef}
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuBxLKn8RrJbzWyZ1jY5VqC2_iJlJXJAqWJGHFdRdXNwLw9a1bqoYG9Y7m9lvqc0ReKnsdXdEndF7rFJVY0Fti_cx0J1f2Cocgs6kIc-6BsoACUI01oIbfKxk3Ob0wX-tnyjURffY93uHTzZ6vETBAIYREYyGhuGV_xE2aW_MyFRLaZMi1Uwi_Zy7jUcAs3T2KMb4M2WRWEBddkO2FCzUMSJgvDi7Xzv4Zb4ljlyZQ4t9JXyvjrjpQLcg1Ht2CHA04IOLz0qrXnACj0"
            alt="ShopEase hero — premium electronics and fashion on white surface"
            className="w-full h-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-r from-[var(--color-background)] via-[rgba(248,249,250,0.4)] to-transparent" />
        </div>

        {/* Hero copy */}
        <div className="relative z-10 max-w-[1280px] mx-auto px-4 md:px-10 w-full">
          <div className="max-w-2xl">
            <span
              className="uppercase tracking-widest text-xs mb-4 block font-medium"
              style={{ color: "var(--color-secondary)", fontFamily: "var(--font-label-mono)" }}
            >
              New Season 2024
            </span>
            <h1
              className="font-bold leading-[1.1] mb-6 text-[32px] md:text-[48px]"
              style={{
                color: "var(--color-primary)",
                fontFamily: "var(--font-display-lg)",
                letterSpacing: "-0.02em",
              }}
            >
              Elevate Your Lifestyle with ShopEase
            </h1>
            <p
              className="text-lg mb-8 max-w-lg leading-relaxed"
              style={{ color: "var(--color-on-surface-variant)", fontFamily: "var(--font-body-lg)" }}
            >
              Discover the finest curated selection of electronics, global fashion, and authentic Pakistani
              craftsmanship delivered to your doorstep.
            </p>
            <div className="flex flex-wrap gap-4">
              <Link
                href="/products"
                className="px-10 py-4 rounded-lg font-bold text-base hover:opacity-90 transition-all active:scale-95 cursor-pointer inline-block"
                style={{
                  background: "var(--color-primary)",
                  color: "var(--color-on-primary)",
                  fontFamily: "var(--font-body-md)",
                }}
              >
                Shop New Arrivals
              </Link>
              <a
                href="#categories"
                className="px-10 py-4 rounded-lg font-bold text-base border hover:bg-[var(--color-surface-container)] transition-all active:scale-95 cursor-pointer inline-block"
                style={{
                  borderColor: "var(--color-primary)",
                  color: "var(--color-primary)",
                  fontFamily: "var(--font-body-md)",
                }}
              >
                Explore Categories
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* ── Categories Bento Grid ───────────────────────────────────────── */}
      <section id="categories" className="py-16 max-w-[1280px] mx-auto px-4 md:px-10 w-full">
        <div className="flex justify-between items-end mb-16">
          <div>
            <h2
              className="text-2xl font-semibold mb-2"
              style={{ color: "var(--color-primary)", fontFamily: "var(--font-headline-md)" }}
            >
              Shop by Category
            </h2>
            <p style={{ color: "var(--color-on-surface-variant)", fontFamily: "var(--font-body-md)" }}>
              Explore our diverse collections across all departments.
            </p>
          </div>
          <Link
            href="/products"
            className="font-bold hover:underline text-sm"
            style={{ color: "var(--color-secondary)", fontFamily: "var(--font-body-sm)" }}
          >
            View All Categories
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 md:grid-rows-2 gap-6 md:h-[600px]">
          {categoryTiles.map((cat, idx) => {
            if (!cat) return null;
            const span =
              idx === 0
                ? "md:col-span-2 md:row-span-2 min-h-[280px]"
                : idx === 1
                  ? "md:col-span-2 min-h-[200px]"
                  : "min-h-[180px]";
            return (
              <Link
                key={cat.id}
                href={`/products`}
                className={`group relative overflow-hidden rounded-xl cursor-pointer ${span}`}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={
                    cat.image_url ||
                    "https://images.unsplash.com/photo-1441986300917-64674bd600d8?auto=format&fit=crop&w=1000&q=80"
                  }
                  alt={cat.name}
                  className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-[rgba(0,0,11,0.8)] via-transparent to-transparent" />
                <div className={`absolute text-white ${idx < 2 ? "bottom-6 left-6" : "bottom-4 left-4"}`}>
                  <h3
                    className={idx < 2 ? "text-2xl font-semibold" : "text-xl font-bold"}
                    style={{ fontFamily: "var(--font-headline-md)" }}
                  >
                    {cat.name}
                  </h3>
                  <p className="text-sm opacity-80" style={{ fontFamily: "var(--font-body-sm)" }}>
                    {cat.product_count} products
                  </p>
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      {/* ── Trending in Pakistan ────────────────────────────────────────── */}
      <section className="py-16" style={{ background: "var(--color-surface-container)" }}>
        <div className="max-w-[1280px] mx-auto px-4 md:px-10">
          {/* Header */}
          <div className="flex flex-col md:flex-row md:items-center justify-between mb-16 gap-6">
            <div>
              <h2
                className="text-2xl font-semibold mb-2"
                style={{ color: "var(--color-primary)", fontFamily: "var(--font-headline-md)" }}
              >
                Trending in Pakistan
              </h2>
              <p style={{ color: "var(--color-on-surface-variant)", fontFamily: "var(--font-body-md)" }}>
                Top rated items frequently ordered across the country.
              </p>
            </div>
            {/* City tabs */}
            <div className="flex gap-2 overflow-x-auto pb-1 hide-scrollbar">
              {CITY_TABS.map((tab, i) => (
                <button
                  key={tab}
                  onClick={() => setActiveCity(i)}
                  className="px-5 py-2 rounded-full text-sm whitespace-nowrap font-medium cursor-pointer transition-colors border"
                  style={{
                    fontFamily: "var(--font-body-sm)",
                    background: activeCity === i ? "var(--color-primary)" : "var(--color-surface)",
                    color: activeCity === i ? "var(--color-on-primary)" : "var(--color-on-surface-variant)",
                    borderColor:
                      activeCity === i ? "transparent" : "var(--color-outline-variant)",
                  }}
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>

          {/* Product cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {loading &&
              Array.from({ length: 4 }).map((_, i) => (
                <div
                  key={i}
                  className="rounded-xl h-96 animate-pulse"
                  style={{ background: "var(--color-surface)" }}
                />
              ))}
            {!loading &&
              trending.map((p) => (
              <Link
                key={p.id}
                href={`/products/${p.id}`}
                className="rounded-xl overflow-hidden shadow-sm hover:shadow-lg transition-shadow duration-300 group cursor-pointer block"
                style={{ background: "var(--color-surface)" }}
              >
                <div
                  className="relative h-72 overflow-hidden"
                  style={{ background: "var(--color-surface-variant)" }}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={p.image}
                    alt={p.name}
                    loading="eager"
                    decoding="async"
                    fetchPriority="high"
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                  />
                  {p.isFeatured && (
                    <div
                      className="absolute top-4 left-4 text-xs font-bold px-3 py-1 rounded-full uppercase"
                      style={{ background: "var(--color-secondary)", color: "var(--color-on-secondary)" }}
                    >
                      Trending
                    </div>
                  )}
                </div>

                <div className="p-6">
                  <p
                    className="text-[10px] mb-1 uppercase tracking-widest"
                    style={{
                      color: "var(--color-on-surface-variant)",
                      fontFamily: "var(--font-label-mono)",
                    }}
                  >
                    {p.category}
                  </p>
                  <h4
                    className="font-bold mb-2 truncate"
                    style={{ color: "var(--color-primary)", fontFamily: "var(--font-body-md)" }}
                  >
                    {p.name}
                  </h4>
                  <div className="flex items-center gap-1 mb-4">
                    <span
                      className="material-symbols-outlined text-sm"
                      style={{ fontSize: 18, fontVariationSettings: "'FILL' 1", color: "#FFB800" }}
                    >
                      star
                    </span>
                    <span className="text-sm font-bold" style={{ fontFamily: "var(--font-body-sm)" }}>
                      {p.rating.toFixed(1)}
                    </span>
                    <span className="text-sm" style={{ color: "var(--color-on-surface-variant)", fontFamily: "var(--font-body-sm)" }}>
                      ({p.reviewsCount} reviews)
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span
                      className="text-2xl font-bold"
                      style={{ color: "var(--color-primary)", fontFamily: "var(--font-headline-md)" }}
                    >
                      {formatPrice(p.price)}
                    </span>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.preventDefault();
                        addItem(p);
                      }}
                      className="p-2 rounded-lg transition-colors hover:bg-[var(--color-secondary)] hover:text-[var(--color-on-secondary)] cursor-pointer"
                      style={{ background: "var(--color-primary)", color: "var(--color-on-primary)" }}
                    >
                      <span className="material-symbols-outlined" style={{ fontSize: 22 }}>add_shopping_cart</span>
                    </button>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ── Newsletter + Brand Promise ──────────────────────────────────── */}
      <section className="py-16">
        <div className="max-w-[1280px] mx-auto px-4 md:px-10 grid md:grid-cols-2 gap-16 items-center">
          {/* Newsletter Card */}
          <div
            className="rounded-3xl p-16 text-white relative overflow-hidden"
            style={{ background: "var(--color-primary-container)" }}
          >
            <div className="relative z-10">
              <h2
                className="font-bold mb-6 text-2xl md:text-[48px] leading-[1.1]"
                style={{ fontFamily: "var(--font-display-lg)", color: "var(--color-on-primary)" }}
              >
                Join the ShopEase Circle
              </h2>
              <p
                className="mb-8 text-lg leading-relaxed"
                style={{ color: "var(--color-on-primary-container)", fontFamily: "var(--font-body-lg)" }}
              >
                Get exclusive access to flash sales, curated launches, and cultural storytelling from across Pakistan.
              </p>
              <form className="flex flex-col sm:flex-row gap-4">
                <input
                  type="email"
                  placeholder="Email Address"
                  className="bg-white/10 border border-white/20 rounded-lg px-6 py-4 flex-grow outline-none text-white placeholder-white/50 focus:ring-2 focus:ring-[var(--color-secondary)]"
                  style={{ fontFamily: "var(--font-body-md)" }}
                />
                <button
                  type="submit"
                  className="px-10 py-4 rounded-lg font-bold text-white shadow-lg active:scale-95 transition-all cursor-pointer"
                  style={{
                    background: "linear-gradient(135deg, #4d41df 0%, #6C63FF 100%)",
                    fontFamily: "var(--font-body-md)",
                  }}
                >
                  Subscribe
                </button>
              </form>
            </div>
            {/* Decorative blob */}
            <div
              className="absolute -right-20 -bottom-20 w-64 h-64 rounded-full blur-3xl"
              style={{ background: "rgba(77,65,223,0.2)" }}
            />
          </div>

          {/* Trust badges */}
          <div className="grid grid-cols-2 gap-6">
            {[
              { icon: "local_shipping", title: "Fast Delivery", desc: "Nationwide shipping within 48-72 hours." },
              { icon: "verified_user", title: "Secure Payments", desc: "100% encrypted checkout process." },
              { icon: "stars", title: "Quality First", desc: "Handpicked premium vendors only." },
              { icon: "support_agent", title: "24/7 Support", desc: "AI & Human assistance whenever needed." },
            ].map(({ icon, title, desc }) => (
              <div
                key={title}
                className="p-6 rounded-xl border flex flex-col items-center text-center"
                style={{
                  background: "var(--color-surface)",
                  borderColor: "var(--color-outline-variant)",
                }}
              >
                <span
                  className="material-symbols-outlined mb-4"
                  style={{ fontSize: 36, color: "var(--color-secondary)" }}
                >
                  {icon}
                </span>
                <h4
                  className="font-bold mb-2"
                  style={{ color: "var(--color-primary)", fontFamily: "var(--font-body-md)" }}
                >
                  {title}
                </h4>
                <p
                  className="text-sm"
                  style={{ color: "var(--color-on-surface-variant)", fontFamily: "var(--font-body-sm)" }}
                >
                  {desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Footer ─────────────────────────────────────────────────────── */}
      <footer style={{ background: "var(--color-primary)", color: "var(--color-on-primary)" }}>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 py-16 px-4 md:px-10 max-w-[1280px] mx-auto">
          {/* Brand */}
          <div>
            <span className="text-2xl font-bold block mb-4" style={{ fontFamily: "var(--font-headline-md)" }}>
              ShopEase
            </span>
            <p
              className="text-sm opacity-80 max-w-xs mb-6 leading-relaxed"
              style={{ color: "var(--color-on-primary-container)", fontFamily: "var(--font-body-sm)" }}
            >
              Pakistan&apos;s most trusted premium e-commerce platform. Bridging the gap between luxury and local heritage.
            </p>
            <div className="flex gap-4">
              {["public", "alternate_email"].map((icon) => (
                <a key={icon} href="#" className="opacity-80 hover:opacity-100 transition-opacity">
                  <span className="material-symbols-outlined" style={{ fontSize: 24 }}>{icon}</span>
                </a>
              ))}
            </div>
          </div>

          {/* Quick Links */}
          <div>
            <h5 className="font-bold mb-6">Quick Links</h5>
            <ul className="flex flex-col gap-4">
              {["About Us", "Contact Support", "Privacy Policy", "Terms of Service"].map((l) => (
                <li key={l}>
                  <a
                    href="#"
                    className="text-sm opacity-80 hover:opacity-100 transition-opacity"
                    style={{ color: "var(--color-on-primary-container)", fontFamily: "var(--font-body-sm)" }}
                  >
                    {l}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Customer Care */}
          <div>
            <h5 className="font-bold mb-6">Customer Care</h5>
            <ul className="flex flex-col gap-4">
              {["Returns & Refunds", "Track Order", "Shipping FAQ", "Gift Cards"].map((l) => (
                <li key={l}>
                  <a
                    href="#"
                    className="text-sm opacity-80 hover:opacity-100 transition-opacity"
                    style={{ color: "var(--color-on-primary-container)", fontFamily: "var(--font-body-sm)" }}
                  >
                    {l}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Our Presence */}
          <div>
            <h5 className="font-bold mb-6">Our Presence</h5>
            <p
              className="text-sm opacity-80 mb-4"
              style={{ color: "var(--color-on-primary-container)", fontFamily: "var(--font-body-sm)" }}
            >
              Main Boulevard, Gulberg III, Lahore, Pakistan.
            </p>
            <p
              className="text-sm opacity-80"
              style={{ color: "var(--color-on-primary-container)", fontFamily: "var(--font-body-sm)" }}
            >
              support@shopease.pk
              <br />
              +92 42 111 000 222
            </p>
          </div>
        </div>

        <div
          className="border-t py-8 px-4 md:px-10 max-w-[1280px] mx-auto text-center"
          style={{ borderColor: "rgba(255,255,255,0.1)" }}
        >
          <p
            className="text-sm opacity-60"
            style={{ fontFamily: "var(--font-label-mono)" }}
          >
            © 2024 ShopEase Pakistan. All rights reserved.
          </p>
        </div>
      </footer>

      {/* ── Floating Right Widget ───────────────────────────────────────── */}
      <div className="fixed right-6 bottom-6 flex flex-col gap-4 z-50">
        {/* Tab Stack — desktop only */}
        <div
          className="hidden md:flex flex-col gap-3 p-3 rounded-2xl shadow-lg border"
          style={{
            background: "rgba(243,244,245,0.92)",
            backdropFilter: "blur(8px)",
            borderColor: "var(--color-outline-variant)",
          }}
        >
          {[
            { icon: "home", label: "Home", active: true, href: "/" },
            { icon: "shopping_bag", label: "Shop", active: false, href: "/products" },
            { icon: "shopping_cart", label: "Cart", active: false, href: "/cart" },
            { icon: "receipt_long", label: "Orders", active: false, href: "/orders" },
          ].map(({ icon, label, active, href }) => (
            <Link
              key={label}
              href={href}
              className={`flex flex-col items-center justify-center p-3 rounded-xl transition-all cursor-pointer ${
                active ? "scale-105" : "hover:bg-[var(--color-surface-variant)]"
              }`}
              style={
                active
                  ? {
                      background: "var(--color-secondary)",
                      color: "var(--color-on-secondary)",
                      boxShadow: "0 2px 8px rgba(77,65,223,0.25)",
                    }
                  : { color: "var(--color-on-surface-variant)" }
              }
            >
              <span className="material-symbols-outlined" style={{ fontSize: 24 }}>{icon}</span>
            </Link>
          ))}
        </div>

        {/* AI FAB */}
        <AgentButton embedded />
      </div>

      {/* AI Greeting Bubble — auto-shows 3s after load */}
      <AiGreeting onOpen={toggleWidget} />

      {/* Agent Chat Widget */}
      <AgentWidget />
    </div>
  );
}

// ─── Timed greeting bubble ────────────────────────────────────────────────────
function AiGreeting({ onOpen }: { onOpen: () => void }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const show = setTimeout(() => setVisible(true), 3000);
    const hide = setTimeout(() => setVisible(false), 8000);
    return () => { clearTimeout(show); clearTimeout(hide); };
  }, []);

  if (!visible) return null;

  return (
    <div
      className="fixed right-28 bottom-8 z-50 rounded-2xl p-4 max-w-[220px] border animate-bounce shadow-lg"
      style={{
        background: "var(--color-surface-container-highest)",
        borderColor: "var(--color-outline-variant)",
      }}
    >
      <p
        className="text-[10px] mb-1 uppercase tracking-widest"
        style={{ color: "var(--color-secondary)", fontFamily: "var(--font-label-mono)" }}
      >
        AI ASSISTANT
      </p>
      <p
        className="text-sm"
        style={{ color: "var(--color-on-surface)", fontFamily: "var(--font-body-sm)" }}
      >
        As-salamu alaykum! How can I help you shop today?
      </p>
      <button
        onClick={() => { setVisible(false); onOpen(); }}
        className="mt-2 text-xs font-bold hover:underline cursor-pointer"
        style={{ color: "var(--color-secondary)", fontFamily: "var(--font-label-mono)" }}
      >
        Chat now →
      </button>
    </div>
  );
}

// ─── Page export ──────────────────────────────────────────────────────────────
export default function HomePage() {
  return (
    <AgentProvider>
      <HomeContent />
    </AgentProvider>
  );
}
