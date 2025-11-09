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
  const [speed, setSpeed] = useState(1); // 1 = 1x, 2 = 2x

  useEffect(() => {
    if (isPaused || currentMinute >= totalMinutes)
      return;
    setTimeout(() => {
      setCurrentMinute(currentMinute + speed);
    }, 1);
  });

  return (
    <div>
      <h2 style={{ fontSize: '22px', marginLeft: '20px', marginTop: '20px', marginBottom: '5px', fontWeight: '600' }}>Timeline Slider</h2>
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
      <button onClick={() => setSpeed(speed === 1 ? 2 : 1)} style={{ marginLeft: '10px' }}>
        {speed}x Speed
      </button>
      <p className="font-mono" style={{ marginTop: '-10px', marginLeft: '20px', marginBottom: 0 }}>
        {currentTime?.toLocaleString("en-US", { timeZone: "UTC" })}
      </p>
    </div>
  );
}