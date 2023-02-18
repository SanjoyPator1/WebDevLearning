import EnterUpdateNewWayJoin from "./EnterUpdateNewWayJoin";
import EnterUpdateOldWay from "./EnterUpdateOldWay";

const M5 = () => {
  return (
    <div>
      <h3>Module 05 - DOM Manipulation</h3>
      <h4>Exercise 01 - Enter-Update Old way</h4>
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
        <EnterUpdateOldWay />
      </div>
      <h4>Exercise 02 - Enter-Update New way Join</h4>
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
        <EnterUpdateNewWayJoin />
      </div>
      <hr />
    </div>
  );
};

export default M5;
