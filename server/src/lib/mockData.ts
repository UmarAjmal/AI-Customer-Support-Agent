import { Product, Order } from "../types";

// ─── Mock Products ─────────────────────────────────────────────────────────────
export const MOCK_PRODUCTS: Product[] = [
  {
    id: "prod-1",
    name: "ShopEase Premium Hoodie",
    price: 59.99,
    description:
      "Crafted from 100% heavy cotton fleece, this premium hoodie offers maximum comfort and style.",
    image: "https://images.unsplash.com/photo-1556821840-3a63f95609a7?q=80&w=600",
    category: "Apparel",
    rating: 4.8,
    reviewsCount: 142,
    stock: 50,
  },
  {
    id: "prod-2",
    name: "Wireless ANC Headphones",
    price: 199.99,
    description:
      "Experience silence with industry-leading Active Noise Canceling technology. 40-hour battery life.",
    image: "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?q=80&w=600",
    category: "Electronics",
    rating: 4.7,
    reviewsCount: 389,
    stock: 20,
  },
  {
    id: "prod-3",
    name: "Minimalist Leather Wallet",
    price: 39.99,
    description:
      "Made from genuine full-grain leather. Ultra-slim with RFID-blocking technology.",
    image: "https://images.unsplash.com/photo-1627124765135-56c33fc36eab?q=80&w=600",
    category: "Accessories",
    rating: 4.5,
    reviewsCount: 94,
    stock: 75,
  },
  {
    id: "prod-4",
    name: "Ergonomic Mechanical Keyboard",
    price: 129.99,
    description:
      "Brown mechanical switches, customizable RGB backlighting, and a premium aluminum frame.",
    image: "https://images.unsplash.com/photo-1587829741301-dc798b83add3?q=80&w=600",
    category: "Electronics",
    rating: 4.9,
    reviewsCount: 204,
    stock: 30,
  },
];

// ─── Mock Orders ───────────────────────────────────────────────────────────────
export const MOCK_ORDERS: Order[] = [
  {
    id: "SE-9821",
    status: "in_transit",
    items: [
      { productId: "prod-2", name: "Wireless ANC Headphones", quantity: 1, price: 199.99 },
      { productId: "prod-3", name: "Minimalist Leather Wallet", quantity: 1, price: 39.99 },
    ],
    total: 239.98,
    estimatedDelivery: "Tomorrow, by 5:00 PM",
    carrier: "DHL Express",
    trackingNumber: "DHL-88392019-SE",
    createdAt: new Date().toISOString(),
  },
  {
    id: "SE-4392",
    status: "delivered",
    items: [{ productId: "prod-1", name: "ShopEase Premium Hoodie", quantity: 1, price: 59.99 }],
    total: 59.99,
    estimatedDelivery: "Delivered 2 days ago",
    carrier: "FedEx SmartPost",
    trackingNumber: "FX-39204820-SE",
    createdAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
  },
];
