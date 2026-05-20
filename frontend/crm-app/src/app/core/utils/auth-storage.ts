const AUTH_TOKEN_KEY = 'access_token';
const CURRENT_SHOP_KEY = 'current_shop_id';

type BrowserStorageName = 'localStorage' | 'sessionStorage';

const memoryStorage = new Map<string, string>();

function getBrowserStorage(name: BrowserStorageName): Storage | null {
  if (typeof window === 'undefined') {
    return null;
  }

  try {
    return window[name];
  } catch {
    return null;
  }
}

function readFrom(storage: Storage | null, key: string): string | null {
  if (!storage) {
    return null;
  }

  try {
    return storage.getItem(key);
  } catch {
    return null;
  }
}

function writeTo(storage: Storage | null, key: string, value: string): boolean {
  if (!storage) {
    return false;
  }

  try {
    storage.setItem(key, value);
    return true;
  } catch {
    return false;
  }
}

function removeFrom(storage: Storage | null, key: string): void {
  if (!storage) {
    return;
  }

  try {
    storage.removeItem(key);
  } catch {
    // Ignore unavailable browser storage. Auth cleanup still happens in memory.
  }
}

function getAuthItem(key: string): string | null {
  return (
    readFrom(getBrowserStorage('localStorage'), key) ||
    readFrom(getBrowserStorage('sessionStorage'), key) ||
    memoryStorage.get(key) ||
    null
  );
}

function setAuthItem(key: string, value: string): void {
  if (writeTo(getBrowserStorage('localStorage'), key, value)) {
    memoryStorage.set(key, value);
    return;
  }

  if (writeTo(getBrowserStorage('sessionStorage'), key, value)) {
    memoryStorage.set(key, value);
    return;
  }

  memoryStorage.set(key, value);
}

function removeAuthItem(key: string): void {
  removeFrom(getBrowserStorage('localStorage'), key);
  removeFrom(getBrowserStorage('sessionStorage'), key);
  memoryStorage.delete(key);
}

export function setSafeSessionItem(key: string, value: string): void {
  if (writeTo(getBrowserStorage('sessionStorage'), key, value)) {
    return;
  }

  memoryStorage.set(`session:${key}`, value);
}

export const authStorage = {
  getToken(): string | null {
    return getAuthItem(AUTH_TOKEN_KEY);
  },

  setToken(token: string): void {
    setAuthItem(AUTH_TOKEN_KEY, token);
  },

  getCurrentShopId(): string | null {
    return getAuthItem(CURRENT_SHOP_KEY);
  },

  setCurrentShopId(shopId: string | number): void {
    setAuthItem(CURRENT_SHOP_KEY, String(shopId));
  },

  clearAuth(): void {
    removeAuthItem(AUTH_TOKEN_KEY);
    removeAuthItem(CURRENT_SHOP_KEY);
  },
};
