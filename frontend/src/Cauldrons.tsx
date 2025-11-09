import { useEffect, useMemo, useState } from "react";

interface CauldronInfo {
    max_volume: number;
    id: string;
    name: string;
    latitude: number;
    longitude: number;
}

interface CauldronLevels {
    cauldron_001: number;
    cauldron_002: number;
    cauldron_003: number;
    cauldron_004: number;
    cauldron_005: number;
    cauldron_006: number;
    cauldron_007: number;
    cauldron_008: number;
    cauldron_009: number;
    cauldron_010: number;
    cauldron_011: number;
    cauldron_012: number;
}

interface CauldronInstant {
    timestamp: string;
    cauldron_levels: CauldronLevels;
}

function Cauldron({ id }) {
    console.log(id);
    const percentFull = 0.5;

    return (
        <img src={'/cauldron' + String(Math.ceil(percentFull * 100)).padStart(4, '0') + '.png'} width="100"></img>
    );
}

function Cauldrons() {
    const [cauldrons, setCauldrons] = useState<CauldronInfo[]>([]);
    const [cauldronData, setCauldronData] = useState<CauldronInstant[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
      const fetchCauldrons = async () => {
        try {
          const response = await fetch("/api/Information/cauldrons");
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }
          const data: CauldronInfo[] = await response.json();
          setCauldrons(data);
        } catch (error) {
          console.error("Error fetching users:", error);
        } finally {
          setLoading(false);
        }
      };

      fetchCauldrons();
    }, []); 

    useEffect(() => {
      const fetchCauldronData = async () => {
        try {
          const response = await fetch("/api/Data");
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }
          const data: CauldronInstant[] = await response.json();
          setCauldronData(data);
        } catch (error) {
          console.error("Error fetching users:", error);
        } finally {
          setLoading(false);
        }
      };

      fetchCauldronData();
    }, []); 

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