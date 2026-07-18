import { Product, Order, OrderItem } from "../types/chat";

const API_BASE =
  typeof window !== "undefined"
    ? "/backend-api"
    : process.env.NEXT_PUBLIC_API_URL || "https://ai-customer-support-agent-dchb.onrender.com/api";

/** Short in-memory cache so page navigations feel instant */
const CACHE_TTL_MS = 60_000;
const memoryCache = new Map<string, { expires: number; data: unknown }>();
const inflight = new Map<string, Promise<unknown>>();

export interface ApiCategory {
  id: string;
  name: string;
  slug: string;
  icon?: string | null;
  image_url?: string | null;
  product_count: number;
}

export interface ApiProduct {
  id: string;
  name: string;
  description?: string | null;
  price: number | string;
  original_price?: number | string | null;
  category: string;
  brand?: string | null;
  image_url?: string | null;
  images?: string[] | null;
  stock_quantity: number;
  is_featured: boolean;
  is_active: boolean;
  rating: number | string;
  review_count: number;
  tags?: string[] | null;
}

export interface ApiOrder {
  id: string;
  order_number: string;
  customer_name?: string | null;
  items: Array<Record<string, unknown>>;
  total_amount: number | string;
  status: string;
  tracking_number?: string | null;
  estimated_delivery?: string | null;
  shipping_address?: Record<string, unknown> | null;
}

interface StandardResponse<T> {
  success: boolean;
  message: string;
  data: T;
}

export function formatPrice(n: number): string {
  return `Rs. ${Math.round(n).toLocaleString("en-PK")}`;
}

/** Resize Unsplash (and similar) URLs so grids load faster */
function optimizeImageUrl(url: string, width = 640): string {
  if (!url || url.startsWith("/")) return url;
  try {
    const u = new URL(url);
    if (u.hostname.includes("unsplash.com")) {
      u.searchParams.set("auto", "format");
      u.searchParams.set("fit", "crop");
      u.searchParams.set("w", String(width));
      u.searchParams.set("q", "75");
      return u.toString();
    }
  } catch {
    /* keep original */
  }
  return url;
}

function deriveCarrier(tracking?: string | null): string {
  if (!tracking) return "ShopEase Logistics";
  const t = tracking.toUpperCase();
  if (t.startsWith("TCS")) return "TCS";
  if (t.startsWith("DHL")) return "DHL Express";
  if (t.startsWith("FX") || t.startsWith("FEDEX")) return "FedEx";
  return "ShopEase Logistics";
}

function mapStatus(status: string): Order["status"] {
  const s = status.toLowerCase();
  if (s === "shipped" || s === "in_transit") return "in_transit";
  if (s === "delivered") return "delivered";
  if (s === "cancelled") return "cancelled";
  return "processing";
}

export function mapProduct(p: ApiProduct): Product {
  const price = typeof p.price === "string" ? parseFloat(p.price) : Number(p.price);
  const rating = typeof p.rating === "string" ? parseFloat(p.rating) : Number(p.rating);
  const images = (p.images?.filter(Boolean) ?? []).map((img) => optimizeImageUrl(img, 800));
  const image = optimizeImageUrl(p.image_url || images[0] || "/window.svg", 640);

  return {
    id: String(p.id),
    name: p.name,
    price: Number.isFinite(price) ? price : 0,
    description: p.description || "",
    image,
    images: images.length ? images : [image],
    category: p.category,
    brand: p.brand || undefined,
    rating: Number.isFinite(rating) ? rating : 0,
    reviewsCount: p.review_count ?? 0,
    stockQuantity: p.stock_quantity,
    isFeatured: p.is_featured,
    originalPrice: p.original_price ? Number(p.original_price) : undefined,
  };
}

export function mapOrder(o: ApiOrder): Order {
  const items: OrderItem[] = (o.items || []).map((item) => ({
    productId: String(item.product_id ?? item.productId ?? ""),
    name: String(item.name ?? "Item"),
    quantity: Number(item.quantity ?? 1),
    price: Number(item.price ?? 0),
  }));

  const total =
    typeof o.total_amount === "string"
      ? parseFloat(o.total_amount)
      : Number(o.total_amount);

  return {
    id: o.order_number,
    status: mapStatus(o.status),
    items,
    total: Number.isFinite(total) ? total : 0,
    estimatedDelivery: o.estimated_delivery
      ? new Date(o.estimated_delivery).toLocaleDateString("en-PK", {
          year: "numeric",
          month: "short",
          day: "numeric",
        })
      : "TBD",
    carrier: deriveCarrier(o.tracking_number),
    trackingNumber: o.tracking_number || "Pending",
  };
}

export function peekCache<T>(path: string): T | null {
  const hit = memoryCache.get(path);
  if (hit && hit.expires > Date.now()) return hit.data as T;
  return null;
}

async function apiGet<T>(path: string, options?: { ttlMs?: number; bypassCache?: boolean }): Promise<T> {
  const ttl = options?.ttlMs ?? CACHE_TTL_MS;
  const key = path;

  if (!options?.bypassCache) {
    const hit = memoryCache.get(key);
    if (hit && hit.expires > Date.now()) {
      return hit.data as T;
    }
    // Stale-while-revalidate: show old data immediately, refresh in background
    if (hit) {
      const pending = inflight.get(key);
      if (!pending) {
        const refresh = (async () => {
          const controller = new AbortController();
          const timer = setTimeout(() => controller.abort(), 12000);
          try {
            const res = await fetch(`${API_BASE}${key}`, {
              headers: { Accept: "application/json" },
              signal: controller.signal,
            });
            if (!res.ok) throw new Error(`API ${key} failed: ${res.status}`);
            const json = (await res.json()) as StandardResponse<T>;
            memoryCache.set(key, { data: json.data, expires: Date.now() + ttl });
            return json.data;
          } finally {
            clearTimeout(timer);
            inflight.delete(key);
          }
        })();
        inflight.set(key, refresh);
      }
      return hit.data as T;
    }
    const pending = inflight.get(key);
    if (pending) {
      return pending as Promise<T>;
    }
  }

  const request = (async () => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 12000);
    try {
      const res = await fetch(`${API_BASE}${key}`, {
        headers: { Accept: "application/json" },
        signal: controller.signal,
      });
      if (!res.ok) {
        throw new Error(`API ${key} failed: ${res.status}`);
      }
      const json = (await res.json()) as StandardResponse<T>;
      memoryCache.set(key, { data: json.data, expires: Date.now() + ttl });
      return json.data;
    } finally {
      clearTimeout(timer);
      inflight.delete(key);
    }
  })();

  inflight.set(key, request);
  return request;
}

export function clearApiCache(prefix?: string) {
  if (!prefix) {
    memoryCache.clear();
    return;
  }
  for (const key of memoryCache.keys()) {
    if (key.startsWith(prefix)) memoryCache.delete(key);
  }
}

export interface ProductListParams {
  search?: string;
  category?: string;
  min_price?: number;
  max_price?: number;
  sort_by?: string;
  page?: number;
  page_size?: number;
}

export async function fetchProducts(params: ProductListParams = {}): Promise<{
  items: Product[];
  total: number;
  page: number;
  page_size: number;
}> {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
  });
  if (!qs.has("page_size")) qs.set("page_size", "50");

  const data = await apiGet<{
    items: ApiProduct[];
    total: number;
    page: number;
    page_size: number;
  }>(`/products?${qs.toString()}`);

  return {
    items: (data.items || []).map(mapProduct),
    total: data.total,
    page: data.page,
    page_size: data.page_size,
  };
}

/** Full catalog — shared across home/products (cached 60s) */
export async function fetchCatalog(): Promise<Product[]> {
  const { items } = await fetchProducts({ page_size: 50 });
  return items;
}

export function peekCatalog(): Product[] | null {
  const cached = peekCache<{
    items: ApiProduct[];
    total: number;
    page: number;
    page_size: number;
  }>("/products?page_size=50");
  if (!cached?.items) return null;
  return cached.items.map(mapProduct);
}

export async function fetchProductById(id: string): Promise<Product | null> {
  // Prefer catalog cache first (instant)
  try {
    const catalog = await fetchCatalog();
    const hit = catalog.find((p) => p.id === id);
    if (hit) return hit;
  } catch {
    /* fall through */
  }
  try {
    const data = await apiGet<ApiProduct>(`/products/${id}`);
    return mapProduct(data);
  } catch {
    return null;
  }
}

export async function fetchCategories(): Promise<ApiCategory[]> {
  return apiGet<ApiCategory[]>("/products/categories", { ttlMs: 120_000 });
}

export async function fetchOrders(): Promise<Order[]> {
  const data = await apiGet<ApiOrder[]>("/orders/demo", { ttlMs: 30_000 });
  return (data || []).map(mapOrder);
}

export async function searchProductsForAgent(query: string): Promise<Product[]> {
  // Prefer filtering cached catalog (instant) instead of new DB round-trip
  try {
    const catalog = await fetchCatalog();
    const q = query.toLowerCase();
    const hits = catalog.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        p.category.toLowerCase().includes(q) ||
        (p.brand || "").toLowerCase().includes(q) ||
        p.description.toLowerCase().includes(q)
    );
    if (hits.length) return hits.slice(0, 6);
  } catch {
    /* fall through */
  }
  const { items } = await fetchProducts({ search: query, page_size: 6 });
  return items;
}

export async function placeOrder(orderData: {
  customer_name?: string;
  customer_email?: string;
  customer_phone?: string;
  items: Array<{ product_id: string; name: string; quantity: number; price: number }>;
  total_amount: number;
  payment_method?: string;
  shipping_address?: Record<string, unknown>;
}): Promise<ApiOrder> {
  const response = await fetch(`${API_BASE}/orders`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "application/json",
    },
    body: JSON.stringify(orderData),
  });

  if (!response.ok) {
    const errorJson = await response.json().catch(() => ({}));
    throw new Error(errorJson.message || errorJson.detail || "Failed to place order");
  }

  const json = (await response.json()) as StandardResponse<ApiOrder>;

  // Clear client-side orders cache so the list loads fresh data
  clearApiCache("/orders");

  return json.data;
}
