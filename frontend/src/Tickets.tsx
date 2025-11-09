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

export default function Tickets() {
  const { currentTime } = useTimeline();
  const { cauldrons, cauldronData, marketData, loading } = useCauldrons();
  const [ticketInfo, setTicketInfo] = useState<TicketsPackage | null>(null);
  const [witchInfo, setWitchInfo] = useState<WitchData[]>([]);
  const [ticketDates, setTicketDates] = useState<Date[]>([]);
  const [myloading, setLoading] = useState(true);

  // --- Fetch data once on mount ---
  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [ticketRes, witchRes] = await Promise.all([
          fetch("/api/Tickets"),
          fetch("/api/Information/couriers"),
        ]);

        if (!ticketRes.ok || !witchRes.ok) {
          throw new Error("Failed to fetch data");
        }

        const ticketData = (await ticketRes.json()) as TicketsPackage;
        const witchData = (await witchRes.json()) as WitchData[];

        setTicketInfo(ticketData);
        setWitchInfo(witchData);
        setTicketDates(ticketData.transport_tickets.map(t => new Date(t.date)));
      } catch (err) {
        console.error("Error loading ticket data:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchAll();
  }, []);

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
      {ticketInfo.transport_tickets.map((t, i) => {
        const date = ticketDates[i];
        const isVisible = currentTime && date <= currentTime;
        return (
            <div>
                {isVisible && (
                    <p key={t.ticket_id}>
            {witchInfo.find(s => s.courier_id == t.courier_id)?.name} delivered {t.amount_collected} liters from {cauldrons.find(c => c.id == t.cauldron_id)?.name} on {t.date}
          </p>
                )}
            </div>
          
        );
      })}
    </div>
  );
}