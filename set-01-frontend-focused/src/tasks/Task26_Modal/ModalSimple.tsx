import type React from "react";
import { useEffect } from "react";

type ModalSimpleProps = {
    isOpen: boolean;
    onClose: () => void
    title?: string;
    children: React.ReactNode;

}

const ModalSimple: React.FC<ModalSimpleProps> = ({ isOpen, onClose, title, children }) => {

    useEffect(()=>{

        const handleKeyDown=(e : KeyboardEvent)=>{
            if(e.key==="Escape"){
                onClose()
            }
        }

        if(isOpen){
            document.addEventListener("keydown",handleKeyDown)
        }

        return(()=>{
            document.removeEventListener("keydown",handleKeyDown)
        })
    },[isOpen])


    if (!isOpen) return null

    return (
        <div
            className="fixed inset-0 flex items-center justify-center bg-black/50"
            aria-modal={true}
            onClick={onClose}
            role="dialog"
            aria-labelledby="modal-title"
        >
            <div
                className="bg-white rounded-xl w-full max-w-md p-4"
                onClick={(e)=>e.stopPropagation()}
            >
                {title &&
                    <h2 id="modal-title">{title}</h2>
                }
                {children}
                <div className="flex justify-end mt-3">
                    <button
                        className="btn btn-primary"
                        onClick={onClose}
                    >close</button>
                </div>
            </div>

        </div>
    )
}

export default ModalSimple