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
      <div className="topnav">
        <Timeline />
      </div>
      <div className="container">
        <div className="div1">
          <Tickets />
        </div>
        <div className="div2">
          <Cauldrons />
          <Market />
        </div>
      </div>
      </CauldronProvider>
      </TimelineProvider>
    </div>
  );
}

export default App;