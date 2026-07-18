"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";
import { AgentProvider } from "../../components/agent/AgentProvider";
import AgentButton from "../../components/agent/AgentButton";
import AgentWidget from "../../components/agent/AgentWidget";
import { useProducts } from "../../hooks/useProducts";
import { useCart } from "../../hooks/useCart";
import { Product } from "../../types/chat";
import { formatPrice } from "../../lib/api";

function StarRow({ rating }: { rating: number }) {
  return (
    <div className="flex" style={{ color: "var(--color-secondary-container)" }}>
      {[1, 2, 3, 4, 5].map((i) => {
        const filled = i <= Math.floor(rating);
        const half = !filled && i === Math.ceil(rating) && rating % 1 !== 0;
        return (
          <span
            key={i}
            className="material-symbols-outlined"
            style={{
              fontSize: 14,
              fontVariationSettings: `'FILL' ${filled || half ? 1 : 0}`,
            }}
          >
            {half ? "star_half" : "star"}
          </span>
        );
      })}
    </div>
  );
}

function Badge({
  label,
  color,
}: {
  label: string;
  color: "primary" | "error" | "tertiary";
}) {
  const base =
    "absolute top-3 left-3 px-3 py-1 rounded-full text-[10px] uppercase tracking-widest font-medium z-10";
  const styles =
    color === "primary"
      ? { background: "var(--color-primary-container)", color: "var(--color-on-primary)" }
      : color === "error"
        ? { background: "var(--color-error)", color: "var(--color-on-error)" }
        : { background: "var(--color-on-tertiary-container)", color: "var(--color-on-tertiary)" };
  return (
    <span className={base} style={styles}>
      {label}
    </span>
  );
}

function ProductCard({ product, priority = false }: { product: Product; priority?: boolean }) {
  const { addItem } = useCart();
  const [inCart, setInCart] = useState(false);

  const badge =
    (product.stockQuantity ?? 0) > 0 && (product.stockQuantity ?? 0) <= 5
      ? { label: "Low Stock", color: "error" as const }
      : product.isFeatured
        ? { label: "Featured", color: "primary" as const }
        : (product.stockQuantity ?? 0) > 0
          ? { label: "In Stock", color: "tertiary" as const }
          : undefined;

  const handleAddToCart = (e: React.MouseEvent) => {
    e.preventDefault();
    addItem(product);
    setInCart(true);
    setTimeout(() => setInCart(false), 2000);
  };

  return (
    <Link
      href={`/products/${product.id}`}
      className="bg-[var(--color-surface-container-lowest)] rounded-2xl p-4 card-shadow group border border-transparent hover:border-[var(--color-outline-variant)] transition-all duration-300 flex flex-col"
    >
      <div className="relative overflow-hidden rounded-xl bg-[var(--color-surface)] mb-4 aspect-[4/5] flex-shrink-0">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={product.image}
          alt={product.name}
          loading={priority ? "eager" : "lazy"}
          decoding="async"
          fetchPriority={priority ? "high" : "auto"}
          className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
        />
        {badge && <Badge label={badge.label} color={badge.color} />}
        <button
          onClick={handleAddToCart}
          className="absolute bottom-4 right-4 bg-[var(--color-surface-container-lowest)]/90 p-2 rounded-full shadow-lg opacity-0 translate-y-4 group-hover:opacity-100 group-hover:translate-y-0 transition-all duration-300 hover:bg-[var(--color-secondary)] hover:text-[var(--color-on-secondary)] cursor-pointer"
          aria-label="Add to cart"
        >
          <span className="material-symbols-outlined" style={{ fontSize: 22 }}>
            {inCart ? "check" : "add_shopping_cart"}
          </span>
        </button>
      </div>

      <div className="flex flex-col flex-1">
        <span
          className="uppercase tracking-tighter text-[10px] font-medium"
          style={{ color: "var(--color-secondary-container)", fontFamily: "var(--font-label-mono)" }}
        >
          {product.category}
        </span>
        <h3
          className="text-base font-bold mt-0.5 group-hover:text-[var(--color-secondary)] transition-colors leading-snug"
          style={{ color: "var(--color-on-surface)", fontFamily: "var(--font-body-md)" }}
        >
          {product.name}
        </h3>

        {product.rating > 0 && (
          <div className="flex items-center gap-2 mt-1">
            <StarRow rating={product.rating} />
            <span
              className="text-[12px] opacity-70"
              style={{
                color: "var(--color-on-surface-variant)",
                fontFamily: "var(--font-label-mono)",
              }}
            >
              ({product.reviewsCount})
            </span>
          </div>
        )}

        <p
          className="mt-4 text-2xl font-semibold"
          style={{ color: "var(--color-primary)", fontFamily: "var(--font-headline-md)" }}
        >
          {formatPrice(product.price)}
        </p>
      </div>
    </Link>
  );
}

function SidebarFilter({
  categories,
  selectedCats,
  toggleCat,
  minRating,
  setMinRating,
  onReset,
}: {
  categories: string[];
  selectedCats: string[];
  toggleCat: (c: string) => void;
  minRating: number;
  setMinRating: (r: number) => void;
  onReset: () => void;
}) {
  return (
    <div className="bg-[var(--color-surface-container-lowest)] p-6 rounded-2xl border border-[var(--color-surface-variant)] card-shadow">
      <div className="flex justify-between items-center mb-6">
        <h2
          className="text-2xl font-semibold"
          style={{ color: "var(--color-primary)", fontFamily: "var(--font-headline-md)" }}
        >
          Filters
        </h2>
        <button
          onClick={onReset}
          className="text-[12px] font-medium uppercase tracking-wider cursor-pointer hover:opacity-80 transition-opacity"
          style={{ color: "var(--color-secondary)", fontFamily: "var(--font-label-mono)" }}
        >
          Reset
        </button>
      </div>

      <div className="mb-10">
        <h3
          className="text-base font-bold mb-4"
          style={{ color: "var(--color-on-surface)", fontFamily: "var(--font-body-md)" }}
        >
          Category
        </h3>
        <div className="space-y-2">
          {categories.map((cat) => (
            <label key={cat} className="flex items-center gap-2 cursor-pointer group">
              <input
                type="checkbox"
                checked={selectedCats.includes(cat)}
                onChange={() => toggleCat(cat)}
                className="w-4 h-4 rounded border-[var(--color-outline-variant)] cursor-pointer"
              />
              <span
                className="text-sm group-hover:text-[var(--color-primary)] transition-colors"
                style={{ color: "var(--color-on-surface-variant)", fontFamily: "var(--font-body-sm)" }}
              >
                {cat}
              </span>
            </label>
          ))}
        </div>
      </div>

      <div>
        <h3
          className="text-base font-bold mb-4"
          style={{ color: "var(--color-on-surface)", fontFamily: "var(--font-body-md)" }}
        >
          Minimum Rating
        </h3>
        <div className="flex flex-col gap-2">
          {[4, 3, 2].map((r) => (
            <button
              key={r}
              onClick={() => setMinRating(minRating === r ? 0 : r)}
              className={`flex items-center gap-2 p-2 rounded-xl border transition-colors cursor-pointer ${
                minRating === r
                  ? "border-[var(--color-secondary)] bg-[var(--color-secondary-fixed)]"
                  : "border-[var(--color-surface-variant)] hover:bg-[var(--color-surface-container)]"
              }`}
            >
              <div className="flex" style={{ color: "var(--color-secondary-container)" }}>
                {[1, 2, 3, 4, 5].map((i) => (
                  <span
                    key={i}
                    className="material-symbols-outlined"
                    style={{
                      fontSize: 18,
                      fontVariationSettings: `'FILL' ${i <= r ? 1 : 0}`,
                    }}
                  >
                    star
                  </span>
                ))}
              </div>
              <span
                className="text-[12px]"
                style={{
                  color: "var(--color-on-surface-variant)",
                  fontFamily: "var(--font-label-mono)",
                }}
              >
                & Up
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function ProductsPageContent() {
  const [selectedCats, setSelectedCats] = useState<string[]>([]);
  const [minRating, setMinRating] = useState(0);
  const [sortBy, setSortBy] = useState("Featured");
  const [searchQuery, setSearchQuery] = useState("");
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);

  // One catalog fetch (cached) — all filters/search are instant client-side
  const { products, categoryNames, total, loading, refreshing, error } = useProducts();

  const filtered = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    let list = products;

    if (q) {
      list = list.filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          p.category.toLowerCase().includes(q) ||
          (p.brand || "").toLowerCase().includes(q) ||
          p.description.toLowerCase().includes(q)
      );
    }

    if (selectedCats.length > 0) {
      list = list.filter((p) => selectedCats.includes(p.category));
    }

    if (minRating > 0) {
      list = list.filter((p) => p.rating >= minRating);
    }

    const sorted = [...list];
    if (sortBy === "Price: Low to High") {
      sorted.sort((a, b) => a.price - b.price);
    } else if (sortBy === "Price: High to Low") {
      sorted.sort((a, b) => b.price - a.price);
    } else if (sortBy === "Newest First") {
      sorted.sort((a, b) => b.rating - a.rating);
    } else {
      // Featured first
      sorted.sort((a, b) => Number(b.isFeatured) - Number(a.isFeatured) || b.rating - a.rating);
    }
    return sorted;
  }, [products, searchQuery, selectedCats, minRating, sortBy]);

  const toggleCat = (c: string) =>
    setSelectedCats((prev) => (prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c]));

  const resetFilters = () => {
    setSelectedCats([]);
    setMinRating(0);
    setSearchQuery("");
  };

  return (
    <div
      className="min-h-screen flex flex-col"
      style={{ background: "var(--color-background)", color: "var(--color-foreground)" }}
    >
      <nav
        className="sticky top-0 z-40 border-b shadow-sm w-full"
        style={{ background: "var(--color-surface)", borderColor: "var(--color-surface-variant)" }}
      >
        <div className="flex justify-between items-center h-20 px-4 sm:px-6 lg:px-10 max-w-[1280px] mx-auto gap-4">
          <div className="flex items-center gap-8 shrink-0">
            <Link
              href="/"
              className="text-2xl font-bold shrink-0"
              style={{ color: "var(--color-primary)", fontFamily: "var(--font-headline-md)" }}
            >
              ShopEase
            </Link>
            <div className="hidden lg:flex gap-6">
              <Link
                href="/products"
                className="text-base hover:text-[var(--color-secondary)] transition-colors"
                style={{ color: "var(--color-on-surface-variant)", fontFamily: "var(--font-body-md)" }}
              >
                Shop
              </Link>
              <Link
                href="/orders"
                className="text-base hover:text-[var(--color-secondary)] transition-colors"
                style={{ color: "var(--color-on-surface-variant)", fontFamily: "var(--font-body-md)" }}
              >
                Orders
              </Link>
            </div>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <div className="relative hidden sm:block">
              <input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-48 md:w-64 pl-10 pr-4 py-2 border rounded-[10px] text-sm outline-none focus:ring-2 transition-all"
                style={{ borderColor: "var(--color-outline-variant)", fontFamily: "var(--font-body-sm)" }}
                placeholder="Search products..."
                type="text"
              />
              <span
                className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2"
                style={{ color: "var(--color-on-surface-variant)", fontSize: 20 }}
              >
                search
              </span>
            </div>
            <button
              onClick={() => setMobileFiltersOpen(!mobileFiltersOpen)}
              className="lg:hidden p-2 rounded-xl border cursor-pointer"
              style={{ borderColor: "var(--color-outline-variant)", color: "var(--color-on-surface-variant)" }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 22 }}>
                tune
              </span>
            </button>
            <Link href="/cart" className="p-2" style={{ color: "var(--color-on-surface-variant)" }}>
              <span className="material-symbols-outlined" style={{ fontSize: 24 }}>
                shopping_cart
              </span>
            </Link>
          </div>
        </div>
      </nav>

      {mobileFiltersOpen && (
        <div
          className="lg:hidden px-4 py-4 border-b"
          style={{ borderColor: "var(--color-surface-variant)", background: "var(--color-surface)" }}
        >
          <SidebarFilter
            categories={categoryNames}
            selectedCats={selectedCats}
            toggleCat={toggleCat}
            minRating={minRating}
            setMinRating={setMinRating}
            onReset={resetFilters}
          />
        </div>
      )}

      <main className="max-w-[1280px] mx-auto w-full px-4 sm:px-6 lg:px-10 py-10 grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1">
        <aside className="hidden lg:block lg:col-span-3">
          <div className="sticky top-24">
            <SidebarFilter
              categories={categoryNames}
              selectedCats={selectedCats}
              toggleCat={toggleCat}
              minRating={minRating}
              setMinRating={setMinRating}
              onReset={resetFilters}
            />
          </div>
        </aside>

        <section className="lg:col-span-9">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4 mb-10">
            <div>
              <h1
                className="text-4xl sm:text-5xl font-bold leading-[1.1] tracking-tight"
                style={{ color: "var(--color-primary)", fontFamily: "var(--font-display-lg)" }}
              >
                Discover Premium
              </h1>
              <p
                className="text-base sm:text-lg mt-2"
                style={{ color: "var(--color-on-surface-variant)", fontFamily: "var(--font-body-lg)" }}
              >
                {loading
                  ? "Loading catalog…"
                  : `Showing ${filtered.length} of ${total} products${refreshing ? " · updating…" : ""}`}
              </p>
            </div>
            <div className="flex gap-2 items-center shrink-0">
              <span
                className="text-[12px] uppercase"
                style={{ color: "var(--color-on-surface-variant)", fontFamily: "var(--font-label-mono)" }}
              >
                Sort By:
              </span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="bg-transparent border-none text-base font-bold cursor-pointer outline-none"
                style={{ color: "var(--color-primary)", fontFamily: "var(--font-body-md)" }}
              >
                <option>Featured</option>
                <option>Price: Low to High</option>
                <option>Price: High to Low</option>
                <option>Newest First</option>
              </select>
            </div>
          </div>

          {error && (
            <div className="mb-6 p-4 rounded-xl border text-sm" style={{ borderColor: "var(--color-error)", color: "var(--color-error)" }}>
              Could not load products: {error}. Is the API running on port 8000?
            </div>
          )}

          {loading && filtered.length === 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6">
              {Array.from({ length: 6 }).map((_, i) => (
                <div
                  key={i}
                  className="rounded-2xl h-80 animate-pulse"
                  style={{ background: "var(--color-surface-variant)" }}
                />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6">
              {filtered.map((p, idx) => (
                <ProductCard key={p.id} product={p} priority={idx < 3} />
              ))}
            </div>
          )}

          {!loading && filtered.length === 0 && !error && (
            <p className="text-center py-20" style={{ color: "var(--color-on-surface-variant)" }}>
              No products match your filters.
            </p>
          )}
        </section>
      </main>

      <footer style={{ background: "var(--color-primary-container)", color: "var(--color-on-primary)" }}>
        <div className="py-10 px-4 max-w-[1280px] mx-auto text-center text-sm opacity-70">
          © 2026 ShopEase Pakistan. Catalog powered by live database.
        </div>
      </footer>

      <div className="fixed right-6 bottom-6 flex flex-col gap-4 z-50">
        <div
          className="rounded-2xl shadow-lg border flex flex-col p-1"
          style={{
            background: "var(--color-surface-container-low)",
            borderColor: "var(--color-surface-variant)",
          }}
        >
          {[
            { icon: "home", label: "Home", active: false, href: "/" },
            { icon: "shopping_bag", label: "Shop", active: true, href: "/products" },
            { icon: "receipt_long", label: "Orders", active: false, href: "/orders" },
          ].map(({ icon, label, active, href }) => (
            <Link
              key={label}
              href={href}
              className={`flex flex-col items-center justify-center p-3 rounded-xl transition-all ${
                active ? "scale-105" : "hover:bg-[var(--color-surface-variant)]"
              }`}
              style={
                active
                  ? {
                      background: "var(--color-secondary)",
                      color: "var(--color-on-secondary)",
                    }
                  : { color: "var(--color-on-surface-variant)" }
              }
            >
              <span className="material-symbols-outlined" style={{ fontSize: 24 }}>
                {icon}
              </span>
            </Link>
          ))}
        </div>
        <AgentButton embedded />
      </div>
      <AgentWidget />
    </div>
  );
}

export default function ProductsPage() {
  return (
    <AgentProvider>
      <ProductsPageContent />
    </AgentProvider>
  );
}
