import { useEffect, useMemo, useState } from "react";
import { useCauldrons, LEFTMOST, UPMOST } from "./CauldronContext";

function Market() {
    const { cauldrons, cauldronData, marketData, loading } = useCauldrons();

    const scale = 100000;
    const xPad = 0;
    var xOff = -1;
    var yOff = -1;
    var positionInfo = {};

    if (!loading)
    {
        xOff = (marketData.longitude - LEFTMOST) * scale + xPad;
        yOff = (marketData.latitude - UPMOST) * scale;
        positionInfo = {
            position: 'absolute',
            left: `${xOff}px`,
            top: `${yOff}px`
        };
    }

    return  (
        <div>
            {!loading && (
            <div style={positionInfo}>
            <p>{marketData.name}</p>
            <img src='/market.png' width="80"></img>
            </div>
            )}
        </div>
    )
}

export default Market;