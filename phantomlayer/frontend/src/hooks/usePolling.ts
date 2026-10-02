import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

export interface UsePollingOptions {
  interval?: number;
  enabled?: boolean;
  immediate?: boolean;
}

export interface UsePollingResult<T> {
  data: T | null;
  error: Error | null;
  isLoading: boolean;
  isRefreshing: boolean;
  refresh: () => Promise<T | null>;
  stop: () => void;
  start: () => void;
}

export function usePolling<T>(
  fetcher: () => Promise<T>,
  options: UsePollingOptions = {},
): UsePollingResult<T> {
  const {
    interval = 15_000,
    enabled = true,
    immediate = true,
  } = options;

  const [data, setData] =
    useState<T | null>(null);

  const [error, setError] =
    useState<Error | null>(null);

  const [isLoading, setIsLoading] =
    useState(immediate);

  const [isRefreshing, setIsRefreshing] =
    useState(false);

  const [running, setRunning] =
    useState(enabled);

  const intervalRef =
    useRef<ReturnType<typeof setInterval> | null>(
      null,
    );

  const mountedRef =
    useRef(true);

  const fetcherRef =
    useRef(fetcher);

  /*
   * Keep the latest fetcher without
   * forcing the polling effect to restart
   * every time the parent renders.
   */
  useEffect(() => {
    fetcherRef.current = fetcher;
  }, [fetcher]);

  /*
   * Track component lifetime.
   */
  useEffect(() => {
    mountedRef.current = true;

    return () => {
      mountedRef.current = false;
    };
  }, []);

  /*
   * Execute one fetch.
   */
  const refresh = useCallback(
    async (): Promise<T | null> => {
      if (!mountedRef.current) {
        return null;
      }

      setError(null);
      setIsRefreshing(true);

      try {
        const result =
          await fetcherRef.current();

        if (mountedRef.current) {
          setData(result);
        }

        return result;
      } catch (err) {
        const normalizedError =
          err instanceof Error
            ? err
            : new Error(
                "Polling request failed.",
              );

        if (mountedRef.current) {
          setError(normalizedError);
        }

        return null;
      } finally {
        if (mountedRef.current) {
          setIsLoading(false);
          setIsRefreshing(false);
        }
      }
    },
    [],
  );

  /*
   * Stop polling.
   */
  const stop = useCallback(() => {
    if (intervalRef.current !== null) {
      clearInterval(
        intervalRef.current,
      );

      intervalRef.current = null;
    }

    setRunning(false);
  }, []);

  /*
   * Start polling.
   */
  const start = useCallback(() => {
    setRunning(true);
  }, []);

  /*
   * Start / stop the actual timer.
   */
  useEffect(() => {
    if (!running) {
      return;
    }

    if (!enabled) {
      return;
    }

    /*
     * Initial request.
     */
    if (immediate) {
      void refresh();
    }

    /*
     * Repeated requests.
     */
    intervalRef.current =
      setInterval(() => {
        void refresh();
      }, interval);

    return () => {
      if (intervalRef.current !== null) {
        clearInterval(
          intervalRef.current,
        );

        intervalRef.current = null;
      }
    };
  }, [
    enabled,
    immediate,
    interval,
    refresh,
    running,
  ]);

  return {
    data,
    error,
    isLoading,
    isRefreshing,
    refresh,
    stop,
    start,
  };
}