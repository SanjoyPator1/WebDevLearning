import React from "react";
import { Link } from "react-router-dom";

interface NotFoundProps {
  type: "page" | "task";
  taskId?: string;
}

const NotFound: React.FC<NotFoundProps> = ({ type, taskId }) => {
  return (
    <div className="flex flex-col items-center justify-center h-full min-h-[400px] text-center p-6">
      <div className="max-w-md">
        <h2 className="text-3xl font-bold mb-4 text-gray-900">
          {type === "page" ? "Page Not Found" : "Task Not Found"}
        </h2>

        {type === "page" ? (
          <p className="text-lg text-gray-600 mb-6">
            The page you are looking for doesn't exist or has been moved.
          </p>
        ) : (
          <p className="text-lg text-gray-600 mb-6">
            The task{" "}
            <span className="font-mono bg-gray-100 px-2 py-1 rounded text-gray-800 font-medium">
              "{taskId}"
            </span>{" "}
            you are looking for hasn't been implemented yet or doesn't exist.
          </p>
        )}

        <div className="mt-8">
          <Link
            to="/task/welcome"
            className="inline-block bg-black text-white py-2 px-6 rounded font-medium transition-colors hover:bg-gray-800"
          >
            Go to Home
          </Link>

          {type === "task" && (
            <p className="mt-4 text-sm text-gray-500 italic">
              Select another task from the sidebar to continue.
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default NotFound;
