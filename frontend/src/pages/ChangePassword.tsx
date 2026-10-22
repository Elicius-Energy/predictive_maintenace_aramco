import { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export default function ChangePassword() {
  const [current, setCurrent] = useState(''); const [next, setNext] = useState(''); const [error, setError] = useState('');
  const navigate = useNavigate(); const { logout } = useAuth();
  const submit = async (e: React.FormEvent) => { e.preventDefault(); setError(''); try { await axios.post('/api/auth/password', { current_password: current, new_password: next }, { withCredentials: true }); await logout(); navigate('/login', { replace: true }); } catch (err: any) { setError(err.response?.data?.detail || 'Unable to change password.'); } };
  return <main className="min-h-screen grid place-items-center bg-slate-50 p-4"><form onSubmit={submit} className="w-full max-w-md space-y-4 rounded-xl bg-white p-7 shadow"><h1 className="text-xl font-bold">Choose a new password</h1><p className="text-sm text-slate-600">Your account requires a password change before you can continue. Use at least 12 characters.</p>{error && <p role="alert" className="text-red-700">{error}</p>}<input required autoComplete="current-password" type="password" className="w-full rounded border p-2" placeholder="Temporary password" value={current} onChange={e => setCurrent(e.target.value)} /><input required minLength={12} autoComplete="new-password" type="password" className="w-full rounded border p-2" placeholder="New password (12+ characters)" value={next} onChange={e => setNext(e.target.value)} /><button className="w-full rounded bg-blue-900 p-2 text-white">Change password</button></form></main>;
}
