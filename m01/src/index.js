const http = require("http");

const server = http.createServer((req, res) => {
  if (req.method === "GET" && req.url === "/") {
    console.log("main rout hit in backend");
    res.end();
  }
});

server.listen(3001, () => {
  console.log("server on http://localhost:3001");
});
