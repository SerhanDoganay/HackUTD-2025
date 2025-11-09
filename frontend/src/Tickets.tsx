import { useEffect, useState } from "react";
import { useTimeline } from "./TimelineContext";
import { useCauldrons, LEFTMOST, UPMOST } from "./CauldronContext";

interface TDateRange {
  start: string;
  end: string;
}

interface TicketData {
  ticket_id: string;
  cauldron_id: string;
  amount_collected: number;
  courier_id: string;
  date: string;
}

interface TMetadata {
  total_tickets: number;
  suspicious_tickets: number;
  date_range: TDateRange;
}

interface TicketsPackage {
  metadata: TMetadata;
  transport_tickets: TicketData[];
}

interface WitchData {
  courier_id: string;
  name: string;
  max_carrying_capacity: number;
}

interface FlagData {
  ticket_id: string;
  cauldron_id: string;
  amount_collected: number;
  courier_id: string;
  date: string;
}

interface DrainData {
  cauldron_id: string;
  start_time: string;
  total_drain: number;
}

interface TicketEntry {
  ticket_id: string;
  cauldron_id: string;
  amount_collected: number;
  courier_id: string;
  date: string;
}

interface EventEntry {
  cauldron_id: string;
  start_time: string;
  total_drain: number;
}

interface PairData {
  ticket: TicketEntry;
  event: EventEntry;
}

interface ApiData {
  date: string;
  total_discrepancy_L: number;
  flagged_tickets_count: number;
  unlogged_drains_count: number;
  flagged_tickets: FlagData[];
  unlogged_drains: DrainData[];
  reconciled_pairs: PairData[];
}

export default function Tickets() {
  const { meta, currentTime } = useTimeline();
  const { cauldrons, cauldronData, marketData, loading } = useCauldrons();
  const [ticketInfo, setTicketInfo] = useState<TicketsPackage | null>(null);
  const [witchInfo, setWitchInfo] = useState<WitchData[]>([]);
  const [ticketDates, setTicketDates] = useState<Date[]>([]);
  const [analysis, setAnalysis] = useState<ApiData[]>([]);
  const [myloading, setLoading] = useState(true);
  const [dateList, setDateList] = useState<string[]>([]);

  useEffect(() => {
    const dates: string[] = [];
  const current = new Date(meta?.start_date);
  const end = new Date(meta?.end_date)
  while(current <= end) {
    const isoDate = current.toISOString().split("T")[0];
    dates.push(isoDate);
    current.setUTCDate(current.getUTCDate() + 1);
  }
  setDateList(dates);
  }, [meta]);

  // --- Fetch data once on mount ---
  useEffect(() => {
    const fetchAll = async () => {
        const postData = {
            days: dateList
        };
        const reqOptions = {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(postData)
        };
      try {
        const [ticketRes, witchRes, analysisRes] = await Promise.all([
          fetch("/api/Tickets"),
          fetch("/api/Information/couriers"),
          fetch("http://localhost:8000/query_days", reqOptions)
        ]);

        if (!ticketRes.ok || !witchRes.ok || !analysisRes.ok) {
          throw new Error("Failed to fetch data");
        }

        const ticketData = (await ticketRes.json()) as TicketsPackage;
        const witchData = (await witchRes.json()) as WitchData[];
        const analysisData = (await analysisRes.json()) as ApiData[];

        setTicketInfo(ticketData);
        setWitchInfo(witchData);
        setAnalysis(analysisData);
        setTicketDates(ticketData.transport_tickets.map(t => new Date(t.date)));
      } catch (err) {
        console.error("Error loading ticket data:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchAll();
  }, [meta]);

  // --- Early return while loading ---
  if (myloading) {
    return <p>Loading tickets...</p>;
  }

  // --- Early return if no data ---
  if (!ticketInfo) {
    return <p>No ticket data available.</p>;
  }

  // --- Render ---
  return (
    <div>
      <h3>Tickets: (Red Tickets are Inaccurate)</h3>
      {ticketInfo.transport_tickets.map((t, i) => {
        const date = ticketDates[i];
        const isVisible = currentTime && date <= currentTime && analysis;
        return (
            <div>
                {isVisible && (
                    <p key={t.ticket_id} style={{ color: analysis.find(d => d.flagged_tickets.find(q => q.ticket_id == t.ticket_id)) ? 'red' : 'black' }}>
                      {witchInfo.find(s => s.courier_id == t.courier_id)?.name} delivered {t.amount_collected} liters from {cauldrons.find(c => c.id == t.cauldron_id)?.name} on {analysis.find(d => d.reconciled_pairs.find(p => p.ticket.ticket_id == t.ticket_id))?.reconciled_pairs.find(p => p.ticket.ticket_id == t.ticket_id)?.event.start_time} {t.date}
                    </p>
                )}
            </div>
          
        );
      })}
    </div>
  );
}