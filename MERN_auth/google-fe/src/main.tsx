import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.tsx";
import "./index.css";
import { GoogleOAuthProvider } from "@react-oauth/google";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    {/* {console.log("gid", process.env.REACT_APP_GOOGLE_CLIENT_ID)} */}
    <GoogleOAuthProvider clientId={'21721051800-v8jt35m704l5ocm5b9ik9o7uptvldjbp.apps.googleusercontent.com'}>
      <App />
    </GoogleOAuthProvider>
  </React.StrictMode>
);
