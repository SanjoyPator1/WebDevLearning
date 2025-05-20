import React from "react"
import type { TodoType } from "./CustomComparison"

type TodoProp = {
    data: TodoType[]
}

const Todo: React.FC<TodoProp> = ({ data }) => {

    console.log("Rerender - todo component")

    return (
        <div className="space-y-3 p-3 bg-blue-100/40 md:h-[400px] overflow-y-auto">
            <h4>
                TODO list :
            </h4>
            {
                data.map((todo) => {
                    return (
                        <div key={todo.id} className="p-2 border">
                            <p>
                                {todo.id}
                            </p>
                            <p>
                                {todo.task}
                            </p>
                            <p>
                                {todo.done}
                            </p>
                        </div>
                    )
                })
            }
        </div>
    )
}

// we can have a separate helper function to check if the props are equal for a complex props
const areTodosEqual = (prevProps: TodoProp, nextProps: TodoProp): boolean => {
    const prev = prevProps.data
    const next = nextProps.data

    if (prev.length !== next.length) return false

    return prev.every((prevTodo, index) => {
        const nextTodo = next[index]
        return (
            prevTodo.id === nextTodo.id &&
            prevTodo.task === nextTodo.task &&
            prevTodo.done === nextTodo.done
        )
    })
}


// and use that helper function in here - it should return a boolean
const MemoizedTodo = React.memo(
    Todo,
    areTodosEqual
)

export default MemoizedTodo