"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";
import { AgentProvider } from "../../components/agent/AgentProvider";
import AgentButton from "../../components/agent/AgentButton";
import AgentWidget from "../../components/agent/AgentWidget";
import { useAgent } from "../../hooks/useAgent";
import { useCart } from "../../hooks/useCart";
import { placeOrder } from "../../lib/api";

// ─── Types ─────────────────────────────────────────────────────────────────────
type PaymentMethod = "card" | "easypaisa" | "jazzcash" | "cod";

const SHIPPING = 250;

// ─── Step indicator ────────────────────────────────────────────────────────────
function Stepper({ active }: { active: 1 | 2 | 3 }) {
  const steps = [
    { n: 1, label: "SHIPPING" },
    { n: 2, label: "PAYMENT" },
    { n: 3, label: "REVIEW" },
  ];

  return (
    <div className="flex items-center justify-center mb-16">
      <div className="flex items-center w-full max-w-3xl">
        {steps.map((s, i) => {
          const done = s.n < active;
          const current = s.n <= active;
          return (
            <React.Fragment key={s.n}>
              <div className="flex flex-col items-center flex-1">
                <div
                  className="w-10 h-10 rounded-full border-2 flex items-center justify-center font-bold text-sm transition-all"
                  style={
                    current
                      ? {
                          borderColor: "var(--color-secondary)",
                          color: "var(--color-secondary)",
                          background: "var(--color-secondary-fixed)",
                        }
                      : {
                          borderColor: "var(--color-outline-variant)",
                          color: "var(--color-on-surface-variant)",
                          background: "transparent",
                          opacity: 0.4,
                        }
                  }
                >
                  {done ? (
                    <span className="material-symbols-outlined" style={{ fontSize: 18, fontVariationSettings: "'FILL' 1" }}>
                      check
                    </span>
                  ) : (
                    s.n
                  )}
                </div>
                <span
                  className="mt-2 text-[11px] font-medium tracking-widest"
                  style={{
                    fontFamily: "var(--font-label-mono)",
                    color: current ? "var(--color-secondary)" : "var(--color-on-surface-variant)",
                    opacity: current ? 1 : 0.4,
                  }}
                >
                  {s.label}
                </span>
              </div>

              {/* connector line */}
              {i < steps.length - 1 && (
                <div
                  className="h-[2px] flex-1 mx-2 transition-all"
                  style={{
                    background:
                      s.n < active
                        ? "var(--color-secondary)"
                        : "var(--color-surface-variant)",
                  }}
                />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}

// ─── Checkout content ──────────────────────────────────────────────────────────
function CheckoutContent() {
  const { toggleWidget, sendMessage, isOpen } = useAgent();
  const { items, totalPrice, clearCart } = useCart();
  const [activeStep, setActiveStep] = useState<1 | 2 | 3>(2);
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("card");
  const [placed, setPlaced] = useState(false);
  const [aiTooltip, setAiTooltip] = useState(false);

  // Submit and error states
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const SUBTOTAL = totalPrice;
  const DISCOUNT = Math.round(SUBTOTAL * 0.1);
  const TOTAL = Math.max(0, SUBTOTAL + SHIPPING - DISCOUNT);

  const orderItems = useMemo(
    () =>
      items.map((item) => ({
        id: item.product.id,
        name: item.product.name,
        variant: `${item.product.category} × ${item.quantity}`,
        price: item.product.price * item.quantity,
        image: item.product.image,
      })),
    [items]
  );

  // Form state
  const [form, setForm] = useState({
    name: "",
    phone: "",
    address: "",
    city: "Lahore",
    postal: "",
    cardNumber: "",
    expiry: "",
    cvv: "",
  });

  const updateForm = (k: keyof typeof form, v: string) =>
    setForm((prev) => ({ ...prev, [k]: v }));

  const handleSecureCheckout = async () => {
    if (!form.name.trim() || !form.phone.trim() || !form.address.trim()) {
      setErrorMsg("Please fill in Name, Phone, and Street Address under Shipping Information.");
      return;
    }

    setSubmitting(true);
    setErrorMsg(null);

    try {
      const payloadItems = items.map((item) => ({
        product_id: item.product.id,
        name: item.product.name,
        quantity: item.quantity,
        price: item.product.price,
      }));

      const shippingAddress = {
        street: form.address,
        city: form.city,
        province: form.city === "Karachi" ? "Sindh" : form.city === "Islamabad" ? "ICT" : "Punjab",
        postal_code: form.postal || "54000",
      };

      await placeOrder({
        customer_name: form.name,
        customer_email: `${form.name.toLowerCase().replace(/[^a-z0-9]/g, "") || "guest"}@example.com`,
        customer_phone: form.phone,
        items: payloadItems,
        total_amount: TOTAL,
        payment_method: paymentMethod.toUpperCase(),
        shipping_address: shippingAddress,
      });

      clearCart();
      setPlaced(true);
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : "Failed to place order. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleAskAI = async () => {
    if (!isOpen) toggleWidget();
    setTimeout(async () => {
      await sendMessage("I need help with my checkout — shipping rates or payment options.");
    }, 400);
  };

  // ── Placed confirmation screen ───────────────────────────────────────────────
  if (placed) {
    return (
      <div
        className="min-h-screen flex flex-col"
        style={{ background: "var(--color-background)" }}
      >
        <CheckoutNav />
        <main className="flex-1 flex items-center justify-center px-4 py-24">
          <div
            className="rounded-2xl p-10 text-center max-w-md w-full border"
            style={{
              background: "var(--color-surface-container-lowest)",
              borderColor: "var(--color-surface-variant)",
              boxShadow: "0 4px 12px rgba(26,26,46,0.05)",
            }}
          >
            <div
              className="w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-6"
              style={{ background: "var(--color-secondary-fixed)" }}
            >
              <span
                className="material-symbols-outlined"
                style={{ fontSize: 40, color: "var(--color-secondary)", fontVariationSettings: "'FILL' 1" }}
              >
                check_circle
              </span>
            </div>
            <h2
              className="text-2xl font-bold mb-3"
              style={{ color: "var(--color-primary)", fontFamily: "var(--font-headline-md)" }}
            >
              Order Placed!
            </h2>
            <p
              className="mb-8 text-base leading-relaxed"
              style={{ color: "var(--color-on-surface-variant)", fontFamily: "var(--font-body-md)" }}
            >
              Thank you for shopping with ShopEase. Your payment was secure and your order is now being packed for
              delivery.
            </p>
            <Link
              href="/orders"
              className="inline-flex items-center gap-2 px-8 py-3 rounded-[10px] font-bold text-sm transition-all active:scale-95"
              style={{
                background: "var(--color-primary)",
                color: "var(--color-on-primary)",
                fontFamily: "var(--font-body-sm)",
              }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: 18 }}>receipt_long</span>
              Track My Order
            </Link>
            <div className="mt-4">
              <Link
                href="/"
                className="text-sm hover:underline"
                style={{ color: "var(--color-secondary)", fontFamily: "var(--font-body-sm)" }}
              >
                Continue Shopping →
              </Link>
            </div>
          </div>
        </main>
        <AgentButton embedded />
        <AgentWidget />
      </div>
    );
  }

  // ── Main checkout ────────────────────────────────────────────────────────────
  return (
    <div
      className="min-h-screen flex flex-col"
      style={{ background: "var(--color-background)", color: "var(--color-on-surface)" }}
    >
      <CheckoutNav />

      <main className="max-w-[1280px] mx-auto w-full px-4 md:px-10 py-16 flex-1">
        {/* Stepper */}
        <Stepper active={activeStep} />

        {/* Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-start">
          {/* ── Left: Forms ──────────────────────────────────────────────── */}
          <div className="lg:col-span-8 space-y-6">

            {/* ── Shipping Address ───────────────────────────────────────── */}
            <section
              className="rounded-2xl p-6 md:p-8"
              style={{
                background: "var(--color-surface-container-lowest)",
                boxShadow: "0 4px 12px rgba(26,26,46,0.05)",
              }}
            >
              <div className="flex justify-between items-center mb-6">
                <h2
                  className="text-2xl font-semibold flex items-center gap-2"
                  style={{ color: "var(--color-primary)", fontFamily: "var(--font-headline-md)" }}
                >
                  <span
                    className="material-symbols-outlined"
                    style={{ color: "var(--color-secondary)", fontSize: 26 }}
                  >
                    local_shipping
                  </span>
                  Shipping Information
                </h2>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {/* Full Name */}
                <FormField
                  label="FULL NAME"
                  value={form.name}
                  onChange={(v) => updateForm("name", v)}
                  placeholder="Ali Ahmed"
                  type="text"
                />
                {/* Phone */}
                <FormField
                  label="PHONE NUMBER"
                  value={form.phone}
                  onChange={(v) => updateForm("phone", v)}
                  placeholder="+92 300 1234567"
                  type="tel"
                />
                {/* Street Address — full width */}
                <div className="md:col-span-2">
                  <FormField
                    label="STREET ADDRESS"
                    value={form.address}
                    onChange={(v) => updateForm("address", v)}
                    placeholder="Apartment 4B, Gulberg Heights, Main Boulevard"
                    type="text"
                  />
                </div>
                {/* City */}
                <div className="flex flex-col gap-1">
                  <label
                    className="text-[11px] tracking-widest font-medium"
                    style={{ color: "var(--color-on-surface-variant)", fontFamily: "var(--font-label-mono)" }}
                  >
                    CITY
                  </label>
                  <select
                    value={form.city}
                    onChange={(e) => updateForm("city", e.target.value)}
                    className="w-full px-4 py-3 rounded-[10px] border outline-none transition-all bg-white cursor-pointer"
                    style={{
                      borderColor: "var(--color-surface-variant)",
                      fontFamily: "var(--font-body-md)",
                      color: "var(--color-on-surface)",
                    }}
                  >
                    {["Lahore", "Karachi", "Islamabad", "Faisalabad"].map((c) => (
                      <option key={c}>{c}</option>
                    ))}
                  </select>
                </div>
                {/* Postal */}
                <FormField
                  label="POSTAL CODE"
                  value={form.postal}
                  onChange={(v) => updateForm("postal", v)}
                  placeholder="54000"
                  type="text"
                />
              </div>
            </section>

            {/* ── Payment Method ─────────────────────────────────────────── */}
            <section
              className="rounded-2xl p-6 md:p-8"
              style={{
                background: "var(--color-surface-container-lowest)",
                boxShadow: "0 4px 12px rgba(26,26,46,0.05)",
              }}
            >
              <h2
                className="text-2xl font-semibold mb-6 flex items-center gap-2"
                style={{ color: "var(--color-primary)", fontFamily: "var(--font-headline-md)" }}
              >
                <span className="material-symbols-outlined" style={{ color: "var(--color-secondary)", fontSize: 26 }}>
                  payments
                </span>
                Payment Method
              </h2>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <PaymentOption
                  id="card"
                  selected={paymentMethod === "card"}
                  onSelect={() => setPaymentMethod("card")}
                  label="Credit / Debit Card"
                  sub="Visa, Mastercard"
                  icon="credit_card"
                  iconColor={undefined}
                />
                <PaymentOption
                  id="easypaisa"
                  selected={paymentMethod === "easypaisa"}
                  onSelect={() => setPaymentMethod("easypaisa")}
                  label="EasyPaisa"
                  sub="Mobile Wallet"
                  icon="account_balance_wallet"
                  iconColor="#22c55e"
                  iconFilled
                />
                <PaymentOption
                  id="jazzcash"
                  selected={paymentMethod === "jazzcash"}
                  onSelect={() => setPaymentMethod("jazzcash")}
                  label="JazzCash"
                  sub="Mobile Wallet"
                  icon="payments"
                  iconColor="#ef4444"
                  iconFilled
                />
                <PaymentOption
                  id="cod"
                  selected={paymentMethod === "cod"}
                  onSelect={() => setPaymentMethod("cod")}
                  label="Cash on Delivery"
                  sub="Pay at doorstep"
                  icon="handshake"
                  iconColor={undefined}
                />
              </div>

              {/* Credit card form — shown only when card selected */}
              {paymentMethod === "card" && (
                <div
                  className="mt-6 p-6 rounded-xl space-y-5"
                  style={{ background: "var(--color-surface-container-low)" }}
                >
                  {/* Card number */}
                  <div className="flex flex-col gap-1">
                    <label
                      className="text-[11px] tracking-widest font-medium"
                      style={{ color: "var(--color-on-surface-variant)", fontFamily: "var(--font-label-mono)" }}
                    >
                      CARD NUMBER
                    </label>
                    <div className="relative">
                      <input
                        value={form.cardNumber}
                        onChange={(e) => updateForm("cardNumber", e.target.value)}
                        className="w-full pl-4 pr-12 py-3 rounded-[10px] border outline-none transition-all"
                        style={{
                          borderColor: "var(--color-surface-variant)",
                          fontFamily: "var(--font-label-mono)",
                          letterSpacing: "0.08em",
                        }}
                        placeholder="0000  0000  0000  0000"
                        type="text"
                        maxLength={19}
                      />
                      <span
                        className="material-symbols-outlined absolute right-4 top-1/2 -translate-y-1/2"
                        style={{ color: "var(--color-on-surface-variant)", fontSize: 20 }}
                      >
                        lock
                      </span>
                    </div>
                  </div>
                  {/* Expiry + CVV */}
                  <div className="grid grid-cols-2 gap-5">
                    <div className="flex flex-col gap-1">
                      <label
                        className="text-[11px] tracking-widest font-medium"
                        style={{ color: "var(--color-on-surface-variant)", fontFamily: "var(--font-label-mono)" }}
                      >
                        EXPIRY DATE
                      </label>
                      <input
                        value={form.expiry}
                        onChange={(e) => updateForm("expiry", e.target.value)}
                        className="w-full px-4 py-3 rounded-[10px] border outline-none transition-all"
                        style={{
                          borderColor: "var(--color-surface-variant)",
                          fontFamily: "var(--font-label-mono)",
                        }}
                        placeholder="MM / YY"
                        type="text"
                        maxLength={7}
                      />
                    </div>
                    <div className="flex flex-col gap-1">
                      <label
                        className="text-[11px] tracking-widest font-medium"
                        style={{ color: "var(--color-on-surface-variant)", fontFamily: "var(--font-label-mono)" }}
                      >
                        CVV
                      </label>
                      <input
                        value={form.cvv}
                        onChange={(e) => updateForm("cvv", e.target.value)}
                        className="w-full px-4 py-3 rounded-[10px] border outline-none transition-all"
                        style={{
                          borderColor: "var(--color-surface-variant)",
                          fontFamily: "var(--font-label-mono)",
                        }}
                        placeholder="•••"
                        type="password"
                        maxLength={4}
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Mobile wallet instruction */}
              {(paymentMethod === "easypaisa" || paymentMethod === "jazzcash") && (
                <div
                  className="mt-6 p-5 rounded-xl flex items-start gap-4"
                  style={{ background: "var(--color-secondary-fixed)" }}
                >
                  <span
                    className="material-symbols-outlined mt-0.5"
                    style={{ color: "var(--color-secondary)", fontSize: 24 }}
                  >
                    info
                  </span>
                  <div>
                    <p
                      className="font-semibold text-sm mb-1"
                      style={{ color: "var(--color-primary)", fontFamily: "var(--font-body-sm)" }}
                    >
                      {paymentMethod === "easypaisa" ? "EasyPaisa" : "JazzCash"} Mobile Wallet
                    </p>
                    <p
                      className="text-sm"
                      style={{ color: "var(--color-on-surface-variant)", fontFamily: "var(--font-body-sm)" }}
                    >
                      After clicking &quot;Secure Checkout&quot; you will receive an OTP on your registered mobile number
                      to confirm this payment.
                    </p>
                  </div>
                </div>
              )}

              {/* COD note */}
              {paymentMethod === "cod" && (
                <div
                  className="mt-6 p-5 rounded-xl flex items-start gap-4"
                  style={{ background: "var(--color-surface-container)" }}
                >
                  <span
                    className="material-symbols-outlined mt-0.5"
                    style={{ color: "var(--color-on-surface-variant)", fontSize: 24 }}
                  >
                    handshake
                  </span>
                  <p
                    className="text-sm"
                    style={{ color: "var(--color-on-surface-variant)", fontFamily: "var(--font-body-sm)" }}
                  >
                    Pay in cash directly to the delivery rider. Please keep the exact amount ready. COD
                    orders may take an additional 24 hours to be dispatched.
                  </p>
                </div>
              )}
            </section>
          </div>

          {/* ── Right: Order Summary ──────────────────────────────────────── */}
          <aside className="lg:col-span-4 lg:sticky lg:top-24">
            <div
              className="rounded-2xl p-6 border"
              style={{
                background: "var(--color-surface-container-lowest)",
                borderColor: "var(--color-surface-variant)",
                boxShadow: "0 4px 12px rgba(26,26,46,0.05)",
              }}
            >
              <h3
                className="text-2xl font-semibold mb-6"
                style={{ color: "var(--color-primary)", fontFamily: "var(--font-headline-md)" }}
              >
                Order Summary
              </h3>

              {/* Items */}
              <div
                className="space-y-4 mb-6 pb-6 border-b"
                style={{ borderColor: "var(--color-surface-variant)" }}
              >
                {orderItems.length === 0 ? (
                  <p className="text-sm" style={{ color: "var(--color-on-surface-variant)" }}>
                    Your cart is empty.{" "}
                    <Link href="/products" className="underline" style={{ color: "var(--color-secondary)" }}>
                      Add products
                    </Link>
                  </p>
                ) : (
                  orderItems.map((item) => (
                  <div key={item.id} className="flex items-center gap-4">
                    <div
                      className="w-16 h-16 rounded-xl overflow-hidden flex-shrink-0"
                      style={{ background: "var(--color-surface-container)" }}
                    >
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={item.image} alt={item.name} className="w-full h-full object-cover" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p
                        className="font-bold text-sm truncate"
                        style={{ color: "var(--color-on-surface)", fontFamily: "var(--font-body-sm)" }}
                      >
                        {item.name}
                      </p>
                      <p
                        className="text-xs mt-0.5"
                        style={{ color: "var(--color-on-surface-variant)", fontFamily: "var(--font-body-sm)" }}
                      >
                        {item.variant}
                      </p>
                    </div>
                    <p
                      className="font-bold text-sm flex-shrink-0"
                      style={{ fontFamily: "var(--font-body-sm)" }}
                    >
                      Rs. {item.price.toLocaleString()}
                    </p>
                  </div>
                  ))
                )}
              </div>

              {/* Promo */}
              <div className="flex gap-2 mb-6">
                <input
                  className="flex-1 px-4 py-2.5 rounded-[10px] border text-sm outline-none transition-all"
                  style={{
                    borderColor: "var(--color-outline-variant)",
                    fontFamily: "var(--font-label-mono)",
                    letterSpacing: "0.06em",
                  }}
                  placeholder="FIRST10"
                  type="text"
                  defaultValue="FIRST10"
                />
                <button
                  className="px-4 py-2.5 rounded-[10px] text-sm font-bold cursor-pointer transition-all active:scale-95"
                  style={{
                    background: "var(--color-secondary-fixed)",
                    color: "var(--color-secondary)",
                    fontFamily: "var(--font-label-mono)",
                  }}
                >
                  APPLY
                </button>
              </div>

              {/* Price breakdown */}
              <div
                className="space-y-3 mb-6 text-sm"
                style={{ color: "var(--color-on-surface-variant)", fontFamily: "var(--font-body-sm)" }}
              >
                <div className="flex justify-between">
                  <span>Subtotal</span>
                  <span style={{ color: "var(--color-on-surface)" }}>Rs. {SUBTOTAL.toLocaleString()}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="flex items-center gap-1">
                    Shipping
                    <span
                      className="material-symbols-outlined cursor-help"
                      style={{ fontSize: 14, color: "var(--color-outline)" }}
                      title="Standard delivery in 2–4 business days"
                    >
                      info
                    </span>
                  </span>
                  <span style={{ color: "var(--color-on-surface)" }}>Rs. {SHIPPING}</span>
                </div>
                <div className="flex justify-between" style={{ color: "var(--color-on-tertiary-container)" }}>
                  <span>Discount (FIRST10)</span>
                  <span>− Rs. {DISCOUNT.toLocaleString()}</span>
                </div>
              </div>

              {/* Total */}
              <div
                className="flex justify-between items-center py-5 border-y mb-6"
                style={{ borderColor: "var(--color-surface-variant)" }}
              >
                <span
                  className="text-2xl font-bold"
                  style={{ color: "var(--color-primary)", fontFamily: "var(--font-headline-md)" }}
                >
                  Total
                </span>
                <span
                  className="text-2xl font-bold"
                  style={{ color: "var(--color-secondary)", fontFamily: "var(--font-headline-md)" }}
                >
                  Rs. {TOTAL.toLocaleString()}
                </span>
              </div>

              {/* Error message */}
              {errorMsg && (
                <div className="p-3 mb-4 text-xs font-semibold text-red-700 bg-red-50 border border-red-200 rounded-lg">
                  {errorMsg}
                </div>
              )}

              {/* CTA */}
              <button
                onClick={handleSecureCheckout}
                disabled={submitting || items.length === 0}
                className={`w-full py-4 rounded-2xl font-bold text-lg flex items-center justify-center gap-3 text-white shadow-lg hover:scale-[1.02] active:scale-95 transition-all cursor-pointer ${(submitting || items.length === 0) ? "opacity-50 cursor-not-allowed" : ""}`}
                style={{
                  background: "linear-gradient(135deg, #6C63FF 0%, #4D41DF 100%)",
                  boxShadow: "0 8px 20px rgba(108,99,255,0.28)",
                  fontFamily: "var(--font-body-lg)",
                }}
              >
                <span className="material-symbols-outlined" style={{ fontSize: 22, fontVariationSettings: "'FILL' 1" }}>
                  {submitting ? "hourglass_empty" : "lock_person"}
                </span>
                {submitting ? "Processing..." : "Secure Checkout"}
              </button>

              {/* SSL badge */}
              <p
                className="mt-4 text-xs text-center flex items-center justify-center gap-1"
                style={{ color: "var(--color-on-surface-variant)", fontFamily: "var(--font-body-sm)" }}
              >
                <span
                  className="material-symbols-outlined"
                  style={{ fontSize: 16, color: "#22c55e", fontVariationSettings: "'FILL' 1" }}
                >
                  verified
                </span>
                Bank-level 256-bit SSL encryption
              </p>
            </div>
          </aside>
        </div>
      </main>

      {/* ── Footer ──────────────────────────────────────────────────────── */}
      <footer className="mt-16" style={{ background: "var(--color-primary)", color: "var(--color-on-primary)" }}>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 py-16 px-4 md:px-10 max-w-[1280px] mx-auto">
          <div className="md:col-span-2">
            <span
              className="text-2xl font-bold block mb-4"
              style={{ fontFamily: "var(--font-headline-md)" }}
            >
              ShopEase
            </span>
            <p
              className="opacity-80 max-w-md text-sm leading-relaxed"
              style={{ color: "var(--color-on-primary-container)", fontFamily: "var(--font-body-sm)" }}
            >
              Premium e-commerce experience tailored for Pakistan. Offering curated selections across lifestyle,
              fashion, and technology with secure local payments.
            </p>
          </div>

          {[
            {
              title: "Company",
              links: ["About Us", "Terms of Service", "Privacy Policy"],
            },
            {
              title: "Help",
              links: ["Contact Support", "Track Order", "Returns"],
            },
          ].map(({ title, links }) => (
            <div key={title} className="flex flex-col gap-3">
              <h4
                className="font-bold mb-2"
                style={{ color: "var(--color-secondary-fixed-dim)" }}
              >
                {title}
              </h4>
              {links.map((l) => (
                <a
                  key={l}
                  href="#"
                  className="text-sm opacity-80 hover:opacity-100 transition-opacity"
                  style={{
                    color: "var(--color-on-primary-container)",
                    fontFamily: "var(--font-body-sm)",
                  }}
                >
                  {l}
                </a>
              ))}
            </div>
          ))}
        </div>
        <div
          className="border-t py-5 px-4 md:px-10 max-w-[1280px] mx-auto text-center opacity-60"
          style={{ borderColor: "rgba(255,255,255,0.1)" }}
        >
          <p className="text-sm" style={{ fontFamily: "var(--font-label-mono)" }}>
            © 2024 ShopEase Pakistan. All rights reserved.
          </p>
        </div>
      </footer>

      {/* ── Floating AI FAB with hover tooltip ──────────────────────────── */}
      <div className="fixed right-6 bottom-6 flex flex-col gap-4 z-50">
        <div
          className="relative"
          onMouseEnter={() => setAiTooltip(true)}
          onMouseLeave={() => setAiTooltip(false)}
        >
          {/* Tooltip */}
          {aiTooltip && (
            <div
              className="absolute bottom-full right-0 mb-4 w-64 rounded-2xl p-5 shadow-2xl border z-50"
              style={{
                background: "var(--color-surface-container-lowest)",
                borderColor: "var(--color-surface-variant)",
              }}
            >
              <p
                className="font-bold mb-1"
                style={{ color: "var(--color-on-surface)", fontFamily: "var(--font-body-sm)" }}
              >
                Need help, Ali?
              </p>
              <p
                className="text-sm mb-4"
                style={{ color: "var(--color-on-surface-variant)", fontFamily: "var(--font-body-sm)" }}
              >
                I can help with shipping rates or payment issues.
              </p>
              <button
                onClick={handleAskAI}
                className="w-full py-2 rounded-lg text-[11px] font-bold uppercase tracking-widest cursor-pointer transition-all hover:text-white"
                style={{
                  background: "var(--color-secondary-fixed)",
                  color: "var(--color-secondary)",
                  fontFamily: "var(--font-label-mono)",
                }}
                onMouseEnter={(e) => {
                  (e.target as HTMLButtonElement).style.background = "var(--color-secondary)";
                  (e.target as HTMLButtonElement).style.color = "white";
                }}
                onMouseLeave={(e) => {
                  (e.target as HTMLButtonElement).style.background = "var(--color-secondary-fixed)";
                  (e.target as HTMLButtonElement).style.color = "var(--color-secondary)";
                }}
              >
                START CHAT
              </button>
            </div>
          )}
          <AgentButton embedded />
        </div>
      </div>

      <AgentWidget />
    </div>
  );
}

// ─── Shared top nav ────────────────────────────────────────────────────────────
function CheckoutNav() {
  return (
    <nav
      className="sticky top-0 z-50 border-b shadow-sm"
      style={{
        background: "var(--color-surface)",
        borderColor: "var(--color-surface-variant)",
      }}
    >
      <div className="flex justify-between items-center h-20 px-4 md:px-10 max-w-[1280px] mx-auto">
        <div className="flex items-center gap-8">
          <Link
            href="/"
            className="text-2xl font-bold"
            style={{ color: "var(--color-primary)", fontFamily: "var(--font-headline-md)" }}
          >
            ShopEase
          </Link>
          <nav className="hidden md:flex items-center gap-10">
            {["Categories", "New Arrivals", "Deals"].map((l) => (
              <a
                key={l}
                href="#"
                className="text-base transition-colors hover:text-[var(--color-secondary)]"
                style={{ color: "var(--color-on-surface-variant)", fontFamily: "var(--font-body-md)" }}
              >
                {l}
              </a>
            ))}
          </nav>
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
    </nav>
  );
}

// ─── Reusable form field ───────────────────────────────────────────────────────
function FormField({
  label,
  value,
  onChange,
  placeholder,
  type,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  type: string;
}) {
  const [focused, setFocused] = useState(false);

  return (
    <div className="flex flex-col gap-1">
      <label
        className="text-[11px] tracking-widest font-medium"
        style={{ color: "var(--color-on-surface-variant)", fontFamily: "var(--font-label-mono)" }}
      >
        {label}
      </label>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        className="w-full px-4 py-3 rounded-[10px] border outline-none transition-all"
        style={{
          borderColor: focused ? "var(--color-secondary)" : "var(--color-surface-variant)",
          boxShadow: focused ? "0 0 0 3px rgba(77,65,223,0.12)" : "none",
          fontFamily: "var(--font-body-md)",
          color: "var(--color-on-surface)",
        }}
        placeholder={placeholder}
        type={type}
      />
    </div>
  );
}

// ─── Payment option radio card ─────────────────────────────────────────────────
function PaymentOption({
  id,
  selected,
  onSelect,
  label,
  sub,
  icon,
  iconColor,
  iconFilled,
}: {
  id: PaymentMethod;
  selected: boolean;
  onSelect: () => void;
  label: string;
  sub: string;
  icon: string;
  iconColor?: string;
  iconFilled?: boolean;
}) {
  return (
    <label
      className="flex items-center gap-4 p-5 rounded-xl border cursor-pointer transition-all"
      style={{
        borderColor: selected ? "var(--color-secondary)" : "var(--color-surface-variant)",
        background: selected ? "var(--color-secondary-fixed)" : "transparent",
      }}
    >
      <input
        type="radio"
        name="payment"
        checked={selected}
        onChange={onSelect}
        className="w-5 h-5 cursor-pointer accent-[var(--color-secondary)]"
      />
      <div className="flex flex-col flex-1">
        <span
          className="font-bold text-sm"
          style={{ color: "var(--color-on-surface)", fontFamily: "var(--font-body-sm)" }}
        >
          {label}
        </span>
        <span
          className="text-xs"
          style={{ color: "var(--color-on-surface-variant)", fontFamily: "var(--font-body-sm)" }}
        >
          {sub}
        </span>
      </div>
      <span
        className="material-symbols-outlined opacity-50"
        style={{
          fontSize: 24,
          color: iconColor ?? "var(--color-on-surface-variant)",
          fontVariationSettings: iconFilled ? "'FILL' 1" : "'FILL' 0",
        }}
      >
        {icon}
      </span>
    </label>
  );
}

// ─── Page export ───────────────────────────────────────────────────────────────
export default function CheckoutPage() {
  return (
    <AgentProvider>
      <CheckoutContent />
    </AgentProvider>
  );
}
