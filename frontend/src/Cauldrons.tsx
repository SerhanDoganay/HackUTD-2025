import { useEffect, useMemo, useState } from "react";
import { useCauldrons, LEFTMOST, UPMOST } from "./CauldronContext";
import { useTimeline } from "./TimelineContext";

function Cauldron({ id }) {
    const { cauldrons, cauldronData, marketData, loading } = useCauldrons();
    const { currentTime } = useTimeline();
    
    const formattedTime = currentTime?.toISOString().replace(/\.\d{3}Z$/, '+00:00');
    const inst = cauldronData.find(c => c.timestamp == formattedTime);
    const myStat = inst?.cauldron_levels[id as keyof CauldronLevels];

    const myInfo = cauldrons.find(c => c.id == id);

    const percentFull = myStat / myInfo?.max_volume;

    const [visible, setVisible] = useState(false);

    const scale = 200000;
    const xOff = (myInfo?.longitude - LEFTMOST) * scale;
    const yOff = (myInfo?.latitude - UPMOST) * scale;

    const positionInfo = {
        position: 'absolute',
        left: `${xOff}px`,
        top: `${yOff}px`
    };

    return (
        <div style={positionInfo}>
            <p>{myInfo?.name}</p>
            <img 
            onMouseEnter={() => setVisible(true)}
            onMouseLeave={() => setVisible(false)}
            src={'/cauldron' + String(Math.ceil(percentFull * 100)).padStart(4, '0') + '.png'} width="60"></img>

            {visible && (
                <div className="absolute left-full top-1/2 ml-2 -translate-y-1/2 
                        px-2 py-1 bg-gray-800 text-white text-sm rounded shadow-md">
                    {myStat} / {myInfo?.max_volume} liters ({String(Math.ceil(percentFull * 100))}% full)
                </div>
            )}
        </div>
    );
}

function Cauldrons() {
    const { cauldrons, cauldronData, loading } = useCauldrons();
    const numCauldrons = cauldrons.length;
    var i = 0;
    return (
        <div>
            {cauldrons.map(cauldron => (
                <Cauldron id={cauldron.id} />
            ))}
        </div>
    );
}

export default Cauldrons;