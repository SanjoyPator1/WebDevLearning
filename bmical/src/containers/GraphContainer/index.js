import React from 'react'
import BarChart from '../../components/BarChart'


const GraphContainer = ({gdata}) => {

    console.log("graph container gdata ",gdata)
    let stringData = JSON.stringify(gdata)
    console.log({stringData})

  return (
    <>
    <BarChart gdata={gdata} />
    </>
  )
}

export default GraphContainer