import { Router, Request, Response } from "express";
import { MOCK_ORDERS } from "../lib/mockData";
import { Order } from "../types";

const router = Router();

// GET /api/orders — list all orders (real app: filter by user ID from JWT)
router.get("/", (_req: Request, res: Response) => {
  res.json({ data: MOCK_ORDERS, count: MOCK_ORDERS.length });
});

// GET /api/orders/:id — get single order with tracking info
router.get("/:id", (req: Request, res: Response) => {
  const order = MOCK_ORDERS.find((o) => o.id === req.params.id);
  if (!order) {
    res.status(404).json({ error: `Order '${req.params.id}' not found` });
    return;
  }
  res.json({ data: order });
});

// POST /api/orders — place a new order
router.post("/", (req: Request, res: Response) => {
  const { items, shippingAddress, paymentMethod } = req.body;

  if (!items || !Array.isArray(items) || items.length === 0) {
    res.status(400).json({ error: "Order must contain at least one item" });
    return;
  }

  const total = items.reduce(
    (sum: number, item: { price: number; quantity: number }) =>
      sum + item.price * item.quantity,
    0
  );

  const newOrder: Order = {
    id: `SE-${Math.floor(Math.random() * 90000) + 10000}`,
    status: "processing",
    items,
    total: parseFloat(total.toFixed(2)),
    estimatedDelivery: "3–5 business days",
    carrier: "TCS Pakistan",
    trackingNumber: `TCS-${Date.now()}-SE`,
    createdAt: new Date().toISOString(),
  };

  // In production: persist to Supabase here
  console.log("📦 New order placed:", newOrder.id, "| Address:", shippingAddress, "| Payment:", paymentMethod);

  res.status(201).json({
    data: newOrder,
    message: "Order placed successfully!",
  });
});

// PATCH /api/orders/:id/cancel — cancel an order (only if processing)
router.patch("/:id/cancel", (req: Request, res: Response) => {
  const order = MOCK_ORDERS.find((o) => o.id === req.params.id);
  if (!order) {
    res.status(404).json({ error: `Order '${req.params.id}' not found` });
    return;
  }
  if (order.status !== "processing") {
    res.status(409).json({
      error: `Cannot cancel order with status '${order.status}'`,
    });
    return;
  }

  // In production: update Supabase here
  order.status = "cancelled";
  res.json({ data: order, message: "Order cancelled successfully" });
});

export default router;
