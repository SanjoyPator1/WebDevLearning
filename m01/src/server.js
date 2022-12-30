const express = require("express");
const app = express();

app.use(express.static("static"));

/**
 * app.[method]([route], [route handler])
 */
app.get("/", (req, res) => {
  // sending back a json
  console.log("main route hit");
  res.json({ message: "hello from server" });
});

module.exports = app;
