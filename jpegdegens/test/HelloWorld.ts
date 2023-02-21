import "@nomiclabs/hardhat-waffle";
import _ from "@nomiclabs/hardhat-ethers";

//we need to do thsi steps
//1. setup
//2. deploy our contract
//3. call our functions to test

import { ethers } from "hardhat";
import { expect } from "chai";

describe("HelloWorld", () => {
  it("should get the hello world", async () => {
    //2. deploy our contract
    const HelloWorld = await ethers.getContractFactory("HelloWorld");
    const hello = await HelloWorld.deploy();

    expect(await hello.hello()).to.equal("Hello, World");
  });
});
