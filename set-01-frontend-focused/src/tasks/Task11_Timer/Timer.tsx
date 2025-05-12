import { useEffect, useState } from "react";

type TimerStateType = "start" | "stop" | "reset";

const formatTime = (time: number): string => {
  const minutes = Math.floor(time / 60);
  const seconds = time % 60;
  const paddedMinutes = String(minutes).padStart(2, "0");
  const paddedSeconds = String(seconds).padStart(2, "0");
  return `${paddedMinutes}:${paddedSeconds}`;
};

function Timer() {
  const [timerCount, setTimerCount] = useState(0);
  const [timerState, setTimerState] = useState<TimerStateType>("stop");

  useEffect(() => {
    if (timerState !== "start") return;

    const timer = setInterval(() => {
      setTimerCount((prev) => prev + 1);
    }, 1000);

    return () => {
      clearInterval(timer);
    };
  }, [timerState]);

  const handleChangeTimerState = (newState: TimerStateType) => {
    if (newState === "reset") {
      setTimerCount(0);
      setTimerState("stop");
    } else {
      setTimerState(newState);
    }
  };

  return (
    <div className="task-container">
      <h2>Task 11: Timer/Stopwatch</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Create a stopwatch with start, stop, and reset functions</li>
          <li>Display time in mm:ss format</li>
          <li>Include start, stop, and reset buttons</li>
        </ul>
      </div>

      <div className="implementation space-y-2 w-fit flex flex-col  items-center">
        {/* time container */}
        <div className="flex rounded-full p-5 bg-gray-900 w-48 h-48 items-center justify-center">
          <p className="text-3xl text-white">{formatTime(timerCount)}</p>
        </div>
        {/* controls container */}
        <div className="border rounded-md w-fit flex gap-4 p-4 bg-blue-100">
          <button
            aria-label="Start timer"
            className={`btn  ${
              timerState === "start" ? "btn-primary" : "btn-secondary"
            }`}
            onClick={() => handleChangeTimerState("start")}
          >
            start
          </button>
          <button
            aria-label="Stop timer"
            className={`btn  ${
              timerState === "stop" ? "btn-primary" : "btn-secondary"
            }`}
            onClick={() => handleChangeTimerState("stop")}
          >
            stop
          </button>
          <button
            aria-label="Reset timer"
            className={`btn  ${
              timerState === "reset" ? "btn-primary" : "btn-secondary"
            }`}
            onClick={() => handleChangeTimerState("reset")}
          >
            reset
          </button>
        </div>
      </div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li>
            Used <code>useEffect</code> to handle side effects—specifically to
            start and clear the timer interval based on <code>timerState</code>.
            The interval only runs when <code>timerState === "start"</code>.
          </li>
          <li>
            Inside <code>useEffect</code>, <code>setInterval</code> is used to
            increment <code>timerCount</code> every second. A cleanup function
            with <code>clearInterval</code> ensures the interval is cleared when
            the component unmounts or <code>timerState</code> changes,
            preventing memory leaks.
          </li>
          <li>
            The timer display is formatted to <code>mm:ss</code> using a
            separate <code>formatTime</code> utility function, improving
            readability and separation of concerns.
          </li>
          <li>
            The <code>handleChangeTimerState</code> function centrally manages
            all state transitions for the timer, including resetting the timer
            and stopping it immediately when reset is clicked.
          </li>
          <li>
            Button styles are conditionally applied based on the current{" "}
            <code>timerState</code> to reflect the active state visually.
          </li>
          <li>
            Added <code>aria-label</code> attributes to each button for better
            accessibility and screen reader support.
          </li>
        </ul>
      </div>
    </div>
  );
}

export default Timer;
