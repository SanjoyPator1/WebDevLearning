import React, { useEffect, useRef, useState, type ReactElement } from "react"

type HoverCardRenderPropsType = {
    render: (isHovered: boolean) => ReactElement
}

const HoverCardRenderProps: React.FC<HoverCardRenderPropsType> = ({ render }) => {

    const [isHovered, setIsHovered] = useState(false)
    const divRef = useRef<HTMLDivElement | null>(null)


    useEffect(() => {
        const ref = divRef.current;
        if (!ref) return;

        const handleMouseEnter = () => setIsHovered(true);
        const handleMouseLeave = () => setIsHovered(false);

        ref.addEventListener("mouseenter", handleMouseEnter);
        ref.addEventListener("mouseleave", handleMouseLeave);

        return () => {
            ref.removeEventListener("mouseenter", handleMouseEnter);
            ref.removeEventListener("mouseleave", handleMouseLeave);
        };
    }, []);


    return (
        <div ref={divRef} className={`border shadow-md rounded-md px-4 py-7 w-full`}>
            Normal card demo - hover to see something
            {
                isHovered && render(isHovered)

            }

        </div>
    )

}

export default HoverCardRenderProps