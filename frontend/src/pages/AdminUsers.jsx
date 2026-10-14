import { useCallback, useEffect, useState } from "react";
import AlertMessage from "../components/AlertMessage.jsx";
import {
  createAdminUser,
  deleteAdminUser,
  getAdminUsers,
  updateAdminUser
} from "../services/adminService.js";

const blankUser = {
  full_name: "",
  email: "",
  phone: "",
  district: "",
  state: "",
  password: "",
  role: "user"
};

const blankProfile = { full_name: "", phone: "", district: "", state: "" };

export default function AdminUsers() {
  const [users, setUsers] = useState([]);
  const [form, setForm] = useState(blankUser);
  const [profileForm, setProfileForm] = useState(blankProfile);
  const [editingId, setEditingId] = useState(null);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pagination, setPagination] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const result = await getAdminUsers({ search: search || undefined, page, per_page: 20 });
      setUsers(result.users);
      setPagination(result.pagination);
      setError("");
    } catch (requestError) {
      setError(requestError.response?.data?.message || "Users could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, [search, page]);

  useEffect(() => { loadUsers(); }, [loadUsers]);

  function changeSearch(event) {
    setPage(1);
    setSearch(event.target.value);
  }

  async function submit(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    try {
      await createAdminUser(form);
      setForm(blankUser);
      setMessage("User account created.");
      await loadUsers();
    } catch (requestError) {
      setError(requestError.response?.data?.message || "User could not be created.");
    }
  }

  async function saveProfile(event) {
    event.preventDefault();
    if (editingId === null) return;
    setError("");
    setMessage("");
    try {
      await updateAdminUser(editingId, profileForm);
      setEditingId(null);
      setProfileForm(blankProfile);
      setMessage("User details updated.");
      await loadUsers();
    } catch (requestError) {
      setError(requestError.response?.data?.message || "User details could not be updated.");
    }
  }

  function startEditing(user) {
    setEditingId(user.id);
    setProfileForm({
      full_name: user.full_name,
      phone: user.phone,
      district: user.district,
      state: user.state
    });
    setError("");
    setMessage("");
  }

  async function changeRole(user, role) {
    setError("");
    try {
      await updateAdminUser(user.id, { role });
      await loadUsers();
    } catch (requestError) {
      setError(requestError.response?.data?.message || "User role could not be updated.");
    }
  }

  async function removeUser(user) {
    if (!window.confirm(`Delete ${user.full_name} and their associated records?`)) return;
    setError("");
    try {
      await deleteAdminUser(user.id);
      setMessage("User and associated records deleted.");
      await loadUsers();
    } catch (requestError) {
      setError(requestError.response?.data?.message || "User could not be deleted.");
    }
  }

  return (
    <div className="dashboard-page">
      <div className="page-intro"><span className="page-overline">ADMINISTRATION</span><h2>Manage users</h2><p>Create accounts, review account details, assign roles, or remove accounts.</p></div>
      {error && <AlertMessage message={error} />}
      {message && <p className="alert alert-success" role="status">{message}</p>}
      <section className="surface-card mb-3">
        <h3 className="h5">Create an account</h3>
        <form className="row g-3" onSubmit={submit}>
          {[
            ["full_name", "Full name", "text"],
            ["email", "Email", "email"],
            ["phone", "Phone", "tel"],
            ["district", "District", "text"],
            ["state", "State", "text"],
            ["password", "Temporary password", "password"]
          ].map(([name, label, type]) => (
            <div className="col-md-4" key={name}>
              <label className="form-label" htmlFor={`new-user-${name}`}>{label}</label>
              <input className="form-control" id={`new-user-${name}`} type={type} value={form[name]} onChange={(event) => setForm((current) => ({ ...current, [name]: event.target.value }))} required />
            </div>
          ))}
          <div className="col-md-4">
            <label className="form-label" htmlFor="new-user-role">Role</label>
            <select className="form-select" id="new-user-role" value={form.role} onChange={(event) => setForm((current) => ({ ...current, role: event.target.value }))}>
              <option value="user">User</option><option value="admin">Administrator</option>
            </select>
          </div>
          <div className="col-12"><button className="btn btn-primary" type="submit">Create user</button></div>
        </form>
      </section>
      <section className="surface-card">
        <div className="surface-heading"><h3 className="h5">User directory</h3><input aria-label="Search users" className="form-control" placeholder="Search name or email" value={search} onChange={changeSearch} /></div>
        {editingId !== null && <form className="row g-3 border-bottom pb-3 mb-3" onSubmit={saveProfile}>
          <div className="col-12"><h4 className="h6 mb-0">Edit account #{editingId}</h4></div>
          {[["full_name", "Full name"], ["phone", "Phone"], ["district", "District"], ["state", "State"]].map(([name, label]) => (
            <div className="col-md-3" key={name}><label className="form-label" htmlFor={`edit-user-${name}`}>{label}</label><input id={`edit-user-${name}`} className="form-control" value={profileForm[name]} onChange={(event) => setProfileForm((current) => ({ ...current, [name]: event.target.value }))} required /></div>
          ))}
          <div className="col-12 d-flex gap-2"><button className="btn btn-primary btn-sm" type="submit">Save changes</button><button className="btn btn-outline-secondary btn-sm" type="button" onClick={() => { setEditingId(null); setProfileForm(blankProfile); }}>Cancel</button></div>
        </form>}
        {loading ? <p role="status">Loading users…</p> : users.length === 0 ? <p className="text-secondary mb-0">No matching users.</p> : (
          <div className="table-responsive"><table className="table align-middle"><thead><tr><th>Name</th><th>Email</th><th>Location</th><th>Role</th><th>Actions</th></tr></thead><tbody>
            {users.map((user) => <tr key={user.id}>
              <td>{user.full_name}</td><td>{user.email}</td><td>{user.district}, {user.state}</td>
              <td><select aria-label={`Role for ${user.full_name}`} className="form-select" value={user.role} onChange={(event) => changeRole(user, event.target.value)}><option value="user">User</option><option value="admin">Administrator</option></select></td>
              <td><div className="d-flex gap-2"><button className="btn btn-outline-primary btn-sm" type="button" onClick={() => startEditing(user)}>Edit</button><button className="btn btn-outline-danger btn-sm" type="button" onClick={() => removeUser(user)}>Delete</button></div></td>
            </tr>)}
          </tbody></table></div>
        )}
        {pagination && pagination.total_pages > 1 && <div className="d-flex align-items-center justify-content-between mt-3"><span>Page {pagination.page} of {pagination.total_pages} · {pagination.total_items} accounts</span><div className="d-flex gap-2"><button className="btn btn-outline-primary btn-sm" type="button" disabled={!pagination.has_previous || loading} onClick={() => setPage((current) => current - 1)}>Previous</button><button className="btn btn-outline-primary btn-sm" type="button" disabled={!pagination.has_next || loading} onClick={() => setPage((current) => current + 1)}>Next</button></div></div>}
      </section>
    </div>
  );
}
