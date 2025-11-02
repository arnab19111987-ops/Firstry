import React from 'react';

interface User {
  id: number;
  name: string;
  email: string;
}

interface Props {
  users: User[];
  onUserSelect: (user: User) => void;
}

const UserList: React.FC<Props> = ({ users, onUserSelect }) => {
  return (
    <div className="user-list">
      <h2>Team Members</h2>
      {users.length === 0 ? (
        <p>No users found</p>
      ) : (
        <ul>
          {users.map((user) => (
            <li key={user.id} onClick={() => onUserSelect(user)}>
              <strong>{user.name}</strong>
              <br />
              <span>{user.email}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default UserList;