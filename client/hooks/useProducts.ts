"use client";

import { useCallback, useEffect, useState } from "react";
import { Product } from "../types/chat";
import {
  ApiCategory,
  fetchCatalog,
  fetchCategories,
  fetchProductById,
  fetchProducts,
  peekCache,
  peekCatalog,
  ProductListParams,
} from "../lib/api";

function initialProducts(): Product[] {
  return peekCatalog() || [];
}

function initialCategories(): ApiCategory[] {
  return peekCache<ApiCategory[]>("/products/categories") || [];
}

/**
 * Loads the full product catalog once (cached) and keeps UI filled
 * while background refresh runs — no full-page skeleton flicker.
 */
export function useProducts(_params: ProductListParams = {}) {
  const [products, setProducts] = useState<Product[]>(initialProducts);
  const [categories, setCategories] = useState<ApiCategory[]>(initialCategories);
  const [total, setTotal] = useState(() => initialProducts().length);
  const [loading, setLoading] = useState(() => initialProducts().length === 0);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    const hasData = (peekCatalog()?.length ?? 0) > 0 || products.length > 0;
    if (hasData) setRefreshing(true);
    else setLoading(true);
    setError(null);
    try {
      const [items, cats] = await Promise.all([fetchCatalog(), fetchCategories()]);
      setProducts(items);
      setTotal(items.length);
      setCategories(cats);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load products");
      if (!hasData) {
        setProducts([]);
        setTotal(0);
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const getProductById = useCallback(
    async (id: string): Promise<Product | undefined> => {
      const cached = products.find((p) => p.id === id);
      if (cached) return cached;
      const remote = await fetchProductById(id);
      return remote ?? undefined;
    },
    [products]
  );

  const searchProducts = useCallback(
    async (query: string): Promise<Product[]> => {
      const q = query.toLowerCase().trim();
      if (!q) return products.slice(0, 20);
      const local = products.filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          p.category.toLowerCase().includes(q) ||
          (p.brand || "").toLowerCase().includes(q) ||
          p.description.toLowerCase().includes(q)
      );
      if (local.length) return local.slice(0, 20);
      const res = await fetchProducts({ search: query, page_size: 20 });
      return res.items;
    },
    [products]
  );

  const categoryNames = categories.map((c) => c.name);

  return {
    products,
    categories,
    categoryNames,
    total,
    loading,
    refreshing,
    error,
    reload,
    getProductById,
    searchProducts,
  };
}

export default useProducts;
