import React from "react"

type MessageCardProps = {
    message: string;
    updateMessage: (newMessage: string) => void
}

const MessageCard: React.FC<MessageCardProps> = React.memo(({ message, updateMessage }) => {

    console.log("Child: message card component rendered")

    return (
        <div className="bg-yellow-100/50 p-4 space-y-3 w-fit">
            <div>
                <label>Message:</label>
                <p>{message}</p>
            </div>
            <input
                aria-label="Message input"
                className="p-2 border border-yellow-300 rounded"
                value={message}
                placeholder="Enter message"
                onChange={(e) => updateMessage(e.target.value)}
            />
        </div>
    )
})

export default MessageCard
