import React from "react";
import { useEffect } from "react";
import ReactDOM from "react-dom";

type ModalPortalProps = {
    isOpen: boolean;
    onClose: () => void
    title?: string;
    children: React.ReactNode;

}

// in the main app root - i have a div with the id modal-root
const modalRoot = document.getElementById("modal-root")

const ModalPortal: React.FC<ModalPortalProps> = ({ isOpen, onClose, title, children }) => {

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


    if (!isOpen || !modalRoot) return null

    const ModalContent = <div
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

    return ReactDOM.createPortal(ModalContent, modalRoot)
}

export default ModalPortal