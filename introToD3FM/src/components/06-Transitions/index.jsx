import AnimateWithTranisitionBarGraph from "./AnimateWithTranisitionBarGraph";
import FilteringAndUpdatingFlowers from "./FilteringAndUpdatingFlowers";

const M6 = () => {
  return (
    <div>
      <h3>Module 06 - transitions</h3>
      <h4>Exercise 01 - Animate with Transitions - bar graph</h4>
      <div
        style={{
          border: "1px solid black",
          width: "100%",
          // height: "400px",
          overflow: "auto",
          backgroundColor: "white",
          padding: 30,
          margin: "0 auto",
        }}
      >
        <AnimateWithTranisitionBarGraph />
      </div>
      <h4>Exercise 02 - Filtering and Updating data - Flower data</h4>
      <div
        style={{
          justifyContent: "center",
          border: "1px solid black",
          width: "95%",
          height: "700px",
          overflow: "auto",
          backgroundColor: "white",
          padding: "20",
          margin: "0 auto",
        }}
      >
        <FilteringAndUpdatingFlowers />
      </div>
      <hr />
    </div>
  );
};

export default M6;
