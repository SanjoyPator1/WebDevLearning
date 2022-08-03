import React, { useState } from 'react'
import GraphContainer from '../../containers/GraphContainer'
import InputNumberContainer from '../../containers/InputNumberContainer'

const Main = () => {
      
    let[bmi1,setBmi1] =  useState(0);
    let[bmi2,setBmi2] =  useState(0);
    let[bmi3,setBmi3] =  useState(0);
    let[bmi4,setBmi4] =  useState(0);

    let gdata = [
        {name : "Person 01",no: bmi1},
        {name : "Person 02",no: bmi2},
        {name : "Person 03",no: bmi3},
        {name : "Person 04",no: bmi4},
    ]
    
    console.log({gdata})


  return (
    <div className="flex-container">
        <div className='left-child'>
          <h1>Personal Details</h1>
          <div className='personCol'>
            <InputNumberContainer setBmi1={setBmi1} setBmi2={setBmi2} setBmi3={setBmi3} setBmi4={setBmi4}/>
          </div>
        </div>
        <div className='right-child'>
            <h1>graph</h1>
          <GraphContainer gdata={gdata}/>
        </div>
    </div>
  )
}

export default Main