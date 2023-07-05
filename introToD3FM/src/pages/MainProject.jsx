// import FilteringAndUpdatingFlowers from "../components/06-Transitions/FilteringAndUpdatingFlowers";
import ForceFlowersPosition from "../components/FM-Container/07-PositioningFunction/ForceFlowersPosition";
import { useInView } from "react-intersection-observer";
import { useEffect } from "react";

const MainProject = () => {
  const { ref, inView, entry } = useInView({
    /* Optional options */
    threshold: 0,
  });

  useEffect(() => {
    if (inView) {
      // do something here to trigger a re-render
      console.log("animation inview state ", inView);
    }
  }, [inView]);

  return (
    <div>
      <div ref={ref}>
        {inView ? (
          <ForceFlowersPosition />
        ) : (
          console.log("animation not in view")
        )}
      </div>
    </div>
  );
};

export default MainProject;
