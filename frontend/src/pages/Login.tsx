import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../utils/api';

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const navigate = useNavigate();
  const { login } = useAuth();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);
    
    try {
      const response = await api.post('/api/auth/login', {
        username,
        password
      });
      
      const { access_token } = response.data;
      login(access_token);
      navigate('/');
    } catch (err: any) {
      if (err.response && err.response.status === 401) {
        setError('Invalid username or password');
      } else {
        setError('Connection error. Please ensure backend is running.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="relative min-h-screen flex items-center justify-center overflow-hidden">
      {/* Static Background Image */}
      <div className="static-bg" />

      {/* Decorative accent accents */}
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary via-primary-light to-primary z-20" />
      <div className="absolute top-1/4 left-0 w-64 h-64 bg-primary/8 rounded-full blur-3xl -ml-32 pointer-events-none" />
      <div className="absolute bottom-1/4 right-0 w-96 h-96 bg-primary/6 rounded-full blur-3xl -mr-48 pointer-events-none" />

      {/* Login Card — Liquid Glass */}
      <div className="relative z-10 industrial-card p-10 w-full max-w-md">
        <div className="flex flex-col items-center mb-10">
          <div className="flex items-center justify-center gap-6 mb-8 bg-white px-8 py-4 rounded-2xl shadow-[0_4px_20px_rgba(0,0,0,0.2)]">
            <img src="/Elicius_Logo.png" alt="Elicius" className="h-14 object-contain" />
            <div className="w-[1px] h-12 bg-gray-200" />
            <img src="/ledl.png" alt="LEDL" className="h-14 object-contain" />
          </div>
          <h1 className="text-3xl font-extrabold text-text-primary tracking-tight text-center">Elicius PDM App</h1>
          <p className="text-sm font-bold text-text-muted mt-2 text-center uppercase tracking-widest">
            Elicius Energy & LEDL
          </p>
        </div>

        <form onSubmit={handleLogin} className="space-y-6">
          {error && (
            <div className="bg-accent-red/10 text-accent-red text-sm font-bold p-3 rounded-xl border border-accent-red/20 text-center">
              {error}
            </div>
          )}
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-bold text-text-secondary mb-2 uppercase tracking-wide">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-5 py-3 rounded-xl glass-input text-text-primary font-medium transition-all"
                placeholder="admin"
                disabled={isSubmitting}
              />
            </div>
            
            <div>
              <label className="block text-sm font-bold text-text-secondary mb-2 uppercase tracking-wide">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-5 py-3 rounded-xl glass-input text-text-primary font-medium transition-all"
                placeholder="•••••"
                disabled={isSubmitting}
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className={`w-full bg-primary hover:bg-primary-light text-white font-bold py-4 rounded-xl transition-all shadow-lg shadow-primary/20 hover:shadow-primary/30 active:transform active:scale-[0.98] ${isSubmitting ? 'opacity-70 cursor-not-allowed' : ''}`}
          >
            {isSubmitting ? 'Authenticating...' : 'Access System'}
          </button>
        </form>

        <div className="mt-8 text-center text-xs text-text-muted font-medium">
          Confidential System Demo
        </div>
      </div>
    </div>
  );
};

export default Login;
