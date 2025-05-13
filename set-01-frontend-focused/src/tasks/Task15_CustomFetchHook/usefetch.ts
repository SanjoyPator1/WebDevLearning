import { useEffect, useState } from "react";

export type FetchModeType = "success" | "error";

type FetchOptions = {
  url: string
  timeout?: number;
};

type FetchState<T> = {
  data: T | null;
  loading: boolean;
  error?: string;
  success: boolean;
};

const useFetch = <T=unknown>({
  url,
  timeout=0
}: FetchOptions): FetchState<T> => {
  const [state, setState] = useState<FetchState<T>>({
    data: null,
    loading: false,
    success: false,
  });

  useEffect(() => {
    // Variable to track if the component is mounted.
    let isMounted = true;

    // Create an AbortController instance to manage fetch cancellation.
    const controller = new AbortController();
    
    // `signal` is used to listen to abort events for the fetch request.
    const signal = controller.signal;

    const fetchData = async () => {
      setState({ data: null, loading: true, success: false });

      try {
        // Simulate network delay if timeout is provided
        if (timeout > 0) {
          await new Promise((resolve) => setTimeout(resolve, timeout));
        }

        // Perform the fetch request, passing the signal to allow cancellation
        const response = await fetch(url, { signal });

        // Check if the response is successful, otherwise throw an error
        if (!response.ok) {
          throw new Error(`Error fetching API with status code ${response.status}`);
        }

        // Parse the response as JSON
        const result = await response.json() as T;

        // Ensure the component is still mounted before updating the state
        if (isMounted) {
          setState({ data: result, loading: false, success: true });
        }
      } catch (err) {
        const error = err as Error;

        // Handle fetch errors, including aborted requests
        if (isMounted) {
          setState({
            data: null,
            loading: false,
            success: false,
            error: error.name === "AbortError" ? "Request was cancelled!" : error.message,
          });
        }
      }
    };

    // Call the fetchData function to initiate the API call
    fetchData();

    // Cleanup function to abort the fetch if the component unmounts
    return () => {
      // Mark the component as unmounted
      isMounted = false;

      // Abort the ongoing fetch request using the AbortController
      controller.abort();
    };
  }, [url, timeout]); // Dependencies: url and timeout

  // Return the current state of the request (data, loading, error, success)
  return state;
};

export default useFetch;
