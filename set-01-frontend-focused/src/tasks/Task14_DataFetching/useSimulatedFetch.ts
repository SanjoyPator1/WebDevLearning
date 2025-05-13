import { useEffect, useState } from "react";

export type ApiReturnMode = "success" | "error";

type FetchOptions<T> = {
  fetchMode: ApiReturnMode;
  delay?: number;
  fn: (mode: ApiReturnMode) => T
}

type FetchState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
};

const useSimulatedFetch = <T>({ fetchMode, delay = 2000, fn }: FetchOptions<T>): FetchState<T> => {

  const [state, setState] = useState<FetchState<T>>({
    data: null,
    loading: false,
    error: null
  })

  useEffect(()=>{
    let isMounted = true;

    const simulateFetch = ():Promise<T> =>{
      return new Promise((resolve,reject)=>{
        setTimeout(()=>{
          try{
            resolve(fn(fetchMode))
          }catch(err){
            reject(err)
          }
        },delay)
      })
    }

    // initially before fetching the api set it with default values but loading is true
    setState({
      data: null,
      loading: true,
      error: null
    })

    simulateFetch()
      .then((result)=>{
        if (isMounted) {
          setState({
            data: result,
            loading: false,
            error: null
          })
        }
      })
      .catch((err)=>{
        if (isMounted) {
          setState({
            data: null,
            loading: false,
            error: err.message || "Unknown error",
          })
        }
      })

    return ()=>{
      isMounted= false
    }

  },[fetchMode, delay, fn])

  return state
}

export default useSimulatedFetch