export interface Product {
  id: string;
  name: string;
  price: number;
  description: string;
  image: string;
  images?: string[];
  category: string;
  brand?: string;
  rating: number;
  reviewsCount: number;
  stockQuantity?: number;
  isFeatured?: boolean;
  originalPrice?: number;
}

export interface OrderItem {
  productId: string;
  name: string;
  quantity: number;
  price: number;
}

export interface Order {
  id: string;
  status: "processing" | "in_transit" | "delivered" | "cancelled";
  items: OrderItem[];
  total: number;
  estimatedDelivery: string;
  carrier: string;
  trackingNumber: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: number;
  products?: Product[];
  order?: Order;
  isStreaming?: boolean;
  handoff?: boolean;
}

export interface ChatSession {
  messages: Message[];
  unreadCount: number;
  humanHandoff: boolean;
}
