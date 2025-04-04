class StorageService {
    private prefix: string;
    
    constructor(prefix: string = 'showtrackr_') {
      this.prefix = prefix;
    }
    
    /**
     * Store a value in localStorage with the app's prefix
     */
    public setItem(key: string, value: string): void {
      localStorage.setItem(this.prefix + key, value);
    }
    
    /**
     * Retrieve a value from localStorage using the app's prefix
     */
    public getItem(key: string): string | null {
      return localStorage.getItem(this.prefix + key);
    }
    
    /**
     * Remove a value from localStorage using the app's prefix
     */
    public removeItem(key: string): void {
      localStorage.removeItem(this.prefix + key);
    }
    
    /**
     * Clear all app-related items from localStorage
     */
    public clear(): void {
      Object.keys(localStorage)
        .filter(key => key.startsWith(this.prefix))
        .forEach(key => localStorage.removeItem(key));
    }
    
    /**
     * Store a complex object in localStorage (serialized as JSON)
     */
    public setObject<T>(key: string, value: T): void {
      this.setItem(key, JSON.stringify(value));
    }
    
    /**
     * Retrieve and parse a JSON object from localStorage
     */
    public getObject<T>(key: string): T | null {
      const value = this.getItem(key);
      if (value) {
        try {
          return JSON.parse(value) as T;
        } catch (e) {
          console.error(`Error parsing stored JSON for key ${key}:`, e);
          return null;
        }
      }
      return null;
    }
  }
  
  // Create and export a singleton instance
  export const storageService = new StorageService();