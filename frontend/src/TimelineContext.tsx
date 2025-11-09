import { createContext, useContext, useEffect, useMemo, useState, ReactNode } from "react";

interface Metadata {
  start_date: string;
  end_date: string;
  interval_minutes: number;
  unit: string;
}

interface TimelineContextValue {
  meta?: Metadata;
  loading: boolean;
  currentMinute: number;
  setCurrentMinute: (minute: number) => void;
  currentTime: Date | null;
  totalMinutes: number;
}

const TimelineContext = createContext<TimelineContextValue | undefined>(undefined);

export const TimelineProvider = ({ children }: { children: ReactNode }) => {
  const [meta, setMetadata] = useState<Metadata>();
  const [loading, setLoading] = useState(true);
  const [currentMinute, setCurrentMinute] = useState(0);

  useEffect(() => {
    const fetchMetadata = async () => {
      try {
        const response = await fetch("/api/Data/metadata");
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data: Metadata = await response.json();
        setMetadata(data);
      } catch (error) {
        console.error("Error fetching metadata:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchMetadata();
  }, []);

  const start = useMemo(() => (meta ? new Date(meta.start_date) : null), [meta]);
  const end = useMemo(() => (meta ? new Date(meta.end_date) : null), [meta]);

  const totalMinutes = useMemo(() => {
    if (!start || !end) return 0;
    return Math.floor((end.getTime() - start.getTime()) / 60000);
  }, [start, end]);

  // Initialize currentMinute to "now"
  const [initialized, setInitialized] = useState(false);

useEffect(() => {
  if (start && end && currentMinute === 0) {
    const now = Date.now();
    const diffMinutes = Math.floor((now - start.getTime()) / 60000);
    const clamped = Math.max(0, Math.min(diffMinutes, totalMinutes));
    setCurrentMinute(clamped);
  }
}, [start, end, totalMinutes]);

  const currentTime = useMemo(() => (
  start ? new Date(start.getTime() + currentMinute * 60000) : null
), [currentMinute, start]);

  return (
    <TimelineContext.Provider
      value={{
        meta,
        loading,
        currentMinute,
        setCurrentMinute,
        currentTime,
        totalMinutes,
      }}
    >
      {children}
    </TimelineContext.Provider>
  );
};

export const useTimeline = () => {
  const ctx = useContext(TimelineContext);
  if (!ctx) throw new Error("useTimeline must be used inside TimelineProvider");
  return ctx;
};