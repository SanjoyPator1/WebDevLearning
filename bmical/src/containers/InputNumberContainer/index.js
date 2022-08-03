
import React, { useEffect, useState } from "react";
import InputNumber  from "../../components/InputNumber";

const InputNumberContainer = ({setBmi1, setBmi2, setBmi3, setBmi4}) => {

    let [height01, setHeight01] = useState(0);
    let [weight01, setWeight01] = useState(0);
  
    let [height02, setHeight02] = useState(0);
    let [weight02, setWeight02] = useState(0);
  
    let [height03, setHeight03] = useState(0);
    let [weight03, setWeight03] = useState(0);
  
    let [height04, setHeight04] = useState(0);
    let [weight04, setWeight04] = useState(0);

  
    useEffect(()=> {
      console.log("useEffect called")
      
  
      //for p01
      if(weight01!==0 && height01!==0 && weight01!==null && height01!==null){
        //calculate and show bmi
        console.log("calculating bmi")
        let b1 =  weight01 / (height01**2)
        setBmi1(b1)
      }
  
      //for p02
      if(weight02!==0 && height02!==0 && weight02!==null && height02!==null){
        //calculate and show bmi
        console.log("calculating bmi")
        let b2 =  weight02 / (height02**2)
        setBmi2(b2)
      }
  
      //for p03
      if(weight03!==0 && height03!==0 && weight03!==null && height03!==null){
        //calculate and show bmi
        console.log("calculating bmi")
        let b3 =  weight03 / (height03**2)
        setBmi3(b3)
      }
  
      //for p04
      if(weight04!==0 && height04!==0 && weight04!==null && height04!==null){
        //calculate and show bmi
        console.log("calculating bmi")
        let b4 =  weight04 / (height04**2)
        setBmi4(b4)
      }
  
  
    },[height01, weight01, height02, weight02, height03, weight03, height04, weight04, setBmi1, setBmi2, setBmi3, setBmi4])

  return (
    <>
    <InputNumber name="person01" setHeight={setHeight01} setWeight={setWeight01} height={height01} weight={weight01}/>
    <InputNumber name="person02" setHeight={setHeight02} setWeight={setWeight02} height={height02} weight={weight02}/>
    <InputNumber name="person03" setHeight={setHeight03} setWeight={setWeight03} height={height03} weight={weight03}/>
    <InputNumber name="person04" setHeight={setHeight04} setWeight={setWeight04} height={height04} weight={weight04}/>
    </>
  )
}

export default InputNumberContainer