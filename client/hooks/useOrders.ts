"use client";

import { useCallback, useEffect, useState } from "react";
import { Order } from "../types/chat";
import { fetchOrders, mapOrder, peekCache, ApiOrder } from "../lib/api";

function initialOrders(): Order[] {
  const cached = peekCache<ApiOrder[]>("/orders/demo");
  return cached ? cached.map(mapOrder) : [];
}

export function useOrders() {
  const [orders, setOrders] = useState<Order[]>(initialOrders);
  const [loading, setLoading] = useState(() => initialOrders().length === 0);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    const hasData = (peekCache<ApiOrder[]>("/orders/demo")?.length ?? 0) > 0 || orders.length > 0;
    if (!hasData) setLoading(true);
    setError(null);
    try {
      const data = await fetchOrders();
      setOrders(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load orders");
      if (!hasData) setOrders([]);
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { orders, loading, error, reload };
}

export default useOrders;
