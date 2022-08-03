import React from 'react'

const InputNumber = ({name, setHeight, setWeight, height, weight}) => {
    console.log("weight  is ",weight);
    console.log("height is ",height);
    return (
    <>
    <div className='pno'>
                <h4>{name}</h4>
              </div>
              <div className='height-c'>
                <input
                  type="number"
                  name="height"
                  placeholder='height'
                  value={height}
                  onChange={event => setHeight(event.target.value)}
                />
              </div>
              <div className='weight-c'>
                <input
                  type="number"
                  name="weight"
                  value={weight}
                  placeholder='weight'
                  onChange={event => setWeight(event.target.value)}
                />
    </div>
    </>
  )
}

export default InputNumber