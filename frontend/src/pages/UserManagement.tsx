import { useEffect, useState } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';

type ManagedUser = { username: string; role: string; is_active: boolean; device_ids: string[]; mfa_enabled: boolean };
type Device = { device_id: string; alias: string };

export default function UserManagement() {
  const { user } = useAuth();
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [username, setUsername] = useState('');
  const [role, setRole] = useState('viewer');
  const [grants, setGrants] = useState<string[]>([]);
  const [temporaryPassword, setTemporaryPassword] = useState('');
  const [mfaSecret, setMfaSecret] = useState('');
  const [mfaCode, setMfaCode] = useState('');
  const [error, setError] = useState('');
  const load = async () => {
    const [u, d] = await Promise.all([axios.get('/api/users', { withCredentials: true }), axios.get('/api/devices', { withCredentials: true })]);
    setUsers(u.data); setDevices(d.data);
  };
  useEffect(() => { load().catch(() => setError('Unable to load user management data.')); }, []);
  if (user?.role.toLowerCase() !== 'admin') return <div className="p-8">Administrator access required.</div>;
  const create = async () => {
    setError('');
    try { const result = await axios.post('/api/users', { username, role, device_ids: grants }, { withCredentials: true }); setTemporaryPassword(result.data.temporary_password); setUsername(''); await load(); }
    catch (e: any) { setError(e.response?.data?.detail || 'Could not create user.'); }
  };
  const update = async (target: ManagedUser, values: Partial<ManagedUser>) => {
    try { await axios.put(`/api/users/${encodeURIComponent(target.username)}`, { role: values.role || target.role, is_active: values.is_active ?? target.is_active, device_ids: values.device_ids || target.device_ids }, { withCredentials: true }); await load(); }
    catch (e: any) { setError(e.response?.data?.detail || 'Could not update user.'); }
  };
  const reset = async (target: ManagedUser) => {
    try { const result = await axios.post(`/api/users/${encodeURIComponent(target.username)}/reset-password`, {}, { withCredentials: true }); setTemporaryPassword(`${target.username}: ${result.data.temporary_password}`); await load(); }
    catch (e: any) { setError(e.response?.data?.detail || 'Could not reset password.'); }
  };
  const startMfa = async () => { try { const r = await axios.post('/api/auth/mfa/setup', {}, { withCredentials: true }); setMfaSecret(r.data.secret); } catch (e: any) { setError(e.response?.data?.detail || 'Could not start MFA setup.'); } };
  const enableMfa = async () => { try { await axios.post('/api/auth/mfa/enable', { code: mfaCode }, { withCredentials: true }); setMfaSecret(''); setMfaCode(''); await load(); } catch (e: any) { setError(e.response?.data?.detail || 'Could not enable MFA.'); } };
  return <main className="max-w-6xl mx-auto p-6 space-y-6">
    <h1 className="text-2xl font-bold text-slate-900">User management</h1>
    <p className="text-sm text-slate-600">Roles control actions; device assignments control asset visibility. New and reset passwords must be changed at first sign in.</p>
    {error && <p role="alert" className="rounded bg-red-50 p-3 text-red-700">{error}</p>}
    {temporaryPassword && <div className="rounded border border-amber-300 bg-amber-50 p-4">Show this temporary password once and deliver it securely: <code className="font-bold">{temporaryPassword}</code><button className="ml-3 underline" onClick={() => setTemporaryPassword('')}>Dismiss</button></div>}
    <section className="rounded-xl bg-white p-5 shadow space-y-4">
      <h2 className="font-semibold">Administrator MFA</h2>
      <p className="text-sm text-slate-600">Use an authenticator app. MFA is required at sign in after it is enabled.</p>
      {!mfaSecret ? <button className="rounded border px-3 py-2" onClick={startMfa}>Set up MFA</button> : <div className="space-y-2"><p>Add this secret to your authenticator app: <code className="font-bold">{mfaSecret}</code></p><div className="flex gap-2"><input className="border rounded px-3 py-2" placeholder="6 digit code" value={mfaCode} onChange={e => setMfaCode(e.target.value)} /><button className="rounded bg-blue-900 px-4 py-2 text-white" onClick={enableMfa}>Confirm and enable</button></div></div>}
    </section>
    <section className="rounded-xl bg-white p-5 shadow space-y-4">
      <h2 className="font-semibold">Create account</h2>
      <div className="flex flex-wrap gap-3"><input className="border rounded px-3 py-2" placeholder="Username" value={username} onChange={e => setUsername(e.target.value)} />
      <select className="border rounded px-3 py-2" value={role} onChange={e => setRole(e.target.value)}><option value="viewer">Viewer</option><option value="analyst">Analyst</option><option value="admin">Admin</option></select>
      <button className="rounded bg-blue-900 px-4 py-2 text-white" onClick={create} disabled={username.trim().length < 3}>Create</button></div>
      <div className="flex flex-wrap gap-4">{devices.map(d => <label key={d.device_id} className="text-sm"><input type="checkbox" checked={grants.includes(d.device_id)} onChange={e => setGrants(e.target.checked ? [...grants, d.device_id] : grants.filter(id => id !== d.device_id))} /> {d.alias || 'Device'} · {d.device_id.slice(0, 6)}…{d.device_id.slice(-6)}</label>)}</div>
    </section>
    <section className="rounded-xl bg-white shadow overflow-x-auto"><table className="w-full text-left text-sm"><thead className="bg-slate-100"><tr><th className="p-3">Username</th><th className="p-3">Role</th><th className="p-3">Allowed devices</th><th className="p-3">Status / MFA</th><th className="p-3">Actions</th></tr></thead><tbody>
      {users.map(u => <tr key={u.username} className="border-t"><td className="p-3 font-medium">{u.username}</td><td className="p-3"><select value={u.role.toLowerCase()} onChange={e => update(u, { role: e.target.value })} className="border rounded p-1"><option value="admin">Admin</option><option value="analyst">Analyst</option><option value="viewer">Viewer</option></select></td>
      <td className="p-3"><details><summary>{u.device_ids.length} assigned{u.role.toLowerCase() === 'admin' ? ' (all devices)' : ''}</summary><div className="grid gap-1 py-2">{devices.map(d => <label key={d.device_id}><input type="checkbox" checked={u.device_ids.includes(d.device_id)} onChange={e => update(u, { device_ids: e.target.checked ? [...u.device_ids, d.device_id] : u.device_ids.filter(id => id !== d.device_id) })} /> {d.alias || 'Device'} · {d.device_id.slice(0, 6)}…{d.device_id.slice(-6)}</label>)}</div></details></td>
      <td className="p-3">{u.is_active ? 'Active' : 'Disabled'}{u.mfa_enabled ? ' · MFA enabled' : ''}</td><td className="p-3 whitespace-nowrap"><button className="underline mr-3" onClick={() => update(u, { is_active: !u.is_active })}>{u.is_active ? 'Disable' : 'Enable'}</button><button className="underline" onClick={() => reset(u)}>Reset password</button></td></tr>)}
    </tbody></table></section>
  </main>;
}
