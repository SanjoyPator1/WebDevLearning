import AttrAndStyle from "./AttrAndStyle";
import AttrAndStyleGenreExercise from "./AttrAndStyleGenreExercise";
import CreateDomElements from "./CreateDomElements";
import CreateDomElementsExercise from "./CreateDomElementsExercise";
import DataBinding from "./DataBinding";
import SelectComponent from "./SelectComponent";
import TranslateTransform from "./TranslateTransform";

const M2 = () => {
  return (
    <div>
      <h3>Module 02 - API</h3>
      <h4>Exercise 01 - Selections</h4>
      <div
        style={{
          border: "1px solid black",
          width: "170px",
          height: "170px",
          backgroundColor: "white",
          padding: 10,
          margin: "0 auto"
        }}
      >
        <SelectComponent />
      </div>

      <h4>Exercise 02 - Data Binding</h4>
      <div
        style={{
          border: "1px solid black",
          width: "170px",
          height: "170px",
          backgroundColor: "white",
          padding: 10,
          margin: "0 auto"
        }}
      >
        <DataBinding />
      </div>

      <h4>Exercise 03 - Attr And Style</h4>
      <div
        style={{
          border: "1px solid black",
          width: "280px",
          height: "100px",
          backgroundColor: "white",
          padding: 10,
          margin: "0 auto"
        }}
      >
        <AttrAndStyle />
      </div>

      <h4>Exercise 04 - Attr And Style Genre Exercise</h4>
      <div
        style={{
          border: "1px solid black",
          width: "510px",
          height: "100px",
          backgroundColor: "white",
          padding: 10,
          margin: "0 auto"
        }}
      >
        <AttrAndStyleGenreExercise />
      </div>

      <h4>Exercise 05 - Create a DOM element from Data</h4>
      <div
        style={{
          border: "1px solid black",
          width: "280px",
          height: "100px",
          backgroundColor: "white",
          padding: 10,
          margin: "0 auto"
        }}
      >
        <CreateDomElements />
      </div>

      <h4>Exercise 06 - Create a DOM element from Data - Exercise</h4>
      <div
        style={{
          justifyContent: "center",
          border: "1px solid black",
          width: "100%",
          height: "500px",
          overflow: "auto",
          backgroundColor: "white",
          padding: "20",
          margin: "0 auto"
        }}
      >
        <CreateDomElementsExercise />
      </div>
      <h4>Exercise 07 - Translate Transform</h4>
      <div
        style={{
          border: "1px solid black",
          width: "100%",
          // height: "400px",
          overflow: "auto",
          backgroundColor: "white",
          padding: 30,
          margin: "0 auto"
        }}
      >
        <TranslateTransform />
      </div>
      <hr />
    </div>
  );
};

export default M2;
