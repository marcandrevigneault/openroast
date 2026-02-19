/**
 * Toast notification store — provides a global notification queue
 * for errors, warnings, and info messages.
 */

export type ToastType = "error" | "warning" | "info";

export interface Toast {
  id: number;
  message: string;
  type: ToastType;
  machineLabel?: string;
}

let nextId = 1;
let listeners: Array<() => void> = [];
let toasts: Toast[] = [];

function notify() {
  for (const fn of listeners) fn();
}

export function getToasts(): Toast[] {
  return toasts;
}

export function subscribe(fn: () => void): () => void {
  listeners.push(fn);
  return () => {
    listeners = listeners.filter((l) => l !== fn);
  };
}

export function addToast(
  message: string,
  type: ToastType = "error",
  machineLabel?: string,
): number {
  const id = nextId++;
  toasts = [...toasts, { id, message, type, machineLabel }];
  notify();

  // Auto-dismiss after 6 seconds
  setTimeout(() => {
    dismissToast(id);
  }, 6000);

  return id;
}

export function dismissToast(id: number): void {
  toasts = toasts.filter((t) => t.id !== id);
  notify();
}

export function clearToasts(): void {
  toasts = [];
  notify();
}
