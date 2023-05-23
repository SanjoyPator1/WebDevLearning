import express from "express"
import router from "./router"
import morgan from 'morgan'
import cors from 'cors'

const app = express();

const customLogger = (message) => (req,res,next)=>{
  console.log("custom logger ",message);
  next()
}

app.use(cors())
app.use(morgan('dev'))
app.use(express.json())
app.use(express.urlencoded({ extended: true }))
app.use(customLogger("Hello from custom world"))

app.use((req,res, next)=>{
  //adding this to request object
  req.customMiddleware = 'my custom demo middleware';
  next();
})

app.get("/", (req, res) => {
  // sending back a json
  console.log("main route hit");
  res.json({ message: "hello from server" });
});

app.use('/api', router)

export default app;
