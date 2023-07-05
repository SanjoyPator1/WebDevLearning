import ForceFlowersPosition from "./ForceFlowersPosition";
import { useInView } from "react-intersection-observer";
import { useEffect } from "react";
import { Typography } from "@mui/material";
import { moduleTypoStyle } from "../../styles";

const M7 = () => {
  const { ref, inView, entry } = useInView({
    /* Optional options */
    threshold: 0,
  });

  useEffect(() => {
    if (inView) {
      // do something here to trigger a re-render
      // console.log("animation inview state ", inView);
    }
  }, [inView]);
  return (
    <div>
      <Typography variant="h4" sx={moduleTypoStyle}>
        Module 07 - Positioning Functions
      </Typography>
      <h4>Exercise 01 - Force Position - Flower data</h4>
      <div
        ref={ref}
        style={{
          justifyContent: "center",
          border: "1px solid black",
          width: "95%",
          height: "auto",
          overflow: "auto",
          backgroundColor: "white",
          padding: "20",
          margin: "0 auto",
        }}
      >
        {inView ? (
          <ForceFlowersPosition />
        ) : (
          console.log("animation not in view")
        )}
      </div>
      <hr />
    </div>
  );
};

export default M7;
