"use client";

import { useCallback, useState } from "react";

export type ToastType = "success" | "error" | "info";
export type ToastData = { id: string; type: ToastType; message: string };

const bgMap: Record<ToastType, string> = {
  success: "bg-emerald-600",
  error: "bg-red-600",
  info: "bg-blue-700",
};

export function Toast({ type, message, onClose }: { type: ToastType; message: string; onClose: () => void }) {
  return (
    <div className={`toast-enter flex items-center gap-3 rounded-2xl ${bgMap[type]} px-5 py-3 text-sm text-white shadow-lg`}>
      <span className="flex-1">{message}</span>
      <button type="button" onClick={onClose} className="flex-shrink-0 rounded-full p-1 opacity-70 hover:opacity-100">✕</button>
    </div>
  );
}

export function ToastManager({ toasts, onDismiss }: { toasts: ToastData[]; onDismiss: (id: string) => void }) {
  return (
    <div className="fixed right-6 top-6 z-50 flex flex-col gap-2">
      {toasts.map((t) => <Toast key={t.id} type={t.type} message={t.message} onClose={() => onDismiss(t.id)} />)}
    </div>
  );
}

export function useToast() {
  const [toasts, setToasts] = useState<ToastData[]>([]);
  const addToast = useCallback((type: ToastType, message: string, duration = 3000) => {
    const id = `t-${Math.random().toString(36).slice(2, 8)}`;
    setToasts((prev) => [...prev, { id, type, message }]);
    if (duration > 0) setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), duration);
  }, []);
  const dismissToast = useCallback((id: string) => setToasts((prev) => prev.filter((t) => t.id !== id)), []);
  return { toasts, addToast, dismissToast };
}
