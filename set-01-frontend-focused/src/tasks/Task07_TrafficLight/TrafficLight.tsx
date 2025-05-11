import { useCallback, useEffect, useState } from "react";

type TrafficLightModeType = "red" | "yellow" | "green";

interface LightProps {
  lightMode: TrafficLightModeType;
  lightOn: "on" | "off";
  time: number;
}

type LightStyle = {
  on: string;
  off: string;
};

const lightStyles: Record<TrafficLightModeType, LightStyle> = {
  red: {
    on: "bg-red-500",
    off: "bg-red-100",
  },
  yellow: {
    on: "bg-yellow-500",
    off: "bg-yellow-100",
  },
  green: {
    on: "bg-green-500",
    off: "bg-green-100",
  },
};

const Light: React.FC<LightProps> = ({ lightMode, lightOn, time }) => {
  return (
    <div
      className={`rounded-full h-14 w-14 flex items-center justify-center text-3xl text-white font-bold transition-colors duration-300 ease-in-out
 ${lightStyles[lightMode][lightOn]}`}
    >
      {lightOn === "on" && time}
    </div>
  );
};

function TrafficLight() {
  const [currentTrafficLightMode, setCurrentTrafficLightMode] =
    useState<TrafficLightModeType>("red");
  const [time, setTime] = useState(0);

  //change alternatively
  const handleCycleLightMode = useCallback(() => {
    setCurrentTrafficLightMode((prev) => {
      if (prev === "red") return "yellow";
      if (prev === "yellow") return "green";
      return "red";
    });
    setTime(0);
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      setTime((prevTime) => prevTime + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (time > 2) {
      handleCycleLightMode();
    }
  }, [time]);

  return (
    <div className="task-container">
      <h2>Task 7: Traffic Light</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Create a traffic light with three lights (red, yellow, green)</li>
          <li>Only one light active at a time</li>
          <li>Button to cycle through the lights</li>
          <li>Optional: Auto-cycle with a timer</li>
        </ul>
      </div>

      <div className="implementation flex flex-col gap-4 items-center">
        <div className="flex flex-col gap-3 border rounded-md w-fit p-3 bg-gray-900">
          {["red", "yellow", "green"].map((mode) => (
            <Light
              key={mode}
              lightMode={mode as TrafficLightModeType}
              lightOn={currentTrafficLightMode === mode ? "on" : "off"}
              time={currentTrafficLightMode === mode ? time : 0}
            />
          ))}
        </div>
        <button
          className="btn btn-primary w-fit"
          onClick={handleCycleLightMode}
          aria-label="Manually cycle to next traffic light"
        >
          change
        </button>
      </div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li>
            The traffic light uses three states: "red", "yellow", and "green",
            managed with useState.
          </li>
          <li>
            Only one light is active at a time. The active light displays a
            timer, while inactive ones show nothing.
          </li>
          <li>
            handleCycleLightMode cycles the light from red → yellow → green →
            red and resets the timer. It's memoized with useCallback to ensure
            the reference remains consistent.
          </li>
          <li>
            useEffect with setInterval updates the time state every second.
          </li>
          <li>
            A separate useEffect watches the time and triggers a light change
            once the timer exceeds 2 seconds for auto-cycling.
          </li>
          <li>
            The Light component takes in lightMode, lightOn, and time as props
            and renders according to the current mode using Tailwind CSS
            classes.
          </li>
          <li>
            The lights are rendered dynamically using map() for cleaner and
            scalable rendering.
          </li>
          <li>
            The timer inside each light is only shown when the light is active.
          </li>
          <li>
            A manual override button ("change") is provided for cycling through
            the lights manually, independent of the timer.
          </li>
          <li>
            Tailwind utility classes such as transition-colors, duration-300,
            and ease-in-out are used for smooth transitions between light
            states.
          </li>
          <li>
            Accessibility: The button includes an aria-label for screen reader
            support to describe its action.
          </li>
        </ul>
      </div>
    </div>
  );
}

export default TrafficLight;
