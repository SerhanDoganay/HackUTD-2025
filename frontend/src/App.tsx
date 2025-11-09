import { CauldronProvider } from "./CauldronContext";
import { TimelineProvider } from "./TimelineContext";
import Cauldrons from './Cauldrons';
import Market from './Market';
import Timeline from './Timeline';
import Tickets from './Tickets';

function App() {
  return (
    <div>
      <TimelineProvider>
      <CauldronProvider>
        <Timeline />
        <Cauldrons />
        <Market />
        <Tickets />
      </CauldronProvider>
      </TimelineProvider>
    </div>
  );
}

export default App;