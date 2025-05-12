import { useEffect, useState } from "react";

type Dimensions = {
  height: number;
  width: number;
};

function WindowSizeTracker() {
  const [dimensions, setDimensions] = useState<Dimensions>({
    height: 0,
    width: 0,
  });

  useEffect(() => {
    console.log("useEffect ran");

    // this will hold the timeoutId for clear timeout when multiple is being fired
    let timeoutId: ReturnType<typeof setTimeout>;

    // debounce for performance
    const updateMeasurements = () => {
      clearTimeout(timeoutId);

      timeoutId = setTimeout(() => {
        setDimensions({
          height: window.innerHeight,
          width: window.innerWidth,
        });
      }, 150);
    };

    // for initial measurement
    updateMeasurements();
    window.addEventListener("resize", updateMeasurements);

    // cleanup on unmount
    return () => {
      window.removeEventListener("resize", updateMeasurements);
      clearTimeout(timeoutId);
    };
  }, []);

  return (
    <div className="task-container">
      <h2>Task 13: Window Size Tracker</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Display the current width and height of the browser window</li>
          <li>Update the dimensions when the window is resized</li>
        </ul>
      </div>

      <div className="implementation p-4">
        <p>Height: {dimensions.height}</p>
        <p>Width: {dimensions.width}</p>
      </div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li>
            Use <code>useEffect</code> to add and clean up the resize event
            listener
          </li>
          <li>
            Use <code>useState</code> to store the window dimensions
          </li>
          <li>
            Debounce the resize event using <code>setTimeout</code> for
            performance optimization
          </li>
          <li>
            Clear the timeout on every resize and during cleanup to avoid memory
            leaks
          </li>
          <li>
            Initialize dimensions in <code>useEffect</code> to prevent accessing{" "}
            <code>window</code> during SSR
          </li>
        </ul>
      </div>
    </div>
  );
}

export default WindowSizeTracker;
