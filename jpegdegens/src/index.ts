import { ethers } from "ethers";

function getEth() {
  //@ts-ignore
  const eth = window.ethereum;
  if (!eth) {
    throw new Error("get Metamask");
  }
  return eth;
}

async function hasAccounts() {
  const eth = getEth();
  const accounts = (await eth.request({ method: "eth_accounts" })) as string[];

  return accounts && accounts.length > 0;
}

async function requestAccounts() {
  const eth = getEth();
  const accounts = (await eth.request({
    method: "eth_requestAccounts",
  })) as string[];

  return accounts && accounts.length > 0;
}

async function run() {
  if (!(await hasAccounts()) && !(await requestAccounts())) {
    throw new Error("Please let me have your money lol");
  }

  const address = "0x5fbdb2315678afecb367f032d93f642f64180aa3";

  //we have metask now we need to call contract
  const hello = new ethers.Contract(
    address,
    ["function hello() public pure returns (string memory)"],
    new ethers.providers.Web3Provider(getEth())
  );
  console.log("We have done it, time to call");
  console.log(await hello.hello());

  document.body.innerHTML = await hello.hello();
}

run();
