import React from "react";
import logo from "./logo.svg";
import "./App.css";
//import pages
import BasicForm from "./pages/BasicForm";

function App() {
  return (
    <div className="App">
      <h2>Formik + TypeScript + MaterialUi4 </h2>
      <h6>(In the simplest form possible)</h6>
      <hr />
      <BasicForm />
    </div>
  );
}

export default App;
