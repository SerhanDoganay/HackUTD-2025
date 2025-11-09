import { createContext, useContext, useState, useEffect, ReactNode } from "react";

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

interface MarketInfo {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  description: string;
}

interface CauldronContextValue {
  cauldrons: CauldronInfo[];
  cauldronData: CauldronInstant[];
  marketData: MarketInfo;
  loading: boolean;
}

export var LEFTMOST = 1000; // longitude
export var UPMOST = 1000; // latitude
var foundExtremes = false;

const CauldronContext = createContext<CauldronContextValue | undefined>(undefined);

export const CauldronProvider = ({ children }: { children: ReactNode }) => {
  const [cauldrons, setCauldrons] = useState<CauldronInfo[]>([]);
  const [cauldronData, setCauldronData] = useState<CauldronInstant[]>([]);
  const [marketData, setMarketData] = useState<MarketInfo>();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAll = async () => {
      const [cauldronsRes, dataRes, marketRes] = await Promise.all([
        fetch("/api/Information/cauldrons"),
        fetch("/api/Data"),
        fetch("/api/Information/market"),
      ]);
      const cauldrons = await cauldronsRes.json();
      const cauldronData = await dataRes.json();
      const marketData = await marketRes.json();
      setCauldrons(cauldrons);
      setCauldronData(cauldronData);
      setMarketData(marketData);
      setLoading(false);
    };
    fetchAll();
  }, []);

  if (!foundExtremes)
  {
    for (let i = 0; i < cauldrons.length; i++)
    {
      if (cauldrons[i].longitude < LEFTMOST)
        LEFTMOST = cauldrons[i].longitude;
      if (cauldrons[i].latitude < UPMOST)
        UPMOST = cauldrons[i].latitude;
    }
    if (marketData)
    {
      if (marketData?.longitude < LEFTMOST)
      LEFTMOST = marketData?.longitude;
    if (marketData?.latitude < UPMOST)
      UPMOST = marketData?.latitude;
    console.log("LEFTMOST: " + LEFTMOST);
    console.log("UPMOST: " + UPMOST);
    if (UPMOST != 1000)
      foundExtremes = true;
    }
  }

  return (
    <CauldronContext.Provider value={{ cauldrons, cauldronData, marketData, loading }}>
      {children}
    </CauldronContext.Provider>
  );
};

export const useCauldrons = () => {
  const ctx = useContext(CauldronContext);
  if (!ctx) throw new Error("useCauldrons must be used inside CauldronProvider");
  return ctx;
};