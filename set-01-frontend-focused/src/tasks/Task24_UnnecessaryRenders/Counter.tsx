import React from "react";

type IncrementType = "increment" | "decrement"

type CounterProps = {
    counter: number;
    handleCounter: (mode: IncrementType)=>void
}

const Counter: React.FC<CounterProps> = ({counter,handleCounter}) =>{
    
        console.log("Child: counter component rendered")
    
    return (
        <div className="rounded-md bg-blue-100/50 p-3 w-fit space-y-2">
            <p>Counter: {counter}</p>
            <div className="flex gap-3">
                <button onClick={()=>handleCounter("decrement")} className="btn btn-primary">-</button>
                <button onClick={()=>handleCounter("increment")} className="btn btn-primary">+</button>
            </div>
        </div>
    )
}

const MemoizedCounter = React.memo(Counter)

export default MemoizedCounter