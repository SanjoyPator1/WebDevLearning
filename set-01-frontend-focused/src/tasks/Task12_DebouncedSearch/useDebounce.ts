import { useEffect, useState } from "react";

/**
 * Custom hook to debounce a value.
 *
 * @template T - Generic type parameter representing the type of the value being debounced.
 * @param value - The input value that needs to be debounced.
 * @param delay - The debounce delay in milliseconds.
 * @returns The debounced value of the same type as the input.
 *
 * Example usage:
 * const debouncedSearch = useDebounce(searchInput, 500);
 */
const useDebounce = <T>(value: T, delay: number): T => {
  const [debounced, setDebounced] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebounced(value);
    }, 500);

    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]);

  return debounced;
};

export default useDebounce;
