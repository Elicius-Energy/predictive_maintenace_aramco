import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity } from 'lucide-react';

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (username === 'admin' && password === 'admin') {
      sessionStorage.setItem('isAuthenticated', 'true');
      navigate('/');
    } else {
      setError('Invalid username or password');
    }
  };

  return (
    <div className="relative min-h-screen flex items-center justify-center bg-white overflow-hidden">
      {/* Real Image Watermark Background */}
      <div 
        className="absolute inset-0 z-0 opacity-[0.03] pointer-events-none"
        style={{
          backgroundImage: `url('/Elicius_Logo.png')`,
          backgroundRepeat: 'no-repeat',
          backgroundPosition: 'center center',
          backgroundSize: 'contain',
          transform: 'scale(0.8)'
        }}
      />

      {/* Decorative Purple/White Accents */}
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary to-purple-400 z-10" />
      <div className="absolute top-1/4 left-0 w-64 h-64 bg-primary/10 rounded-full blur-3xl -ml-32 pointer-events-none" />
      <div className="absolute bottom-1/4 right-0 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl -mr-48 pointer-events-none" />

      {/* Login Card */}
      <div className="relative z-10 bg-white p-10 rounded-3xl shadow-[0_8px_30px_rgb(0,0,0,0.12)] w-full max-w-md border border-purple-100">
        <div className="flex flex-col items-center mb-10">
          <div className="w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center mb-4">
            <Activity size={32} className="text-primary" />
          </div>
          <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight text-center">Elicius PDM App</h1>
          <p className="text-sm font-bold text-gray-400 mt-2 text-center uppercase tracking-widest">
            Elicius Energy PVT LTD
          </p>
        </div>

        <form onSubmit={handleLogin} className="space-y-6">
          {error && (
            <div className="bg-red-50 text-red-600 text-sm font-bold p-3 rounded-xl border border-red-100 text-center">
              {error}
            </div>
          )}
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-bold text-gray-700 mb-2 uppercase tracking-wide">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-5 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary/50 text-gray-900 font-medium transition-all"
                placeholder="admin"
              />
            </div>
            
            <div>
              <label className="block text-sm font-bold text-gray-700 mb-2 uppercase tracking-wide">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-5 py-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary/50 text-gray-900 font-medium transition-all"
                placeholder="•••••"
              />
            </div>
          </div>

          <button
            type="submit"
            className="w-full bg-primary hover:bg-indigo-600 text-white font-bold py-4 rounded-xl transition-all shadow-lg shadow-primary/20 hover:shadow-primary/40 active:transform active:scale-[0.98]"
          >
            Access System
          </button>
        </form>

        <div className="mt-8 text-center text-xs text-gray-400 font-medium">
          Confidential System Demo
        </div>
      </div>
    </div>
  );
};

export default Login;
