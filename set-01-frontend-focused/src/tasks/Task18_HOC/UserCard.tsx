import type React from "react";
import type { WithLoadingProps } from "./WithLoaderHOC";

export type UserType = {
  name: string;
  email: string;
};

export type UserCardProps = {
  userData: UserType;
} & WithLoadingProps;

const UserCard: React.FC<UserCardProps> = ({ userData, isLoading }) => {
  if (isLoading) {
    console.log(
      "While the loading is shown we can do other task in loading period"
    );
  }

  return (
    <div className="border rounded-md p-3 space-y-3">
      UserCard
      <div className="space-y-2">
        <p>name: {userData.name}</p>
        <p>email: {userData.email}</p>
      </div>
    </div>
  );
};

export default UserCard;
