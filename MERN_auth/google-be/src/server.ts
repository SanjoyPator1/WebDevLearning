import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import axios from "axios";
// const path = require('path');

dotenv.config();

const app = express();
app.use(express.json());
app.use(cors());

const googleId = process.env.GOOGLE_CLIENT_ID
// console.log("googleId be  ",googleId)

const users = [];

function upsert(array, item) {
  const i = array.findIndex((_item) => _item.email === item.email);
  if (i > -1) array[i] = item;
  else array.push(item);
}

app.post("/api/google-login", async (req, res) => {
  const { token } = req.body;
  // console.log("be token received ", token);

  try {
    const ticket = await axios.get(`https://www.googleapis.com/oauth2/v1/userinfo?access_token=${token}`)
    // console.log("ticket ", ticket.data);
    const { name, email, picture } = ticket.data;
    upsert(users, { name, email, picture });
    res.status(201);
    res.json({ name, email, picture });
  } catch (err) {
    console.log("error in be ", err);
  }
});

app.get("/allusers", (req, res, next) => {
  console.log("all users route hit");
  res.status(200).json({ users: users });
});

app.get("/health", (req, res, next) => {
  console.log("health route hit");
  res.status(200).json({ message: "server is running" });
});

export default app;
