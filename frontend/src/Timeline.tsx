import { useEffect, useMemo, useState } from "react";

interface Metadata {
    start_date: string;
    end_date: string;
    interval_minutes: number;
    unit: string;
}

function Timeline() {
    const [meta, setMetadata] = useState<Metadata>();
    const [loading, setLoading] = useState(true);

    useEffect(() => {
    const fetchMetadata = async () => {
      try {
        const response = await fetch("/api/Data/metadata");
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data: Metadata = await response.json();
        setMetadata(data);
      } catch (error) {
        console.error("Error fetching users:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchMetadata();
    }, []);

    const start = useMemo(() => {
        return meta ? new Date(meta.start_date) : null;
    }, [meta]);

    const end = useMemo(() => {
        return meta ? new Date(meta.end_date) : null;
    }, [meta]);

    const totalMinutes = useMemo(() => {
        if (!start || !end) return 0;
        return Math.floor((end.getTime() - start.getTime()) / 60000);
    }, [start, end]);
    
    const [currentMinute, setCurrentMinute] = useState(0);

    useEffect(() => {
        if (start && end) {
            const now = Date.now();
            const diffMinutes = Math.floor((now - start.getTime()) / 60000);
            // Clamp between 0 and totalMinutes
            const clamped = Math.max(0, Math.min(diffMinutes, totalMinutes));
            setCurrentMinute(clamped);
        }
    }, [start, end, totalMinutes]);

    // Compute current date/time based on slider position
    const currentTime = useMemo(() => {
        if (!start) return null;
        const newTime = new Date(start);
        newTime.setMinutes(start.getMinutes() + currentMinute);
        return newTime;
    }, [currentMinute, start]);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setCurrentMinute(parseInt(e.target.value, 10));
    };

    return (
        <div className="p-4 max-w-md mx-auto text-center">
            <h2 className="text-lg font-semibold mb-2">Timeline Slider</h2>

            <input
                type="range"
                min={0}
                max={totalMinutes}
                step={1} // snap to 1-minute increments
                value={currentMinute}
                onChange={handleChange}
                className="w-full"
            />

            <p className="mt-2 font-mono">
                {currentTime?.toLocaleString("en-US", { timeZone: "UTC" })}
            </p>
        </div>
    );
}

export default Timeline;