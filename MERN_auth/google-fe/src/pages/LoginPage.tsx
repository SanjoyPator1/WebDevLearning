import { GoogleLogin, useGoogleLogin } from "@react-oauth/google";
import { useState } from "react";

const LoginPage = () => {
  const [loginData, setLoginData] = useState(
    localStorage.getItem("loginData")
      ? JSON.parse(localStorage.getItem("loginData"))
      : null
  );

  const handleFailure = () => {
    alert("Login failed");
  };

  const handleLogin = async (googleData) => {
    console.log("sending this data to be from fe ", googleData);
    try {
      const res = await fetch("http://localhost:3001/api/google-login", {
        method: "POST",
        body: JSON.stringify({
          token: googleData.access_token,
        }),
        headers: {
          "Content-Type": "application/json",
        },
      });

      const data = await res.json();
      console.log("google data received from backend in fe ", data);
      setLoginData(data);
      localStorage.setItem("loginData", JSON.stringify(data));
    } catch (err) {
      console.log("failed google login fe");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("loginData");
    setLoginData(null);
  };

  const login = useGoogleLogin({
    onError: handleFailure,
    onSuccess: handleLogin,
  });

  return (
    <div className="App">
      <h2>React Google Login App</h2>
      <div>
        {loginData ? (
          <div>
            <h3>You logged in as {loginData.name}</h3>
            <h3>with email {loginData.email}</h3>
            {/* <p>{loginData.picture}</p> */}
            <img
              src={loginData.picture}
              alt="google dp"
              style={{ width: "100px", height: "100px" }}
            />
            <br/>
            <button onClick={handleLogout}>Logout</button>
          </div>
        ) : (
          <button onClick={() => login()}>google</button>
        )}
      </div>
    </div>
  );
};

export default LoginPage;
