import { useCallback, useEffect, useState } from 'react';


const useLocalStorage = <T,>(
    key: string,
    initialValue: T
): [T,(newStoredValue: T) => void] => {

    const [storedValue, setStoredValue] = useState<T>(
        ()=>{
            // Avoid running this code on the server
            if(typeof window==="undefined"){
                return initialValue;
            }
            try{
                //try to get the item from local storage and set the state if not present set the initial value
                const cachedValue = window.localStorage.getItem(key)
                return cachedValue? JSON.parse(cachedValue): initialValue
            }catch(err){
                console.log("error in local storage hook - ",err)
                return initialValue
            }
        }
    )

    // listen for changes in local storage from other tabs or windows
     useEffect(()=>{
        const handleStorageChange=(event:StorageEvent)=>{
        if(event.key===key && event.newValue){
            try{
                setStoredValue(JSON.parse(event.newValue))
            }catch(error){
                console.warn(`Error parsing localStorage value for key "${key}":`, error);            }
        }
      }

      window.addEventListener("storage",handleStorageChange)

      return()=>{
        window.removeEventListener("storage",handleStorageChange)
      }
    },[key])
    


    /**
   * Updates localStorage and the React state
   * Wrapped in useCallback to avoid unnecessary re-renders
   */
    const setValue = useCallback((newStoredValue: T) =>{
        if(window){
            const stringifiedObj = JSON.stringify(newStoredValue)
            window.localStorage.setItem(key,stringifiedObj)

            setStoredValue(newStoredValue)
        }
    },[key])


  return [storedValue, setValue ]
}

export default useLocalStorage