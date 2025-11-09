import { useEffect, useState } from "react";
import { useTimeline } from "./TimelineContext";

export default function Timeline() {
  const {
    loading,
    totalMinutes,
    currentMinute,
    setCurrentMinute,
    currentTime,
  } = useTimeline();

  if (loading) return <p>Loading timeline...</p>;

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setCurrentMinute(parseInt(e.target.value, 10));
  };

  const [isPaused, setPaused] = useState(false);

  useEffect(() => {
    if (isPaused)
      return;
    setTimeout(() => {
      setCurrentMinute(currentMinute + 1);
    }, 1);
  });

  return (
    <div>
      <h2 className="text-lg font-semibold mb-2">Timeline Slider</h2>
      <input
        type="range"
        min={0}
        max={totalMinutes}
        step={1}
        value={currentMinute}
        onChange={handleChange}
        className="myslider"
      />
      <button onClick={() => setPaused(!isPaused)}>
        {isPaused ? "Play" : "Pause"}
      </button>
      <p className="mt-2 font-mono">
        {currentTime?.toLocaleString("en-US", { timeZone: "UTC" })}
      </p>
    </div>
  );
}