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

    const scale = 100000;
    const xPad = 150;
    const xOff = (myInfo?.longitude - LEFTMOST) * scale + xPad;
    const yOff = ((myInfo?.latitude - UPMOST) * scale) - 20;

    const positionInfo = {
        position: 'absolute',
        left: `${xOff}px`,
        top: `${yOff}px`
    };

    return (
        <div style={positionInfo}>
            <p style={{
                color: 'white',
                textShadow: '-1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000',
                fontWeight: 'bold'
            }}>{myInfo?.name}</p>
            <img 
            onMouseEnter={() => setVisible(true)}
            onMouseLeave={() => setVisible(false)}
            src={'/cauldron' + String(Math.ceil(percentFull * 100)).padStart(4, '0') + '.png'} width="40"></img>

            {visible && (
                <div className="absolute left-full top-1/2 ml-2 -translate-y-1/2 
                        px-2 py-1 bg-gray-800 text-white text-sm rounded shadow-md cpopup">
                    {myStat} / {myInfo?.max_volume} liters ({String(Math.ceil(percentFull * 100))}% full)
                </div>
            )}
        </div>
    );
}

function Cauldrons() {
    const { cauldrons, cauldronData, loading } = useCauldrons();
    const { meta } = useTimeline();
    const numCauldrons = cauldrons.length;
    var i = 0;
    
    const formatDate = (dateString: string) => {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
        });
    };
    
    return (
        <div>
            {meta && (
                <h2 style={{ 
                    position: 'fixed',
                    top: '20px',
                    left: '50%',
                    transform: 'translateX(-50%)',
                    margin: 0,
                    zIndex: 1000,
                    pointerEvents: 'none'
                }}>
                    Cauldron Levels from {formatDate(meta.start_date)} to {formatDate(meta.end_date)}
                </h2>
            )}
            {cauldrons.map(cauldron => (
                <Cauldron key={cauldron.id} id={cauldron.id} />
            ))}
        </div>
    );
}

export default Cauldrons;