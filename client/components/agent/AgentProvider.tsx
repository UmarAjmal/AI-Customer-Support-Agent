"use client";

import React, { createContext, useState, useEffect, useCallback, useRef } from "react";
import { Message, Product, Order } from "../../types/chat";
import { fetchOrders, fetchProducts, searchProductsForAgent } from "../../lib/api";

interface AgentContextType {
  messages: Message[];
  isOpen: boolean;
  isTyping: boolean;
  unreadCount: number;
  humanHandoff: boolean;
  toggleWidget: () => void;
  minimizeWidget: () => void;
  closeWidget: () => void;
  sendMessage: (content: string) => Promise<void>;
  sendQuickReply: (reply: string) => void;
  clearChat: () => void;
}

export const AgentContext = createContext<AgentContextType | undefined>(undefined);

const LOCAL_STORAGE_KEY = "shopease-chat-history";
const LOCAL_STORAGE_OPEN_KEY = "shopease-chat-open";
const LOCAL_STORAGE_HANDOFF_KEY = "shopease-chat-handoff";

export const AgentProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [humanHandoff, setHumanHandoff] = useState(false);

  const isStreamingRef = useRef(false);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  // Generate or restore session key — fetches a server-signed HMAC key
  const [sessionKey, setSessionKey] = useState<string>("");

  useEffect(() => {
    if (typeof window === "undefined") return;

    const stored = localStorage.getItem("shopease-session-key");

    // Re-use existing signed key if it's a server-signed format (contains 4 colons)
    if (stored && stored.split(":").length >= 5) {
      setSessionKey(stored);
      return;
    }

    // Fetch a new signed session key from the server
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://ai-customer-support-agent-dchb.onrender.com";
    fetch(`${API_BASE}/api/chat/session`)
      .then((r) => r.json())
      .then((data) => {
        const key = data.session_key as string;
        localStorage.setItem("shopease-session-key", key);
        setSessionKey(key);
      })
      .catch(() => {
        // Fallback: use random key if server unreachable (degraded mode)
        const fallback = "ses:fallback:" + Math.random().toString(36).substring(2, 15) + ":0:unsigned";
        localStorage.setItem("shopease-session-key", fallback);
        setSessionKey(fallback);
      });
  }, []);

  // Restore state from LocalStorage on mount
  useEffect(() => {
    if (typeof window !== "undefined") {
      const storedHistory = localStorage.getItem(LOCAL_STORAGE_KEY);
      const storedOpen = localStorage.getItem(LOCAL_STORAGE_OPEN_KEY);
      const storedHandoff = localStorage.getItem(LOCAL_STORAGE_HANDOFF_KEY);

      if (storedHistory) {
        try {
          setMessages(JSON.parse(storedHistory));
        } catch (e) {
          console.error("Failed to parse chat history", e);
        }
      } else {
        // Initial welcome message
        const welcomeMessage: Message = {
          id: "welcome-msg",
          role: "assistant",
          content: "Hi! Welcome to **ShopEase** support. 🛍️\n\nI am your ShopEase AI Assistant. I can help you find products, track order delivery statuses, or answer store policy questions.\n\nWhat can I help you with today?",
          timestamp: Date.now(),
        };
        setMessages([welcomeMessage]);
      }

      if (storedOpen) {
        setIsOpen(storedOpen === "true");
      }
      if (storedHandoff) {
        setHumanHandoff(storedHandoff === "true");
      }
    }
  }, []);

  // Persist messages to LocalStorage
  const saveMessages = (updatedMessages: Message[]) => {
    setMessages(updatedMessages);
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(updatedMessages));
  };

  // Toggle widget open/close
  const toggleWidget = useCallback(() => {
    setIsOpen((prev) => {
      const nextState = !prev;
      localStorage.setItem(LOCAL_STORAGE_OPEN_KEY, String(nextState));
      if (nextState) {
        setUnreadCount(0); // clear unread count when opened
      }
      return nextState;
    });
  }, []);

  const minimizeWidget = useCallback(() => {
    setIsOpen(false);
    localStorage.setItem(LOCAL_STORAGE_OPEN_KEY, "false");
  }, []);

  const closeWidget = useCallback(() => {
    setIsOpen(false);
    localStorage.setItem(LOCAL_STORAGE_OPEN_KEY, "false");
  }, []);

  const clearChat = useCallback(() => {
    const welcomeMessage: Message = {
      id: "welcome-msg",
      role: "assistant",
      content: "Hi! Welcome to **ShopEase** support. 🛍️\n\nI am your ShopEase AI Assistant. I can help you find products, track order delivery statuses, or answer store policy questions.\n\nWhat can I help you with today?",
      timestamp: Date.now(),
    };
    saveMessages([welcomeMessage]);
    setHumanHandoff(false);
    localStorage.setItem(LOCAL_STORAGE_HANDOFF_KEY, "false");
    setUnreadCount(0);
  }, []);

  // Shop-only client fallback when backend is unreachable (still uses live DB APIs)
  const processAgentResponseFallback = async (
    userText: string
  ): Promise<{ text: string; products?: Product[]; order?: Order }> => {
    const text = userText.toLowerCase().trim();

    const shopHints = [
      "product", "order", "track", "return", "refund", "shipping", "payment", "cod",
      "laptop", "phone", "shoes", "headphones", "shop", "shopease", "recommend",
      "find", "buy", "policy", "warranty", "easypaisa", "jazzcash", "cart", "delivery",
      "parcel", "human", "agent", "hello", "hi", "hey", "salam", "thanks", "thank",
    ];
    const offTopicHints = [
      "capital of", "weather", "cricket", "homework", "write code", "bitcoin",
      "politics", "joke", "recipe", "movie", "chatgpt", "math",
    ];

    const looksShop = shopHints.some((k) => text.includes(k)) || /\b(se|ord|ret)[- ]?\d{3,6}\b/i.test(text);
    const looksOffTopic = offTopicHints.some((k) => text.includes(k));

    if (looksOffTopic && !looksShop) {
      return {
        text: "I'm ShopEase Customer Care, so I can only help with our store — products, orders, delivery, returns, payments, and policies. I can't assist with that topic. How can I help with your ShopEase shopping today?",
      };
    }

    if (
      text.includes("human") ||
      text.includes("live agent") ||
      text.includes("real person") ||
      text.includes("talk to agent") ||
      text.includes("speak to")
    ) {
      return {
        text: "Of course — I'm connecting you with a human ShopEase support specialist. Meanwhile: support@shopease.pk · +92 300 1234567 (Mon–Sat, 9am–6pm).",
      };
    }

    if (text.includes("order") || text.includes("track") || text.includes("delivery") || text.includes("parcel") || /\b(se|ord)-\d+/i.test(text)) {
      try {
        const orders = await fetchOrders();
        const byDigits = orders.find((o) => {
          const digits = o.id.replace(/\D/g, "");
          return digits && text.includes(digits);
        });
        const match = orders.find((o) => text.includes(o.id.toLowerCase())) || byDigits;
        if (match) {
          return {
            text: `I found order **#${match.id}**. Status: **${match.status.replace("_", " ")}**. Courier: **${match.carrier}**. Tracking: \`${match.trackingNumber}\`. Est. delivery: **${match.estimatedDelivery}**.`,
            order: match,
          };
        }
        return {
          text: "I couldn't find that order. Please share a valid order number (e.g. *SE-9821* or *ORD-1023*).",
        };
      } catch {
        return { text: "I couldn't reach our order database right now. Please try again shortly." };
      }
    }

    if (
      text.includes("product") ||
      text.includes("find") ||
      text.includes("recommend") ||
      text.includes("buy") ||
      text.includes("shop") ||
      text.includes("headphones") ||
      text.includes("laptop") ||
      text.includes("phone") ||
      text.includes("shoes") ||
      text.includes("show me")
    ) {
      try {
        let query = "";
        if (text.includes("headphones") || text.includes("sony")) query = "headphones";
        else if (text.includes("laptop") || text.includes("macbook")) query = "laptop";
        else if (text.includes("phone") || text.includes("mobile") || text.includes("iphone")) query = "phone";
        else if (text.includes("shoes") || text.includes("nike") || text.includes("adidas")) query = "shoes";
        else if (text.includes("shirt") || text.includes("fashion")) query = "shirt";

        const products = query
          ? await searchProductsForAgent(query)
          : (await fetchProducts({ page_size: 3 })).items;

        return {
          text: "Here are matching items from our live ShopEase catalog. You can add them to cart below:",
          products: products.slice(0, 3),
        };
      } catch {
        return { text: "I couldn't load products right now. Please open the Shop page or try again." };
      }
    }

    if (text.includes("return") || text.includes("refund") || text.includes("policy")) {
      return {
        text: "ShopEase offers a **30-day free return** window after delivery. Refunds usually take 5–7 business days after we receive the item. Share an order number (e.g. *SE-4392*) if you want a live return status check.",
      };
    }

    if (text.includes("payment") || text.includes("cod") || text.includes("jazzcash") || text.includes("easypaisa") || text.includes("visa")) {
      return {
        text: "We accept **COD**, **EasyPaisa**, **JazzCash**, and **Visa/Mastercard**. Need help with a failed payment or COD limit? Tell me more.",
      };
    }

    if (text.includes("hello") || text.includes("hi") || text.includes("hey") || text.includes("salam") || text.includes("thank")) {
      return {
        text: "As-salamu alaykum! Welcome to **ShopEase** Customer Care. I can help with products, order tracking, returns, and store policies. What do you need?",
      };
    }

    if (!looksShop) {
      return {
        text: "I'm ShopEase Customer Care — I only handle store questions (products, orders, shipping, returns, payments). Try: *\"Show me laptops\"*, *\"Track order SE-9821\"*, or *\"What is your return policy?\"*.",
      };
    }

    return {
      text: "I can help with ShopEase products, tracking, returns, and policies. Try asking: *\"Show me headphones\"*, *\"Track order SE-9821\"*, or *\"Shipping policy\"*.",
    };
  };

  // Real-time backend streaming fetch via Server Sent Events (SSE)
  const streamBotResponse = async (userText: string) => {
    isStreamingRef.current = true;
    setIsTyping(true);

    const botMessageId = "bot-msg-" + Date.now();
    
    // Create initial empty message card
    const initialMessage: Message = {
      id: botMessageId,
      role: "assistant",
      content: "",
      timestamp: Date.now(),
      isStreaming: true,
    };
    
    setMessages((prev) => [...prev, initialMessage]);
    
    let currentContent = "";
    const backendUrl =
      typeof window !== "undefined"
        ? "/backend-api"
        : process.env.NEXT_PUBLIC_API_URL || "https://ai-customer-support-agent-dchb.onrender.com/api";

    try {
      const response = await fetch(`${backendUrl}/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          session_key: sessionKey || "session-default",
          message: userText,
        }),
      });

      if (!response.ok || !response.body) {
        throw new Error("Backend connection failed");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        
        const lines = chunk.split("\n");
        for (const line of lines) {
          const trimmedLine = line.trim();
          if (trimmedLine.startsWith("data: ")) {
            try {
              const payload = JSON.parse(trimmedLine.substring(6).trim());
              if (payload.token) {
                currentContent += payload.token;
                
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === botMessageId
                      ? { ...msg, content: currentContent }
                      : msg
                  )
                );

                if (messagesEndRef.current) {
                  messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
                }
              }
            } catch (err) {
              // Ignore partial parsing issues in transmission
            }
          }
        }
      }
    } catch (error) {
      console.error("Backend connection failed:", error);
      
      const errorMsg = (
        "⚠️ **Connection to ShopEase AI Server Failed.**\n\n" +
        "Please check if your backend server is running locally (usually on port 8000) or check the Render deployment status.\n\n" +
        "*Tip for developers*: Make sure `NEXT_PUBLIC_API_URL` in `client/.env.local` points to `http://localhost:8000/api` if you are testing local changes."
      );
      
      const words = errorMsg.split(" ");
      currentContent = "";

      for (let i = 0; i < words.length; i++) {
        if (!isStreamingRef.current) break;
        currentContent += (i === 0 ? "" : " ") + words[i];

        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === botMessageId
              ? { ...msg, content: currentContent }
              : msg
          )
        );

        if (messagesEndRef.current) {
          messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
        }

        await new Promise((resolve) => setTimeout(resolve, 15));
      }

      setMessages((prev) => {
        const final = prev.map((msg) =>
          msg.id === botMessageId
            ? { ...msg, content: currentContent, isStreaming: false }
            : msg
        );
        localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(final));
        return final;
      });

      setIsTyping(false);
      isStreamingRef.current = false;
      return;
    }

    // Finalize normal API message — attach matching DB products when keywords match
    let products: Product[] | undefined;
    try {
      const lower = userText.toLowerCase();
      if (lower.includes("headphones") || lower.includes("audio") || lower.includes("sony")) {
        products = await searchProductsForAgent("headphones");
      } else if (lower.includes("laptop") || lower.includes("macbook")) {
        products = await searchProductsForAgent("laptop");
      } else if (lower.includes("phone") || lower.includes("mobile") || lower.includes("iphone")) {
        products = await searchProductsForAgent("phone");
      } else if (lower.includes("recommend") || lower.includes("product") || lower.includes("shop")) {
        products = (await fetchProducts({ page_size: 3 })).items;
      }
    } catch {
      products = undefined;
    }

    setMessages((prev) => {
      const final = prev.map((msg) =>
        msg.id === botMessageId
          ? { ...msg, content: currentContent, isStreaming: false, products }
          : msg
      );
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(final));
      return final;
    });

    setIsTyping(false);
    isStreamingRef.current = false;

    if (!isOpen) {
      setUnreadCount((c) => c + 1);
    }
  };

  const sendMessage = async (content: string) => {
    if (!content.trim() || isTyping) return;

    // 1. Add User Message
    const userMessage: Message = {
      id: "user-msg-" + Date.now(),
      role: "user",
      content,
      timestamp: Date.now(),
    };

    const updatedMessages = [...messages, userMessage];
    saveMessages(updatedMessages);

    // 2. Trigger typing indicator
    setIsTyping(true);
    await new Promise((resolve) => setTimeout(resolve, 300));

    // Live agent Handoff dummy fallback
    if (humanHandoff) {
      const liveAgentResponses = [
        "Sure, I'm checking that account detail for you. Give me just one moment.",
        "Thanks for confirming. I have updated your shipping notes in our system.",
        "I understand. Let me check with our fulfillment department to see if we can speed this up.",
        "Yes, returns are processed within 3 days. Is there anything else I can help you with?"
      ];
      const randomResponse = liveAgentResponses[Math.floor(Math.random() * liveAgentResponses.length)];
      isStreamingRef.current = true;
      let currentContent = "";
      
      const botMessageId = "bot-msg-" + Date.now();
      setMessages((prev) => [...prev, { id: botMessageId, role: "assistant", content: "", timestamp: Date.now(), isStreaming: true }]);

      const words = randomResponse.split(" ");
      for (let i = 0; i < words.length; i++) {
        currentContent += (i === 0 ? "" : " ") + words[i];
        setMessages((prev) => prev.map((msg) => msg.id === botMessageId ? { ...msg, content: currentContent } : msg));
        await new Promise((resolve) => setTimeout(resolve, 40));
      }

      setMessages((prev) => prev.map((msg) => msg.id === botMessageId ? { ...msg, content: currentContent, isStreaming: false } : msg));
      setIsTyping(false);
      isStreamingRef.current = false;
      return;
    }

    // Update handoff flag locally if keywords trigger human handoff
    if (content.toLowerCase().includes("human") || content.toLowerCase().includes("agent") || content.toLowerCase().includes("support") || content.toLowerCase().includes("person") || content.toLowerCase().includes("talk to")) {
      setHumanHandoff(true);
      localStorage.setItem(LOCAL_STORAGE_HANDOFF_KEY, "true");
    }

    // 3. Stream from FastAPI backend API endpoint (falls back to mock if offline)
    await streamBotResponse(content);
  };

  const sendQuickReply = (reply: string) => {
    sendMessage(reply);
  };

  return (
    <AgentContext.Provider
      value={{
        messages,
        isOpen,
        isTyping,
        unreadCount,
        humanHandoff,
        toggleWidget,
        minimizeWidget,
        closeWidget,
        sendMessage,
        sendQuickReply,
        clearChat,
      }}
    >
      {children}
    </AgentContext.Provider>
  );
};
