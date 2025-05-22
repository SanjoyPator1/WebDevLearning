import React, { useRef } from "react";
import { useEffect } from "react";
import ReactDOM from "react-dom";

type ModalAdvancedPortalProps = {
    isOpen: boolean;
    onClose: () => void
    title?: string;
    children: React.ReactNode;

}

const ModalAdvancedPortal: React.FC<ModalAdvancedPortalProps> = ({ isOpen, onClose, title, children }) => {

    const elRef = useRef<HTMLDivElement | null>(null)

    // Lazily create the div once inside the effect
    useEffect(() => {
        const el = document.createElement("div");
        elRef.current = el;
        document.body.appendChild(el);

        return () => {
            document.body.removeChild(el);
        };
    }, []);

    useEffect(() => {

        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === "Escape") {
                onClose()
            }
        }

        if (isOpen) {
            document.addEventListener("keydown", handleKeyDown)
        }

        return (() => {
            document.removeEventListener("keydown", handleKeyDown)
        })
    }, [isOpen])


    if (!isOpen || !elRef.current) return null

    const ModalContent = <div
        className="fixed inset-0 flex items-center justify-center bg-black/50"
        aria-modal={true}
        onClick={onClose}
        role="dialog"
        aria-labelledby="modal-title"
    >
        <div
            className="bg-white rounded-xl w-full max-w-md p-4"
            onClick={(e) => e.stopPropagation()}
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

    return ReactDOM.createPortal(ModalContent, elRef.current)
}

export default ModalAdvancedPortal