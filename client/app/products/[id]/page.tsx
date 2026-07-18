"use client";

import React, { use, useEffect, useState } from "react";
import Link from "next/link";
import { AgentProvider } from "../../../components/agent/AgentProvider";
import AgentButton from "../../../components/agent/AgentButton";
import AgentWidget from "../../../components/agent/AgentWidget";
import { useAgent } from "../../../hooks/useAgent";
import { useCart } from "../../../hooks/useCart";
import { Product } from "../../../types/chat";
import { fetchCatalog, fetchProductById, formatPrice, peekCatalog } from "../../../lib/api";

interface PageProps {
  params: Promise<{ id: string }>;
}

const TABS = ["Description", "Shipping Info"];

function ProductDetailContent({ params }: PageProps) {
  const resolvedParams = use(params);
  const { addItem } = useCart();
  const { sendMessage, toggleWidget, isOpen } = useAgent();

  const [product, setProduct] = useState<Product | null>(() => {
    const catalog = peekCatalog();
    return catalog?.find((p) => p.id === resolvedParams.id) ?? null;
  });
  const [related, setRelated] = useState<Product[]>(() => {
    const catalog = peekCatalog();
    const current = catalog?.find((p) => p.id === resolvedParams.id);
    if (!catalog || !current) return [];
    return catalog
      .filter((x) => x.category === current.category && x.id !== current.id)
      .slice(0, 4);
  });
  const [loading, setLoading] = useState(() => !peekCatalog()?.some((p) => p.id === resolvedParams.id));
  const [notFound, setNotFound] = useState(false);
  const [activeThumb, setActiveThumb] = useState(0);
  const [activeTab, setActiveTab] = useState(0);
  const [added, setAdded] = useState(false);
  const [wishlisted, setWishlisted] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const cached = peekCatalog()?.find((p) => p.id === resolvedParams.id);
      if (!cached) {
        setLoading(true);
      }
      setNotFound(false);
      try {
        // Catalog is memory-cached — usually instant after first visit
        const [p, catalog] = await Promise.all([
          fetchProductById(resolvedParams.id),
          fetchCatalog(),
        ]);
        if (cancelled) return;
        if (!p) {
          setNotFound(true);
          setLoading(false);
          return;
        }
        setProduct(p);
        setRelated(
          catalog
            .filter((x) => x.category === p.category && x.id !== p.id)
            .slice(0, 4)
        );
      } catch {
        if (!cancelled) setNotFound(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [resolvedParams.id]);

  const gallery = product?.images?.length
    ? product.images
    : product
      ? [product.image]
      : [];

  const handleAddToCart = () => {
    if (!product) return;
    addItem(product);
    setAdded(true);
    setTimeout(() => setAdded(false), 2000);
  };

  const handleAskAI = async () => {
    if (!product) return;
    if (!isOpen) toggleWidget();
    setTimeout(async () => {
      await sendMessage(`Tell me more about the ${product.name}`);
    }, 400);
  };

  if (loading) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        style={{ background: "var(--color-background)" }}
      >
        <p style={{ color: "var(--color-on-surface-variant)" }}>Loading product…</p>
      </div>
    );
  }

  if (notFound || !product) {
    return <NotFound />;
  }

  return (
    <div
      className="min-h-screen flex flex-col"
      style={{ background: "var(--color-background)", color: "var(--color-on-surface)" }}
    >
      <header
        className="sticky top-0 z-50 border-b shadow-sm"
        style={{ background: "var(--color-surface)", borderColor: "var(--color-surface-variant)" }}
      >
        <div className="flex justify-between items-center h-20 px-4 md:px-10 max-w-[1280px] mx-auto">
          <Link
            href="/"
            className="text-2xl font-bold"
            style={{ color: "var(--color-primary)", fontFamily: "var(--font-headline-md)" }}
          >
            ShopEase
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/products" style={{ color: "var(--color-on-surface-variant)" }}>
              Shop
            </Link>
            <Link href="/cart" style={{ color: "var(--color-secondary)" }}>
              <span className="material-symbols-outlined" style={{ fontSize: 24 }}>
                shopping_cart
              </span>
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-[1280px] mx-auto w-full px-4 md:px-10 py-16 flex-1">
        <nav
          className="mb-6 flex items-center gap-2 text-sm"
          style={{ color: "var(--color-on-surface-variant)", fontFamily: "var(--font-body-sm)" }}
        >
          <Link href="/" className="hover:text-[var(--color-secondary)]">
            Home
          </Link>
          <span className="material-symbols-outlined" style={{ fontSize: 14 }}>
            chevron_right
          </span>
          <Link href="/products" className="hover:text-[var(--color-secondary)]">
            {product.category}
          </Link>
          <span className="material-symbols-outlined" style={{ fontSize: 14 }}>
            chevron_right
          </span>
          <span style={{ color: "var(--color-on-surface)" }}>{product.name}</span>
        </nav>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-16">
          <div className="lg:col-span-7 grid grid-cols-4 gap-4">
            <div
              className="col-span-4 rounded-xl overflow-hidden border"
              style={{
                background: "var(--color-surface-container-lowest)",
                borderColor: "var(--color-surface-variant)",
                aspectRatio: "4/3",
              }}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={gallery[activeThumb] || product.image}
                alt={product.name}
                className="w-full h-full object-cover"
              />
            </div>
            {gallery.slice(0, 4).map((src, i) => (
              <button
                key={src + i}
                type="button"
                onClick={() => setActiveThumb(i)}
                className="col-span-1 rounded-xl overflow-hidden border cursor-pointer"
                style={{
                  borderColor:
                    activeThumb === i ? "var(--color-secondary)" : "var(--color-surface-variant)",
                  aspectRatio: "1/1",
                }}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={src} alt="" className="w-full h-full object-cover" />
              </button>
            ))}
          </div>

          <div className="lg:col-span-5 flex flex-col gap-6">
            <div>
              <span
                className="inline-block px-3 py-1 rounded-full text-xs mb-4 uppercase tracking-wider font-medium"
                style={{
                  background: "var(--color-surface-variant)",
                  color: "var(--color-on-surface-variant)",
                  fontFamily: "var(--font-label-mono)",
                }}
              >
                {product.brand || product.category}
              </span>
              <h1
                className="font-bold leading-[1.1] mb-2"
                style={{
                  color: "var(--color-primary)",
                  fontFamily: "var(--font-display-lg)",
                  fontSize: "clamp(28px, 4vw, 48px)",
                }}
              >
                {product.name}
              </h1>
              <div className="flex items-center gap-2 mb-6">
                <div className="flex" style={{ color: "var(--color-secondary)" }}>
                  {[1, 2, 3, 4, 5].map((i) => (
                    <span
                      key={i}
                      className="material-symbols-outlined"
                      style={{
                        fontSize: 18,
                        fontVariationSettings: `'FILL' ${i <= Math.round(product.rating) ? 1 : 0}`,
                      }}
                    >
                      star
                    </span>
                  ))}
                </div>
                <span
                  className="text-sm"
                  style={{ color: "var(--color-on-surface-variant)", fontFamily: "var(--font-body-sm)" }}
                >
                  ({product.reviewsCount} Reviews)
                </span>
              </div>
              <div
                className="text-4xl font-bold"
                style={{ color: "var(--color-secondary)", fontFamily: "var(--font-display-lg)" }}
              >
                {formatPrice(product.price)}
              </div>
              {product.originalPrice && product.originalPrice > product.price && (
                <p
                  className="text-sm line-through mt-1"
                  style={{ color: "var(--color-on-surface-variant)" }}
                >
                  {formatPrice(product.originalPrice)}
                </p>
              )}
            </div>

            <p
              className="leading-relaxed"
              style={{ color: "var(--color-on-surface-variant)", fontFamily: "var(--font-body-md)" }}
            >
              {product.description}
            </p>

            <p className="text-sm" style={{ color: "var(--color-on-surface-variant)" }}>
              Stock: {product.stockQuantity ?? 0} available
            </p>

            <div className="flex flex-col gap-3">
              <button
                onClick={handleAddToCart}
                className="w-full py-4 rounded-[10px] font-bold text-lg transition-all active:scale-[0.98] cursor-pointer"
                style={{
                  background: added ? "#22c55e" : "var(--color-primary)",
                  color: "var(--color-on-primary)",
                }}
              >
                {added ? "✓ Added to Cart" : "Buy Now"}
              </button>
              <button
                onClick={handleAskAI}
                className="w-full py-3 rounded-[10px] font-medium text-sm border cursor-pointer flex items-center justify-center gap-2"
                style={{
                  borderColor: "var(--color-secondary)",
                  color: "var(--color-secondary)",
                }}
              >
                <span className="material-symbols-outlined" style={{ fontSize: 18 }}>
                  smart_toy
                </span>
                Ask AI About This
              </button>
              <button
                onClick={() => setWishlisted(!wishlisted)}
                className="p-3 rounded-[10px] border self-start cursor-pointer"
                style={{
                  borderColor: wishlisted ? "var(--color-error)" : "var(--color-outline-variant)",
                  color: wishlisted ? "var(--color-error)" : "var(--color-on-surface-variant)",
                }}
              >
                <span
                  className="material-symbols-outlined"
                  style={{ fontVariationSettings: `'FILL' ${wishlisted ? 1 : 0}` }}
                >
                  favorite
                </span>
              </button>
            </div>
          </div>
        </div>

        <div className="mt-24">
          <div
            className="flex border-b gap-10 mb-6"
            style={{ borderColor: "var(--color-surface-variant)" }}
          >
            {TABS.map((tab, i) => (
              <button
                key={tab}
                onClick={() => setActiveTab(i)}
                className="pb-6 border-b-2 font-medium cursor-pointer"
                style={{
                  borderColor: activeTab === i ? "var(--color-secondary)" : "transparent",
                  color:
                    activeTab === i ? "var(--color-secondary)" : "var(--color-on-surface-variant)",
                }}
              >
                {tab}
              </button>
            ))}
          </div>
          {activeTab === 0 && (
            <p
              className="py-6 max-w-2xl leading-relaxed"
              style={{ color: "var(--color-on-surface-variant)" }}
            >
              {product.description}
            </p>
          )}
          {activeTab === 1 && (
            <div className="py-6 max-w-2xl space-y-4">
              {[
                { icon: "local_shipping", label: "Standard Delivery", value: "3–5 business days — Free" },
                { icon: "bolt", label: "Express Delivery", value: "1–2 business days — Rs. 299" },
                { icon: "sync", label: "Returns", value: "30-day hassle-free returns" },
              ].map(({ icon, label, value }) => (
                <div
                  key={label}
                  className="flex items-center gap-4 py-4 border-b"
                  style={{ borderColor: "var(--color-surface-variant)" }}
                >
                  <span
                    className="material-symbols-outlined"
                    style={{ fontSize: 24, color: "var(--color-secondary)" }}
                  >
                    {icon}
                  </span>
                  <div>
                    <p className="font-semibold text-sm">{label}</p>
                    <p className="text-sm" style={{ color: "var(--color-on-surface-variant)" }}>
                      {value}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {related.length > 0 && (
          <div className="mt-24">
            <h2
              className="text-2xl font-semibold mb-10"
              style={{ color: "var(--color-primary)", fontFamily: "var(--font-headline-md)" }}
            >
              You Might Also Like
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {related.map((p) => (
                <Link
                  key={p.id}
                  href={`/products/${p.id}`}
                  className="group block rounded-xl overflow-hidden border hover:shadow-lg transition-all"
                  style={{
                    background: "var(--color-surface-container-lowest)",
                    borderColor: "var(--color-surface-variant)",
                  }}
                >
                  <div className="relative h-52 overflow-hidden">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={p.image}
                      alt={p.name}
                      className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                    />
                  </div>
                  <div className="p-5">
                    <p
                      className="text-[10px] mb-1 uppercase tracking-widest"
                      style={{ color: "var(--color-secondary-container)" }}
                    >
                      {p.category}
                    </p>
                    <h3 className="font-bold text-base mb-3">{p.name}</h3>
                    <span className="text-xl font-bold" style={{ color: "var(--color-primary)" }}>
                      {formatPrice(p.price)}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        )}
      </main>

      <div className="fixed right-6 bottom-6 z-50">
        <AgentButton embedded />
      </div>
      <AgentWidget />
    </div>
  );
}

function NotFound() {
  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center gap-4 text-center px-4"
      style={{ background: "var(--color-background)" }}
    >
      <h2 className="text-2xl font-bold" style={{ color: "var(--color-primary)" }}>
        Product Not Found
      </h2>
      <Link
        href="/products"
        className="mt-4 px-6 py-3 rounded-[10px] font-bold text-sm"
        style={{ background: "var(--color-primary)", color: "var(--color-on-primary)" }}
      >
        ← Return to Shop
      </Link>
    </div>
  );
}

export default function ProductDetailPage({ params }: PageProps) {
  return (
    <AgentProvider>
      <ProductDetailContent params={params} />
    </AgentProvider>
  );
}
