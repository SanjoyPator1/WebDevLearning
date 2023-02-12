import "./styles.css";
import M1SVG from "./components/01-SVG";
import M2 from "./components/02-API";
import M3 from "./components/03-Specifications";
import M4 from "./components/04-GroupElements";
import M5 from "./components/05-DOMManipulation";
import M6 from "./components/06-Transitions";
import M7 from "./components/07-PositioningFunction";
import M8 from "./components/08-D3-HTML";

export default function App() {
  return (
    <div className="App">
      <h1>Basic of D3</h1>
      <h6>This project contains 8 module with different learning items</h6>
      <hr />
      <M1SVG />
      <M2 />
      <M3 />
      <M4 />
      <M5 />
      <M6 />
      <M7 />
      <M8 />
    </div>
  );
}
