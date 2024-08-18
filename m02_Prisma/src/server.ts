import express from "express"
const app = express();

app.get("/", (req, res) => {
  // sending back a json
  console.log("main route hit");
  res.json({ message: "hello from server" });
});

export default app;
